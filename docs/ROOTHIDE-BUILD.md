# RootHide build workflow

The RootHide build workflow and its source-preparation helper are maintained on the default `main` branch.

## Keep this fork updated

Use GitHub's built-in fork sync instead of a scheduled sync workflow:

1. Open the [jumeny/macos repository](https://github.com/jumeny/macos).
2. On the Code page, select **Sync fork**.
3. Review the upstream commits and select **Update branch**.

This updates the fork's default `main` branch from `nfzerox/VirtualMacOniPad`. GitHub will prompt for conflict resolution if upstream changes overlap with local changes. There is no scheduled mirror workflow or `upstream-sync` branch.

The build workflow now checks out its helper from `main`. When a build is started, the helper separately fetches the selected upstream tag, branch, commit, or approved ZIP and applies the pinned Cupecups port to that fresh source tree. This keeps upstream source updates separate from the RootHide port overlay. GitHub's Sync fork control updates the default branch; it does not update unrelated topic branches.

## RootHide port model

- The RootHide port is generated from the pinned Cupecups snapshot (`ae364321cd47553342d4d8e69c011eabc5be7e45`) relative to nfzerox tag `1.2.3`.
- A selected upstream tag, commit, or approved nfzerox ZIP is accepted only if that port applies without conflicts.
- The preparation script uses `git apply --check` before applying anything. If nfzerox has changed a required area, the job stops and asks for a port refresh rather than publishing an unverified package.

## Manual build

Use **Actions → Build RootHide package** on the default branch. Supply either an upstream ref (for example `1.2.3`, `1.2.4`, or a commit SHA) or a ZIP URL hosted by the official nfzerox repository. Choose artifact-only first; choose publish only after reviewing the result.

The GitHub Actions runner is macOS because Cupecups' RootHide builder requires Xcode/iOS SDK tooling. The workflow downloads the official nfzerox `1.2.3` `.deb` as the runtime base and verifies its SHA-256 (`435ce1dc76b9e18b1547c77b84e2cf33ffe40a16be63e366f181d14709a41aa0`) before invoking `scripts/build-roothide-deb.sh`. This is deliberate: Cupecups' builder expects that known package layout and its prebuilt Apple runtime payload. Building a fresh standard `.deb` from source is a separate process that requires large restore IPSWs and the `prepare-inputs.sh` toolchain; the RootHide workflow does not attempt that unrelated full-source build.

The `upstream_ref` input selects the nfzerox source tree to which the pinned Cupecups source port is applied. It does **not** change the pinned `1.2.3` binary runtime base. Moving that runtime base to a newer release requires checking its package layout and updating the Cupecups builder assumptions and expected digest.

When publishing a release, the workflow uses nfzerox's GitHub Release description as the changelog for a matching tag. For branches or commits without published release notes, it checks for a changelog file at the exact upstream commit and then falls back to commit subjects since the latest nfzerox release. The RootHide release attaches only the `.deb`; it does not attach a provenance text file or a separate SHA-256 file. The Actions artifact includes the `.deb` and the RootHide build log.
