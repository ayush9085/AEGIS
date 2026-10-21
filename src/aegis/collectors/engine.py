"""Core collection engine running allowlisted probes against an authorized target."""

from __future__ import annotations

import platform
from datetime import UTC, datetime
from typing import Any

from aegis import __version__
from aegis.adb import get_adb_version, list_devices, run_adb_command
from aegis.collectors.allowlist import ALLOWLIST_ITEMS
from aegis.redaction import redact_sensitive_text, redact_serial
from aegis.schema import (
    CollectionMetadata,
    DeviceContext,
    EvidenceReport,
    Observation,
    SummaryCounts,
)


def get_collection_plan() -> list[dict[str, str]]:
    """Return an inspection plan previewing all allowlisted probes."""
    plan = []
    for item in ALLOWLIST_ITEMS:
        plan.append(
            {
                "key": item.key,
                "label": item.label,
                "method": " ".join(item.command_args),
                "description": item.description,
                "caveat": item.caveat,
            }
        )
    return plan


def collect_device_evidence(
    serial: str,
    consent_given: bool = True,
    timeout: float = 10.0,
    adb_path: str | None = None,
) -> EvidenceReport:
    """Execute allowlisted read-only probes against a single authorized device.

    Enforces consent, device presence, and read-only non-destructive bounds.
    """
    if not consent_given:
        raise PermissionError(
            "Evidence collection halted: explicit user consent is required before probing device."
        )

    # Verify device exists and is authorized
    devices = list_devices(adb_path=adb_path)
    target_device = next((d for d in devices if d.serial == serial), None)
    if target_device is None:
        raise RuntimeError(
            f"Device '{serial}' was not found in attached ADB devices. Run 'aegis devices' to inspect."
        )

    if not target_device.is_authorized:
        raise RuntimeError(
            f"Target device '{serial}' is not in authorized 'device' state (reported: '{target_device.state}').\n"
            f"Authorize USB debugging on the handset display and try again."
        )

    collected_at = datetime.now(UTC).isoformat()
    observations: list[Observation] = []

    for item in ALLOWLIST_ITEMS:
        try:
            returncode, stdout, stderr = run_adb_command(
                serial=serial,
                args=item.command_args,
                timeout=timeout,
                adb_path=adb_path,
            )
        except TimeoutError as exc:
            observations.append(
                Observation(
                    key=item.key,
                    label=item.label,
                    status="error",
                    value=None,
                    raw_value=None,
                    source_command=["adb", "-s", "<device>"] + item.command_args,
                    collected_at=collected_at,
                    error=f"Timeout after {timeout}s: {exc}",
                    caveat=item.caveat,
                )
            )
            continue
        except (OSError, RuntimeError) as exc:
            observations.append(
                Observation(
                    key=item.key,
                    label=item.label,
                    status="error",
                    value=None,
                    raw_value=None,
                    source_command=["adb", "-s", "<device>"] + item.command_args,
                    collected_at=collected_at,
                    error=str(exc),
                    caveat=item.caveat,
                )
            )
            continue

        out_clean = stdout.strip()
        err_clean = stderr.strip()

        if returncode != 0:
            lower_err = err_clean.lower()
            if "permission denied" in lower_err or "inaccessible" in lower_err:
                status = "inaccessible"
                err_msg = err_clean or "Permission denied by SELinux / system."
            else:
                status = "error"
                err_msg = err_clean or f"Command exited with non-zero status {returncode}."

            observations.append(
                Observation(
                    key=item.key,
                    label=item.label,
                    status=status,
                    value=None,
                    raw_value=None,
                    source_command=["adb", "-s", "<device>"] + item.command_args,
                    collected_at=collected_at,
                    error=err_msg,
                    caveat=item.caveat,
                )
            )
            continue

        if not out_clean:
            observations.append(
                Observation(
                    key=item.key,
                    label=item.label,
                    status="unsupported",
                    value=None,
                    raw_value="",
                    source_command=["adb", "-s", "<device>"] + item.command_args,
                    collected_at=collected_at,
                    error="Property is empty or unsupported on this target build.",
                    caveat=item.caveat,
                )
            )
            continue

        # Clean/sanitize value
        safe_val: Any = out_clean
        safe_raw: str | None = out_clean
        is_redacted = False

        if item.is_sensitive:
            safe_val = redact_sensitive_text(out_clean, known_serials=[serial])
            safe_raw = safe_val
            is_redacted = True

        observations.append(
            Observation(
                key=item.key,
                label=item.label,
                status="observed",
                value=safe_val,
                raw_value=safe_raw,
                source_command=["adb", "-s", "<device>"] + item.command_args,
                collected_at=collected_at,
                error=None,
                caveat=item.caveat,
                redacted=is_redacted,
            )
        )

    # Build device summary context
    obs_map = {o.key: o.value for o in observations if o.status == "observed"}
    device_ctx = DeviceContext(
        serial_redacted=redact_serial(serial),
        state=target_device.state,
        manufacturer=obs_map.get("product.manufacturer"),
        model=obs_map.get("product.model"),
        product_name=obs_map.get("product.name"),
        android_version=obs_map.get("build.version.release"),
        sdk_version=obs_map.get("build.version.sdk"),
        security_patch=obs_map.get("build.version.security_patch"),
        build_id=obs_map.get("build.id"),
        fingerprint=obs_map.get("build.fingerprint"),
    )

    metadata = CollectionMetadata(
        timestamp_utc=collected_at,
        method="adb_read_only",
        scope="phase_one_allowlist",
        consent_given=consent_given,
        host_os=f"{platform.system()} {platform.release()}",
        host_python=platform.python_version(),
        host_adb_version=get_adb_version(adb_path=adb_path),
    )

    summary = SummaryCounts.from_observations(observations)

    return EvidenceReport(
        schema_version="0.1.0",
        tool={"name": "aegis", "version": __version__},
        collection=metadata,
        device=device_ctx,
        observations=observations,
        summary=summary,
    )
