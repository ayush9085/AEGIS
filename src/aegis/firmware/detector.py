"""Conservative signature-based format detection for firmware artifacts."""

from __future__ import annotations

from pathlib import Path

MAGIC_BOOT_IMG = b"ANDROID!"
MAGIC_VENDOR_BOOT_IMG = b"VNDRBOOT"
MAGIC_SPARSE_IMG = b"\x3a\xff\x26\xed"  # 0xED26FF3A little-endian
MAGIC_ZIP_ARCHIVE = b"PK\x03\x04"
MAGIC_VBMETA = b"AVB0"
MAGIC_PAYLOAD_BIN = b"CrAU"


def detect_file_format(file_path: Path) -> str:
    """Detect file format using conservative magic-byte and structural signatures.

    Does not load large contents into memory.
    """
    try:
        size = file_path.stat().st_size
    except OSError:
        return "inaccessible"

    if size == 0:
        return "empty"

    try:
        with file_path.open("rb") as f:
            header = f.read(64)
    except OSError:
        return "inaccessible"

    if len(header) >= 8 and header.startswith(MAGIC_BOOT_IMG):
        return "android_boot_image"
    if len(header) >= 8 and header.startswith(MAGIC_VENDOR_BOOT_IMG):
        return "android_vendor_boot_image"
    if len(header) >= 4 and header.startswith(MAGIC_SPARSE_IMG):
        return "android_sparse_image"
    if len(header) >= 4 and header.startswith(MAGIC_ZIP_ARCHIVE):
        return "zip_archive"
    if len(header) >= 4 and header.startswith(MAGIC_VBMETA):
        return "avb_vbmeta_image"
    if len(header) >= 4 and header.startswith(MAGIC_PAYLOAD_BIN):
        return "android_payload_bin"

    # Name-based heuristic check for common Android property files
    filename_lower = file_path.name.lower()
    if filename_lower.endswith(".prop") or filename_lower in {"build.prop", "default.prop", "prop.default"}:
        # Verify text encoding
        try:
            with file_path.open("r", encoding="utf-8", errors="strict") as tf:
                sample = tf.read(512)
                if any("=" in line for line in sample.splitlines() if not line.strip().startswith("#")):
                    return "android_build_prop"
        except (UnicodeDecodeError, OSError):
            pass

    return "unknown"
