"""Safe ZIP and OTA firmware archive inspector."""

from __future__ import annotations

import zipfile
from pathlib import Path

from aegis.firmware.models import FirmwareFinding

PARSER_NAME = "aegis_zip_inspector"
PARSER_VERSION = "0.1.0"

MAX_ENTRIES = 50_000
MAX_METADATA_READ_BYTES = 64 * 1024  # 64 KB limit for safe text extraction

KNOWN_COMPONENTS = {
    "payload.bin": "A/B OTA Update Engine Payload",
    "boot.img": "Kernel & Ramdisk Boot Image",
    "init_boot.img": "Generic Ramdisk Init Boot Image (Android 13+)",
    "vendor_boot.img": "Vendor Boot Image (Android 11+)",
    "vbmeta.img": "Android Verified Boot (AVB) Root Metadata",
    "vbmeta_system.img": "AVB Chained System Metadata",
    "vbmeta_vendor.img": "AVB Chained Vendor Metadata",
    "super.img": "Dynamic Partitions Super Image",
    "system.img": "Android System OS Partition",
    "vendor.img": "Hardware Vendor Partition",
    "product.img": "Product Customization Partition",
    "system_ext.img": "System Extension Partition",
    "odm.img": "Original Design Manufacturer Partition",
    "recovery.img": "AOSP / OEM Recovery Image",
    "dtbo.img": "Device Tree Blob Overlay",
}


def parse_zip_archive(
    file_path: Path,
    rel_path: str,
) -> tuple[str, list[FirmwareFinding], list[str], str | None]:
    """Inspect ZIP/OTA archive metadata safely without extracting files to disk.

    Returns: (parse_status, findings, warnings, error)
    """
    findings: list[FirmwareFinding] = []
    warnings: list[str] = []

    try:
        zf = zipfile.ZipFile(file_path, mode="r")
    except zipfile.BadZipFile as exc:
        return "error", [], ["Bad ZIP archive format"], f"Invalid ZIP file: {exc}"
    except OSError as exc:
        return "inaccessible", [], [], f"Failed to open archive: {exc}"

    with zf:
        infolist = zf.infolist()
        total_entries = len(infolist)

        if total_entries > MAX_ENTRIES:
            warnings.append(
                f"Archive contains {total_entries} entries exceeding safety limit ({MAX_ENTRIES}). Truncating inspection."
            )
            infolist = infolist[:MAX_ENTRIES]

        seen_names: set[str] = set()
        duplicate_entries: list[str] = []
        path_traversal_entries: list[str] = []
        total_uncompressed_bytes = 0
        detected_components: list[dict[str, str]] = []

        metadata_entry: zipfile.ZipInfo | None = None

        for info in infolist:
            name = info.filename
            total_uncompressed_bytes += info.file_size

            # Check duplicate entry
            if name in seen_names:
                duplicate_entries.append(name)
            seen_names.add(name)

            # Check path traversal
            if name.startswith(("/", "\\")) or "../" in name or "..\\" in name:
                path_traversal_entries.append(name)

            # Component identification
            base_name = Path(name).name.lower()
            if base_name in KNOWN_COMPONENTS:
                detected_components.append(
                    {
                        "archive_path": name,
                        "component": KNOWN_COMPONENTS[base_name],
                        "size_bytes": info.file_size,
                    }
                )

            # Locate OTA metadata
            if name == "META-INF/com/android/metadata":
                metadata_entry = info

        # Record findings
        findings.extend(
            [
                FirmwareFinding(
                    finding_id=f"{rel_path}:archive:total_entries",
                    category="archive_content",
                    key="zip.total_entries",
                    label="Archive Total Entries",
                    status="observed",
                    value=total_entries,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                ),
                FirmwareFinding(
                    finding_id=f"{rel_path}:archive:uncompressed_size",
                    category="archive_content",
                    key="zip.uncompressed_total_bytes",
                    label="Archive Total Uncompressed Bytes",
                    status="observed",
                    value=total_uncompressed_bytes,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                ),
                FirmwareFinding(
                    finding_id=f"{rel_path}:archive:detected_components",
                    category="partition_component",
                    key="zip.detected_firmware_components",
                    label="Detected Firmware Components",
                    status="observed" if detected_components else "not_applicable",
                    value=detected_components,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                    caveat="Identified via internal archive structure and standard Android component names.",
                ),
            ]
        )

        # Path traversal and duplicate audit
        security_warnings = []
        if duplicate_entries:
            security_warnings.append(f"{len(duplicate_entries)} duplicate archive entries detected")
            warnings.append(f"Archive contains duplicate filenames: {duplicate_entries[:5]}")
        if path_traversal_entries:
            security_warnings.append(f"{len(path_traversal_entries)} path traversal entries detected")
            warnings.append(f"Suspicious path traversal in archive: {path_traversal_entries[:5]}")

        findings.append(
            FirmwareFinding(
                finding_id=f"{rel_path}:security:archive_audit",
                category="security_metadata",
                key="zip.archive_safety_audit",
                label="Archive Path Traversal & Integrity Audit",
                status="observed" if not security_warnings else "error",
                value="clean" if not security_warnings else f"flagged: {', '.join(security_warnings)}",
                evidence_source=rel_path,
                parser=PARSER_NAME,
                parser_version=PARSER_VERSION,
                caveat="Evaluates path traversal, escape characters, and duplicate filenames in archive directory.",
            )
        )

        # Parse bounded metadata if available
        if metadata_entry is not None:
            if metadata_entry.file_size <= MAX_METADATA_READ_BYTES:
                try:
                    with zf.open(metadata_entry) as mf:
                        meta_text = mf.read(MAX_METADATA_READ_BYTES).decode("utf-8", errors="replace")
                        for line in meta_text.splitlines():
                            line = line.strip()
                            if not line or line.startswith("#") or "=" not in line:
                                continue
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip()
                            findings.append(
                                FirmwareFinding(
                                    finding_id=f"{rel_path}:ota_metadata:{k}",
                                    category="os_metadata",
                                    key=f"ota_metadata.{k}",
                                    label=f"OTA Metadata: {k}",
                                    status="observed",
                                    value=v,
                                    evidence_source=f"{rel_path}!/{metadata_entry.filename}",
                                    parser=PARSER_NAME,
                                    parser_version=PARSER_VERSION,
                                    confidence="authoritative",
                                )
                            )
                except (OSError, UnicodeDecodeError, KeyError) as exc:
                    warnings.append(f"Failed to read OTA metadata: {exc}")
            else:
                warnings.append(
                    f"OTA metadata entry {metadata_entry.file_size} bytes exceeds max read limit {MAX_METADATA_READ_BYTES}"
                )

    return "observed", findings, warnings, None
