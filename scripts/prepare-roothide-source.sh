#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

UPSTREAM_REPO="https://github.com/nfzerox/VirtualMacOniPad.git"
CUP_REPO="https://github.com/cupecups/VirtualMacOniPad-Roothide.git"
CUP_COMMIT="ae364321cd47553342d4d8e69c011eabc5be7e45"
BASELINE_REF="1.2.3"
WORK="${RUNNER_TEMP:-${TMPDIR:-/tmp}}/virtualmac-roothide-port"
SOURCE="$WORK/source"
PATCH_REPO="$WORK/patch-repo"
PATCH_FILE="$WORK/cupecups-port.patch"
CUP_CLONE="$WORK/cupecups"
UPSTREAM_CLONE="$WORK/upstream"
UPSTREAM_REF="${UPSTREAM_REF:-}"
SOURCE_ZIP_URL="${SOURCE_ZIP_URL:-}"

die() { echo "::error::$*" >&2; exit 1; }
need() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }
for tool in git tar rsync curl shasum python3; do need "$tool"; done

[[ -n "$UPSTREAM_REF" || -n "$SOURCE_ZIP_URL" ]] || die "set UPSTREAM_REF or SOURCE_ZIP_URL"
ZIP_REF=""
if [[ -n "$SOURCE_ZIP_URL" ]]; then
    case "$SOURCE_ZIP_URL" in
        https://github.com/nfzerox/VirtualMacOniPad/archive/refs/heads/*.zip)
            ZIP_REF="refs/heads/${SOURCE_ZIP_URL##*/refs/heads/}"
            ZIP_REF="${ZIP_REF%.zip}"
            ;;
        https://github.com/nfzerox/VirtualMacOniPad/archive/refs/tags/*.zip)
            ZIP_REF="refs/tags/${SOURCE_ZIP_URL##*/refs/tags/}"
            ZIP_REF="${ZIP_REF%.zip}"
            ;;
        https://github.com/nfzerox/VirtualMacOniPad/archive/*.zip)
            ZIP_REF="${SOURCE_ZIP_URL##*/archive/}"
            ZIP_REF="${ZIP_REF%.zip}"
            ;;
        https://api.github.com/repos/nfzerox/VirtualMacOniPad/zipball/*)
            ZIP_REF="${SOURCE_ZIP_URL##*/zipball/}"
            ;;
        *) die "ZIP URL must be an archive from nfzerox/VirtualMacOniPad" ;;
    esac
fi

rm -rf "$WORK"
mkdir -p "$WORK" "$SOURCE" "$PATCH_REPO" "$WORK/base-export" "$WORK/cup-export"

echo "Fetching the Cupecups RootHide snapshot..."
git clone --quiet --no-checkout "$CUP_REPO" "$CUP_CLONE"
git -C "$CUP_CLONE" checkout --quiet --detach "$CUP_COMMIT"

echo "Fetching the 1.2.3 upstream baseline used by the Cupecups port..."
git clone --quiet --no-checkout "$UPSTREAM_REPO" "$UPSTREAM_CLONE"
git -C "$UPSTREAM_CLONE" fetch --quiet --depth=1 origin "refs/tags/$BASELINE_REF:refs/tags/$BASELINE_REF"
git -C "$UPSTREAM_CLONE" archive "$BASELINE_REF" | tar -xf - -C "$WORK/base-export"
git -C "$CUP_CLONE" archive "$CUP_COMMIT" | tar -xf - -C "$WORK/cup-export"

# Build a reproducible binary-capable patch from the upstream 1.2.3 tree to
# the pinned Cupecups snapshot. This keeps the patch independent of checkout
# paths and lets git apply reject upstream conflicts instead of guessing.
rsync -a --delete "$WORK/base-export/" "$PATCH_REPO/"
git -C "$PATCH_REPO" init --quiet
git -C "$PATCH_REPO" config user.name "RootHide Build"
git -C "$PATCH_REPO" config user.email "actions@users.noreply.github.com"
git -C "$PATCH_REPO" add -A
git -C "$PATCH_REPO" commit --quiet -m "nfzerox 1.2.3 baseline"
rsync -a --delete --exclude=.git "$WORK/cup-export/" "$PATCH_REPO/"
git -C "$PATCH_REPO" add -A
git -C "$PATCH_REPO" diff --cached --binary --no-renames HEAD > "$PATCH_FILE"
[[ -s "$PATCH_FILE" ]] || die "generated Cupecups port patch is empty"

if [[ -n "$SOURCE_ZIP_URL" ]]; then
    echo "Resolving the supplied official nfzerox archive URL through Git..."
    git -C "$UPSTREAM_CLONE" fetch --quiet --depth=1 origin "$ZIP_REF"
    git -C "$UPSTREAM_CLONE" checkout --quiet --detach FETCH_HEAD
    UPSTREAM_COMMIT="$(git -C "$UPSTREAM_CLONE" rev-parse HEAD)"
    git -C "$UPSTREAM_CLONE" archive HEAD | tar -xf - -C "$SOURCE"
    SOURCE_SHA256=""
    UPSTREAM_REF="$ZIP_REF"
else
    echo "Checking out nfzerox ref: $UPSTREAM_REF"
    git -C "$UPSTREAM_CLONE" fetch --quiet origin "$UPSTREAM_REF"
    git -C "$UPSTREAM_CLONE" checkout --quiet --detach FETCH_HEAD
    UPSTREAM_COMMIT="$(git -C "$UPSTREAM_CLONE" rev-parse HEAD)"
    git -C "$UPSTREAM_CLONE" archive HEAD | tar -xf - -C "$SOURCE"
    SOURCE_SHA256=""
fi

[[ -f "$SOURCE/VirtualMac/scripts/build-ipad-deb.sh" ]] || die "source is not a VirtualMacOniPad tree"
[[ -f "$SOURCE/VirtualMac/scripts/lib/common.sh" ]] || die "source is missing the expected build system"

# Keep the exact 1.2.3 source as a tag in the temporary build repository.
# Cupecups regression tests compare files against this baseline tag.
mkdir -p "$WORK/upstream-export"
rsync -a --delete "$SOURCE/" "$WORK/upstream-export/"
rm -rf "$SOURCE"
mkdir -p "$SOURCE"
rsync -a --delete "$WORK/base-export/" "$SOURCE/"
git -C "$SOURCE" init --quiet
git -C "$SOURCE" config user.name "RootHide Build"
git -C "$SOURCE" config user.email "actions@users.noreply.github.com"
git -C "$SOURCE" add -A
git -C "$SOURCE" commit --quiet -m "nfzerox 1.2.3 baseline"
git -C "$SOURCE" tag "$BASELINE_REF"
rsync -a --delete --exclude=.git "$WORK/upstream-export/" "$SOURCE/"
git -C "$SOURCE" add -A
git -C "$SOURCE" commit --quiet -m "nfzerox source $UPSTREAM_COMMIT"

echo "Checking whether the pinned Cupecups port applies cleanly..."
git -C "$SOURCE" apply --check -p1 "$PATCH_FILE" ||
    die "Cupecups port does not apply cleanly to this upstream source. Update the port before building this version."
git -C "$SOURCE" apply -p1 "$PATCH_FILE"

echo "Applying the maintained lock-on-device-lock feature..."
python3 "$SCRIPT_DIR/apply-roothide-lock-feature.py" "$SOURCE"

git -C "$SOURCE" add -A
git -C "$SOURCE" commit --quiet -m "RootHide port for $UPSTREAM_COMMIT"

cat > "$SOURCE/VirtualMac/roothide-build-provenance.txt" <<EOF
upstream_repository=https://github.com/nfzerox/VirtualMacOniPad
upstream_ref=$UPSTREAM_REF
upstream_commit=$UPSTREAM_COMMIT
upstream_zip_sha256=$SOURCE_SHA256
cupecups_repository=https://github.com/cupecups/VirtualMacOniPad-Roothide
cupecups_commit=$CUP_COMMIT
port_baseline=$BASELINE_REF
EOF

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
        echo "source_dir=$SOURCE"
        echo "upstream_ref=$UPSTREAM_REF"
        echo "upstream_commit=$UPSTREAM_COMMIT"
        echo "source_sha256=$SOURCE_SHA256"
        echo "port_commit=$CUP_COMMIT"
    } >> "$GITHUB_OUTPUT"
fi

echo "Prepared RootHide source: $SOURCE"
echo "Upstream provenance: $UPSTREAM_COMMIT"
