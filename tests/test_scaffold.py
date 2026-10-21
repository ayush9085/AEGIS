from aegis.adb import AdbDevice
from aegis.cli import build_parser


def test_parser_has_expected_commands():
    parser = build_parser()
    assert parser.parse_args(["doctor"]).command == "doctor"
    assert parser.parse_args(["devices"]).command == "devices"
    assert parser.parse_args(["collect", "--device", "mock-123", "--out", "./out"]).command == "collect"
    assert parser.parse_args(["report", "evidence.json"]).command == "report"
    assert parser.parse_args(["validate", "evidence.json"]).command == "validate"


def test_adb_device_model():
    device = AdbDevice(serial="example-serial", state="device")
    assert device.serial == "example-serial"
    assert device.state == "device"
    assert device.is_authorized is True

    unauth = AdbDevice(serial="unauth-serial", state="unauthorized")
    assert unauth.is_authorized is False
