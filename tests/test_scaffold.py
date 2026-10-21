from aegis.adb import AdbDevice
from aegis.cli import build_parser


def test_parser_has_expected_commands():
    parser = build_parser()
    assert parser.parse_args(["doctor"]).command == "doctor"
    assert parser.parse_args(["devices"]).command == "devices"


def test_adb_device_model():
    device = AdbDevice(serial="example-serial", state="device")
    assert device.serial == "example-serial"
    assert device.state == "device"
