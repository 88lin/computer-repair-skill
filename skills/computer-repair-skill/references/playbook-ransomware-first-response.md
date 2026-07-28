---
name: ransomware-first-response
description: Contain a live ransomware or mass-encryption event, preserve evidence and protect backups before attempting recovery
platform: all
category: incident-response
last_reviewed: 2026-07-28
author: computer-repair-skill-maintainers
source: local
---

# Ransomware First Response

## When to activate

Files are being renamed or become unreadable in bulk, documents open as garbage or with an unfamiliar extension, a ransom note appears as a text file or wallpaper or in every folder, a shared drive fills with unreadable copies, backup jobs suddenly fail or complete far too fast, or the user reports "all my photos are gone" together with a payment demand.

Also activate on the near misses that matter: an alert naming ransomware behaviour that was blocked, encryption that stopped partway, or a single folder affected on a machine with network shares mapped. Partial encryption almost always means the process was interrupted, not that it finished.

This playbook is the first hour. It is about stopping the spread, protecting what is still intact, and preserving what an investigator will need. Broader infection analysis belongs to `malware-triage`; run it after containment, not instead of it.

## Quick check

Three decisions come before any tooling, and getting them wrong is the difference between losing one machine and losing the whole estate.

**1. Is encryption still running?** If files are still changing, isolate the machine from the network immediately — pull the cable, disable the wireless adapter, or disconnect the wireless network. Isolation stops the spread to shares and other hosts.

Do not shut the machine down as the first move. On some families the decryption key material lives only in memory, and there are documented cases where it was recovered from a running system; a power-off destroys that possibility along with the volatile evidence. Hibernation and sleep are also state changes to avoid. Isolate first, then decide about power with the responder who will handle the case.

**2. Is this a managed or business-owned machine?** If it belongs to an employer, a client or an institution, this is their incident from this minute. Notify their security or IT contact before doing anything else. Many organisations carry legal, contractual and regulatory notification duties with short clocks, and cyber-insurance policies commonly void coverage if the environment is altered before their responder arrives. In that case your job is: isolate, preserve, document, hand over.

**3. Where else could it reach?** Enumerate the blast radius before touching files: mapped network drives, file servers, network-attached storage, cloud-synchronised folders, external and USB disks still attached, and any backup target reachable with the same credentials. Cloud sync is the most commonly missed path — an encrypted local file syncs upward and overwrites the good copy for everyone.

Disconnect other machines' access to the same shares, and physically disconnect backup media that is still attached. Do not "test" a backup by mounting it on the infected host.

Ask the user directly, with `ui_user_question`, what matters most in the next hour: (a) preserve everything for investigation and possible insurance or law-enforcement action, (b) recover data as fast as possible from backups, or (c) both, in that order. Never assume, and never start deleting or reformatting because option (b) sounds urgent.

## Standard diagnostic path

### 1. Freeze the scene and write things down

Start a written timeline immediately, with clock times: when the user first noticed, what they were doing, what the machine did, what you disconnected and when. This record is what an insurer, investigator or law-enforcement report is built from, and memory degrades within hours.

Photograph the ransom note and any on-screen messages with a phone rather than saving new files to the affected disk. Every write to that disk reduces the chance of recovering remnants of the originals.

Preserve, do not clean: keep the ransom note files, the encrypted samples, and any suspicious executable in place. Do not run a cleanup tool, do not delete the note, and do not start an antivirus removal action that quarantines the encryptor before the sample is preserved — the sample is often what identifies the family and whether a free decryptor exists.

### 2. Establish scope on disk

Work from copies or read-only access wherever practical. Inventory what is affected rather than assuming everything is:

- Use `win_path_inventory` to enumerate the affected trees on Windows and record, per location, how many files carry the new extension, the first and last modification timestamps, and which directories are untouched. On macOS and Linux, do the equivalent read-only inventory of the affected paths.
- Note the exact ransom-note filename and the exact appended extension, character for character. Both are the primary identifiers for the family.
- Check whether file *contents* are actually encrypted or merely renamed. A minority of cases are pure extortion bluffs, and some "encryption" is a reversible rename. Read a few bytes of a small affected file and compare against a known-good copy if one exists.
- Identify which files were open at the time — databases, mailbox files and virtual disks are often partially damaged rather than fully encrypted, and they need different handling.
- Use `win_volume_inventory` to record every volume, its filesystem and free space, including volumes that appear untouched, and to spot volumes that were mounted at the time and are now inaccessible.
- Check whether the volume is encrypted at rest with `win_bitlocker_status`. Full-disk encryption does not prevent ransomware, but its state matters for imaging, and recovery keys must be located before any offline work. Follow `windows-bitlocker-recovery-triage` on Windows if the key situation is unclear.

The timestamps from this step give you the encryption window, which is what every later step correlates against.

### 3. Find the entry point from logs

Read logs on the affected host without modifying them. Use `mac_read_log` on macOS and `linux_read_log` on Linux; on Windows read the security, system and application logs for the encryption window and the days before it.

Look for, in order of value:

- remote access: successful sign-ins from unfamiliar addresses, remote desktop or SSH sessions, a commercial remote-support agent starting, and repeated failed authentication followed by a success;
- new or elevated accounts, group membership changes, and password resets not made by the user;
- security tooling being stopped, uninstalled, or given new exclusions immediately before the encryption window — a near-universal precursor;
- deletion of shadow copies, snapshots or local backup catalogues, and disabling of recovery options;
- mass file access from a single process, and that process's path and signature;
- the initial delivery: an email attachment opened, an installer run, a browser download, or an exposed service reachable from the internet.

Use `knowledge_read` to consult the local reference material for the identified extension and note filename before searching externally. Record indicators as text — paths, hashes, addresses, account names — rather than copying the malicious files anywhere.

### 4. Protect and validate what remains

Backups are the only reliable recovery path, and this is the step where they are most often destroyed.

Treat every backup as suspect until validated, and validate on a clean machine, never on the infected host. Check that a restore actually produces readable files, not just that the job reports success — an encrypted source produces an encrypted backup with a green status. Follow `backup-verify-restore` for the restore test itself.

Priorities, in order:

1. Physically disconnect and write-protect any backup media that was attached.
2. Confirm at least one offline or immutable copy exists, and identify its most recent point in time before the encryption window.
3. For cloud storage and collaboration platforms, check version history and the provider's recycle bin or retention window immediately — many keep prior versions for a limited number of days, and that clock is running. Restore from a version predating the first encrypted timestamp.
4. Suspend sync clients on every other device before reconnecting anything, so a device holding good copies does not receive the encrypted versions.
5. Locate local snapshots and shadow copies, without expecting them: deleting them is standard behaviour for these families.
6. If there is no validated backup, preserve the encrypted data as-is. Keep a full copy of the encrypted files even if recovery looks impossible today — decryptors are released later for some families, and data destroyed now cannot benefit from that.

Use `local-data-audit` to establish what the user actually needs recovered and where it lived, so recovery effort is spent on the right data.

### 5. Decide the recovery route

Rank the routes by reliability, and be explicit about which one applies:

1. **Restore from a validated offline or immutable backup onto a rebuilt machine.** The only route that yields a trustworthy system.
2. **Cloud or file-server version history**, where an intact prior version predates the encryption window.
3. **A free, reputable decryptor** if the family is identified and one genuinely exists. Obtain it only from a recognised vendor or a public no-more-ransom style project, verify the family match first, and test on copies.
4. **Filesystem-level or forensic recovery of remnants** where the encryptor wrote new files and deleted originals rather than encrypting in place. On Windows, `windows-data-recovery-triage` covers this; the golden rule is to work from an image or read-only mount and never write to the affected volume.
5. **Accept the loss** for data with no backup and no recovery path, and record it plainly.

On paying: it is a business, legal and sometimes sanctions question, not a technical one, and it belongs to the owner or their counsel and insurer — not to the person at the keyboard. State the technical facts honestly: payment does not guarantee a working decryptor, does not remove the intruder's access, does not undo data theft, and is frequently accompanied by a second demand. Do not negotiate, and do not contact the operators on the user's behalf.

Plan on rebuilding the affected machine from known-good media rather than cleaning it. A host that reached mass-encryption stage had code execution with high privilege, and integrity cannot be re-established by deleting files.

### 6. Close the door before restoring

Restoring into an environment the intruder still controls simply repeats the event, sometimes within days. Before any restore:

- Rotate credentials for every account used on or reachable from the affected machine — local accounts, domain and cloud identities, email, remote access, backup system accounts, service accounts, and API and SSH keys. Do this from a trusted device, and follow `credential-cleanup` for the sequence. Backup-system credentials matter most: they are a primary target precisely because they can destroy recovery.
- Invalidate active sessions and tokens, not only passwords, and re-enrol multi-factor authentication where it may have been altered.
- Close the entry path: patch or remove the exposed service, disable internet-facing remote desktop, and restrict remote access to a controlled path.
- Restore protection and monitoring on rebuilt hosts before reconnecting them to the network, and reconnect one host at a time.
- Then continue with `malware-triage` and `activate_playbook` to run the platform-specific persistence audit on any host that was not rebuilt, so a dormant component is not left in place.

Report the incident to the appropriate national cybercrime or law-enforcement channel and, where personal data is involved, expect a regulatory notification duty with a short deadline. Advise the owner to check their obligations rather than deciding for them.

## Verification

Containment is verified when: the affected host is isolated and no file modification is continuing; every other host, share and sync client that could reach the same data is disconnected or confirmed unaffected; at least one validated backup or intact version history predating the encryption window has been identified and test-restored on a clean machine; the ransom note, encrypted samples and log excerpts are preserved with hashes and timestamps; and the written timeline is complete. Recovery is verified when restored files open correctly in their own applications on a rebuilt host, the restore point predates the first encrypted timestamp, credentials have been rotated and sessions invalidated, the entry path is closed, protection and monitoring are active, backups are running again to an offline or immutable target, and a subsequent full scan and persistence enumeration on the rebuilt host are clean. Anything unverified must be reported as unverified.

## Caveats

- Powering off can destroy in-memory key material and volatile evidence; isolate from the network first and let the responsible responder decide about power.
- Backup jobs that report success can be backing up encrypted files; only a restore test on a clean machine proves recoverability.
- Cloud sync propagates encryption to every linked device and to colleagues; version history is the recovery path, and its retention window expires.
- Shadow copies, local snapshots and backup catalogues are routinely deleted by these families; their absence is expected, not surprising.
- Encryption is frequently the last stage of an intrusion that began days or weeks earlier, and data was usually stolen before it. Recovery does not undo theft, and double-extortion demands follow.
- Partial or interrupted encryption often leaves files damaged in ways that open without error but contain corruption; verify content, not just that a file opens.
- "Decryptor" downloads offered by search results and forums are frequently malware or paid scams; use only a recognised vendor or public project, and test on copies.
- Reformatting or reinstalling on the affected disk destroys the encrypted data permanently, foreclosing recovery if a decryptor is released later.
- Altering a business environment before an insurer's or law enforcement's responder arrives can void coverage and compromise a case.
- Databases, mailbox stores and virtual machine disks need application-aware recovery; file-level restore alone can produce a technically present but inconsistent dataset.

## Escalation

Escalate immediately, before further technical work, for any managed, business, institutional or shared environment, for any file server or network-attached storage, for any case with personal, financial, health or regulated data, and whenever more than one host is affected. Route to: the organisation's security or IT leadership, its cyber-insurance provider, a qualified incident-response firm, the national cybercrime reporting channel, and legal or privacy counsel for notification duties. Escalate to the backup or cloud provider while the version-retention window is still open. Recommend rebuild over cleanup in every case that reached mass encryption. Hand over: the timeline with clock times, the exact note filename and appended extension, photographs of the note, affected paths with file counts and first and last modification timestamps, the volume inventory and encryption state, log excerpts covering the entry and encryption windows, indicators as text with hashes, the isolation and disconnection actions taken, backup locations with their validation status, credentials rotated and still outstanding, and everything that was deliberately left untouched.

## Tools referenced

- `win_volume_inventory`
- `win_bitlocker_status`
- `win_path_inventory`
- `mac_read_log`
- `linux_read_log`
- `ui_user_question`
- `activate_playbook`
- `knowledge_read`
