"""Unit tests for firmware artifact parsers (boot image, sparse, zip, props)."""

import struct
import zipfile

from aegis.firmware.detector import detect_file_format
from aegis.firmware.parsers.boot_img import (
    _decode_os_version,
    parse_boot_image,
    parse_vendor_boot_image,
)
from aegis.firmware.parsers.props import parse_build_prop
from aegis.firmware.parsers.sparse import (
    CHUNK_TYPE_DONT_CARE,
    CHUNK_TYPE_FILL,
    CHUNK_TYPE_RAW,
    parse_sparse_image,
)
from aegis.firmware.parsers.zip_archive import parse_zip_archive


def test_decode_os_version_known_values():
    # Android 12.0.0, patch 2023-08
    # os = 12 << 14 = 196608; raw_os = 196608 << 11 = 402653184
    # patch = (23 << 4) | 8 = 376
    raw = 402653184 | 376
    os_str, patch_str = _decode_os_version(raw)
    assert os_str == "12"
    assert patch_str == "2023-08"

    # Android 13.1.2, patch 2024-01
    os_val = (13 << 14) | (1 << 7) | 2
    raw2 = (os_val << 11) | ((24 << 4) | 1)
    os_str2, patch_str2 = _decode_os_version(raw2)
    assert os_str2 == "13.1.2"
    assert patch_str2 == "2024-01"

    # Zero
    os_zero, patch_zero = _decode_os_version(0)
    assert os_zero is None
    assert patch_zero is None


def test_boot_image_v0_parsing(tmp_path):
    boot_path = tmp_path / "boot_v0.img"

    # Construct synthetic v0 header (1632 bytes minimum)
    magic = b"ANDROID!"
    kernel_size = 4096
    kernel_addr = 0x10008000
    ramdisk_size = 2048
    ramdisk_addr = 0x11000000
    second_size = 0
    second_addr = 0
    tags_addr = 0x10000100
    page_size = 2048
    header_version = 0
    os_version = (12 << 25) | ((23 << 4) | 8)
    name = b"test_kernel\x00".ljust(16, b"\x00")
    cmdline = b"console=ttyMSM0,115200 androidboot.hardware=qcom\x00".ljust(512, b"\x00")
    id_sha = b"\x01" * 32
    extra_cmdline = b"\x00" * 1024

    hdr = struct.pack(
        "<8s10I16s512s32s1024s",
        magic,
        kernel_size,
        kernel_addr,
        ramdisk_size,
        ramdisk_addr,
        second_size,
        second_addr,
        tags_addr,
        page_size,
        header_version,
        os_version,
        name,
        cmdline,
        id_sha,
        extra_cmdline,
    )
    # Total size padding to cover declared components
    total_data = hdr.ljust(page_size + 4096 + 2048, b"\xaa")
    boot_path.write_bytes(total_data)

    assert detect_file_format(boot_path) == "android_boot_image"

    status, findings, warnings, error = parse_boot_image(boot_path, "boot_v0.img")
    assert status == "observed"
    assert error is None
    assert len(warnings) == 0

    f_map = {f.key: f for f in findings}
    assert f_map["boot.header_version"].value == 0
    assert f_map["boot.page_size"].value == 2048
    assert f_map["boot.kernel_size_bytes"].value == 4096
    assert f_map["boot.ramdisk_size_bytes"].value == 2048
    assert "console=ttyMSM0" in f_map["boot.cmdline"].value
    assert f_map["boot.declared_security_patch"].value == "2023-08"


def test_boot_image_v3_parsing(tmp_path):
    boot_path = tmp_path / "boot_v3.img"

    # v3 layout:
    # magic: 8s
    # kernel_size: I
    # ramdisk_size: I
    # os_version: I
    # header_size: I (4096)
    # reserved[4]: 4I
    # header_version: I (offset 36 -> 3)
    # cmdline: 1536s
    magic = b"ANDROID!"
    kernel_size = 8192
    ramdisk_size = 4096
    os_version = ((13 << 14) << 11) | ((24 << 4) | 5)
    header_size = 4096
    header_version = 3
    cmdline = b"bootconfig androidboot.verifiedbootstate=orange\x00".ljust(1536, b"\x00")

    hdr = struct.pack(
        "<8s4I4II1536s",
        magic,
        kernel_size,
        ramdisk_size,
        os_version,
        header_size,
        0, 0, 0, 0,
        header_version,
        cmdline,
    )
    data = hdr.ljust(header_size + kernel_size + ramdisk_size, b"\xbb")
    boot_path.write_bytes(data)

    status, findings, _warnings, error = parse_boot_image(boot_path, "boot_v3.img")
    assert status == "observed"
    assert error is None

    f_map = {f.key: f for f in findings}
    assert f_map["boot.header_version"].value == 3
    assert f_map["boot.kernel_size_bytes"].value == 8192
    assert f_map["boot.ramdisk_size_bytes"].value == 4096
    assert f_map["boot.declared_os_version"].value == "13"
    assert f_map["boot.declared_security_patch"].value == "2024-05"
    assert "verifiedbootstate=orange" in f_map["boot.cmdline"].value


def test_boot_image_truncated_and_invalid_magic(tmp_path):
    # Truncated
    trunc = tmp_path / "trunc.img"
    trunc.write_bytes(b"ANDROID!\x00\x00")
    status, _, _, err = parse_boot_image(trunc, "trunc.img")
    assert status == "error"
    assert "Truncated" in str(err)

    # Invalid magic
    inv = tmp_path / "inv.img"
    inv.write_bytes(b"NOTBOOT!\x00" * 20)
    status2, _, _, err2 = parse_boot_image(inv, "inv.img")
    assert status2 == "error"
    assert "Magic bytes do not match" in str(err2)


def test_vendor_boot_image_parsing(tmp_path):
    vboot_path = tmp_path / "vendor_boot.img"

    # Magic (8s), header_version (I = 4), page_size (I = 4096), kernel_addr (I), ramdisk_addr (I), vendor_ramdisk_size (I = 2048)
    magic = b"VNDRBOOT"
    version = 4
    page_size = 4096
    v_ramdisk_size = 2048

    hdr = struct.pack("<8s4I", magic, version, page_size, 0x10008000, 0x11000000)
    hdr += struct.pack("<I", v_ramdisk_size)
    hdr = bytearray(hdr.ljust(2200, b"\x00"))
    # At offset 2112: vendor_ramdisk_table_size (I = 128)
    # At offset 2120: bootconfig_size (I = 512)
    struct.pack_into("<I", hdr, 2112, 128)
    struct.pack_into("<I", hdr, 2120, 512)

    vboot_path.write_bytes(hdr)
    assert detect_file_format(vboot_path) == "android_vendor_boot_image"

    status, findings, _, error = parse_vendor_boot_image(vboot_path, "vendor_boot.img")
    assert status == "observed"
    assert error is None

    f_map = {f.key: f for f in findings}
    assert f_map["vendor_boot.header_version"].value == 4
    assert f_map["vendor_boot.page_size"].value == 4096
    assert f_map["vendor_boot.ramdisk_size_bytes"].value == 2048
    assert f_map["vendor_boot.bootconfig_size_bytes"].value == 512


def test_sparse_image_parsing(tmp_path):
    sparse_path = tmp_path / "system.sparse.img"

    # Build valid sparse image:
    # Header (28 bytes): magic 0xED26FF3A, v1.0, file_hdr_sz=28, chunk_hdr_sz=12, blk_sz=4096, total_blks=10, total_chunks=3
    file_hdr = struct.pack(
        "<I4H4I",
        0xED26FF3A,
        1, 0,
        28, 12,
        4096,
        10, 3,
        0,
    )

    # Chunk 1: RAW chunk (2 blocks = 8192 bytes payload, total_sz = 12 + 8192 = 8204)
    c1_hdr = struct.pack("<2H2I", CHUNK_TYPE_RAW, 0, 2, 8204)
    c1_data = b"\x11" * 8192

    # Chunk 2: FILL chunk (4 blocks, payload = 4 bytes fill value, total_sz = 12 + 4 = 16)
    c2_hdr = struct.pack("<2H2I", CHUNK_TYPE_FILL, 0, 4, 16)
    c2_data = struct.pack("<I", 0xDEADBEEF)

    # Chunk 3: DONT_CARE chunk (4 blocks, payload = 0 bytes, total_sz = 12)
    c3_hdr = struct.pack("<2H2I", CHUNK_TYPE_DONT_CARE, 0, 4, 12)

    data = file_hdr + c1_hdr + c1_data + c2_hdr + c2_data + c3_hdr
    sparse_path.write_bytes(data)

    assert detect_file_format(sparse_path) == "android_sparse_image"

    status, findings, warnings, error = parse_sparse_image(sparse_path, "system.sparse.img")
    assert status == "observed"
    assert error is None
    assert len(warnings) == 0

    f_map = {f.key: f for f in findings}
    assert f_map["sparse.block_size_bytes"].value == 4096
    assert f_map["sparse.declared_total_blocks"].value == 10
    assert f_map["sparse.declared_total_chunks"].value == 3
    assert f_map["sparse.uncompressed_output_size_bytes"].value == 40960
    assert f_map["sparse.structural_consistency"].value == "consistent"
    assert f_map["sparse.chunk_type_distribution"].value["raw"] == 1
    assert f_map["sparse.chunk_type_distribution"].value["fill"] == 1
    assert f_map["sparse.chunk_type_distribution"].value["dont_care"] == 1


def test_sparse_image_corrupted_lengths(tmp_path):
    sparse_path = tmp_path / "bad.sparse.img"
    # Declared total_chunks = 2, total_blks = 10, but chunk data is truncated
    file_hdr = struct.pack("<I4H4I", 0xED26FF3A, 1, 0, 28, 12, 4096, 10, 2, 0)
    c1_hdr = struct.pack("<2H2I", CHUNK_TYPE_RAW, 0, 2, 8204)
    # Give only 100 bytes instead of 8192
    data = file_hdr + c1_hdr + (b"\x00" * 100)
    sparse_path.write_bytes(data)

    status, findings, warnings, _ = parse_sparse_image(sparse_path, "bad.sparse.img")
    assert status == "observed"
    assert len(warnings) > 0
    f_map = {f.key: f for f in findings}
    assert f_map["sparse.structural_consistency"].status == "error"


def test_zip_archive_clean_and_component_detection(tmp_path):
    zip_path = tmp_path / "ota_update.zip"

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("boot.img", b"ANDROID!" + b"\x00" * 100)
        zf.writestr("payload.bin", b"CrAU" + b"\x00" * 50)
        zf.writestr("vbmeta.img", b"AVB0" + b"\x00" * 50)
        zf.writestr(
            "META-INF/com/android/metadata",
            "ota-type=AB\npost-build=google/pixel7/panther:13/TQ1A.230205.002:user/release-keys\npost-timestamp=1675555200\n",
        )

    assert detect_file_format(zip_path) == "zip_archive"

    status, findings, warnings, error = parse_zip_archive(zip_path, "ota_update.zip")
    assert status == "observed"
    assert error is None
    assert len(warnings) == 0

    f_map = {f.key: f for f in findings}
    assert f_map["zip.total_entries"].value == 4
    assert f_map["zip.archive_safety_audit"].value == "clean"

    comps = [c["archive_path"] for c in f_map["zip.detected_firmware_components"].value]
    assert "boot.img" in comps
    assert "payload.bin" in comps
    assert "vbmeta.img" in comps

    assert f_map["ota_metadata.ota-type"].value == "AB"
    assert "TQ1A.230205.002" in f_map["ota_metadata.post-build"].value


def test_zip_archive_security_traversal_and_duplicates(tmp_path):
    zip_path = tmp_path / "traversal.zip"

    # ZipFile prevents ../ in writestr normally unless ZipInfo is crafted directly
    with zipfile.ZipFile(zip_path, "w") as zf:
        zinfo_trav = zipfile.ZipInfo(filename="../etc/shadow")
        zf.writestr(zinfo_trav, b"root::0:0:root:::")
        # Duplicate entry
        zf.writestr("duplicate.txt", b"content 1")
        zf.writestr("duplicate.txt", b"content 2")

    status, findings, warnings, _ = parse_zip_archive(zip_path, "traversal.zip")
    assert status == "observed"
    assert any("path traversal" in w.lower() for w in warnings)
    assert any("duplicate" in w.lower() for w in warnings)

    f_map = {f.key: f for f in findings}
    audit = f_map["zip.archive_safety_audit"]
    assert audit.status == "error"
    assert "flagged" in audit.value


def test_build_prop_parsing(tmp_path):
    prop_path = tmp_path / "build.prop"
    prop_path.write_text(
        """# Sample build.prop
ro.product.manufacturer=Samsung
ro.product.model=SM-M115F
ro.build.version.release=12
ro.build.version.sdk=31
ro.build.version.security_patch=2023-04-01
ro.build.id=SP1A.210812.016
ro.boot.flash.locked=1
custom.irrelevant.prop=ignored_here
""",
        encoding="utf-8",
    )

    assert detect_file_format(prop_path) == "android_build_prop"

    status, findings, warnings, error = parse_build_prop(prop_path, "build.prop")
    assert status == "observed"
    assert error is None
    assert len(warnings) == 0

    f_map = {f.key: f for f in findings}
    assert f_map["build_prop.ro.product.manufacturer"].value == "Samsung"
    assert f_map["build_prop.ro.product.model"].value == "SM-M115F"
    assert f_map["build_prop.ro.build.version.release"].value == "12"
    assert f_map["build_prop.ro.boot.flash.locked"].value == "1"
