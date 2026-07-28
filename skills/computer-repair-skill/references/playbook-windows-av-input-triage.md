---
name: windows-av-input-triage
description: Troubleshoot Windows camera, microphone, headset, and speaker failures across hardware, permissions, drivers, and apps
platform: windows
category: windows-repair-boot-hardware
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Windows Audio and Video Input Triage

## When to activate

Use when a camera, microphone, headset, speaker or meeting application cannot see, open or select an input/output device.

## Quick check

Record the exact device, whether it is built in, wired, Bluetooth or virtual, the affected application, the Windows build, current default input/output, and whether the issue began after an update or vendor utility change. Do not record private audio/video beyond a short local test needed to establish function.

## Standard diagnostic path

### 1. Check the physical layer

Confirm the computer actually has the claimed camera or microphone, the cable and jack are correct, Bluetooth is connected, the camera shutter is open, and keyboard, side or vendor software privacy switches are enabled. A headset without a microphone cannot provide microphone input.

### 2. Check Windows visibility and privacy

Inspect Device Manager for cameras, audio inputs/outputs and sound controllers. In Windows privacy settings, confirm camera and microphone access for the device and desktop applications. Check that the intended input and output are selected and not muted or disabled.

### 3. Test with simple system applications

Use the built-in Camera and Sound Recorder or a short speaker test. If the system application fails, stay below the browser or meeting application layer. If it works, the remaining cause is usually an application device choice, site permission or virtual-device conflict.

### 4. Remove selection conflicts

List virtual cameras, audio routers, game capture devices and vendor effects software. Temporarily select the physical endpoint or disable only a clearly identified unused virtual device after approval. For vendor audio suites, check whether a headset was classified as `headphones` instead of `headset`; restore the device-type prompt rather than uninstalling the vendor utility blindly.

### 5. Check drivers in the controlled order

Use `windows-driver-lifecycle-audit`: same-version reinstall first, rollback if the failure followed an update, then an exact official vendor package. Do not update a healthy device for its own sake.

### 6. Check the target application last

In the browser or meeting tool, allow the site, select the same working input/output, close competing applications and retry. Compare with a second trusted browser or application without changing system-wide defaults.

## Verification

Confirm the physical device is visible, the system test passes, the target application selects the intended endpoint, privacy permissions remain enabled, and no unrelated virtual devices or security controls were altered.

## Caveats

- Camera LEDs and mute indicators are useful evidence but do not prove that the application received data.
- A vendor control panel may own jack detection and can override Windows defaults.
- Browser permissions are per-site and can remain denied even when Windows permissions are correct.

## Escalation

Escalate a device missing from firmware or Device Manager, liquid or physical damage, repeated driver failures, an enterprise privacy policy, suspected eavesdropping, or a request to disable security software to make a camera or microphone work.

## Tools referenced

- `win_pnp_device_list`
- `win_driver_inventory`
- `win_policy_list`
- `win_file_signature`
- `ui_spa`
- `shell_run`
