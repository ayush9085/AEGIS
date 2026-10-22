"""Offline firmware analysis engine coordinator."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from aegis import __version__
from aegis.firmware.detector import detect_file_format
from aegis.firmware.models import (
    DEFAULT_FIRMWARE_LIMITATIONS,
    FIRMWARE_SCHEMA_VERSION,
    ArtifactInventory,
    FirmwareFinding,
    FirmwareReport,
)
from aegis.firmware.parsers.boot_img import parse_boot_image, parse_vendor_boot_image
from aegis.firmware.parsers.props import parse_build_prop
from aegis.firmware.parsers.sparse import parse_sparse_image
from aegis.firmware.parsers.zip_archive import parse_zip_archive

MAX_FILES_IN_DIRECTORY = 5_000
HASH_CHUNK_SIZE = 64 * 1024  # 64 KB streaming buffer


def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash by streaming file in bounded chunks."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(HASH_CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


def inspect_firmware(
    target: Path | str,
    max_file_size_mb: int = 2048,
) -> FirmwareReport:
    """Inspect user-provided firmware file or directory offline and emit a FirmwareReport."""
    target_path = Path(target).resolve()
    if not target_path.exists():
        raise FileNotFoundError(f"Firmware target path does not exist: {target_path}")

    target_type = "directory" if target_path.is_dir() else "file"
    target_name = target_path.name

    artifacts: list[ArtifactInventory] = []
    all_findings: list[FirmwareFinding] = []
    global_warnings: list[str] = []

    # Gather files to inspect
    files_to_inspect: list[tuple[Path, str]] = []
    if target_type == "file":
        files_to_inspect.append((target_path, target_path.name))
    else:
        root_resolved = target_path.resolve()
        count = 0
        for p in sorted(target_path.rglob("*")):
            if count >= MAX_FILES_IN_DIRECTORY:
                global_warnings.append(
                    f"Directory contains over {MAX_FILES_IN_DIRECTORY} files. Scanning was truncated for safety."
                )
                break

            # Prevent symlink directory escape
            try:
                p_resolved = p.resolve()
                if not p_resolved.is_relative_to(root_resolved):
                    global_warnings.append(f"Skipping symlink escaping target root: {p}")
                    continue
            except (OSError, ValueError):
                continue

            if p.is_file():
                rel_path = p.relative_to(target_path).as_posix()
                files_to_inspect.append((p, rel_path))
                count += 1

    max_size_bytes = max_file_size_mb * 1024 * 1024

    for file_path, rel_path in files_to_inspect:
        try:
            size_bytes = file_path.stat().st_size
        except OSError as exc:
            artifacts.append(
                ArtifactInventory(
                    path=rel_path,
                    size_bytes=0,
                    sha256="",
                    detected_format="inaccessible",
                    parse_status="inaccessible",
                    error=f"Stat error: {exc}",
                )
            )
            continue

        # File size safety threshold
        if size_bytes > max_size_bytes:
            sha256 = ""
            detected_format = "oversized"
            parser_used = None
            parse_status = "unsupported"
            art_warnings = [
                f"File size ({size_bytes // (1024*1024)} MB) exceeds configured limit ({max_file_size_mb} MB). Skipped."
            ]
            artifacts.append(
                ArtifactInventory(
                    path=rel_path,
                    size_bytes=size_bytes,
                    sha256=sha256,
                    detected_format=detected_format,
                    parser_used=parser_used,
                    parse_status=parse_status,
                    warnings=art_warnings,
                )
            )
            continue

        try:
            sha256 = compute_file_sha256(file_path)
        except OSError as exc:
            artifacts.append(
                ArtifactInventory(
                    path=rel_path,
                    size_bytes=size_bytes,
                    sha256="",
                    detected_format="inaccessible",
                    parse_status="inaccessible",
                    error=f"Read error: {exc}",
                )
            )
            continue

        detected_format = detect_file_format(file_path)
        parser_used: str | None = None
        parse_status = "observed"
        art_warnings: list[str] = []
        error_msg: str | None = None
        item_findings: list[FirmwareFinding] = []

        if detected_format == "android_boot_image":
            parser_used = "aegis_boot_img_parser"
            parse_status, item_findings, art_warnings, error_msg = parse_boot_image(file_path, rel_path)
        elif detected_format == "android_vendor_boot_image":
            parser_used = "aegis_boot_img_parser"
            parse_status, item_findings, art_warnings, error_msg = parse_vendor_boot_image(file_path, rel_path)
        elif detected_format == "android_sparse_image":
            parser_used = "aegis_sparse_parser"
            parse_status, item_findings, art_warnings, error_msg = parse_sparse_image(file_path, rel_path)
        elif detected_format == "zip_archive":
            parser_used = "aegis_zip_inspector"
            parse_status, item_findings, art_warnings, error_msg = parse_zip_archive(file_path, rel_path)
        elif detected_format == "android_build_prop":
            parser_used = "aegis_prop_parser"
            parse_status, item_findings, art_warnings, error_msg = parse_build_prop(file_path, rel_path)
        elif detected_format == "avb_vbmeta_image":
            parser_used = "aegis_vbmeta_detector"
            parse_status = "observed"
            item_findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:format:vbmeta",
                    category="partition_component",
                    key="avb.container_type",
                    label="AVB VBMeta Image Container",
                    status="observed",
                    value="Android Verified Boot (AVB) 2.0 VBMeta Structure",
                    evidence_source=rel_path,
                    parser=parser_used,
                    confidence="authoritative",
                    caveat="AVB signature verification requires OEM public key ring.",
                )
            )
        elif detected_format == "android_payload_bin":
            parser_used = "aegis_payload_detector"
            parse_status = "observed"
            item_findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:format:payload_bin",
                    category="partition_component",
                    key="ota.payload_format",
                    label="A/B OTA Payload Binary",
                    status="observed",
                    value="ChromeOS/Android Update Engine Payload (CrAU)",
                    evidence_source=rel_path,
                    parser=parser_used,
                    confidence="authoritative",
                    caveat="Payload extraction requires block-level delta decompression.",
                )
            )
        elif detected_format == "empty":
            parse_status = "not_applicable"
            art_warnings.append("File is empty (0 bytes)")
        else:
            parse_status = "unsupported"
            art_warnings.append(f"Format '{detected_format}' not supported for deep parsing")

        artifacts.append(
            ArtifactInventory(
                path=rel_path,
                size_bytes=size_bytes,
                sha256=sha256,
                detected_format=detected_format,
                parser_used=parser_used,
                parse_status=parse_status,
                warnings=art_warnings,
                error=error_msg,
            )
        )
        all_findings.extend(item_findings)
        global_warnings.extend(art_warnings)

    # Sort artifacts and findings deterministically
    artifacts.sort(key=lambda a: a.path)
    all_findings.sort(key=lambda f: f.finding_id)

    # Calculate summary counts
    summary = {
        "total_artifacts": len(artifacts),
        "total_findings": len(all_findings),
        "observed": sum(1 for f in all_findings if f.status == "observed"),
        "unsupported": sum(1 for f in all_findings if f.status == "unsupported"),
        "inaccessible": sum(1 for f in all_findings if f.status == "inaccessible"),
        "not_applicable": sum(1 for f in all_findings if f.status == "not_applicable"),
        "unknown": sum(1 for f in all_findings if f.status == "unknown"),
        "error": sum(1 for f in all_findings if f.status == "error"),
        "warnings_count": len(global_warnings),
    }

    return FirmwareReport(
        schema_version=FIRMWARE_SCHEMA_VERSION,
        aegis_version=__version__,
        analyzed_at_utc=datetime.now(UTC).isoformat(),
        target_name=target_name,
        target_type=target_type,
        artifacts=artifacts,
        findings=all_findings,
        summary=summary,
        limitations=list(DEFAULT_FIRMWARE_LIMITATIONS),
        warnings=global_warnings,
    )
