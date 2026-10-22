"""Firmware artifact parsers."""

from aegis.firmware.parsers.boot_img import parse_boot_image, parse_vendor_boot_image
from aegis.firmware.parsers.props import parse_build_prop
from aegis.firmware.parsers.sparse import parse_sparse_image
from aegis.firmware.parsers.zip_archive import parse_zip_archive

__all__ = [
    "parse_boot_image",
    "parse_build_prop",
    "parse_sparse_image",
    "parse_vendor_boot_image",
    "parse_zip_archive",
]
