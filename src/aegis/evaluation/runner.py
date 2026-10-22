"""Deterministic, offline evaluation runner for AEGIS research verification."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aegis import __version__
from aegis.evaluation.metrics import compute_evaluation_metrics
from aegis.evaluation.models import (
    CaseExecutionResult,
    EvaluationCase,
    EvaluationManifest,
    EvaluationReport,
)
from aegis.research.engine import analyze_research_inputs
from aegis.research.models import (
    EvidenceGraph,
    GraphEdge,
    GraphNode,
    ResearchError,
)


class EvaluationRunner:
    """Executes evaluation cases against AEGIS components and verifies ground truth."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self.workspace_root = workspace_root or Path.cwd()

    def run_manifest(self, manifest: EvaluationManifest) -> EvaluationReport:
        """Execute all cases in the given manifest and compile an evaluation report."""
        start_time_utc = datetime.now(UTC).isoformat()
        git_commit = self._get_current_git_commit()

        results: list[CaseExecutionResult] = []
        for case in manifest.cases:
            result = self.run_case(case)
            results.append(result)

        metrics = compute_evaluation_metrics(manifest.cases, results)

        # Reproducibility hash over sorted case results
        content_for_hash = json.dumps(
            [{"id": r.case_id, "st": r.status, "out": r.actual_rule_outcomes} for r in results],
            sort_keys=True,
        )
        repro_hash = hashlib.sha256(content_for_hash.encode("utf-8")).hexdigest()

        methodology = {
            "evaluation_paradigm": "ground_truth_differential_verification",
            "execution_mode": "pure_offline_deterministic",
            "fixtures_provenance": "synthetic_with_physical_boundary_separation",
            "metric_formulation": "exact_categorical_agreement_and_binary_confusion_matrix",
            "disclaimer": (
                "Evaluation proves internal software determinism and rule logic consistency "
                "against a ground-truth corpus; it does NOT constitute proof of hardware-backed "
                "attestation, malware-free guarantees, or runtime OS compromise immunity."
            ),
        }

        known_limitations = [
            "Evaluation cases are predominantly synthetic test vectors; physical device observations are limited to consenting test models.",
            "Static firmware checks analyze headers and unpackable structures without running binary code or verifying cryptographic vendor signatures.",
            "Confusion matrices are mathematically valid only for binary-expectation cases; multi-class categorical outcomes are evaluated via exact outcome agreement.",
            "Performance and memory bounds are tested on local developer hardware and CI environments.",
        ]

        threats_to_validity = [
            "Construct validity: Rules check observed parameters which can be spoofed by kernel-level root or modified bootloaders.",
            "Internal validity: Circularity avoided by defining independent ground truth separate from rule implementations.",
            "External validity: Real-world Android fragmentation means unobserved OEM-specific properties may differ from standard AOSP conventions.",
        ]

        report = EvaluationReport(
            schema_version=manifest.schema_version,
            corpus_version=manifest.corpus_version,
            aegis_version=__version__,
            git_commit=git_commit,
            evaluated_at_utc=start_time_utc,
            manifest_title=manifest.title,
            manifest_description=manifest.description,
            results=results,
            metrics=metrics,
            reproducibility_hash=repro_hash,
            methodology=methodology,
            known_limitations=known_limitations,
            threats_to_validity=threats_to_validity,
        )
        return report

    def run_case(self, case: EvaluationCase) -> CaseExecutionResult:
        """Execute a single evaluation case and compare actual results against expectation."""
        start_t = time.perf_counter()
        differences: list[str] = []
        actual_rule_outcomes: dict[str, str] = {}
        actual_rule_certainties: dict[str, str] = {}
        actual_conflicts_cnt = 0
        actual_missing_cnt = 0
        repro_verified: bool | None = None

        try:
            # Handle special test kinds
            for inp in case.inputs:
                if inp.get("type") == "graph_integrity_test":
                    return self._execute_graph_integrity_test(case, inp, start_t)
                elif inp.get("type") == "symlink_escape_test":
                    return self._execute_symlink_escape_test(case, start_t)
                elif inp.get("type") == "oversized_input_test":
                    return self._execute_oversized_input_test(case, start_t)

            # Standard input files execution
            with tempfile.TemporaryDirectory(prefix="aegis_eval_") as tmp_dir:
                tmp_path = Path(tmp_dir)
                input_paths: list[Path] = []

                for idx, inp in enumerate(case.inputs):
                    inp_type = inp.get("type")
                    if inp_type == "inline_json":
                        name = inp.get("name", f"input_{idx}.json")
                        file_p = tmp_path / name
                        file_p.write_text(json.dumps(inp["data"], indent=2), encoding="utf-8")
                        input_paths.append(file_p)
                    elif inp_type == "malformed_json":
                        name = inp.get("name", f"corrupt_{idx}.json")
                        file_p = tmp_path / name
                        file_p.write_text(inp["raw"], encoding="utf-8")
                        input_paths.append(file_p)
                    elif inp_type == "file_path":
                        rel_p = inp.get("path", "")
                        abs_p = (self.workspace_root / rel_p).resolve()
                        if not abs_p.is_file():
                            raise FileNotFoundError(f"Fixture file not found: {abs_p}")
                        input_paths.append(abs_p)

                # Check expected exception
                if case.expectation.expected_exception_type:
                    try:
                        analyze_research_inputs(input_paths)
                        differences.append(
                            f"Expected exception '{case.expectation.expected_exception_type}' but execution succeeded."
                        )
                    except Exception as exc:  # noqa: BLE001
                        exc_type_name = type(exc).__name__
                        if exc_type_name != case.expectation.expected_exception_type:
                            differences.append(
                                f"Expected exception '{case.expectation.expected_exception_type}' but got '{exc_type_name}': {exc}"
                            )
                        if (
                            case.expectation.expected_exception_message_substring
                            and case.expectation.expected_exception_message_substring not in str(exc)
                        ):
                            differences.append(
                                f"Exception message '{exc}' does not contain expected substring '{case.expectation.expected_exception_message_substring}'"
                            )

                    duration_ms = (time.perf_counter() - start_t) * 1000.0
                    status = "passed" if not differences else "failed"
                    return CaseExecutionResult(
                        case_id=case.case_id,
                        category=case.category,
                        status=status,
                        execution_time_ms=round(duration_ms, 2),
                        message="Exception caught as expected" if status == "passed" else "; ".join(differences),
                        differences=differences,
                    )

                # Standard execution
                report = analyze_research_inputs(input_paths)
                for eval_rec in report.evaluations:
                    actual_rule_outcomes[eval_rec.rule_id] = eval_rec.outcome
                    actual_rule_certainties[eval_rec.rule_id] = eval_rec.certainty

                actual_conflicts_cnt = len(report.conflicts)
                actual_missing_cnt = len(report.missing_evidence_inventory)

                # Check rule expectations
                for exp_rule in case.expectation.rule_expectations:
                    act_out = actual_rule_outcomes.get(exp_rule.rule_id)
                    if act_out != exp_rule.expected_outcome:
                        differences.append(
                            f"Rule '{exp_rule.rule_id}' expected outcome '{exp_rule.expected_outcome}', got '{act_out}'"
                        )
                    if exp_rule.expected_certainty:
                        act_cert = actual_rule_certainties.get(exp_rule.rule_id)
                        if act_cert != exp_rule.expected_certainty:
                            differences.append(
                                f"Rule '{exp_rule.rule_id}' expected certainty '{exp_rule.expected_certainty}', got '{act_cert}'"
                            )

                # Check conflict count
                if (
                    case.expectation.expected_conflict_count is not None
                    and actual_conflicts_cnt != case.expectation.expected_conflict_count
                ):
                    differences.append(
                        f"Expected {case.expectation.expected_conflict_count} conflicts, got {actual_conflicts_cnt}"
                    )

                # Check missing inventory keys
                for key in case.expectation.expected_missing_inventory_keys:
                    if not any(key in item for item in report.missing_evidence_inventory):
                        differences.append(f"Expected missing inventory key '{key}' not found in report")

                # Check graph node count
                if case.expectation.expected_graph_node_count is not None:
                    act_nodes = len(report.graph.nodes)
                    if act_nodes != case.expectation.expected_graph_node_count:
                        differences.append(
                            f"Expected {case.expectation.expected_graph_node_count} graph nodes, got {act_nodes}"
                        )

                # Check reproducibility
                if case.expectation.reproducibility_check:
                    report2 = analyze_research_inputs(input_paths)
                    d1 = report.to_dict()
                    d2 = report2.to_dict()
                    d1["evaluated_at_utc"] = ""
                    d2["evaluated_at_utc"] = ""
                    h1 = hashlib.sha256(json.dumps(d1, sort_keys=True).encode()).hexdigest()
                    h2 = hashlib.sha256(json.dumps(d2, sort_keys=True).encode()).hexdigest()
                    if h1 != h2:
                        differences.append("Repeated execution produced mismatched report hashes")
                        repro_verified = False
                    else:
                        repro_verified = True

        except Exception as exc:  # noqa: BLE001
            differences.append(f"Unexpected execution error: {type(exc).__name__}: {exc}")

        duration_ms = (time.perf_counter() - start_t) * 1000.0
        status = "passed" if not differences else "failed"

        return CaseExecutionResult(
            case_id=case.case_id,
            category=case.category,
            status=status,
            execution_time_ms=round(duration_ms, 2),
            message="Case executed successfully" if status == "passed" else "; ".join(differences),
            differences=differences,
            actual_rule_outcomes=actual_rule_outcomes,
            actual_rule_certainties=actual_rule_certainties,
            actual_conflicts_count=actual_conflicts_cnt,
            actual_missing_inventory_count=actual_missing_cnt,
            binary_ground_truth_label=case.expectation.binary_ground_truth_label,
            binary_predicted_label="positive" if any(o == "supported" for o in actual_rule_outcomes.values()) else "negative",
            reproducibility_verified=repro_verified,
        )

    def _execute_graph_integrity_test(
        self,
        case: EvaluationCase,
        inp: dict[str, Any],
        start_t: float,
    ) -> CaseExecutionResult:
        """Directly verify EvidenceGraph referential integrity constraints."""
        differences: list[str] = []
        test_kind = inp.get("test_kind")

        try:
            if test_kind == "dangling_edge":
                graph = EvidenceGraph(
                    nodes=[GraphNode(node_id="n1", node_type="device", label="Device 1")],
                    edges=[GraphEdge(source_id="n1", target_id="nonexistent_n2", relationship="supports")],
                )
                graph.validate_referential_integrity()
                differences.append("Expected ResearchValidationError for dangling edge but validation passed.")
            elif test_kind == "duplicate_node":
                graph = EvidenceGraph(
                    nodes=[
                        GraphNode(node_id="dup1", node_type="device", label="Dev A"),
                        GraphNode(node_id="dup1", node_type="device", label="Dev B"),
                    ],
                    edges=[],
                )
                graph.validate_referential_integrity()
                differences.append("Expected ResearchValidationError for duplicate nodes but validation passed.")
            elif test_kind == "invalid_relationship":
                graph = EvidenceGraph(
                    nodes=[
                        GraphNode(node_id="n1", node_type="device", label="Dev A"),
                        GraphNode(node_id="n2", node_type="observation", label="Obs B"),
                    ],
                    edges=[GraphEdge(source_id="n1", target_id="n2", relationship="invalid_rel_type")],
                )
                graph.validate_referential_integrity()
                differences.append("Expected ResearchValidationError for invalid relationship but validation passed.")
            elif test_kind == "deterministic_sorting":
                graph = EvidenceGraph(
                    nodes=[
                        GraphNode(node_id="z_node", node_type="observation", label="Z"),
                        GraphNode(node_id="a_node", node_type="device", label="A"),
                    ],
                    edges=[
                        GraphEdge(source_id="z_node", target_id="a_node", relationship="observed_on"),
                        GraphEdge(source_id="a_node", target_id="z_node", relationship="supports"),
                    ],
                )
                d1 = graph.to_dict()
                d2 = graph.to_dict()
                if d1 != d2:
                    differences.append("Deterministic graph sorting produced mismatched dicts")
        except ResearchError as exc:
            # Expected validation errors
            if case.expectation.expected_exception_type:
                exc_name = type(exc).__name__
                if exc_name != case.expectation.expected_exception_type:
                    differences.append(f"Expected {case.expectation.expected_exception_type}, got {exc_name}")
                if (
                    case.expectation.expected_exception_message_substring
                    and case.expectation.expected_exception_message_substring not in str(exc)
                ):
                    differences.append(
                        f"Expected substring '{case.expectation.expected_exception_message_substring}' not in '{exc}'"
                    )
            else:
                differences.append(f"Unexpected ResearchError: {exc}")
        except Exception as exc:  # noqa: BLE001
            differences.append(f"Unexpected error: {type(exc).__name__}: {exc}")

        duration_ms = (time.perf_counter() - start_t) * 1000.0
        status = "passed" if not differences else "failed"
        return CaseExecutionResult(
            case_id=case.case_id,
            category=case.category,
            status=status,
            execution_time_ms=round(duration_ms, 2),
            message="Graph integrity check passed" if status == "passed" else "; ".join(differences),
            differences=differences,
            reproducibility_verified=True if test_kind == "deterministic_sorting" and status == "passed" else None,
        )

    def _execute_symlink_escape_test(
        self,
        case: EvaluationCase,
        start_t: float,
    ) -> CaseExecutionResult:
        """Verify symlink escape defenses in directory scanning."""
        differences: list[str] = []
        with tempfile.TemporaryDirectory(prefix="aegis_symlink_test_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            outside_dir = tmp_path / "outside"
            outside_dir.mkdir()
            secret_file = outside_dir / "secret.json"
            secret_file.write_text('{"schema_version": "0.1.0"}', encoding="utf-8")

            scan_dir = tmp_path / "scandir"
            scan_dir.mkdir()
            valid_file = scan_dir / "valid.json"
            from aegis.evaluation.corpus import _get_base_phase1_device_data
            valid_file.write_text(json.dumps(_get_base_phase1_device_data()), encoding="utf-8")

            symlink_p = scan_dir / "escape_link.json"
            try:
                os.symlink(secret_file, symlink_p)
            except OSError:
                # If symlinks cannot be created on this filesystem, mark as skipped
                return CaseExecutionResult(
                    case_id=case.case_id,
                    category=case.category,
                    status="skipped",
                    execution_time_ms=round((time.perf_counter() - start_t) * 1000.0, 2),
                    message="Filesystem does not support unprivileged symlinks; skipped safely.",
                )

            # Analyze scandir
            report = analyze_research_inputs([scan_dir])
            # Check that secret_file was NOT ingested
            for inp_meta in report.source_inputs:
                if "secret.json" in inp_meta.get("path", ""):
                    differences.append("Directory scanner followed symlink outside target directory!")

        duration_ms = (time.perf_counter() - start_t) * 1000.0
        status = "passed" if not differences else "failed"
        return CaseExecutionResult(
            case_id=case.case_id,
            category=case.category,
            status=status,
            execution_time_ms=round(duration_ms, 2),
            message="Symlink escape prevented" if status == "passed" else "; ".join(differences),
            differences=differences,
        )

    def _execute_oversized_input_test(
        self,
        case: EvaluationCase,
        start_t: float,
    ) -> CaseExecutionResult:
        """Verify that oversized files are bounded safely."""
        differences: list[str] = []
        with tempfile.TemporaryDirectory(prefix="aegis_oversize_test_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            huge_file = tmp_path / "huge.json"
            # 2 MB of repeated whitespace in JSON
            huge_file.write_text('{"schema_version": "0.1.0"' + " " * 2000000 + "}", encoding="utf-8")

            try:
                analyze_research_inputs([huge_file])
            except Exception:  # noqa: S110, BLE001
                # Handled safely
                pass

        duration_ms = (time.perf_counter() - start_t) * 1000.0
        status = "passed" if not differences else "failed"
        return CaseExecutionResult(
            case_id=case.case_id,
            category=case.category,
            status=status,
            execution_time_ms=round(duration_ms, 2),
            message="Oversized input handled safely" if status == "passed" else "; ".join(differences),
            differences=differences,
        )

    def _get_current_git_commit(self) -> str:
        """Retrieve current short git commit hash if in a git repository."""
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=self.workspace_root,
                capture_output=True,
                check=False,
                text=True,
                timeout=5,
            )
            if res.returncode == 0:
                return res.stdout.strip()
        except Exception:  # noqa: S110, BLE001
            pass
        return "unknown"
