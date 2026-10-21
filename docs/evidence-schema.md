# AEGIS Evidence Schema Specification

**Version:** `0.1.0`  
**Specification Status:** Active MVP Standard  
**Format:** JSON (UTF-8)

---

## 1. Schema Overview

The AEGIS Evidence Schema defines a standardized, reproducible, and verifiable format for documenting Android boot-chain and platform reconnaissance observations.

Every evidence document contains eight top-level sections:
1. `schema_version` (string): Semantic version identifier (`0.1.0`).
2. `tool` (object): Name and version of the AEGIS tool that performed collection.
3. `collection` (object): Audit metadata describing the collection session, timestamps, and host context.
4. `device` (object): Non-sensitive device profile and build context.
5. `observations` (array of objects): Detailed evidence records for each probed property.
6. `summary` (object): Quantitative breakdown of observations by status category.
7. `limitations` (array of strings): Explicit technical scope limitations of the collection method.
8. `non_goals` (array of strings): Explicit non-goals clarifying that the report is not a certification of security.

---

## 2. Controlled Status Vocabulary

Every observation item must be assigned exactly one status from the controlled vocabulary:

| Status | Definition | Interpretation & Action |
| :--- | :--- | :--- |
| `observed` | The probe executed successfully and returned a valid, non-empty value. | The observed value is recorded directly (with privacy masking where applicable). |
| `unsupported` | The probe executed successfully, but returned an empty response or indicated the property is nonexistent. | Expected on varied hardware or older Android versions; not proof that a security subsystem is absent. |
| `inaccessible` | The probe was rejected due to permission constraints, SELinux enforcement, or access control. | Indicates userspace boundary limitations; highlights what unprivileged ADB cannot access. |
| `not_applicable` | The probe is not relevant to the target device architecture or OS generation. | Used when a check does not apply to the identified platform. |
| `unknown` | An ambiguous response was received that cannot be definitively classified. | Indicates uncertainty; AEGIS refuses to guess. |
| `error` | The probe failed due to a command error, timeout, or unexpected communication fault. | Error details and stderr are captured in the observation record. |

---

## 3. Data Dictionary

### Top-Level Document

| Field | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `schema_version` | String | Yes | Version of this schema (`0.1.0`). |
| `tool` | Object | Yes | `{"name": "aegis", "version": "0.1.0"}` |
| `collection` | Object | Yes | Session audit metadata. |
| `device` | Object | Yes | Device profile and build identity. |
| `observations` | Array | Yes | List of `Observation` objects. |
| `summary` | Object | Yes | Integer counts for each status type. |
| `limitations` | Array[String]| Yes | Explicit technical limitation statements. |
| `non_goals` | Array[String]| Yes | Non-goal declarations. |

### `collection` Object

| Field | Type | Description |
| :--- | :--- | :--- |
| `timestamp_utc` | String | ISO-8601 UTC timestamp when collection started (`YYYY-MM-DDTHH:MM:SSZ`). |
| `method` | String | Collection method identifier (`adb_read_only`). |
| `scope` | String | Defined scope profile (`phase_one_allowlist`). |
| `consent_given` | Boolean | Confirmation that explicit operator consent was verified prior to execution. |
| `host_os` | String | Operating system of host workstation (e.g. `Darwin 24.1.0`). |
| `host_python` | String | Python runtime version on host (e.g. `3.12.0`). |
| `host_adb_version` | String/Null | Version string reported by `adb version`. |

### `device` Object

| Field | Type | Description |
| :--- | :--- | :--- |
| `serial_redacted` | String | Partially masked hardware serial number (e.g. `R5***67`). |
| `state` | String | ADB connection state (`device`, `unauthorized`, `offline`). |
| `manufacturer` | String/Null | Hardware manufacturer name (e.g. `Samsung`). |
| `model` | String/Null | Device model identifier (e.g. `SM-M115F`). |
| `product_name` | String/Null | Internal product name (e.g. `m11qsnsxx`). |
| `android_version`| String/Null | User-visible Android release version (e.g. `12`). |
| `sdk_version` | String/Null | Android API level integer string (e.g. `31`). |
| `security_patch` | String/Null | Declared security patch date (e.g. `2023-04-01`). |
| `build_id` | String/Null | Build identifier string (e.g. `SP1A.210812.016`). |
| `fingerprint` | String/Null | Full Android build fingerprint. |

### `Observation` Object

| Field | Type | Description |
| :--- | :--- | :--- |
| `key` | String | Unique dot-notated probe key (e.g. `boot.verifiedbootstate`). |
| `label` | String | Human-readable label for reports (e.g. `Verified Boot State`). |
| `status` | String | Exactly one of the 6 controlled statuses. |
| `value` | Any | Normalized value (or `null` if not observed). |
| `raw_value` | String/Null | Sanitized raw command output (redacted if sensitive). |
| `source_command` | Array[String]| Argument vector used to execute the probe (e.g. `["adb", "-s", "<device>", "shell", "getprop", "..."]`). |
| `collected_at` | String | ISO-8601 UTC timestamp of individual probe completion. |
| `error` | String/Null | Error message or stderr output if status is `error` or `inaccessible`. |
| `caveat` | String | Technical limitation and interpretation note. |
| `redacted` | Boolean | True if output underwent privacy masking. |

---

## 4. Synthetic Example Document

See [tests/fixtures/sample_evidence.json](file:///Users/ayush9085/Documents/AEGIS/tests/fixtures/sample_evidence.json) for a complete, schema-compliant synthetic reference document.
