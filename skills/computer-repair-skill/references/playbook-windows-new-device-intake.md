---
name: windows-new-device-intake
description: Inspect a new Windows computer, preserve unboxing evidence, verify support/warranty, and establish a safe baseline
platform: windows
category: health-performance-storage-backup
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Windows New Device Intake

## When to activate

Use for a new laptop or desktop unboxing, acceptance check, return or warranty decision, first-time setup, suspected wrong specification, or a repair request on a recently purchased device.

## Quick check

Keep the sealed box, labels, accessories and purchase record. Record the model, serial/service tag, exact CPU, memory, storage, display, Windows edition, battery state and visible defects without publishing personal identifiers. Photograph the box seal, opening, accessories, screen and any defect before changing the system.
If the machine is still offline or within a return window, do not require activation or Internet access for the local inspection. Save the service tag and mark online support/warranty checks as pending until the owner approves connectivity.

## Standard diagnostic path

### 1. Preserve identity and schedule official verification

Capture the model and service tag locally first. When the owner approves connectivity, use the manufacturer's official support URL or app, reached from a known vendor domain, to verify model, warranty, factory configuration, firmware and drivers. Until then, mark support and warranty as pending; do not require activation just to inspect the machine. Do not trust a search-engine result, map listing or caller claiming to be an official repair center.

### 2. Run a non-destructive acceptance check

Check Device Manager, storage SMART/health metadata, battery health, display for dead pixels or damage, keyboard, touchpad, ports, camera, microphone, speakers, wireless and charging. Compare the result with the invoice and advertised configuration. Keep the machine offline during initial inspection when connecting could activate software or complicate a return.

### 3. Preserve account and license boundaries

Before reinstalling or removing anything, confirm Windows activation channel, Office entitlement, manufacturer recovery options, cloud account ownership and whether a school or employer account is temporary. Do not treat an educational account, cloud quota or preinstalled trial as a permanent personal license.

### 4. Set up conservatively

After the return decision is closed and the owner approves connectivity or activation, create a recovery path, update Windows and vendor drivers from official sources, enable supported security controls, and remove only clearly unwanted applications through their native uninstall path. Avoid driver packs, registry cleaners, activation tools and broad debloat presets.

### 5. Record the baseline

Save a de-identified hardware/software inventory, firmware version, BitLocker/device-encryption status, recovery-key location and the first successful network/audio/video/storage tests. Keep purchase and warranty evidence separate from the diagnostic report.

## Verification

Confirm the machine matches the ordered specification, local core devices work, and no third-party installer or unauthorized teardown was used. Record official support, warranty, activation and recovery status as verified or explicitly pending; an offline intake may finish with those online checks pending.

## Caveats

- Opening a device or replacing parts during the return window can affect warranty or evidence; check the vendor policy first.
- Battery and storage health readings are snapshots, not a lifetime guarantee.
- Vendor utilities may control camera shutters, audio jack detection, thermal modes or firmware updates; do not uninstall them before identifying those dependencies.

## Escalation

Escalate a configuration mismatch, physical damage, suspicious seal, missing serial/service tag, unknown seller, warranty dispute, firmware problem, BitLocker key uncertainty or a request to bypass activation.

## Tools referenced

- `win_system_info`
- `win_pnp_device_list`
- `win_volume_inventory`
- `win_bitlocker_status`
- `win_file_signature`
- `win_file_hash`
- `ui_spa`
