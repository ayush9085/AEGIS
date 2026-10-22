"""AEGIS Offline Firmware Intelligence Engine."""

from aegis.firmware.engine import inspect_firmware
from aegis.firmware.models import (
    FIRMWARE_SCHEMA_VERSION,
    ArtifactInventory,
    FirmwareFinding,
    FirmwareReport,
    validate_firmware_report_dict,
)

__all__ = [
    "FIRMWARE_SCHEMA_VERSION",
    "ArtifactInventory",
    "FirmwareFinding",
    "FirmwareReport",
    "inspect_firmware",
    "validate_firmware_report_dict",
]
