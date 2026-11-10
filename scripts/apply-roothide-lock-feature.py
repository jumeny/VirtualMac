#!/usr/bin/env python3
"""Apply the maintained local lock-on-device-lock feature to the pinned Cupecups tree.

The RootHide build starts from nfzerox source and applies Cupecups' snapshot.
This overlay deliberately targets that exact post-port source and fails closed
when its expected structure changes.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-roothide-lock-feature.py SOURCE_DIR")

root = Path(sys.argv[1])
vm = root / "VirtualMac"
changed = []


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    count = content.count(old)
    if count != 1:
        raise SystemExit(
            f"RootHide lock overlay expected one anchor in {path.relative_to(root)}, "
            f"found {count}; update the overlay for this Cupecups source"
        )
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    changed.append(path.relative_to(root).as_posix())


replace_once(
    vm / "vz/host/VZAppSettings.h",
    'FOUNDATION_EXPORT NSString * const VZDebugLoggingKey;\n',
    'FOUNDATION_EXPORT NSString * const VZDebugLoggingKey;\n'
    'FOUNDATION_EXPORT NSString * const VZLockGuestWhenDeviceLocksKey;\n',
)

replace_once(
    vm / "vz/host/VZAppSettings.m",
    'NSString * const VZDebugLoggingKey = @"DebugLogging";\n',
    'NSString * const VZDebugLoggingKey = @"DebugLogging";\n'
    'NSString * const VZLockGuestWhenDeviceLocksKey = @"LockGuestWhenDeviceLocks";\n',
)

replace_once(
    vm / "vz/host/VZAppSettings.m",
    '        VZDebugLoggingKey: VZDebugLoggingModeOff,\n',
    '        VZDebugLoggingKey: VZDebugLoggingModeOff,\n'
    '        VZLockGuestWhenDeviceLocksKey: @NO,\n',
)

replace_once(
    vm / "vz/host/VZSettingsViewController.m",
    'return section == 0 ? 4 : section == 1 ? 6 : section == 2 ? 4 :',
    'return section == 0 ? 5 : section == 1 ? 6 : section == 2 ? 4 :',
)

replace_once(
    vm / "vz/host/VZSettingsViewController.m",
    '    } else if (indexPath.section == 0) {\n'
    '        cell.textLabel.text = VZSettingsFittingTitle(tableView,',
    '    } else if (indexPath.section == 0 && indexPath.row == 3) {\n'
    '        cell.textLabel.text = VZSettingsFittingTitle(tableView,',
)

replace_once(
    vm / "vz/host/VZSettingsViewController.m",
    '        cell.accessoryView = slider;\n'
    '        cell.selectionStyle = UITableViewCellSelectionStyleNone;\n'
    '    } else if (indexPath.section == 1 && indexPath.row < 5) {',
    '        cell.accessoryView = slider;\n'
    '        cell.selectionStyle = UITableViewCellSelectionStyleNone;\n'
    '    } else if (indexPath.section == 0 && indexPath.row == 4) {\n'
    '        cell.textLabel.text = VZL(@"Lock macOS when iPad locks");\n'
    '        UISwitch *toggle = [[[UISwitch alloc] init] autorelease];\n'
    '        toggle.tag = 200;\n'
    '        toggle.on = [settings boolForKey:VZLockGuestWhenDeviceLocksKey];\n'
    '        [toggle addTarget:self action:@selector(inputToggleChanged:)\n'
    '            forControlEvents:UIControlEventValueChanged];\n'
    '        cell.accessoryView = toggle;\n'
    '        cell.selectionStyle = UITableViewCellSelectionStyleNone;\n'
    '    } else if (indexPath.section == 1 && indexPath.row < 5) {',
)

replace_once(
    vm / "vz/host/VZSettingsViewController.m",
    '    NSString *key = sender.tag >= 100 ? compatibilityKeys[sender.tag - 100]\n'
    '        : sender.tag >= 30 ? iPadOSKeys[sender.tag - 30]\n'
    '        : sender.tag == 20 ? VZKeyboardShortcutCaptureKey\n'
    '                           : touchKeys[sender.tag];',
    '    NSString *key = sender.tag == 200 ? VZLockGuestWhenDeviceLocksKey\n'
    '        : sender.tag >= 100 ? compatibilityKeys[sender.tag - 100]\n'
    '        : sender.tag >= 30 ? iPadOSKeys[sender.tag - 30]\n'
    '        : sender.tag == 20 ? VZKeyboardShortcutCaptureKey\n'
    '                           : touchKeys[sender.tag];',
)

replace_once(
    vm / "vz/host/VirtualMacApp.m",
    '- (void)applicationWillResignActive:(UIApplication *)application\n',
    '- (void)applicationProtectedDataWillBecomeUnavailable:(UIApplication *)application\n'
    '{\n'
    '    (void)application;\n'
    '    if (![VZAppSettings.sharedSettings\n'
    '          boolForKey:VZLockGuestWhenDeviceLocksKey])\n'
    '        return;\n'
    '    if (!gVirtualMachine || !gKeyboard) {\n'
    '        printf("[VirtualMac] device locked; no active guest keyboard to lock\\\\n");\n'
    '        return;\n'
    '    }\n'
    '\n'
    '    // macOS Control-Command-Q locks the guest session. Send the shortcut\n'
    '    // directly through the existing virtual keyboard before iPadOS\n'
    '    // finishes making protected data unavailable and suspends this app.\n'
    '    printf("[VirtualMac] device protected data becoming unavailable; locking guest\\\\n");\n'
    '    sendKey((UIKeyboardHIDUsage)0xe0, YES); // Left Control\n'
    '    sendKey((UIKeyboardHIDUsage)0xe3, YES); // Left Command\n'
    '    sendKey((UIKeyboardHIDUsage)0x14, YES); // Q\n'
    '    sendKey((UIKeyboardHIDUsage)0x14, NO);\n'
    '    sendKey((UIKeyboardHIDUsage)0xe3, NO);\n'
    '    sendKey((UIKeyboardHIDUsage)0xe0, NO);\n'
    '}\n'
    '\n'
    '- (void)applicationWillResignActive:(UIApplication *)application\n',
)

localization = vm / "resources/Localizations/en.lproj/Localizable.strings"
content = localization.read_text(encoding="utf-8")
for entry in (
    '"Lock macOS when iPad locks" = "Lock macOS when iPad locks";',
    '"Locks the macOS guest when iPadOS is about to make protected data unavailable. A device passcode is required." = "Locks the macOS guest when iPadOS is about to make protected data unavailable. A device passcode is required.";'
):
    if entry not in content:
        content += "\n" + entry
        changed.append(localization.relative_to(root).as_posix())
localization.write_text(content.rstrip() + "\n", encoding="utf-8")

# Explain the passcode requirement in the General section footer.
settings = vm / "vz/host/VZSettingsViewController.m"
replace_once(
    settings,
    '    if (section == 4)\n        return VZStorageFooterText();\n',
    '    if (section == 0)\n'
    '        return VZL(@"Locks the macOS guest when iPadOS is about to make protected data unavailable. A device passcode is required.");\n'
    '    if (section == 4)\n'
    '        return VZStorageFooterText();\n',
)

print("Applied lock-on-device-lock overlay to:")
for path in sorted(set(changed)):
    print(f"  {path}")
