#!/usr/bin/env python3
"""Apply the opt-in microphone lifecycle fix to a prepared Virtual Mac source tree."""

from pathlib import Path
import re
import sys


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one exact match, found {count}")
    return text.replace(old, new, 1)


def replace_regex_once(text: str, pattern: str, replacement: str, label: str) -> str:
    updated, count = re.subn(pattern, lambda _match: replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"{label}: expected one source block, found {count}")
    return updated


def patch_app(path: Path) -> None:
    text = path.read_text()

    text = replace_once(
        text,
        "static BOOL gVMJetsamProtectionActive;",
        "static BOOL gVMJetsamProtectionActive;\nstatic BOOL gAudioSessionActive;",
        "audio-session state declaration",
    )

    microphone_functions = r'''static BOOL activateAudioSession(AVAudioSessionCategory category,
                                AVAudioSessionCategoryOptions options,
                                const char *purpose) {
    AVAudioSession *session = AVAudioSession.sharedInstance;
    NSError *categoryError = nil;
    BOOL categoryOK = [session setCategory:category
                                      mode:AVAudioSessionModeDefault
                                   options:options
                                     error:&categoryError];
    NSError *activeError = nil;
    BOOL activeOK = categoryOK &&
        [session setActive:YES error:&activeError];
    gAudioSessionActive = activeOK;
    NSError *reportedError = activeError ?: categoryError;
    printf("[VirtualMac] audio session purpose=%s category=%s configured=%d active=%d error=%s\n",
           purpose, category.UTF8String, categoryOK, activeOK,
           reportedError ? reportedError.localizedDescription.UTF8String : "none");
    return activeOK;
}

static BOOL activatePlaybackAudioSession(void) {
    return activateAudioSession(
        AVAudioSessionCategoryPlayback,
        AVAudioSessionCategoryOptionMixWithOthers,
        "playback-only");
}

static BOOL activateMicrophoneAudioSession(void) {
    AVAudioSessionCategoryOptions sessionOptions =
        AVAudioSessionCategoryOptionMixWithOthers |
        AVAudioSessionCategoryOptionDefaultToSpeaker |
        VZAVSessionOptionAllowBluetoothHFP;
    return activateAudioSession(
        AVAudioSessionCategoryPlayAndRecord, sessionOptions, "microphone");
}

static void requestMicrophoneAccess(void (^continuation)(BOOL granted)) {
    AVAudioSession *session = AVAudioSession.sharedInstance;
    AVAudioSessionRecordPermission permission = session.recordPermission;
    printf("[VirtualMac] microphone permission before request=%lu\n",
           (unsigned long)permission);

    if (permission == AVAudioSessionRecordPermissionDenied) {
        printf("[VirtualMac] microphone permission denied; input disabled for this boot\n");
        continuation(NO);
        return;
    }
    if (permission == AVAudioSessionRecordPermissionGranted) {
        continuation(activateMicrophoneAudioSession());
        return;
    }

    // Request permission only when a VM configuration explicitly enables
    // microphone input. Playback-only VMs never enter this code path.
    __block BOOL continued = NO;
    void (^finish)(BOOL, const char *) = ^(BOOL granted, const char *reason) {
        dispatch_async(dispatch_get_main_queue(), ^{
            if (continued)
                return;
            continued = YES;
            printf("[VirtualMac] microphone permission granted=%d via=%s\n",
                   granted, reason);
            BOOL active = granted && activateMicrophoneAudioSession();
            continuation(active);
        });
    };
    [session requestRecordPermission:^(BOOL granted) {
        finish(granted, "TCC callback");
    }];
    // Some platform-installed builds may not deliver the TCC callback.
    // Never make VM startup wait indefinitely.
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, 5 * NSEC_PER_SEC),
                   dispatch_get_main_queue(), ^{
        finish(NO, "timeout");
    });
}

static void prepareAudioSessionForVM(
    NSDictionary *options, void (^continuation)(NSDictionary *)) {
    BOOL inputEnabled = [options[@"AudioInputEnabled"] boolValue];
    BOOL outputEnabled = [options[@"AudioOutputEnabled"] boolValue];

    if (inputEnabled) {
        requestMicrophoneAccess(^(BOOL granted) {
            if (granted) {
                continuation(options);
                return;
            }
            NSMutableDictionary *playbackOnly =
                [NSMutableDictionary dictionaryWithDictionary:options];
            playbackOnly[@"AudioInputEnabled"] = @NO;
            printf("[VirtualMac] continuing without microphone input\n");
            if (outputEnabled)
                activatePlaybackAudioSession();
            continuation(playbackOnly);
        });
        return;
    }

    // YouTube and other guest audio playback need an output-only session,
    // not PlayAndRecord. This category does not open the host microphone.
    if (outputEnabled)
        activatePlaybackAudioSession();
    continuation(options);
}

static void deactivateAudioSession(void) {
    if (!gAudioSessionActive)
        return;
    NSError *error = nil;
    BOOL deactivated = [AVAudioSession.sharedInstance
        setActive:NO error:&error];
    printf("[VirtualMac] audio session deactivated=%d error=%s\n",
           deactivated,
           error ? error.localizedDescription.UTF8String : "none");
    // AVAudioSession can report a busy status while still transitioning
    // inactive; do not retain a stale active flag across VM shutdown.
    gAudioSessionActive = NO;
}'''

    text = replace_regex_once(
        text,
        r"static void requestMicrophoneAccess\(dispatch_block_t continuation\) \{.*?\n\}\n(?=\nstatic void configureNetwork)",
        microphone_functions + "\n",
        "microphone/audio-session lifecycle",
    )

    text = replace_once(
        text,
        "requestMicrophoneAccess(^{",
        "dispatch_async(dispatch_get_main_queue(), ^{",
        "startup microphone prompt removal",
    )

    start_function = r'''static void startVirtualMachineWithRuntimeOptions(
    UIView *container, id delegate, NSString *bundlePath,
    NSDictionary *runtimeOptions) {
    // Ventura's VZ startup performs synchronous XPC and device construction.
    // On iPadOS 14, doing that from a tap blocks UIKit long enough to trip the
    // 10-second scene-update watchdog. Keep iPadOS 15/16 on their proven path.
    if (NSProcessInfo.processInfo.operatingSystemVersion.majorVersion == 14 &&
        pthread_main_np()) {
        VZStartContext *context = calloc(1, sizeof(*context));
        context->container = [container retain];
        context->delegate = [delegate retain];
        context->bundlePath = [bundlePath copy];
        context->options = [runtimeOptions copy];
        dispatch_async_f(
            dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), context,
            startVirtualMachineOnBackgroundQueue);
        return;
    }
    startVirtualMachineWorker(container, delegate, bundlePath, runtimeOptions);
}

static void startVirtualMachine(UIView *container, id delegate,
                                NSString *bundlePath,
                                NSDictionary *options) {
    NSDictionary *runtimeOptions = runtimeDisplayOptions(options, container);
    // Configure audio only for the selected VM. Playback uses a playback-only
    // session; microphone capture requires an explicit VM setting and TCC grant.
    dispatch_async(dispatch_get_main_queue(), ^{
        prepareAudioSessionForVM(runtimeOptions, ^(NSDictionary *preparedOptions) {
            startVirtualMachineWithRuntimeOptions(
                container, delegate, bundlePath, preparedOptions);
        });
    });
}'''

    text = replace_regex_once(
        text,
        r"static void startVirtualMachine\(UIView \*container, id delegate,\s*NSString \*bundlePath,\s*NSDictionary \*options\) \{.*?\n\}\n(?=\n// ─── External Display)",
        start_function + "\n",
        "VM startup audio-session gating",
    )

    text = replace_once(
        text,
        "- (void)finishVMAndShowLibraryWithError:(NSError *)error\n{\n    setVMJetsamProtection(NO);",
        "- (void)finishVMAndShowLibraryWithError:(NSError *)error\n{\n    deactivateAudioSession();\n    setVMJetsamProtection(NO);",
        "VM-stop audio-session deactivation",
    )

    path.write_text(text)


def patch_library(path: Path) -> None:
    text = path.read_text()
    text = replace_once(
        text,
        'static NSString * const VZAudioInputEnabledKey = @"AudioInputEnabled";',
        'static NSString * const VZAudioInputEnabledKey = @"AudioInputEnabled";\nstatic NSString * const VZAudioInputConfiguredKey = @"AudioInputConfigured";',
        "microphone opt-in marker",
    )
    text = replace_once(
        text,
        "        VZAudioOutputEnabledKey: @YES,\n        VZAudioInputEnabledKey: @YES,",
        "        VZAudioOutputEnabledKey: @YES,\n        VZAudioInputEnabledKey: @NO,\n        VZAudioInputConfiguredKey: @NO,",
        "microphone-off default",
    )
    text = replace_once(
        text,
        "    if ([saved isKindOfClass:NSDictionary.class])\n        [options addEntriesFromDictionary:saved];",
        "    if ([saved isKindOfClass:NSDictionary.class])\n        [options addEntriesFromDictionary:saved];\n    // Older manifests inherited microphone-on as a default. Treat those as\n    // legacy defaults, not as a deliberate permission to capture audio.\n    if (![saved[VZAudioInputConfiguredKey] boolValue]) {\n        options[VZAudioInputEnabledKey] = @NO;\n        options[VZAudioInputConfiguredKey] = @NO;\n    }",
        "legacy VM microphone migration",
    )
    text = replace_once(
        text,
        "    self.options[keys[sender.tag]] = @(sender.on);",
        "    if (sender.tag == 1)\n        self.options[VZAudioInputConfiguredKey] = @YES;\n    self.options[keys[sender.tag]] = @(sender.on);",
        "explicit microphone setting persistence",
    )
    path.write_text(text)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: apply-microphone-audio-policy.py VirtualMacApp.m VZVMLibraryViewController.m"
        )
    app_path, library_path = map(Path, sys.argv[1:])
    if not app_path.is_file() or not library_path.is_file():
        raise SystemExit("microphone policy patch: expected host source files are missing")
    patch_app(app_path)
    patch_library(library_path)
    print("Applied opt-in microphone policy and playback-only audio session.")


if __name__ == "__main__":
    main()
