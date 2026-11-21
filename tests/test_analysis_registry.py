import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PLUGIN_ROOT/'scripts'))
INIT_PROJECT = PLUGIN_ROOT / "scripts" / "init_project.py"
REGISTRY = PLUGIN_ROOT / "scripts" / "analysis_registry.py"
VALIDATE_PROJECT = PLUGIN_ROOT / "scripts" / "validate_project.py"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONUTF8": "1"},
        check=False,
    )


def read_frontmatter(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---\n", 4)
    return json.loads(text[4:end])


class AnalysisRegistryTests(unittest.TestCase):
    def test_origin_is_preserved_through_adoption_and_cannot_be_relabelled(self):
        import copy
        import analysis_contracts as c
        import analysis_registry as registry
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); entry=self._valid_entry(root)
            path=root/'analysis-run.json';run=json.loads(path.read_text(encoding='utf-8'))
            run['schema_version']=2
            run['analysis_context']={'inferential_status':'EXPLORATORY','analysis_role':'CANDIDATE',
                'basis_ref':'post-result proposal','search_set_id':'set-1','parent_analysis_id':None,'discovered_after_results':True}
            run['context_hash']=c.context_hash(run['analysis_context'])
            path.write_text(json.dumps(run),encoding='utf-8')
            reference=registry.validate_formal_reference(entry,root)
            self.assertEqual(reference.get('analysis_context'),run['analysis_context'])
            bad=copy.deepcopy(entry);bad['analysis_context']={**run['analysis_context'],'inferential_status':'PRESPECIFIED','discovered_after_results':False}
            with self.assertRaisesRegex(ValueError,'context|origin'):
                registry.validate_formal_reference(bad,root)

    def _project(self, root: Path) -> tuple[Path, str]:
        manuscript = root / "paper.txt"
        original = "authoritative manuscript"
        manuscript.write_text(original, encoding="utf-8")
        result = run_script(
            INIT_PROJECT,
            "--project-root", str(root),
            "--manuscript", str(manuscript),
            "--confirm-create",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return manuscript, original

    def test_registry_creation_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            self._project(root)
            result = run_script(REGISTRY, "init", "--project-root", str(root))
            self.assertEqual(result.returncode, 2)
            self.assertIn("--confirm-create is required", result.stderr)
            self.assertFalse(
                (root / ".psychology-paper" / "ANALYSIS_REGISTRY.md").exists()
            )

    def test_registry_initialization_updates_project_state_not_manuscript(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            manuscript, original = self._project(root)
            result = run_script(
                REGISTRY,
                "init",
                "--project-root", str(root),
                "--confirm-create",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            registry_path = root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
            self.assertTrue(registry_path.is_file())
            registry = read_frontmatter(registry_path)
            self.assertEqual(registry["schema"], "psychology-paper-analysis-registry")
            self.assertEqual(registry["analyses"], [])
            project = read_frontmatter(root / ".psychology-paper" / "PROJECT.md")
            self.assertEqual(
                project["optional_state_files"]["analysis_registry"],
                str(registry_path.resolve()),
            )
            self.assertEqual(manuscript.read_text(encoding="utf-8"), original)

    def test_result_is_not_registered_without_user_adoption(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            self._project(root)
            self.assertEqual(
                run_script(
                    REGISTRY,
                    "init",
                    "--project-root", str(root),
                    "--confirm-create",
                ).returncode,
                0,
            )
            entry_path = root / "candidate.json"
            entry_path.write_text(
                json.dumps(self._valid_entry(root), ensure_ascii=False), encoding="utf-8"
            )
            result = run_script(
                REGISTRY,
                "add",
                "--project-root", str(root),
                "--entry", str(entry_path),
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("--confirm-adopt is required", result.stderr)
            registry = read_frontmatter(
                root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
            )
            self.assertEqual(registry["analyses"], [])

    def test_adopted_result_with_one_formal_source_is_registered(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            self._project(root)
            run_script(
                REGISTRY,
                "init",
                "--project-root", str(root),
                "--confirm-create",
            )
            entry_path = root / "adopted.json"
            entry_path.write_text(
                json.dumps(self._valid_entry(root), ensure_ascii=False), encoding="utf-8"
            )
            result = run_script(
                REGISTRY,
                "add",
                "--project-root", str(root),
                "--entry", str(entry_path),
                "--confirm-adopt",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            registry = read_frontmatter(
                root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
            )
            self.assertEqual(len(registry["analyses"]), 1)
            self.assertEqual(registry["analyses"][0]["adoption_status"], "USER_ADOPTED")

    def test_adopted_result_rejects_two_formal_sources(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            self._project(root)
            run_script(
                REGISTRY,
                "init",
                "--project-root", str(root),
                "--confirm-create",
            )
            entry = self._valid_entry()
            entry["sources"].append(
                {"role": "AUTHORITATIVE", "software": "Python", "version": "3.13"}
            )
            entry_path = root / "conflict.json"
            entry_path.write_text(json.dumps(entry), encoding="utf-8")
            result = run_script(
                REGISTRY,
                "add",
                "--project-root", str(root),
                "--entry", str(entry_path),
                "--confirm-adopt",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("exactly one AUTHORITATIVE source", result.stderr)

    def test_project_validation_rejects_unadopted_registry_entries(self) -> None:
        with tempfile.TemporaryDirectory(prefix="统计登记-") as raw:
            root = Path(raw)
            self._project(root)
            run_script(
                REGISTRY,
                "init",
                "--project-root", str(root),
                "--confirm-create",
            )
            registry_path = root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
            text = registry_path.read_text(encoding="utf-8")
            end = text.find("\n---\n", 4)
            registry = json.loads(text[4:end])
            entry = self._valid_entry()
            entry["adoption_status"] = "CANDIDATE"
            registry["analyses"] = [entry]
            registry_path.write_text(
                "---\n"
                + json.dumps(registry, ensure_ascii=False, indent=2)
                + "\n---\n"
                + text[end + 5 :],
                encoding="utf-8",
            )
            result = run_script(
                VALIDATE_PROJECT, "--project-root", str(root)
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("analysis registry contains an unadopted entry", result.stdout)

    def test_confirmed_adoption_rejects_missing_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            run_script(REGISTRY, "init", "--project-root", str(root), "--confirm-create")
            entry = root / "entry.json"
            entry.write_text(json.dumps(self._valid_entry()), encoding="utf-8")
            result = run_script(REGISTRY, "add", "--project-root", str(root), "--entry", str(entry), "--confirm-adopt")
            self.assertEqual(result.returncode, 2)

    def test_integrity_candidate_immutability_duplicate_and_tamper(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            run_script(REGISTRY, "init", "--project-root", str(root), "--confirm-create")
            entry = self._valid_entry(root)
            candidate = root / "analysis-run.json"
            original = candidate.read_bytes()
            entry_path = root / "entry.json"
            def add():
                entry_path.write_text(json.dumps(entry), encoding="utf-8")
                return run_script(REGISTRY, "add", "--project-root", str(root), "--entry", str(entry_path), "--confirm-adopt", "--json")
            entry["spec_hash"] = "b" * 64
            self.assertEqual(add().returncode, 2)
            entry = self._valid_entry(root)
            result = add()
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertTrue(json.loads(result.stdout)["ok"])
            self.assertEqual(candidate.read_bytes(), original)
            registry_path = root / ".psychology-paper" / "ANALYSIS_REGISTRY.md"
            saved = registry_path.read_bytes()
            self.assertEqual(add().returncode, 3)
            self.assertEqual(registry_path.read_bytes(), saved)
            candidate.write_bytes(original + b" ")
            validated = run_script(VALIDATE_PROJECT, "--project-root", str(root))
            self.assertEqual(validated.returncode, 1)
            self.assertIn("integrity failure", validated.stdout)

    def test_existing_lock_refuses_write_and_is_preserved(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            lock = root / ".psychology-paper" / "analysis.lock"
            lock.write_text("other writer", encoding="utf-8")
            result = run_script(REGISTRY, "init", "--project-root", str(root), "--confirm-create")
            self.assertEqual(result.returncode, 3)
            self.assertEqual(lock.read_text(), "other writer")

    def test_atomic_interruption_and_revision_conflict(self):
        import importlib.util
        from unittest.mock import patch
        sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))
        spec = importlib.util.spec_from_file_location("registry_test_module", REGISTRY)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module.os, "open", side_effect=AssertionError("unconfirmed write")):
            self.assertEqual(module.main(["init", "--project-root", str(PLUGIN_ROOT), "--json"]), 2)
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "state.md"
            path.write_bytes(b"before")
            with patch.object(module.os, "replace", side_effect=OSError("interrupted")):
                with self.assertRaises(OSError): module.atomic_write(path, "after", b"before")
            self.assertEqual(path.read_bytes(), b"before")
            self.assertEqual(list(Path(raw).iterdir()), [path])
            with self.assertRaises(module.Conflict): module.atomic_write(path, "after", b"outdated")
            self.assertEqual(path.read_bytes(), b"before")

    def test_metadata_must_match_actual_computation(self):
        for key, replacement in (("model", {"method": "pearson"}), ("sample", {"n": 207}), ("scoring", {"method": "scale"}), ("software", {"name": "SPSS", "version": "29"})):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                self._project(root)
                run_script(REGISTRY, "init", "--project-root", str(root), "--confirm-create")
                entry = self._valid_entry(root)
                entry[key] = replacement
                path = root / "entry.json"
                path.write_text(json.dumps(entry), encoding="utf-8")
                result = run_script(REGISTRY, "add", "--project-root", str(root), "--entry", str(path), "--confirm-adopt")
                self.assertEqual(result.returncode, 2)

    def test_invented_inference_metadata_is_rejected(self):
        for key, replacement in (("estimation", "one-tailed"), ("bootstrap", {"iterations": 10000, "ci": "BCa"}), ("random_seed", 42)):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                self._project(root)
                run_script(REGISTRY, "init", "--project-root", str(root), "--confirm-create")
                entry = self._valid_entry(root)
                entry[key] = replacement
                path = root / "entry.json"
                path.write_text(json.dumps(entry), encoding="utf-8")
                result = run_script(REGISTRY, "add", "--project-root", str(root), "--entry", str(path), "--confirm-adopt")
                self.assertEqual(result.returncode, 2)

    def test_external_r_mixed_model_registration_and_hash_checks(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            run_script(REGISTRY, "init", "--project-root", str(root), "--confirm-create")
            entry = self._valid_entry()
            entry.update(evidence_kind="external_analysis", model={"method": "R mixed model", "formula": "y ~ x + (1|subject)"},
                         software={"name": "R", "version": "4.4"}, estimation="REML", bootstrap={"iterations": 10000, "ci": "BCa"}, random_seed=42,
                         formal_output="model.rds", external_artifacts=[])
            entry["sources"] = [{"source_id": "r-fit", "role": "AUTHORITATIVE", "software": "R", "version": "4.4"}]
            for role, name, content in (("output", "model.rds", b"synthetic native R model fixture"), ("syntax", "model.R", b"fit <- lmer(y ~ x + (1|subject), data=d)")):
                (root / name).write_bytes(content)
                entry["external_artifacts"].append({"role": role, "path": name, "sha256": hashlib.sha256(content).hexdigest(), "software": "R", "version": "4.4"})
            fields = ("research_question", "design_tags", "observation_unit", "field_map", "scoring", "sample", "model", "software", "estimation", "bootstrap", "random_seed", "input_hash")
            entry["spec_hash"] = hashlib.sha256(json.dumps({k: entry[k] for k in fields}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
            path = root / "entry.json"
            path.write_text(json.dumps(entry), encoding="utf-8")
            def add(confirm=True):
                return run_script(REGISTRY, "add", "--project-root", str(root), "--entry", str(path), *( ["--confirm-adopt"] if confirm else []))
            self.assertEqual(add(False).returncode, 2)
            import copy
            for alteration in ("missing_output", "bad_hash", "software_mismatch", "missing_syntax"):
                bad = copy.deepcopy(entry)
                if alteration == "missing_output": bad["external_artifacts"][0]["path"] = "missing.rds"
                elif alteration == "bad_hash": bad["external_artifacts"][0]["sha256"] = "0" * 64
                elif alteration == "software_mismatch": bad["external_artifacts"][1]["software"] = "SPSS"
                else: bad["external_artifacts"] = bad["external_artifacts"][:1]
                path.write_text(json.dumps(bad), encoding="utf-8")
                self.assertEqual(add().returncode, 2, alteration)
            path.write_text(json.dumps(entry), encoding="utf-8")
            self.assertEqual(add().returncode, 0)
            registry = read_frontmatter(root / ".psychology-paper" / "ANALYSIS_REGISTRY.md")
            self.assertEqual(registry["analyses"][0]["evidence_level"], "EXTERNAL_ARTIFACTS_REGISTERED_NUMERICS_UNVERIFIED")
            self.assertEqual(run_script(VALIDATE_PROJECT, "--project-root", str(root)).returncode, 0)
            (root / "model.R").write_text("changed", encoding="utf-8")
            self.assertEqual(run_script(VALIDATE_PROJECT, "--project-root", str(root)).returncode, 1)

    def test_external_python_new_method_json_output(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            run_script(REGISTRY, "init", "--project-root", str(root), "--confirm-create")
            entry = self._valid_entry()
            entry.update(evidence_kind="external_analysis", model={"method": "permutation_test", "iterations": 999},
                         formal_output="result.json", estimation="Monte Carlo permutation", random_seed=42, external_artifacts=[])
            for role, name, content in (("output", "result.json", b'{"p":0.12,"iterations":999}'), ("syntax", "analysis.py", b"# Author supplied permutation implementation")):
                (root / name).write_bytes(content)
                entry["external_artifacts"].append({"role": role, "path": name, "sha256": hashlib.sha256(content).hexdigest(), "software": "Python", "version": "3.13"})
            fields = ("research_question", "design_tags", "observation_unit", "field_map", "scoring", "sample", "model", "software", "estimation", "bootstrap", "random_seed", "input_hash")
            entry["spec_hash"] = hashlib.sha256(json.dumps({k: entry[k] for k in fields}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
            path = root / "entry.json"
            path.write_text(json.dumps(entry), encoding="utf-8")
            result = run_script(REGISTRY, "add", "--project-root", str(root), "--entry", str(path), "--confirm-adopt")
            self.assertEqual(result.returncode, 0, result.stderr)
            saved = read_frontmatter(root / ".psychology-paper" / "ANALYSIS_REGISTRY.md")["analyses"][0]
            self.assertEqual(saved["formal_output_ref"]["origin_status"], "AUTHOR_ATTESTED")

    def test_external_formal_and_optional_different_software_verifier(self):
        import copy
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._project(root)
            run_script(REGISTRY, "init", "--project-root", str(root), "--confirm-create")
            entry = self._valid_entry()
            entry.update(evidence_kind="external_analysis", software={"name": "R", "version": "4.4"}, formal_output="formal.txt", verification_output="check.json", external_artifacts=[])
            entry["sources"] = [{"source_id": "formal", "role": "AUTHORITATIVE", "software": "R", "version": "4.4"}, {"source_id": "check", "role": "VERIFICATION", "software": "Python", "version": "3.13"}]
            for role, name, source, software, version in (("output", "formal.txt", "formal", "R", "4.4"), ("syntax", "formal.R", "formal", "R", "4.4"), ("output", "check.json", "check", "Python", "3.13")):
                content = ("synthetic fixture " + name).encode()
                (root / name).write_bytes(content)
                entry["external_artifacts"].append({"role": role, "path": name, "sha256": hashlib.sha256(content).hexdigest(), "source_id": source, "software": software, "version": version})
            fields = ("research_question", "design_tags", "observation_unit", "field_map", "scoring", "sample", "model", "software", "estimation", "bootstrap", "random_seed", "input_hash")
            entry["spec_hash"] = hashlib.sha256(json.dumps({k: entry[k] for k in fields}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
            path = root / "entry.json"
            def add(value):
                path.write_text(json.dumps(value), encoding="utf-8")
                return run_script(REGISTRY, "add", "--project-root", str(root), "--entry", str(path), "--confirm-adopt")
            for alteration in ("missing_output", "bad_hash", "wrong_source", "aligned"):
                bad = copy.deepcopy(entry)
                if alteration == "missing_output": bad.pop("verification_output")
                elif alteration == "bad_hash": bad["external_artifacts"][-1]["sha256"] = "0" * 64
                elif alteration == "wrong_source": bad["external_artifacts"][-1]["source_id"] = "formal"
                else: bad["discrepancy_status"] = "ALIGNED"
                self.assertEqual(add(bad).returncode, 2, alteration)
            result = add(entry)
            self.assertEqual(result.returncode, 0, result.stderr)
            saved = read_frontmatter(root / ".psychology-paper" / "ANALYSIS_REGISTRY.md")["analyses"][0]
            self.assertEqual(saved["discrepancy_status"], "NOT_ASSESSED")
            self.assertEqual(saved["formal_output_ref"]["verification_process_status"], "UNVERIFIED_CODE_NOT_PROVIDED")
            self.assertEqual(run_script(VALIDATE_PROJECT, "--project-root", str(root)).returncode, 0)

    @staticmethod
    def _valid_entry(root=None) -> dict[str, object]:
        scientific = {"data": {"sha256": "a" * 64, "format": "csv", "read_options": {"encoding": "utf-8", "delimiter": ","}},
                      "design": {"design_tags": ["survey"], "observation_unit": "participant", "research_question_type": "description", "variables": [{"name": "x", "role": "outcome"}]},
                      "field_map": [{"variable": "x", "column": "x"}], "scoring": {"method": "none"},
                      "sample": {"missing": "complete_case", "filters": []},
                      "model": {"method": "descriptive", "columns": ["x"], "covariates": []},
                      "inference": {"alpha": 0.05, "confidence_level": 0.95, "alternative": "two-sided"}}
        digest = hashlib.sha256(json.dumps(scientific, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        run = {"schema_version": 1, "analysis_id": "study-1-correlation-private-peb", "revision": 1,
               "run_id": "run-1", "method_id": "descriptive", "spec_hash": digest, "input_hash": "a" * 64,
               "intent": "CANDIDATE_ANALYSIS", "status": "COMPLETED", "result_complete": True,
               "adoption_status": "CANDIDATE", "scientific_spec": scientific,
               "sample_audit": {"effective_n": 3}, "execution_provenance": {"python": "3.13"},
               "artifact_refs": {"run": "analysis-run.json"},
               "results": [{"outcome_id": "x", "term_id": "mean", "contrast_id": "overall", "estimate": 2, "n": 3, "sd": 1, "se": 0.5773502691896258, "df": 2, "ci": [-0.484137711719546, 4.484137711719546], "confidence_level": .95, "ci_alternative": "two-sided"}]}
        if root is not None:
            (root / "analysis-run.json").write_text(json.dumps(run), encoding="utf-8")
        return {
            "spec_hash": digest, "input_hash": "a" * 64,
            "analysis_id": "study-1-correlation-private-peb",
            "research_question": "Association between psychological distance and private PEB",
            "design_tags": ["survey"],
            "observation_unit": "participant",
            "field_map": scientific["field_map"],
            "scoring": scientific["scoring"],
            "sample": scientific["sample"],
            "model": scientific["model"],
            "software": {"name": "Python", "version": "3.13"},
            "estimation": "NOT_APPLICABLE",
            "bootstrap": None,
            "random_seed": None,
            "sources": [
                {"source_id": "source-1", "role": "AUTHORITATIVE", "software": "Python", "version": "3.13"}
            ],
            "formal_output": "analysis-run.json",
            "manuscript_locations": ["Study 1 Results", "Table 1"],
        }


if __name__ == "__main__":
    unittest.main()
