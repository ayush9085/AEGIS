from aegis.adb import AdbDevice
from aegis.cli import build_parser


def test_parser_has_expected_commands():
    parser = build_parser()
    assert parser.parse_args(["doctor"]).command == "doctor"
    assert parser.parse_args(["devices"]).command == "devices"
    assert parser.parse_args(["collect", "--device", "mock-123", "--out", "./out"]).command == "collect"
    assert parser.parse_args(["report", "evidence.json"]).command == "report"
    assert parser.parse_args(["validate", "evidence.json"]).command == "validate"
    assert parser.parse_args(["snapshot", "evidence.json"]).command == "snapshot"
    assert parser.parse_args(["diff", "s1.json", "s2.json"]).command == "diff"
    assert parser.parse_args(["firmware", "inspect", "boot.img"]).command == "firmware"
    assert parser.parse_args(["research", "analyze", "e1.json"]).command == "research"
    assert parser.parse_args(["evaluation", "run"]).command == "evaluation"


def test_adb_device_model():
    device = AdbDevice(serial="example-serial", state="device")
    assert device.serial == "example-serial"
    assert device.state == "device"
    assert device.is_authorized is True

    unauth = AdbDevice(serial="unauth-serial", state="unauthorized")
    assert unauth.is_authorized is False
