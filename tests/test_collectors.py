from unittest.mock import patch

import pytest

from aegis.adb import AdbDevice
from aegis.collectors.allowlist import ALLOWLIST_ITEMS
from aegis.collectors.engine import collect_device_evidence, get_collection_plan


def test_allowlist_safety_rules():
    forbidden_tokens = {"rm", "reboot", "flash", "format", "fastboot", "su", "wipe", "dd", "sh"}
    for item in ALLOWLIST_ITEMS:
        assert item.key
        assert item.label
        assert item.caveat
        assert item.command_args[0] == "shell"
        # Ensure none of the args use forbidden destructive commands
        for arg in item.command_args:
            assert arg.lower() not in forbidden_tokens


def test_get_collection_plan():
    plan = get_collection_plan()
    assert len(plan) == len(ALLOWLIST_ITEMS)
    for p in plan:
        assert "key" in p
        assert "label" in p
        assert "method" in p
        assert "description" in p


def test_collect_requires_explicit_consent():
    with pytest.raises(PermissionError, match="explicit user consent is required"):
        collect_device_evidence(serial="MOCK_DEVICE", consent_given=False)


def test_collect_rejects_missing_device():
    with patch("aegis.collectors.engine.list_devices", return_value=[]), pytest.raises(
        RuntimeError, match="was not found in attached ADB devices"
    ):
        collect_device_evidence(serial="NONEXISTENT", consent_given=True)


def test_collect_rejects_unauthorized_device():
    unauth_dev = AdbDevice(serial="UNAUTH123", state="unauthorized")
    with patch("aegis.collectors.engine.list_devices", return_value=[unauth_dev]), pytest.raises(
        RuntimeError, match="not in authorized 'device' state"
    ):
        collect_device_evidence(serial="UNAUTH123", consent_given=True)


def test_collect_rejects_offline_device():
    offline_dev = AdbDevice(serial="OFFLINE123", state="offline")
    with patch("aegis.collectors.engine.list_devices", return_value=[offline_dev]), pytest.raises(
        RuntimeError, match="not in authorized 'device' state"
    ):
        collect_device_evidence(serial="OFFLINE123", consent_given=True)


def test_collect_device_evidence_mock_run():
    dev = AdbDevice(serial="R58N1234567", state="device")

    def mock_run_cmd(serial, args, timeout=10.0, adb_path=None):
        cmd_str = " ".join(args)
        if "ro.product.manufacturer" in cmd_str:
            return 0, "Samsung\n", ""
        if "ro.product.model" in cmd_str:
            return 0, "SM-M115F\n", ""
        if "ro.build.version.release" in cmd_str:
            return 0, "12\n", ""
        if "ro.build.fingerprint" in cmd_str:
            return 0, "samsung/m11qsnsxx/m11q:12/SP1A/user/release-keys\n", ""
        if "ro.boot.vbmeta.device_state" in cmd_str:
            return 0, "", ""  # Empty string -> unsupported
        if "uname" in cmd_str:
            return 1, "", "/system/bin/uname: Permission denied\n"  # Inaccessible
        if "ro.boot.flash.locked" in cmd_str:
            raise TimeoutError("Command timed out")  # Error
        return 0, "mock_val", ""

    with (
        patch("aegis.collectors.engine.list_devices", return_value=[dev]),
        patch("aegis.collectors.engine.run_adb_command", side_effect=mock_run_cmd),
        patch("aegis.collectors.engine.get_adb_version", return_value="Android Debug Bridge 1.0.41"),
    ):
        report = collect_device_evidence(serial="R58N1234567", consent_given=True)

        assert report.schema_version == "0.1.0"
        assert report.device.serial_redacted == "R5***67"
        assert report.device.manufacturer == "Samsung"
        assert report.device.model == "SM-M115F"
        assert report.device.android_version == "12"
        assert report.device.fingerprint == "samsung/m11qsnsxx/m11q:12/SP1A/user/release-keys"

        obs_by_key = {o.key: o for o in report.observations}

        # Check observed
        assert obs_by_key["product.manufacturer"].status == "observed"
        assert obs_by_key["product.manufacturer"].value == "Samsung"

        # Check unsupported (empty output)
        assert obs_by_key["boot.vbmeta_state"].status == "unsupported"
        assert obs_by_key["boot.vbmeta_state"].value is None

        # Check inaccessible (permission denied)
        assert obs_by_key["kernel.version"].status == "inaccessible"

        # Check error (timeout)
        assert obs_by_key["boot.flash_locked"].status == "error"

        # Summary check
        assert report.summary.total == len(ALLOWLIST_ITEMS)
        assert report.summary.observed > 0
        assert report.summary.unsupported >= 1
        assert report.summary.inaccessible >= 1
        assert report.summary.error >= 1
