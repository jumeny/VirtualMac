#!/usr/bin/env python3
"""Apply the optional guest-lock feature to the pinned Cupecups RootHide tree.

This remains an opt-in build overlay: the normal RootHide workflow and source
tree are not modified. The guest-lock switch is the first row in Input, with
no explanatory footer text.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: apply-roothide-lock-feature.py SOURCE_DIR")

root = Path(sys.argv[1])
vm = root / "VirtualMac"


def replace_once(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    count = content.count(old)
    if count != 1:
        raise SystemExit(
            f"Guest-lock overlay expected one anchor in {path.relative_to(root)}, "
            f"found {count}; update the overlay for this Cupecups source"
        )
    path.write_text(content.replace(old, new, 1), encoding="utf-8")


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
    'return section == 0 ? 4 : section == 1 ? 6 : section == 2 ? 5 :',
)

replace_once(
    vm / "vz/host/VZSettingsViewController.m",
    '    } else if (indexPath.section == 2 && indexPath.row == 0) {\n'
    '        cell.textLabel.text = VZL(@"Mac Keyboard Shortcuts");\n'
    '        UISwitch *toggle = [[[UISwitch alloc] init] autorelease];\n'
    '        toggle.tag = 20;\n'
    '        toggle.on = [settings boolForKey:VZKeyboardShortcutCaptureKey];\n'
    '        [toggle addTarget:self action:@selector(inputToggleChanged:)\n'
    '            forControlEvents:UIControlEventValueChanged];\n'
    '        cell.accessoryView = toggle;\n'
    '        cell.selectionStyle = UITableViewCellSelectionStyleNone;\n'
    '    } else if (indexPath.section == 2) {',
    '    } else if (indexPath.section == 2 && indexPath.row == 0) {\n'
    '        cell.textLabel.text = VZL(@"Lock macOS when iPad locks");\n'
    '        UISwitch *toggle = [[[UISwitch alloc] init] autorelease];\n'
    '        toggle.tag = 200;\n'
    '        toggle.on = [settings boolForKey:VZLockGuestWhenDeviceLocksKey];\n'
    '        [toggle addTarget:self action:@selector(inputToggleChanged:)\n'
    '            forControlEvents:UIControlEventValueChanged];\n'
    '        cell.accessoryView = toggle;\n'
    '        cell.selectionStyle = UITableViewCellSelectionStyleNone;\n'
    '    } else if (indexPath.section == 2 && indexPath.row == 1) {\n'
    '        cell.textLabel.text = VZL(@"Mac Keyboard Shortcuts");\n'
    '        UISwitch *toggle = [[[UISwitch alloc] init] autorelease];\n'
    '        toggle.tag = 20;\n'
    '        toggle.on = [settings boolForKey:VZKeyboardShortcutCaptureKey];\n'
    '        [toggle addTarget:self action:@selector(inputToggleChanged:)\n'
    '            forControlEvents:UIControlEventValueChanged];\n'
    '        cell.accessoryView = toggle;\n'
    '        cell.selectionStyle = UITableViewCellSelectionStyleNone;\n'
    '    } else if (indexPath.section == 2) {',
)

replace_once(
    vm / "vz/host/VZSettingsViewController.m",
    '        cell.textLabel.text = titles[indexPath.row - 1];\n'
    '        UISwitch *toggle = [[[UISwitch alloc] init] autorelease];\n'
    '        toggle.tag = 30 + indexPath.row - 1;\n'
    '        toggle.on = [settings boolForKey:keys[indexPath.row - 1]];',
    '        cell.textLabel.text = titles[indexPath.row - 2];\n'
    '        UISwitch *toggle = [[[UISwitch alloc] init] autorelease];\n'
    '        toggle.tag = 30 + indexPath.row - 2;\n'
    '        toggle.on = [settings boolForKey:keys[indexPath.row - 2]];',
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
    '    // Control-Command-Q locks the active macOS guest session.\n'
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
label = '"Lock macOS when iPad locks" = "Lock macOS when iPad locks";'
if label not in content:
    content = content.rstrip() + "\n" + label + "\n"
localization.write_text(content, encoding="utf-8")

# Remove the old explanatory footer if a source snapshot already contains it.
settings = vm / "vz/host/VZSettingsViewController.m"
settings_text = settings.read_text(encoding="utf-8")
obsolete_footer = (
    '        return VZL(@"Locks the macOS guest when iPadOS is about to make '
    'protected data unavailable. A device passcode is required.");\n'
)
if obsolete_footer in settings_text:
    settings.write_text(settings_text.replace(obsolete_footer, "", 1),
                        encoding="utf-8")

print("Applied guest-lock overlay: first row of Input; no explanation footer.")
