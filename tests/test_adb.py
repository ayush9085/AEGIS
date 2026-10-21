import subprocess
from unittest.mock import MagicMock, patch

import pytest

from aegis.adb import (
    DEFAULT_ADB_TIMEOUT_SECONDS,
    AdbDevice,
    find_adb,
    get_adb_version,
    list_devices,
    run_adb_command,
)


def test_find_adb_installed():
    with patch("shutil.which", return_value="/usr/local/bin/adb"):
        assert find_adb() == "/usr/local/bin/adb"


def test_find_adb_missing():
    with patch("shutil.which", return_value=None):
        assert find_adb() is None


def test_get_adb_version_success():
    mock_res = MagicMock(returncode=0, stdout="Android Debug Bridge version 1.0.41\nVersion 34.0.5")
    with patch("subprocess.run", return_value=mock_res):
        ver = get_adb_version("/mock/adb")
        assert ver == "Android Debug Bridge version 1.0.41"


def test_get_adb_version_missing():
    with patch("shutil.which", return_value=None):
        assert get_adb_version(None) is None


def test_get_adb_version_failure_returns_none():
    mock_res = MagicMock(returncode=1, stdout="", stderr="error")
    with patch("subprocess.run", return_value=mock_res):
        assert get_adb_version("/mock/adb") is None


def test_list_devices_success():
    output = "List of devices attached\nR58N1234567\tdevice\nemulator-5554\tunauthorized\n\n"
    mock_res = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_res):
        devs = list_devices(adb_path="/mock/adb")
        assert len(devs) == 2
        assert devs[0] == AdbDevice(serial="R58N1234567", state="device")
        assert devs[0].is_authorized is True
        assert devs[1] == AdbDevice(serial="emulator-5554", state="unauthorized")
        assert devs[1].is_authorized is False


def test_list_devices_with_daemon_starting_banner():
    output = (
        "* daemon not running; starting now at tcp:5037\n"
        "* daemon started successfully\n"
        "List of devices attached\n"
        "test-serial-001\tdevice\n"
    )
    mock_res = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_res):
        devs = list_devices(adb_path="/mock/adb")
        assert len(devs) == 1
        assert devs[0].serial == "test-serial-001"
        assert devs[0].state == "device"


def test_list_devices_empty():
    output = "List of devices attached\n\n"
    mock_res = MagicMock(returncode=0, stdout=output, stderr="")
    with patch("subprocess.run", return_value=mock_res):
        devs = list_devices(adb_path="/mock/adb")
        assert devs == []


def test_list_devices_missing_adb_raises_file_not_found():
    with patch("aegis.adb.find_adb", return_value=None), pytest.raises(
        FileNotFoundError, match="ADB was not found"
    ):
        list_devices(adb_path=None)


def test_list_devices_nonzero_exit():
    mock_res = MagicMock(returncode=1, stdout="", stderr="error: server failed")
    with patch("subprocess.run", return_value=mock_res), pytest.raises(
        RuntimeError, match="ADB device discovery failed"
    ):
        list_devices(adb_path="/mock/adb")


def test_list_devices_timeout():
    with patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="adb devices", timeout=10)
    ), pytest.raises(RuntimeError, match="timed out"):
        list_devices(adb_path="/mock/adb")


def test_run_adb_command_success():
    mock_res = MagicMock(returncode=0, stdout="Samsung\n", stderr="")
    with patch("subprocess.run", return_value=mock_res) as mock_run:
        ret, out, err = run_adb_command(
            "device-1", ["shell", "getprop", "ro.product.manufacturer"], adb_path="/mock/adb"
        )
        assert ret == 0
        assert out == "Samsung\n"
        assert err == ""
        # Check command argument array passed without shell=True
        mock_run.assert_called_once_with(
            ["/mock/adb", "-s", "device-1", "shell", "getprop", "ro.product.manufacturer"],
            check=False,
            capture_output=True,
            text=True,
            timeout=DEFAULT_ADB_TIMEOUT_SECONDS,
        )


def test_run_adb_command_timeout():
    with patch(
        "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["adb"], timeout=5)
    ), pytest.raises(TimeoutError, match="ADB command timed out"):
        run_adb_command("device-1", ["shell", "sleep", "10"], timeout=5, adb_path="/mock/adb")


def test_run_adb_command_missing_adb():
    with patch("aegis.adb.find_adb", return_value=None), pytest.raises(
        FileNotFoundError, match="ADB was not found"
    ):
        run_adb_command("device-1", ["shell", "getprop"], adb_path=None)


def test_run_adb_command_output_bounds():
    oversized = "A" * 100000
    mock_res = MagicMock(returncode=0, stdout=oversized, stderr="")
    with patch("subprocess.run", return_value=mock_res):
        _ret, out, _err = run_adb_command("dev-1", ["shell", "cat"], max_bytes=1024, adb_path="/mock/adb")
        assert len(out) == 1024
