from aegis.redaction import redact_sensitive_text, redact_serial


def test_redact_serial():
    assert redact_serial("") == "[EMPTY]"
    assert redact_serial("   ") == "[EMPTY]"
    assert redact_serial("123") == "[REDACTED]"
    assert redact_serial("ABCD") == "[REDACTED]"
    assert redact_serial("R58N1234XYZ") == "R5***YZ"
    assert redact_serial("emulator-5554") == "emulator-5554"
    assert redact_serial("emulator-5556") == "emulator-5556"


def test_redact_sensitive_text_with_serial():
    text = "Connected device: R58N9999ABC with state device"
    cleaned = redact_sensitive_text(text, known_serials=["R58N9999ABC"])
    assert "R58N9999ABC" not in cleaned
    assert "R5***BC" in cleaned


def test_redact_sensitive_text_imei():
    text = "Device IMEI is 864521049281723 in slot 1"
    cleaned = redact_sensitive_text(text)
    assert "864521049281723" not in cleaned
    assert "[REDACTED-IMEI]" in cleaned


def test_redact_sensitive_text_mac():
    text = "wlan0 hardware address is 00:1a:2b:3c:4d:5e active"
    cleaned = redact_sensitive_text(text)
    assert "00:1a:2b:3c:4d:5e" not in cleaned
    assert "[REDACTED-MAC]" in cleaned
