#!/usr/bin/env python3
"""Regression checks for Virtual Mac's automatic microphone passthrough."""

import os
from pathlib import Path

root = Path(os.environ.get("SOURCE_DIR", "."))
app_path = root / "VirtualMac" / "vz" / "host" / "VirtualMacApp.m"
library_path = root / "VirtualMac" / "vz" / "host" / "VZVMLibraryViewController.m"
app = app_path.read_text()
library = library_path.read_text()

checks = {
    "playback-only AVAudioSession category": "AVAudioSessionCategoryPlayback" in app,
    "microphone category remains available for input": "AVAudioSessionCategoryPlayAndRecord" in app,
    "system microphone permission request is preserved": (
        "requestRecordPermission:" in app
        and "NSMicrophoneUsageDescription" in (
            root / "VirtualMac" / "vz" / "host" / "VirtualMac-Info.plist"
        ).read_text()
    ),
    "microphone permission is requested by the existing system flow": (
        app.count("requestMicrophoneAccess(") == 2
        and "requestMicrophoneAccess(^{" not in app
    ),
    "audio session deactivates when VM stops": "deactivateAudioSession();" in app,
    "VM startup prepares audio from selected VM options": (
        "prepareAudioSessionForVM(runtimeOptions" in app
        and 'BOOL inputEnabled = [options[@"AudioInputEnabled"] boolValue];' in app
    ),
    "output and microphone use separate virtio sound devices": (
        'setObj(outputDevice, "setStreams:", @[output]);' in app
        and 'setObj(inputDevice, "setStreams:", @[input]);' in app
        and '"setAudioDevices:", audioDevices' in app
    ),
    "new VM microphone input remains enabled by default": (
        "VZAudioInputEnabledKey: @YES" in library
        and "VZAudioInputConfiguredKey: @NO" in library
    ),
    "legacy VM settings preserve the microphone default": (
        "if (![saved[VZAudioInputConfiguredKey] boolValue])" in library
        and "options[VZAudioInputEnabledKey] = @YES;" in library
    ),
    "user microphone toggle is remembered explicitly": (
        "self.options[VZAudioInputConfiguredKey] = @YES;" in library
    ),
}

failed = [name for name, passed in checks.items() if not passed]
for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'}: {name}")
if failed:
    raise SystemExit("microphone policy regression checks failed: " + ", ".join(failed))
