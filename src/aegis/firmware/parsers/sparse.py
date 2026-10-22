"""Parser for Android sparse image format without expanding partitions to disk."""

from __future__ import annotations

import struct
from pathlib import Path

from aegis.firmware.models import FirmwareFinding

PARSER_NAME = "aegis_sparse_parser"
PARSER_VERSION = "0.1.0"

CHUNK_TYPE_RAW = 0xCAC1
CHUNK_TYPE_FILL = 0xCAC2
CHUNK_TYPE_DONT_CARE = 0xCAC3
CHUNK_TYPE_CRC32 = 0xCAC4

CHUNK_NAMES = {
    CHUNK_TYPE_RAW: "raw",
    CHUNK_TYPE_FILL: "fill",
    CHUNK_TYPE_DONT_CARE: "dont_care",
    CHUNK_TYPE_CRC32: "crc32",
}


def parse_sparse_image(
    file_path: Path,
    rel_path: str,
) -> tuple[str, list[FirmwareFinding], list[str], str | None]:
    """Parse Android sparse image header and chunk structures safely without expanding.

    Returns: (parse_status, findings, warnings, error)
    """
    findings: list[FirmwareFinding] = []
    warnings: list[str] = []

    try:
        file_size = file_path.stat().st_size
    except OSError as exc:
        return "inaccessible", [], [], f"Failed to stat file: {exc}"

    if file_size < 28:
        return "error", [], ["File too small for sparse file header"], "Truncated sparse file"

    try:
        with file_path.open("rb") as f:
            header_bytes = f.read(28)
            if len(header_bytes) < 28:
                return "error", [], ["Header truncated"], "Incomplete header"

            (
                magic,
                major_version,
                _minor_version,
                file_hdr_sz,
                chunk_hdr_sz,
                blk_sz,
                total_blks,
                total_chunks,
                _image_checksum,
            ) = struct.unpack("<I4H4I", header_bytes)

            if magic != 0xED26FF3A:
                return "error", [], ["Invalid sparse magic"], f"Invalid magic 0x{magic:08X}"

            if major_version != 1:
                return (
                    "unsupported",
                    findings,
                    [f"Unsupported sparse major version {major_version}"],
                    None,
                )

            if blk_sz == 0 or (blk_sz % 4) != 0:
                return "error", [], ["Invalid block size"], f"Block size {blk_sz} is not a multiple of 4"

            if chunk_hdr_sz < 12:
                return "error", [], ["Invalid chunk header size"], f"Chunk header size {chunk_hdr_sz} < 12"

            # Skip any extra file header bytes if file_hdr_sz > 28
            if file_hdr_sz > 28:
                f.seek(file_hdr_sz)

            # Record basic header findings
            findings.extend(
                [
                    FirmwareFinding(
                        finding_id=f"{rel_path}:sparse:block_size",
                        category="header",
                        key="sparse.block_size_bytes",
                        label="Sparse Block Size",
                        status="observed",
                        value=blk_sz,
                        evidence_source=rel_path,
                        parser=PARSER_NAME,
                        parser_version=PARSER_VERSION,
                    ),
                    FirmwareFinding(
                        finding_id=f"{rel_path}:sparse:total_blocks",
                        category="header",
                        key="sparse.declared_total_blocks",
                        label="Sparse Declared Total Blocks",
                        status="observed",
                        value=total_blks,
                        evidence_source=rel_path,
                        parser=PARSER_NAME,
                        parser_version=PARSER_VERSION,
                    ),
                    FirmwareFinding(
                        finding_id=f"{rel_path}:sparse:total_chunks",
                        category="header",
                        key="sparse.declared_total_chunks",
                        label="Sparse Declared Total Chunks",
                        status="observed",
                        value=total_chunks,
                        evidence_source=rel_path,
                        parser=PARSER_NAME,
                        parser_version=PARSER_VERSION,
                    ),
                    FirmwareFinding(
                        finding_id=f"{rel_path}:sparse:uncompressed_size",
                        category="partition_component",
                        key="sparse.uncompressed_output_size_bytes",
                        label="Sparse Uncompressed Output Size",
                        status="observed",
                        value=total_blks * blk_sz,
                        evidence_source=rel_path,
                        parser=PARSER_NAME,
                        parser_version=PARSER_VERSION,
                    ),
                ]
            )

            # Stream-inspect chunks
            parsed_chunks = 0
            parsed_blocks = 0
            chunk_type_counts: dict[str, int] = {
                "raw": 0,
                "fill": 0,
                "dont_care": 0,
                "crc32": 0,
                "unknown": 0,
            }

            # Safety bounds: don't loop endlessly on corrupt files
            max_chunks_to_inspect = min(total_chunks, 100_000)

            while parsed_chunks < max_chunks_to_inspect:
                pos = f.tell()
                if pos >= file_size:
                    break

                chunk_hdr = f.read(12)
                if len(chunk_hdr) < 12:
                    warnings.append(f"Unexpected end of file while reading chunk {parsed_chunks + 1}")
                    break

                chunk_type, _res, chunk_sz, total_sz = struct.unpack("<2H2I", chunk_hdr)
                chunk_name = CHUNK_NAMES.get(chunk_type, "unknown")
                chunk_type_counts[chunk_name] += 1

                # Validate expected total_sz
                expected_data_sz = total_sz - chunk_hdr_sz
                if total_sz < chunk_hdr_sz:
                    warnings.append(f"Chunk {parsed_chunks + 1} declared invalid total_sz {total_sz} < {chunk_hdr_sz}")
                    break

                if chunk_type == CHUNK_TYPE_RAW:
                    expected_raw_data = chunk_sz * blk_sz
                    if expected_data_sz != expected_raw_data:
                        warnings.append(
                            f"Raw chunk {parsed_chunks + 1} size mismatch: data={expected_data_sz}, expected={expected_raw_data}"
                        )
                elif chunk_type in (CHUNK_TYPE_FILL, CHUNK_TYPE_CRC32):
                    if expected_data_sz != 4:
                        warnings.append(f"{chunk_name.title()} chunk {parsed_chunks + 1} expected 4 bytes payload, got {expected_data_sz}")
                elif chunk_type == CHUNK_TYPE_DONT_CARE:
                    if expected_data_sz != 0:
                        warnings.append(f"Don't Care chunk {parsed_chunks + 1} expected 0 bytes payload, got {expected_data_sz}")

                parsed_chunks += 1
                if chunk_type != CHUNK_TYPE_CRC32:
                    parsed_blocks += chunk_sz

                # Seek forward to next chunk without loading chunk payload into memory
                seek_bytes = total_sz - 12
                if seek_bytes > 0:
                    next_pos = f.tell() + seek_bytes
                    if next_pos > file_size:
                        warnings.append(f"Chunk {parsed_chunks} extends beyond file boundary ({next_pos} > {file_size})")
                        break
                    f.seek(next_pos)

            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:sparse:chunk_distribution",
                    category="chunk_structure",
                    key="sparse.chunk_type_distribution",
                    label="Sparse Chunk Type Distribution",
                    status="observed",
                    value=chunk_type_counts,
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                )
            )

            # Check block count consistency
            if parsed_blocks != total_blks:
                warnings.append(
                    f"Parsed block count ({parsed_blocks}) does not match declared total blocks ({total_blks})"
                )

            if parsed_chunks != total_chunks:
                warnings.append(
                    f"Parsed chunk count ({parsed_chunks}) does not match declared total chunks ({total_chunks})"
                )

            findings.append(
                FirmwareFinding(
                    finding_id=f"{rel_path}:sparse:consistency",
                    category="chunk_structure",
                    key="sparse.structural_consistency",
                    label="Sparse Structural Consistency",
                    status="observed" if not warnings else "error",
                    value="consistent" if not warnings else "inconsistencies_detected",
                    evidence_source=rel_path,
                    parser=PARSER_NAME,
                    parser_version=PARSER_VERSION,
                    caveat="Verified chunk boundaries and block allocations without expanding image."
                )
            )

    except (struct.error, OSError, ValueError, OverflowError) as exc:
        return "error", findings, warnings, f"Sparse parsing exception: {exc}"

    return "observed", findings, warnings, None
