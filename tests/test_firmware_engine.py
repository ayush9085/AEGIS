"""Unit tests for firmware engine coordinator and resource limits."""

import struct

import pytest

from aegis.firmware.engine import compute_file_sha256, inspect_firmware
from aegis.firmware.parsers.sparse import CHUNK_TYPE_DONT_CARE


def test_engine_inspect_single_boot_file(tmp_path):
    boot_file = tmp_path / "boot.img"
    magic = b"ANDROID!"
    # Minimal v3 header
    hdr = struct.pack("<8s4I4II1536s", magic, 4096, 2048, 0, 4096, 0, 0, 0, 0, 3, b"\x00" * 1536)
    boot_file.write_bytes(hdr.ljust(4096 + 4096 + 2048, b"\x00"))

    report = inspect_firmware(boot_file)
    assert report.target_name == "boot.img"
    assert report.target_type == "file"
    assert len(report.artifacts) == 1
    assert report.artifacts[0].detected_format == "android_boot_image"
    assert report.artifacts[0].sha256 == compute_file_sha256(boot_file)
    assert report.summary["total_artifacts"] == 1
    assert report.summary["observed"] > 0


def test_engine_inspect_directory_multiple_artifacts(tmp_path):
    fw_dir = tmp_path / "firmware_bundle"
    fw_dir.mkdir()

    # Artifact 1: boot.img
    b_file = fw_dir / "boot.img"
    b_hdr = struct.pack("<8s4I4II1536s", b"ANDROID!", 4096, 2048, 0, 4096, 0, 0, 0, 0, 3, b"\x00" * 1536)
    b_file.write_bytes(b_hdr.ljust(4096 + 4096 + 2048, b"\x00"))

    # Artifact 2: build.prop
    p_file = fw_dir / "system" / "build.prop"
    p_file.parent.mkdir()
    p_file.write_text("ro.product.model=Pixel 7\nro.build.version.release=13\n", encoding="utf-8")

    # Artifact 3: sparse image
    s_file = fw_dir / "system.sparse"
    s_hdr = struct.pack("<I4H4I", 0xED26FF3A, 1, 0, 28, 12, 4096, 1, 1, 0)
    c_hdr = struct.pack("<2H2I", CHUNK_TYPE_DONT_CARE, 0, 1, 12)
    s_file.write_bytes(s_hdr + c_hdr)

    # Artifact 4: empty file
    e_file = fw_dir / "empty.bin"
    e_file.write_bytes(b"")

    report = inspect_firmware(fw_dir)
    assert report.target_name == "firmware_bundle"
    assert report.target_type == "directory"
    assert len(report.artifacts) == 4

    art_paths = {a.path: a for a in report.artifacts}
    assert "boot.img" in art_paths
    assert "system/build.prop" in art_paths
    assert "system.sparse" in art_paths
    assert "empty.bin" in art_paths

    assert art_paths["boot.img"].detected_format == "android_boot_image"
    assert art_paths["system/build.prop"].detected_format == "android_build_prop"
    assert art_paths["system.sparse"].detected_format == "android_sparse_image"
    assert art_paths["empty.bin"].detected_format == "empty"
    assert art_paths["empty.bin"].parse_status == "not_applicable"

    # Summary counts reconciliation
    s = report.summary
    assert s["total_artifacts"] == 4
    assert s["total_findings"] == len(report.findings)
    counted_statuses = sum(s[st] for st in ("observed", "unsupported", "inaccessible", "not_applicable", "unknown", "error"))
    assert counted_statuses == s["total_findings"]


def test_engine_symlink_directory_escape_prevented(tmp_path):
    root_dir = tmp_path / "target_root"
    root_dir.mkdir()
    outside_dir = tmp_path / "outside_secret"
    outside_dir.mkdir()
    secret_file = outside_dir / "secret.txt"
    secret_file.write_text("secret_password=1234", encoding="utf-8")

    # Create symlink pointing outside target root
    symlink_path = root_dir / "escaped_link"
    try:
        symlink_path.symlink_to(outside_dir, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation not permitted in this environment")

    report = inspect_firmware(root_dir)
    # The escaped symlink must not leak artifacts into report
    paths = [a.path for a in report.artifacts]
    assert not any("secret" in p for p in paths)
    assert any("symlink escaping" in w.lower() for w in report.warnings)


def test_engine_oversized_file_limit(tmp_path):
    big_file = tmp_path / "large_payload.bin"
    # Write 5 MB file
    big_file.write_bytes(b"\x00" * (5 * 1024 * 1024))

    # Set limit to 2 MB
    report = inspect_firmware(big_file, max_file_size_mb=2)
    assert len(report.artifacts) == 1
    art = report.artifacts[0]
    assert art.detected_format == "oversized"
    assert art.parse_status == "unsupported"
    assert any("exceeds configured limit" in w for w in art.warnings)


def test_engine_missing_path_raises_not_found():
    with pytest.raises(FileNotFoundError, match="does not exist"):
        inspect_firmware("nonexistent_firmware_path_1234")
