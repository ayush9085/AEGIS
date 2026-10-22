# AEGIS Evaluation Methodology & Research Validity

This document outlines the scientific methodology, validation boundaries, metric definitions, and reproducibility protocols of the **AEGIS Phase 5 Research Evaluation Suite**.

---

## 1. Philosophical Grounding: Implementation Testing vs. Research Validity

In security research systems, it is vital to distinguish between two orthogonal questions:

1. **Software Implementation Correctness (Verification)**:
   *Does the code execute deterministically, parse inputs according to schema, enforce referential graph integrity, and correctly implement its rule logic without crashing or leaking memory?*
   - Addressed by automated unit/integration tests (`pytest`) and static analysis (`ruff`).
   - Outcome is binary: pass or fail.

2. **Research Validity (Validation)**:
   *Do the rules, certainty classifications, and correlations reflect justifiable, scientifically restrained conclusions from the available evidence?*
   - Addressed by the **Ground-Truth Evaluation Corpus** (`aegis evaluation run`).
   - Outcome is categorical, acknowledging ambiguity (`insufficient_evidence`, `incomparable`, `not_applicable`, `conflicting_evidence`).

> [!IMPORTANT]
> **Core Non-Goal**: Passing the AEGIS evaluation suite does **NOT** prove that an Android device is cryptographically authentic, hardware-attested, uncompromised, or free of kernel rootkits. AEGIS evaluates userspace observables and static container structures; it is not an attestation authority.

---

## 2. Ground-Truth Corpus Construction

The AEGIS ground-truth corpus consists of curated cases spanning six evaluation categories:

| Category | Objective | Example Cases |
| :--- | :--- | :--- |
| **A. Normalization & Schema** | Verify multi-source parsing and safe rejection of unsupported formats. | `NORM-01-VALID-PHASE1`, `NORM-05-UNSUPPORTED-SCHEMA-VERSION` |
| **B. Graph Integrity** | Enforce referential integrity, typed relationships, and deterministic sorting. | `GRAPH-01-VALID-TOPOLOGY`, `GRAPH-02-DANGLING-EDGE-REJECTION` |
| **C. Rule Evaluation** | Exercise all 6 deterministic research rules across positive, negative, and boundary states. | `RULE-01-BOOT-CHAIN-COMPLETE-POS`, `RULE-05-DIFF-BOOT-DRIFT-INCOMPARABLE` |
| **D. Cross-Source Correlation** | Validate direct conflict detection and missing baseline inventory accounting. | `CORR-01-CONFLICTING-MODEL-VALUES`, `CORR-02-PARTIAL-CORRELATION-GAPS` |
| **E. Security & Robustness** | Confirm HTML/script injection escaping, path traversal defense, and zero-network isolation. | `SEC-01-HTML-INJECTION-DEFENSE`, `SEC-02-SYMLINK-ESCAPE-PREVENTION` |
| **F. Reproducibility** | Prove byte-for-byte serialization stability and ordering independence. | `REPRO-01-DETERMINISTIC-REPORT-HASH`, `REAL-01-PHYSICAL-HANDSET-EVAL` |

### Avoiding Circular Validation
Ground-truth expectations (`CaseExpectation`) are specified independently of the engine implementation:
- If a rule requires 5 core parameters to conclude completeness, the ground truth independently defines test fixtures with 4 parameters and asserts `insufficient_evidence`.
- The evaluation harness checks actual engine outputs against these pre-declared criteria.

---

## 3. Evaluation Metrics Formulation

AEGIS reports explicit metrics and avoids arbitrary pseudo-probabilistic "security scores":

### A. Categorical Agreement Rate
For multi-class outcomes (`supported`, `contradicted`, `insufficient_evidence`, `not_applicable`, `incomparable`, `error`):
$$\text{Agreement Rate} = \frac{\text{Cases with Exact Outcome Match}}{\text{Total Evaluated Cases for Rule}}$$

### B. Binary Confusion Matrices
Confusion matrices are computed **only** when a case has an explicit binary ground-truth label (`positive` vs. `negative`):
- **True Positive (TP)**: Ground-truth condition satisfied, rule evaluated to `supported`.
- **False Positive (FP)**: Ground-truth condition absent/violated, rule erroneously evaluated to `supported`.
- **True Negative (TN)**: Ground-truth condition absent/violated, rule evaluated to non-supported (`insufficient_evidence` or `contradicted`).
- **False Negative (FN)**: Ground-truth condition satisfied, rule failed to evaluate to `supported`.

$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}, \quad \text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}, \quad F_1 = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

Where binary expectations are not applicable (e.g. multi-source conflict preservation), confusion matrices are omitted with explicit notes.

### C. Reproducibility Rate
$$\text{Reproducibility Rate} = \frac{\text{Repeated Executions Yielding Identical Hashes}}{\text{Total Repeated Ingestion Cases}}$$

---

## 4. Synthetic vs. Physical Provenance Boundaries

- **Synthetic Fixtures**: Test vectors designed to test structural edge cases (e.g., corrupted headers, missing properties, script injection strings).
- **Physical Handset Evidence**: Consented read-only telemetry from real hardware (e.g., Xiaomi 2312DRAABI, HyperOS/Android 15).
- **Boundary Rule (`RULE-PROVENANCE-BOUNDARY`)**: Aggregating synthetic test fixtures with physical device telemetry in the same correlation session is flagged as a provenance violation (`contradicted`, `conflicting_evidence`).

---

## 5. Adding New Ground-Truth Cases

To add a new case to the corpus:
1. Open [`src/aegis/evaluation/corpus.py`](../src/aegis/evaluation/corpus.py).
2. Instantiate an `EvaluationCase` with:
   - Unique, uppercase ID (e.g., `RULE-14-CUSTOM-TEST`).
   - Valid category (`normalization`, `graph_integrity`, `rule_evaluation`, `cross_source_correlation`, `security_robustness`, `reproducibility`).
   - Provenance (`synthetic_fixture` or `physical_handset`).
   - Explicit `CaseExpectation` with expected rule outcomes, missing prerequisites, or expected exceptions.
   - Independent rationale and caveats.
3. Run the evaluation suite:
   ```bash
   ./run.sh evaluation run
   ```

---

## 6. How to Reproduce Evaluations

Run the evaluation suite locally using any of the following commands:

```bash
# 1. Run evaluation suite with terminal summary
./run.sh evaluation run

# 2. Run evaluation suite and output self-contained HTML report
./run.sh evaluation run --format html --out ./evaluation_reports/report.html

# 3. Validate evaluation report schema and metrics reconciliation
./run.sh evaluation validate ./evaluation_reports/evaluation-<timestamp>.json

# 4. Render HTML report from existing JSON report
./run.sh evaluation report ./evaluation_reports/evaluation-<timestamp>.json --format html
```
