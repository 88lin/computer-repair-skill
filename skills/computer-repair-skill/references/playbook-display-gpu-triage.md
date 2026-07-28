---
name: display-gpu-triage
description: Diagnose blank screens, flicker, artefacts, wrong resolution, external-monitor and GPU driver faults on any platform
platform: all
category: peripherals-display
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Display and GPU Triage

## When to activate

The screen is blank while the machine is clearly running, an external monitor is not detected or is detected but stays dark, the image flickers, tears, shows coloured artefacts or briefly goes black, the resolution or refresh rate is wrong or cannot be changed, text is blurry or oversized after connecting a different monitor, colours are inverted or washed out, a second display mirrors when it should extend, the screen goes black and recovers with a "display driver stopped responding" notice, or a graphics-heavy application crashes while the rest of the system is fine.

Also activate for the docking-station variants: displays that work when connected directly but not through a dock or hub, a display that drops when a USB device is plugged in, and multi-monitor layouts that rearrange after every sleep cycle.

## Quick check

Decide which of three layers owns the fault before changing any setting. Guessing here is what turns a five-minute cable swap into an afternoon of driver reinstallation.

1. **Panel and link.** Is anything reaching the display at all? Confirm the monitor has power and the correct input selected — an input left on the wrong port is the single most common "monitor is broken". Then swap the cable, swap the port, and connect the monitor to a different machine. A laptop's internal panel is testable by connecting an external display: if the external image is perfect and the internal panel is dark with a faint image visible under bright light, that is a backlight fault, and no software change will help.
2. **GPU and driver.** Record what the system believes it has. On Windows use `win_display_info`, on macOS use `mac_display_info`, and on Linux use `linux_display_info`. Capture the adapter or adapters, driver version and date, the connected outputs and their state, and the current resolution and refresh rate per display. A machine with two GPUs — integrated plus discrete — needs both recorded, along with which one is driving which output.
3. **Compositor and application.** Does the symptom affect everything, or only one application? A single application showing artefacts while the desktop is clean is an application or acceleration problem, not a hardware fault. Ask the user to reproduce the symptom and note whether the mouse pointer, the desktop background and the notification area are affected too.

One more question decides the urgency: does the symptom appear before the operating system loads — in the firmware screen or the vendor logo? If it does, this is firmware, cable, panel or GPU hardware, and the operating system is irrelevant. On Windows, a machine that shows the vendor logo and then nothing may be a boot problem rather than a display problem; `windows-boot-failure-triage` separates the two.

## Standard diagnostic path

### 1. Test the physical link properly

Cheap and decisive, so do it first and do it completely:

- Reseat both ends of the cable. Test a different, known-good cable — a cable that carries a lower resolution successfully can still fail at a higher resolution or refresh rate, which produces intermittent blackouts rather than a dead screen.
- Test each port on the machine and each input on the monitor, and record which combinations work.
- Remove docks, hubs, adapters and extenders from the path and connect directly. If direct works and the dock does not, the dock, its firmware, or its bandwidth budget is the fault.
- Check the cable specification against the requested mode. High resolution at a high refresh rate, with high dynamic range or a colour depth above eight bits, needs cable and connector capability that older cables do not have. Match the mode to the weakest link in the chain, and reduce refresh rate as a test before blaming the GPU.
- On laptops, confirm which physical ports carry video at all: on many machines only some connectors do, and a display attached to a data-only port will never light up.

### 2. Enumerate what the system actually sees

Compare the machine's view against the physical reality. For each output, record whether it is connected, active, and what mode it is running.

Frequent findings at this step:

- A display that is detected but disabled or positioned outside the visible desktop area, which looks identical to "not working".
- A display running a mode the panel does not support, producing an out-of-range message or a black screen with a live backlight.
- A resolution far below the panel's native mode, which is the usual cause of blurry text — the fix is the native mode plus correct scaling, not sharpening.
- Mirroring where the user expected extension, or the wrong display marked as primary.
- A monitor whose identification data cannot be read, which forces the system into a conservative fallback mode. This is a cable, adapter or monitor firmware symptom, and it is why a dock in the path is worth removing.
- On hybrid-graphics machines, outputs wired to the integrated GPU while the application runs on the discrete one, or a power policy that parks the discrete GPU.

Use `shell_run` only for the documented read-only enumeration commands in the platform tool references. Changing resolution, refresh rate or layout is a state change: make one change at a time and record the previous value so it can be restored.

### 3. Attribute driver and firmware faults from evidence

A driver is the right suspect when the symptom began after an update, when the screen recovers on its own after going black, when artefacts appear across all applications, or when the adapter reports an error state.

On Windows, read the system log with `win_read_log` for the symptom window and look for display driver timeout-and-recovery events, adapter reset records and kernel-level display watchdog reports. Then inventory the installed graphics drivers with `win_driver_inventory` and compare the version and date against what the GPU vendor and the machine vendor publish. Perform the change itself through `windows-driver-lifecycle-audit` on Windows, which covers clean installation, rollback and the difference between the vendor's generic driver and the machine manufacturer's build — the latter matters on laptops, where the manufacturer's package carries panel and power-management specifics. If the machine also produced a blue screen or an unexpected restart, treat it as a crash case and continue with `windows-crash-dump-triage` on Windows instead of reinstalling drivers repeatedly.

On macOS, graphics drivers are part of the operating system: the equivalent action is applying pending system updates, not installing a driver. Check the affected application's own logs with `mac_app_logs` when a single application shows artefacts or crashes, and record whether the application uses hardware acceleration or a specific graphics API.

On Linux, establish which stack is in use before changing anything: the kernel driver for the GPU, whether the session is X11 or Wayland, and whether a vendor proprietary driver or the open-source driver is loaded. Then check three things that account for most cases: a kernel and driver-module version mismatch after a partial upgrade, a missing firmware package for the GPU, and Secure Boot rejecting an unsigned out-of-tree module. Switching between X11 and Wayland is a fast, reversible test that separates compositor bugs from driver bugs, and it is worth doing before any driver change.

### 4. Distinguish hardware artefacts from software artefacts

The pattern of corruption is diagnostic:

- Artefacts that persist in the firmware setup screen, in a live boot medium and on a second operating system are hardware. Software changes will not fix them.
- Artefacts that appear only under load, and disappear when the machine is cool or the GPU is limited, point at heat, power delivery or an unstable overclock. Continue with `thermal-battery-health` for the thermal and power evidence, and revert any manual GPU or memory overclock — including a vendor "performance" preset — as a test.
- Artefacts confined to one application or one browser are software. Disabling hardware acceleration in that application is a legitimate diagnostic step and a legitimate workaround, and it identifies the layer even when it is not the final fix.
- Flicker that matches the refresh rate, or that appears only at a specific brightness, is often a panel or backlight behaviour rather than a GPU fault. Variable refresh rate features are a common cause of flicker in windowed applications and at low frame rates; disabling the feature is a reversible test.
- Lines, blocks or discoloured regions fixed in position on a laptop panel, and changing with lid angle or pressure, indicate a panel or cable fault inside the display assembly.
- Random full-screen black periods with automatic recovery are usually driver timeouts; the same symptom without recovery, needing a hard restart, is a stronger hardware or power signal.

If the display symptom coincides with input devices lagging or dropping, check whether the shared factor is a dock or a radio issue rather than graphics — `bluetooth-peripheral-triage` covers that side.

### 5. Handle scaling, colour and multi-monitor layout

Many complaints in this area are configuration rather than fault, and they are solved by explaining the model:

- Mixed-density setups — a high-density laptop panel next to a standard external monitor — cannot look identical on both with a single scaling factor. Set each display to its native resolution and adjust per-display scaling, then accept that applications which do not handle scaling changes will be blurry until restarted.
- Text that is blurry only in some applications after docking or undocking is an application scaling behaviour; restarting that application usually resolves it, and logging out resolves the rest.
- Colour problems divide cleanly: a wrong colour profile affects everything and is fixed in settings; a wrong dynamic-range or colour-range setting produces washed-out or crushed blacks and is often set on the monitor rather than the machine; night-shift and blue-light filters produce a warm cast that users report as a fault; and a colour cast that survives a profile reset and appears on another machine is a panel fault.
- Layouts that rearrange after sleep are usually caused by the machine losing and re-detecting displays in a different order, frequently through a dock. Confirm the layout, then verify it survives a sleep cycle rather than assuming it will.
- Refresh rate should be set explicitly after any change. Panels commonly default to a lower rate, and users perceive the difference as sluggishness rather than as a setting.

### 6. Recover a machine you cannot see

When there is no usable image, keep options open rather than power-cycling repeatedly:

- Connect an external display, or use the platform's display-detection shortcut, before assuming the machine is dead.
- Use the platform's safe or low-resolution startup mode to get a basic image, then correct the mode or the driver from there.
- Where the machine is reachable over the network, a remote session is often fully functional while the local display is not, and it is the safest way to read logs and revert a change.
- On Linux, a text console or a remote session lets you revert a driver or session change without a graphical environment.
- Do not reinstall the operating system to fix a display fault before an external display has been tested; a dark internal panel with a perfect external image is a hardware repair, not a software one.

Record every change and revert failed attempts before trying the next one, so the machine never ends up in an unknown mixed state.

## Verification

Verify against the user's real workload and both display states. Confirm each display runs its native resolution and the intended refresh rate, the layout and primary display are as expected, and scaling produces readable text in the applications the user actually uses. Then sleep and wake the machine, undock and redock if a dock is involved, and reboot — confirming after each that all displays return automatically in the correct layout without manual intervention. Run the previously failing workload for long enough to reach steady-state temperature and confirm no flicker, artefacts or driver recovery events, then re-read the system log for the test window and confirm no new display timeout records. Confirm no other display, audio or peripheral output regressed, and that every changed setting was recorded with its previous value.

## Caveats

- A cable that works at a lower mode can fail at a higher resolution or refresh rate; intermittent blackouts are frequently a cable or bandwidth limit rather than a GPU fault.
- Docks and hubs share bandwidth across displays and data; a configuration that works directly may be impossible through the dock, and dock firmware updates are themselves a risk step.
- Hybrid-graphics laptops route outputs through specific GPUs; testing the wrong one produces misleading conclusions.
- Manufacturer-supplied graphics drivers on laptops can differ from the GPU vendor's generic package in panel, brightness and power behaviour; the generic package is not always an upgrade.
- Dead or stuck pixels, uniformity differences and backlight bleed fall within many manufacturers' tolerance thresholds and are not repairable faults.
- Artefacts that persist in firmware screens and on other operating systems are hardware; continuing to reinstall drivers wastes the user's time.
- Disabling hardware acceleration is a diagnostic and a workaround, not a fix, and it costs performance and battery life.
- Variable refresh rate, high dynamic range and frame-generation features interact badly with some applications; disabling them is a valid test but should be recorded and revisited.
- Virtual machines, remote sessions and screen-sharing tools present synthetic displays whose limitations are unrelated to the physical hardware.
- Do not disable driver signature enforcement, Secure Boot or platform integrity protections to install a graphics driver.

## Escalation

Escalate to the hardware vendor when artefacts or a dark panel persist in firmware screens or on another operating system, when a laptop panel shows position-fixed defects or responds to lid angle and pressure, when a backlight fails, when a GPU fails only under load after thermal and power evidence has been collected, and when an external monitor fails against multiple machines and cables. Escalate to the dock or adapter vendor when the fault exists only through their device with a supported configuration. Escalate to the application vendor when artefacts or crashes are confined to one application with current drivers and a clean desktop. Escalate to the platform or workplace owner when policy manages driver versions, blocks updates or enforces display configuration on a managed machine. Hand over: platform and version, adapter and driver versions with dates, the connected outputs with their modes, monitor models and cable and dock topology, exactly which combinations reproduce the symptom, log excerpts covering one reproduction, the thermal and load conditions, which layers were excluded and how, and every setting changed with its previous value.

## Tools referenced

- `win_display_info`
- `mac_display_info`
- `linux_display_info`
- `win_driver_inventory`
- `win_read_log`
- `mac_app_logs`
- `shell_run`
