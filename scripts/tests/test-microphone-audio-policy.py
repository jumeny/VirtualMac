#!/usr/bin/env python3
"""Regression checks for Virtual Mac's opt-in microphone policy."""

import os
from pathlib import Path

root = Path(os.environ.get("SOURCE_DIR", "."))
app_path = root / "VirtualMac" / "vz" / "host" / "VirtualMacApp.m"
library_path = root / "VirtualMac" / "vz" / "host" / "VZVMLibraryViewController.m"
app = app_path.read_text()
library = library_path.read_text()

checks = {
    "playback-only AVAudioSession category": "AVAudioSessionCategoryPlayback" in app,
    "microphone category remains opt-in": "AVAudioSessionCategoryPlayAndRecord" in app,
    "microphone permission is requested only in VM audio preparation": (
        app.count("requestMicrophoneAccess(") == 2
        and "requestMicrophoneAccess(^{" not in app
    ),
    "VM startup prepares audio from selected VM options": (
        "prepareAudioSessionForVM(runtimeOptions" in app
        and 'BOOL inputEnabled = [options[@"AudioInputEnabled"] boolValue];' in app
    ),
    "audio session deactivates when VM stops": (
        "deactivateAudioSession();" in app
    ),
    "new VM microphone input defaults off": (
        "VZAudioInputEnabledKey: @NO" in library
        and "VZAudioInputConfiguredKey: @NO" in library
    ),
    "legacy VM microphone-on defaults are migrated off": (
        "if (![saved[VZAudioInputConfiguredKey] boolValue])" in library
        and "options[VZAudioInputEnabledKey] = @NO;" in library
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
