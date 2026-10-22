"""Parser for Android boot and vendor_boot image headers (v0 through v4)."""

from __future__ import annotations

import struct
from pathlib import Path

from aegis.firmware.models import FirmwareFinding

PARSER_NAME = "aegis_boot_img_parser"
PARSER_VERSION = "0.1.0"


def _decode_os_version(raw: int) -> tuple[str | None, str | None]:
    """Decode AOSP os_version bitfield into (os_version_str, patch_level_str)."""
    if raw == 0:
        return None, None

    os = raw >> 11
    a = (os >> 14) & 0x7F
    b = (os >> 7) & 0x7F
    c = os & 0x7F

    os_str = None
    if a > 0:
        if b == 0 and c == 0:
            os_str = str(a)
        elif c == 0:
            os_str = f"{a}.{b}"
        else:
            os_str = f"{a}.{b}.{c}"

    patch = raw & 0x7FF
    year = (patch >> 4) + 2000
    month = patch & 0xF

    patch_str = None
    if 2000 <= year <= 2099 and 1 <= month <= 12:
        patch_str = f"{year:04d}-{month:02d}"

    return os_str, patch_str


def parse_boot_image(
    file_path: Path,
    rel_path: str,
) -> tuple[str, list[FirmwareFinding], list[str], str | None]:
    """Parse Android boot image header (v0-v4) and extract component findings.

    Returns: (parse_status, findings, warnings, error)
    """
    findings: list[FirmwareFinding] = []
    warnings: list[str] = []

    try:
        file_size = file_path.stat().st_size
    except OSError as exc:
        return "inaccessible", [], [], f"Failed to stat file: {exc}"

    if file_size < 48:
        return "error", [], ["File too small to contain boot header"], "Truncated boot image"

    try:
        with file_path.open("rb") as f:
            header_bytes = f.read(4096)
    except OSError as exc:
        return "inaccessible", [], [], f"Failed to read file: {exc}"

    if len(header_bytes) < 48 or not header_bytes.startswith(b"ANDROID!"):
        return "error", [], ["Invalid boot image magic"], "Magic bytes do not match ANDROID!"

    # In AOSP bootimg.h, header_version is at offset 40 across v0, v1, v2, v3, and v4
    version = struct.unpack_from("<I", header_bytes, 40)[0]

    if version not in (0, 1, 2, 3, 4):
        # Unknown/unsupported header version
        findings.append(
            FirmwareFinding(
                finding_id=f"{rel_path}:header:header_version",
                category="header",
                key="boot.header_version",
                label="Boot Image Header Version",
                status="unsupported",
                value=version,
                evidence_source=rel_path,
                parser=PARSER_NAME,
                parser_version=PARSER_VERSION,
                caveat=f"Boot image header version {version} is unsupported",
            )
        )
        return "unsupported", findings, [f"Unsupported boot header version: {version}"], None

    findings.append(
        FirmwareFinding(
            finding_id=f"{rel_path}:header:header_version",
            category="header",
            key="boot.header_version",
            label="Boot Image Header Version",
            status="observed",
            value=version,
            evidence_source=rel_path,
            parser=PARSER_NAME,
            parser_version=PARSER_VERSION,
            confidence="authoritative",
        )
    )

    if version in (0, 1, 2):
        if len(header_bytes) < 608:
            return "error", findings, ["Truncated v0-v2 boot header"], "Header bytes truncated"

        (
            kernel_size,
            _kernel_addr,
            ramdisk_size,
            _ramdisk_addr,
            second_size,
            _second_addr,
            _tags_addr,
            page_size,
            _hdr_version,
            os_version_raw,
        ) = struct.unpack_from("<10I", header_bytes, 8)

        cmdline_raw = header_bytes[64:576].split(b"\x00", 1)[0]
        cmdline = cmdline_raw.decode("ascii", errors="replace").strip()

        findings.extend(
            [
                FirmwareFinding(
                    finding_id=f"{rel_path}:header:page_size",
                    category="header",
                    key="boot.page_size",
                    label="Page Size",
                    status="observed",
                    value=page_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                ),
                FirmwareFinding(
                    finding_id=f"{rel_path}:component:kernel_size",
                    category="partition_component",
                    key="boot.kernel_size_bytes",
                    label="Kernel Size (Bytes)",
                    status="observed" if kernel_size > 0 else "not_applicable",
                    value=kernel_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                ),
                FirmwareFinding(
                    finding_id=f"{rel_path}:component:ramdisk_size",
                    category="partition_component",
                    key="boot.ramdisk_size_bytes",
                    label="Ramdisk Size (Bytes)",
                    status="observed" if ramdisk_size > 0 else "not_applicable",
                    value=ramdisk_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                ),
                FirmwareFinding(
                    finding_id=f"{rel_path}:component:second_size",
                    category="partition_component",
                    key="boot.second_stage_size_bytes",
                    label="Second Stage Bootloader Size (Bytes)",
                    status="observed" if second_size > 0 else "not_applicable",
                    value=second_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                ),
            ]
        )

        if cmdline:
            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:header:cmdline",
                    category="header",
                    key="boot.cmdline",
                    label="Kernel Command Line",
                    status="observed",
                    value=cmdline,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                )
            )

        os_ver, patch_lvl = _decode_os_version(os_version_raw)
        if os_ver:
            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:os:declared_os_version",
                    category="os_metadata",
                    key="boot.declared_os_version",
                    label="Declared OS Version",
                    status="observed",
                    value=os_ver,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                )
            )
        if patch_lvl:
            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:os:declared_security_patch",
                    category="os_metadata",
                    key="boot.declared_security_patch",
                    label="Declared Security Patch Level",
                    status="observed",
                    value=patch_lvl,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                )
            )

        # Version 1+ additions
        if version >= 1 and len(header_bytes) >= 1648:
            recovery_dtbo_size = struct.unpack_from("<I", header_bytes, 1632)[0]
            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:component:recovery_dtbo_size",
                    category="partition_component",
                    key="boot.recovery_dtbo_size_bytes",
                    label="Recovery DTBO Size (Bytes)",
                    status="observed" if recovery_dtbo_size > 0 else "not_applicable",
                    value=recovery_dtbo_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                )
            )

        # Version 2 additions
        if version >= 2 and len(header_bytes) >= 1660:
            dtb_size = struct.unpack_from("<I", header_bytes, 1648)[0]
            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:component:dtb_size",
                    category="partition_component",
                    key="boot.dtb_size_bytes",
                    label="DTB Size (Bytes)",
                    status="observed" if dtb_size > 0 else "not_applicable",
                    value=dtb_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                )
            )

        # Check section boundaries against file size
        if page_size > 0:
            def page_align(sz: int) -> int:
                return ((sz + page_size - 1) // page_size) * page_size

            min_expected = page_size + page_align(kernel_size) + page_align(ramdisk_size)
            if min_expected > file_size:
                warnings.append(
                    f"Declared components ({min_expected} bytes) exceed actual file size ({file_size} bytes). File may be truncated."
                )

    elif version in (3, 4):
        # Version 3 / 4 header
        if len(header_bytes) < 40:
            return "error", findings, ["Truncated v3/v4 boot header"], "Header bytes truncated"

        kernel_size, ramdisk_size, os_version_raw, header_size = struct.unpack_from("<4I", header_bytes, 8)
        cmdline_raw = header_bytes[44:1580].split(b"\x00", 1)[0]
        cmdline = cmdline_raw.decode("ascii", errors="replace").strip()

        findings.extend(
            [
                FirmwareFinding(
                    finding_id=f"{rel_path}:component:kernel_size",
                    category="partition_component",
                    key="boot.kernel_size_bytes",
                    label="Kernel Size (Bytes)",
                    status="observed" if kernel_size > 0 else "not_applicable",
                    value=kernel_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                ),
                FirmwareFinding(
                    finding_id=f"{rel_path}:component:ramdisk_size",
                    category="partition_component",
                    key="boot.ramdisk_size_bytes",
                    label="Ramdisk Size (Bytes)",
                    status="observed" if ramdisk_size > 0 else "not_applicable",
                    value=ramdisk_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                ),
            ]
        )

        if cmdline:
            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:header:cmdline",
                    category="header",
                    key="boot.cmdline",
                    label="Kernel Command Line",
                    status="observed",
                    value=cmdline,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                )
            )

        os_ver, patch_lvl = _decode_os_version(os_version_raw)
        if os_ver:
            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:os:declared_os_version",
                    category="os_metadata",
                    key="boot.declared_os_version",
                    label="Declared OS Version",
                    status="observed",
                    value=os_ver,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                )
            )
        if patch_lvl:
            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:os:declared_security_patch",
                    category="os_metadata",
                    key="boot.declared_security_patch",
                    label="Declared Security Patch Level",
                    status="observed",
                    value=patch_lvl,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                )
            )

        if version == 4 and len(header_bytes) >= 1584:
            sig_size = struct.unpack_from("<I", header_bytes, 1580)[0]
            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:security:signature_size",
                    category="security_metadata",
                    key="boot.signature_size_bytes",
                    label="Boot Signature Size (Bytes)",
                    status="observed" if sig_size > 0 else "not_applicable",
                    value=sig_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                )
            )

        # In v3/v4 page size is fixed at 4096 bytes
        v3_page_size = 4096
        def v3_align(sz: int) -> int:
            return ((sz + v3_page_size - 1) // v3_page_size) * v3_page_size

        min_expected = v3_align(header_size) + v3_align(kernel_size) + v3_align(ramdisk_size)
        if min_expected > file_size:
            warnings.append(
                f"Declared v{version} components ({min_expected} bytes) exceed actual file size ({file_size} bytes)."
            )

    return "observed", findings, warnings, None


def parse_vendor_boot_image(
    file_path: Path,
    rel_path: str,
) -> tuple[str, list[FirmwareFinding], list[str], str | None]:
    """Parse Android vendor_boot image header (v3 or v4)."""
    findings: list[FirmwareFinding] = []
    warnings: list[str] = []

    try:
        file_size = file_path.stat().st_size
    except OSError as exc:
        return "inaccessible", [], [], f"Failed to stat file: {exc}"

    if file_size < 32:
        return "error", [], ["File too small for vendor_boot header"], "Truncated vendor_boot"

    try:
        with file_path.open("rb") as f:
            header_bytes = f.read(4096)
    except OSError as exc:
        return "inaccessible", [], [], f"Failed to read file: {exc}"

    if len(header_bytes) < 32 or not header_bytes.startswith(b"VNDRBOOT"):
        return "error", [], ["Invalid vendor_boot magic"], "Magic bytes do not match VNDRBOOT"

    version = struct.unpack_from("<I", header_bytes, 8)[0]
    if version not in (3, 4):
        findings.append(
            FirmwareFinding(
                finding_id=f"{rel_path}:header:vendor_header_version",
                category="header",
                key="vendor_boot.header_version",
                label="Vendor Boot Header Version",
                status="unsupported",
                value=version,
                evidence_source=rel_path,
                parser=PARSER_NAME,
                parser_version=PARSER_VERSION,
                caveat=f"Vendor boot header version {version} is unsupported",
            )
        )
        return "unsupported", findings, [f"Unsupported vendor_boot header version {version}"], None

    page_size, _kaddr, _raddr, v_ramdisk_size = struct.unpack_from("<4I", header_bytes, 12)

    findings.extend(
        [
            FirmwareFinding(
                finding_id=f"{rel_path}:header:vendor_header_version",
                category="header",
                key="vendor_boot.header_version",
                label="Vendor Boot Header Version",
                status="observed",
                value=version,
                evidence_source=rel_path,
                parser=PARSER_NAME,
                parser_version=PARSER_VERSION,
                confidence="authoritative",
            ),
            FirmwareFinding(
                finding_id=f"{rel_path}:header:vendor_page_size",
                category="header",
                key="vendor_boot.page_size",
                label="Vendor Page Size",
                status="observed",
                value=page_size,
                evidence_source=rel_path,
                parser=PARSER_NAME,
                parser_version=PARSER_VERSION,
            ),
            FirmwareFinding(
                finding_id=f"{rel_path}:component:vendor_ramdisk_size",
                category="partition_component",
                key="vendor_boot.ramdisk_size_bytes",
                label="Vendor Ramdisk Size (Bytes)",
                status="observed" if v_ramdisk_size > 0 else "not_applicable",
                value=v_ramdisk_size,
                evidence_source=rel_path,
                parser=PARSER_NAME,
                parser_version=PARSER_VERSION,
            ),
        ]
    )

    if version == 4 and len(header_bytes) >= 2120:
        v_ramdisk_table_size = struct.unpack_from("<I", header_bytes, 2112)[0]
        bootconfig_size = struct.unpack_from("<I", header_bytes, 2120)[0]
        findings.extend(
            [
                FirmwareFinding(
                    finding_id=f"{rel_path}:component:vendor_ramdisk_table_size",
                    category="partition_component",
                    key="vendor_boot.ramdisk_table_size_bytes",
                    label="Vendor Ramdisk Table Size",
                    status="observed" if v_ramdisk_table_size > 0 else "not_applicable",
                    value=v_ramdisk_table_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                ),
                FirmwareFinding(
                    finding_id=f"{rel_path}:component:bootconfig_size",
                    category="partition_component",
                    key="vendor_boot.bootconfig_size_bytes",
                    label="Bootconfig Size",
                    status="observed" if bootconfig_size > 0 else "not_applicable",
                    value=bootconfig_size,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                ),
            ]
        )

    return "observed", findings, warnings, None
