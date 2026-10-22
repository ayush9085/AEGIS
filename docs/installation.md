# AEGIS Installation & Environment Guide

**Version:** `0.1.0`  
**Compatibility:** Python 3.11, 3.12  
**Supported Host Operating Systems:** macOS (Apple Silicon / Intel), Linux (Ubuntu, Debian, Fedora, Arch)  
**Dependencies:** Zero external runtime dependencies (Python standard library only). Developer tooling requires `pytest`, `ruff`, and `build`.

---

## 1. Prerequisites

### A. Python Runtime
AEGIS requires Python 3.11 or 3.12. Verify your current Python version:
```bash
python3 --version
```
If Python is not installed or older than 3.11:
* **macOS**: `brew install python@3.12`
* **Ubuntu/Debian**: `sudo apt update && sudo apt install -y python3 python3-pip python3-venv`
* **Fedora**: `sudo dnf install -y python3 python3-pip`

### B. Android Platform Tools (ADB)
AEGIS uses the official Android Debug Bridge (`adb`) binary to communicate with connected Android devices in read-only mode.
* **macOS (via Homebrew)**:
  ```bash
  brew install android-platform-tools
  ```
* **Ubuntu/Debian**:
  ```bash
  sudo apt install -y adb
  ```
* **Fedora**:
  ```bash
  sudo dnf install -y android-tools
  ```
* **Official Standalone Zip**: Download directly from [developer.android.com/tools/releases/platform-tools](https://developer.android.com/tools/releases/platform-tools) and add the directory to your system `PATH`.

Verify ADB is reachable:
```bash
adb version
```

---

## 2. Installation Methods

### Method 1: Local Developer / Contributor Install (Editable)
Clone the repository and set up an isolated virtual environment:

```bash
git clone https://github.com/ayush9085/AEGIS.git
cd AEGIS

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install AEGIS with development tools
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Alternatively, use the quick runner script:
```bash
./run.sh install
```

### Method 2: Standard Clean Installation from Source
To install AEGIS directly as a package into your active Python environment:
```bash
cd AEGIS
python -m pip install .
```

### Method 3: Installation from Built Wheel
To build and install the distribution wheel:
```bash
python -m build
python -m pip install dist/aegis_android_research-0.1.0-py3-none-any.whl
```

---

## 3. Verifying Your Setup

### Step 1: Run the Environment Doctor
```bash
aegis doctor
# Or via runner: ./run.sh doctor
```
Expected output:
```text
AEGIS Version: 0.1.0
Host Platform: Darwin ... (or Linux ...)
Python: 3.12.0 (...)
ADB Binary: /path/to/adb
ADB Version: Android Debug Bridge version ...
Devices Connected: ...
Status: Environment ready for read-only ADB research.
```

### Step 2: Run the Offline Synthetic Demo
Verify all components function properly without needing a physical handset or internet access:
```bash
./run.sh demo-e2e
# Or: bash scripts/demo.sh
```

---

## 4. Handset Preparation (For Live Physical Reconnaissance)

To inspect a physical handset (e.g. Samsung Galaxy M11, Xiaomi Redmi, Google Pixel):
1. On the phone, open **Settings** → **About phone** → **Software information**.
2. Tap **Build number** 7 times until the toast notification confirms *Developer mode has been enabled*.
3. Go back to **Settings** → **Developer options** and enable **USB debugging**.
4. Connect the handset to your computer using a USB data cable (charge-only cables will not establish an ADB connection).
5. When prompted on the handset screen with *Allow USB debugging?*, check *Always allow from this computer* and tap **Allow**.
6. Verify authorization in AEGIS:
   ```bash
   aegis devices
   ```
   Authorized handsets will display status `device`. If the status shows `unauthorized`, unlock your handset screen and tap **Allow** on the RSA authorization modal.

---

## 5. Troubleshooting Common Issues

| Symptom | Cause | Remediation |
| :--- | :--- | :--- |
| `aegis: command not found` | Virtualenv not activated or wheel not in `PATH` | Run `source .venv/bin/activate` or invoke via `python3 -m aegis.cli`. |
| `ADB Binary: NOT FOUND` | `adb` is missing from environment `PATH` | Install platform-tools or add `/path/to/platform-tools` to `PATH` in `~/.zshrc` / `~/.bashrc`. |
| Device status `unauthorized` | Host RSA key was not accepted on phone | Unlock handset display and tap **Allow** on the USB debugging prompt. |
| Device status `offline` | USB connection drop or unstable cable | Re-plug USB cable, try a different port, or run `adb kill-server && adb start-server`. |
| Property `unsupported` | Property not implemented by OEM build | Expected behavior. Some OEMs omit standard AOSP properties. AEGIS records this faithfully as `unsupported`. |
| Property `inaccessible` | Restricted by SELinux policy or permissions | Expected behavior. Read-only user sessions cannot read privileged properties. AEGIS marks this as `inaccessible`. |
