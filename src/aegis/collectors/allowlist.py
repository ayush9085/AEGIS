"""Strict, read-only allowlist definitions for Android property collection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllowlistItem:
    """Specification of an allowlisted read-only evidence probe."""

    key: str
    label: str
    command_args: list[str]
    description: str
    caveat: str
    is_sensitive: bool = False


# Strictly bounded, read-only collection targets
ALLOWLIST_ITEMS: list[AllowlistItem] = [
    AllowlistItem(
        key="product.manufacturer",
        label="Manufacturer",
        command_args=["shell", "getprop", "ro.product.manufacturer"],
        description="Hardware/device manufacturer name.",
        caveat="Userspace property; identifies brand, not hardware authenticity.",
    ),
    AllowlistItem(
        key="product.model",
        label="Model Identifier",
        command_args=["shell", "getprop", "ro.product.model"],
        description="Market-facing device model string.",
        caveat="Read from build properties; may vary across regional carrier variants.",
    ),
    AllowlistItem(
        key="product.name",
        label="Product Name",
        command_args=["shell", "getprop", "ro.product.name"],
        description="Internal product/board name assigned by vendor.",
        caveat="Useful for identifying specific firmware target branch.",
    ),
    AllowlistItem(
        key="product.device",
        label="Device Codename",
        command_args=["shell", "getprop", "ro.product.device"],
        description="Target hardware codename.",
        caveat="Identifies hardware platform family in standard Android builds.",
    ),
    AllowlistItem(
        key="build.version.release",
        label="Android Release",
        command_args=["shell", "getprop", "ro.build.version.release"],
        description="User-visible Android OS release version.",
        caveat="Reported by system image; indicates nominal Android version level.",
    ),
    AllowlistItem(
        key="build.version.sdk",
        label="SDK / API Level",
        command_args=["shell", "getprop", "ro.build.version.sdk"],
        description="Android framework API level integer.",
        caveat="Framework API version indicator.",
    ),
    AllowlistItem(
        key="build.version.security_patch",
        label="Security Patch Level",
        command_args=["shell", "getprop", "ro.build.version.security_patch"],
        description="Security patch date (YYYY-MM-DD).",
        caveat="Indicates declared software security patch level, not live exploit resistance.",
    ),
    AllowlistItem(
        key="build.id",
        label="Build ID",
        command_args=["shell", "getprop", "ro.build.id"],
        description="Software build identifier string.",
        caveat="Identifies vendor compilation snapshot.",
    ),
    AllowlistItem(
        key="build.fingerprint",
        label="Build Fingerprint",
        command_args=["shell", "getprop", "ro.build.fingerprint"],
        description="Unique system build fingerprint string.",
        caveat="Primary Android identity string; used for OTA matching and compatibility.",
    ),
    AllowlistItem(
        key="bootloader.version",
        label="Bootloader Version",
        command_args=["shell", "getprop", "ro.bootloader"],
        description="Reported primary bootloader version.",
        caveat="Reported by bootloader to kernel cmdline or property service; not full bootloader code.",
    ),
    AllowlistItem(
        key="kernel.version",
        label="Kernel Version",
        command_args=["shell", "uname", "-r"],
        description="Running Linux kernel release version.",
        caveat="Reported by kernel syscall via uname; indicates kernel release family.",
    ),
    AllowlistItem(
        key="boot.verifiedbootstate",
        label="Verified Boot State",
        command_args=["shell", "getprop", "ro.boot.verifiedbootstate"],
        description="Android Verified Boot state (e.g., green, yellow, orange, red).",
        caveat="Reflects boot state passed by bootloader to kernel. Does not independently verify TrustZone/TEE.",
    ),
    AllowlistItem(
        key="boot.vbmeta_state",
        label="VBMeta Device State",
        command_args=["shell", "getprop", "ro.boot.vbmeta.device_state"],
        description="AVB 2.0 metadata state (locked/unlocked).",
        caveat="Reported by AVB subsystem; unexposed on older devices or non-AVB bootloaders.",
    ),
    AllowlistItem(
        key="boot.flash_locked",
        label="Flash Lock State",
        command_args=["shell", "getprop", "ro.boot.flash.locked"],
        description="Hardware bootloader partition flash lock indicator.",
        caveat="1 usually indicates locked bootloader flash; 0 indicates unlocked. Vendor-dependent.",
    ),
    AllowlistItem(
        key="boot.veritymode",
        label="dm-verity Mode",
        command_args=["shell", "getprop", "ro.boot.veritymode"],
        description="dm-verity kernel mount enforcement mode (e.g. enforcing).",
        caveat="Indicates whether block verification was active during initial system mount.",
    ),
]
