---
name: setup-cuda
description: Install NVIDIA CUDA Toolkit on Linux (Ubuntu/Debian, RHEL/Fedora)
platform: linux
last_reviewed: 2026-09-28
author: upstream-maintainers
source: bundled
emoji: 🎮
---

# Set Up NVIDIA CUDA Toolkit

## When to activate
User wants to install CUDA, set up GPU computing, needs NVIDIA drivers for deep learning/ML, or mentions nvcc/nvidia-smi not found on Linux.

## Quick check
Run `shell_run` with `lspci | grep -i nvidia` to verify an NVIDIA GPU is present.
- If no NVIDIA GPU found → wrong playbook, tell user CUDA requires an NVIDIA GPU.
- If GPU found → continue.

## Step 1: Check existing installation
Run `shell_run` with `nvidia-smi` and `nvcc --version`.
- If both work and versions are satisfactory → skip to Step 6 (verify).
- If `nvidia-smi` works but `nvcc` is missing → verify the distro, architecture and configured repository in Steps 2-3, then install only a compatible toolkit in Step 4. Preserve the working driver.
- If neither works → continue with Step 2.

## Step 2: Detect distro and install prerequisites
Run `shell_run` with `cat /etc/os-release` to identify the distribution.
Then install kernel headers and GCC:

**Ubuntu/Debian:**
```
sudo apt update && sudo apt install -y build-essential linux-headers-$(uname -r)
```

**RHEL/Fedora/Rocky:**
```
sudo dnf install -y gcc kernel-devel-$(uname -r)
```

## Step 3: Add the matching repository and plan the driver separately
Check the current official support matrix for the exact distro, architecture, GPU and
toolkit version before using the examples below. They illustrate x86_64 only. Adding
the repository does not install a driver. If a driver is missing, use the distro/vendor
documented signed-driver procedure, preview exact packages and rollback, and obtain
approval before changing it. Stop on unsupported combinations.
**Ubuntu/Debian:**
```
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
```
Adjust `ubuntu2404` to match the actual distro version (ubuntu2204, debian12, etc.).

**RHEL/Fedora/Rocky:**
```
sudo dnf config-manager --add-repo https://developer.download.nvidia.com/compute/cuda/repos/rhel9/x86_64/cuda-rhel9.repo
```
Adjust `rhel9` to match (fedora41, etc.).

Use WAIT_FOR_USER — adding repos and downloading packages can take a few minutes.

## Step 4: Install CUDA Toolkit
**Ubuntu/Debian:**
```
sudo apt install -y cuda-toolkit
```

**RHEL/Fedora/Rocky:**
```
sudo dnf install -y cuda-toolkit
```

The `cuda-toolkit` package installs the compiler, libraries and headers; it does not
install the NVIDIA driver. Check the package-manager transaction preview and verify a
compatible driver independently. Do not replace a working driver to obtain `nvcc`.

Use WAIT_FOR_USER — installation downloads ~2–4 GB and takes 5–15 minutes.

## Step 5: Configure PATH
Add CUDA to the user's PATH by appending to `~/.bashrc`:
```
echo 'export PATH=/usr/local/cuda/bin${PATH:+:${PATH}}' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}' >> ~/.bashrc
source ~/.bashrc
```

If a new NVIDIA driver was installed, stop before rebooting. Tell the user
that the running session will end and ask them to reboot manually:

```text
需要重启才能加载新的 NVIDIA 驱动。请先保存工作，然后在本机运行：sudo reboot。
重启并重新登录后告诉我，我再继续执行第 6 步验证。
```

Use WAIT_FOR_USER. Do not run `sudo reboot` automatically and do not continue
to verification until the user confirms that the system is back.

## Step 6: Verify installation
Run these checks:
```
nvidia-smi
nvcc --version
```
- `nvidia-smi` should show the GPU model and driver version.
- `nvcc` should show the CUDA compiler version.


## Caveats
- If **Secure Boot** prevents loading the driver, use the distro's signed packages and documented MOK enrollment. Keep Secure Boot enabled; escalate unknown signing or enterprise policy constraints.
- If **nouveau** is loaded, follow the matching vendor/distro driver procedure. Do not blindly blacklist a display driver or rebuild initramfs without a verified recovery path and approval.
- On **Fedora 41+** with GCC version mismatches, install the compatibility GCC package and set `NVCC_CCBIN` accordingly.

## Tools referenced
- `shell_run` — run commands to check GPU, install packages, configure PATH
- `ui_spa` with WAIT_FOR_USER — for long-running installs and reboot steps
- `ui_user_question` — ask which distro if auto-detection fails

## Escalation
Check the exact GPU's support in the selected CUDA release rather than assuming a
single compute-capability cutoff works for every version. For black screens or boot
failure, use recovery mode and the recorded package transaction to restore only the
changed driver packages. Do not purge wildcard-matched NVIDIA packages; preserve
the previously working driver, display stack and kernel recovery entry.
