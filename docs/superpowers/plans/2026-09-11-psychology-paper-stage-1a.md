# Psychology Paper Stage 1A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and validate the read-only Stage 1A core of the `psychology-paper` Codex Plugin: adaptive routing, journal fit/style analysis, psychology evidence auditing, bilingual manuscript candidates, and compact approved project state without modifying manuscript files.

**Architecture:** This standalone repository is the plugin root. A short orchestrator selects one primary skill and loads only the shared rules and task fragments needed for the current request; project state is stored separately under each paper's `.psychology-paper/` directory. Stage 1A may create or update project-state files only after explicit approval, but every manuscript remains read-only until Stage 1B introduces and validates `document-patcher`.

**Tech Stack:** Codex Plugin manifests, Markdown-based Skills, JSON-compatible YAML manifests/frontmatter, Python 3.11+ standard library (`argparse`, `dataclasses`, `json`, `pathlib`, `tempfile`, `unittest`), Git, and the bundled `quick_validate.py` / `validate_plugin.py` validators.

## Global Constraints

- Implement only Stage 1A from `docs/superpowers/specs/2026-09-11-psychology-paper-plugin-design.md`; do not create `document-patcher`, `literature-map`, `analysis-adapter`, `review-revision`, or `submission-check` in this plan.
- Manuscript files are read-only throughout Stage 1A. State files may be written only after explicit approval.
- Preserve these exact invariants: `PATCH_FIRST = true`, `FULL_REBUILD_ON_LOCAL_EDIT = false`, `AUTO_VERSIONED_COPY = false`, `FULL_RENDER_ONLY_AT_MILESTONE = true`.
- “先判断/先讨论” means read-only diagnosis or candidate generation; “通过/采用你的/按这个改” approves only the current candidate; write permission remains a separate state.
- Each request has exactly one `PRIMARY_MODULE`; support modules receive a minimal handoff packet and must not widen scope.
- A local edit that changes statistics, sample information, constructs, study numbering, hypotheses, central findings, or source authority must escalate to a `change-impact audit`; broader reading never implies broader writing.
- `skills/.shared/core/state-consistency.md` is the single source of truth for illegal state combinations. Other components may parse and cite rules by stable ID but may not duplicate their condition definitions.
- Use JSON syntax inside files named `.yaml` and inside machine-readable Markdown frontmatter so Stage 1A needs no YAML dependency.
- Support Windows paths and UTF-8 Chinese text. Use `pathlib.Path` and `encoding="utf-8"`; do not build shell commands from user paths.
- Do not create `.mcp.json`, `.app.json`, hooks, a marketplace entry, per-skill READMEs, a changelog, or external service dependencies.
- Automated structural checks prove structure and invariants only. They must not be described as proof of scientific validity, author acceptance, or successful real-world manuscript use.
- Use test-driven development and make one focused commit after each task. Stage only the paths listed by that task because the parent repository contains unrelated manuscript and data files.

---

## Locked File Map

The implementation creates the following files and no additional production modules in Stage 1A:

```text
./
├─ .codex-plugin/
│  └─ plugin.json                         Plugin identity and skill discovery
├─ skills/
│  ├─ .shared/
│  │  ├─ core/
│  │  │  ├─ authorization-and-state.md   Human approval and write-scope rules
│  │  │  ├─ source-authority.md          Source roles and authority transitions
│  │  │  ├─ evidence-boundaries.md       Claim/evidence ceilings
│  │  │  ├─ research-design-taxonomy.md  Multi-label paper/design taxonomy
│  │  │  ├─ terminology-ledger.md        Construct/measure/operation ledger schema
│  │  │  ├─ state-consistency.md         Sole machine-readable state-rule authority
│  │  │  └─ change-propagation.md        Tiered impact-scan rules
│  │  ├─ output/
│  │  │  ├─ candidate-format.md          Chinese/English/translation output contracts
│  │  │  └─ risk-reporting.md            R0-R4 reporting contract
│  │  └─ schemas/
│  │     └─ minimal-handoff.md           Inter-skill minimal packet schema
│  ├─ psychology-paper/
│  │  ├─ SKILL.md                         Short orchestrator entrypoint
│  │  ├─ manifest.yaml                    Routing and progressive-load map
│  │  ├─ agents/openai.yaml               UI metadata
│  │  ├─ static/core/
│  │  │  ├─ routing-principles.md
│  │  │  ├─ authorization.md
│  │  │  └─ project-mode.md
│  │  └─ references/
│  │     ├─ task-routing.md
│  │     ├─ module-handoffs.md
│  │     └─ error-recovery.md
│  ├─ journal-fit-style/
│  │  ├─ SKILL.md
│  │  ├─ manifest.yaml
│  │  ├─ agents/openai.yaml
│  │  ├─ static/core/journal-analysis.md
│  │  ├─ static/fragments/
│  │  │  ├─ journal-unspecified.md
│  │  │  ├─ candidate-scan.md
│  │  │  ├─ confirmed-journal.md
│  │  │  ├─ light-style-scan.md
│  │  │  ├─ deep-style-study.md
│  │  │  └─ profile-refresh.md
│  │  └─ references/
│  │     ├─ manuscript-profile-schema.md
│  │     └─ journal-profile-schema.md
│  ├─ evidence-audit/
│  │  ├─ SKILL.md
│  │  ├─ manifest.yaml
│  │  ├─ agents/openai.yaml
│  │  ├─ static/core/audit-principles.md
│  │  ├─ static/fragments/paper-types/
│  │  │  ├─ empirical.md
│  │  │  ├─ qualitative.md
│  │  │  ├─ review.md
│  │  │  ├─ meta-analysis.md
│  │  │  └─ scale-development.md
│  │  ├─ static/fragments/designs/
│  │  │  ├─ survey.md
│  │  │  ├─ experiment.md
│  │  │  ├─ longitudinal.md
│  │  │  ├─ behavioral-task.md
│  │  │  └─ instrument-based.md
│  │  └─ references/
│  │     ├─ audit-report-schema.md
│  │     └─ change-impact-audit.md
│  └─ manuscript-writing/
│     ├─ SKILL.md
│     ├─ manifest.yaml
│     ├─ agents/openai.yaml
│     ├─ static/core/
│     │  ├─ writing-stance.md
│     │  ├─ workflow.md
│     │  ├─ evidence-boundary.md
│     │  ├─ output-contract.md
│     │  └─ paragraph-logic.md
│     ├─ static/fragments/sections/
│     │  ├─ title.md
│     │  ├─ abstract.md
│     │  ├─ introduction.md
│     │  ├─ hypotheses.md
│     │  ├─ methods.md
│     │  ├─ results.md
│     │  ├─ study-transitions.md
│     │  ├─ discussion.md
│     │  ├─ limitations.md
│     │  └─ conclusion.md
│     ├─ static/fragments/languages/
│     │  ├─ chinese.md
│     │  ├─ english.md
│     │  └─ chinese-to-english.md
│     ├─ static/fragments/tasks/
│     │  ├─ local-edit.md
│     │  ├─ section-rewrite.md
│     │  ├─ full-manuscript.md
│     │  └─ translation.md
│     └─ references/
│        └─ style-delta-schema.md
├─ assets/project-template/.psychology-paper/
│  └─ PROJECT.md                         Empty but valid state template
├─ scripts/
│  ├─ project_state.py                   Shared parser, renderer, and rule evaluator
│  ├─ init_project.py                    Explicit project-state initialization
│  ├─ load_skill_resources.py            Exact Manifest selector loader; no runtime traversal
│  └─ validate_project.py                Read-only project validator
├─ tests/
│  ├─ fixtures/
│  │  ├─ manuscript-en.txt
│  │  └─ manuscript-zh.txt
│  ├─ scenarios/
│  │  ├─ routing.json
│  │  ├─ journal-fit.json
│  │  ├─ evidence-audit.json
│  │  └─ manuscript-writing.json
│  ├─ test_plugin_structure.py
│  ├─ test_project_tools.py
│  ├─ test_shared_contracts.py
│  └─ test_scenario_contracts.py
├─ README.md
└─ LICENSE
```

`manifest.yaml` is a plugin-internal progressive-loading map, not a Codex platform manifest. It is written as JSON-compatible YAML and validated by Stage 1A tests. `.shared` is not a skill and therefore has no `SKILL.md`.

---

### Task 1: Scaffold the Plugin and Lock the Structural Contract

**Files:**
- Create: `./.codex-plugin/plugin.json`
- Create: `./tests/test_plugin_structure.py`
- Create: `./tests/fixtures/manuscript-en.txt`
- Create: `./tests/fixtures/manuscript-zh.txt`
- Create directories from the locked file map as they become needed; do not create empty skill folders for later stages.

**Interfaces:**
- Consumes: the approved design specification and official plugin schema.
- Produces: a valid plugin root and `PluginStructureTests` helpers used by later tasks.

- [ ] **Step 1: Write the failing plugin-structure test**

Create `./tests/test_plugin_structure.py` with this complete initial content:

```python
import json
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class PluginStructureTests(unittest.TestCase):
    def test_plugin_manifest_declares_stage_1a_skill_root(self) -> None:
        manifest_path = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "psychology-paper")
        self.assertEqual(manifest["version"], "0.1.0")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertNotIn("apps", manifest)
        self.assertNotIn("mcpServers", manifest)
        self.assertNotIn("hooks", manifest)

    def test_stage_1a_does_not_include_manuscript_writers(self) -> None:
        forbidden = [
            "document-patcher",
            "analysis-adapter",
            "literature-map",
            "review-revision",
            "submission-check",
        ]
        for name in forbidden:
            self.assertFalse((PLUGIN_ROOT / "skills" / name).exists(), name)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify the scaffold is absent**

Run:

```powershell
python ".\tests\test_plugin_structure.py" -v
```

Expected: `test_plugin_manifest_declares_stage_1a_skill_root` errors because `.codex-plugin/plugin.json` does not exist; the forbidden-module test passes.

- [ ] **Step 3: Generate the minimum official scaffold**

Run from the repository root:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\plugin-creator\scripts\create_basic_plugin.py" psychology-paper --path "." --with-skills --with-scripts --with-assets
```

Expected: `./.codex-plugin/plugin.json`, `skills/`, `scripts/`, and `assets/` are created. Do not request a marketplace entry in Stage 1A.

- [ ] **Step 4: Replace the generated manifest with the locked Stage 1A manifest**

Set `./.codex-plugin/plugin.json` to:

```json
{
  "name": "psychology-paper",
  "version": "0.1.0",
  "description": "Read-only psychology manuscript planning, journal fit, evidence auditing, and bilingual revision candidates.",
  "author": {
    "name": "Psychology Paper Contributors"
  },
  "license": "MIT",
  "keywords": [
    "psychology",
    "scientific-writing",
    "journal-fit",
    "evidence-audit"
  ],
  "skills": "./skills/",
  "interface": {
    "displayName": "Psychology Paper",
    "shortDescription": "Psychology manuscript workflow with evidence boundaries",
    "longDescription": "Plan, audit, and revise psychology manuscripts through journal-aware, evidence-calibrated, human-approved workflows.",
    "developerName": "Psychology Paper Contributors",
    "category": "Productivity",
    "capabilities": [
      "Interactive",
      "Read"
    ],
    "defaultPrompt": [
      "Review my psychology manuscript before making changes.",
      "Assess journal fit and learn the target journal's style.",
      "Draft a bilingual revision candidate for this section."
    ],
    "brandColor": "#365B6D"
  }
}
```

- [ ] **Step 5: Add encoding fixtures**

Create `./tests/fixtures/manuscript-en.txt`:

```text
Moral identity was associated with pro-environmental intentions. The present paragraph is a test fixture, not a scientific result.
```

Create `./tests/fixtures/manuscript-zh.txt`:

```text
道德认同与亲环境意向相关。本段仅用于验证中文路径与文本读取，不代表科学结论。
```

- [ ] **Step 6: Run the test and official plugin validation**

Run:

```powershell
python ".\tests\test_plugin_structure.py" -v
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py" "."
```

Expected: both unit tests pass; plugin validation reports success with no unsupported manifest fields or unfinished scaffold markers.

- [ ] **Step 7: Commit only the scaffold and its test**

```powershell
git add -- "./.codex-plugin/plugin.json" "./tests/test_plugin_structure.py" "./tests/fixtures/manuscript-en.txt" "./tests/fixtures/manuscript-zh.txt"
git commit -m "feat: scaffold psychology paper plugin"
```

---

### Task 2: Implement the Single State-Rule Authority and Project Tools

**Files:**
- Create: `./skills/.shared/core/state-consistency.md`
- Create: `./assets/project-template/.psychology-paper/PROJECT.md`
- Create: `./scripts/project_state.py`
- Create: `./scripts/init_project.py`
- Create: `./scripts/validate_project.py`
- Create: `./tests/test_project_tools.py`

**Interfaces:**
- Consumes: JSON-compatible Markdown frontmatter and explicit filesystem paths.
- Produces:
  - `extract_json_frontmatter(path: Path) -> dict[str, object]`
  - `render_json_frontmatter(data: dict[str, object], body: str) -> str`
  - `load_state_rules(path: Path, expected_version: int = 1) -> dict[str, object]`
  - `evaluate_rules(context: dict[str, object], rules: dict[str, object], component: str) -> list[Violation]`
  - CLI `init_project.py --project-root PATH --manuscript PATH --confirm-create [--journal NAME]`
  - CLI `validate_project.py --project-root PATH`

- [ ] **Step 1: Write failing tests for initialization, validation, and rule reuse**

Create `./tests/test_project_tools.py` with tests that exercise these exact cases:

```python
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
INIT = PLUGIN_ROOT / "scripts" / "init_project.py"
VALIDATE = PLUGIN_ROOT / "scripts" / "validate_project.py"
RULES = PLUGIN_ROOT / "skills" / ".shared" / "core" / "state-consistency.md"


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


class ProjectToolTests(unittest.TestCase):
    def test_init_requires_explicit_confirmation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="心理学项目-") as raw:
            root = Path(raw)
            manuscript = root / "当前稿件.txt"
            manuscript.write_text("test", encoding="utf-8")
            result = run_script(
                INIT,
                "--project-root", str(root),
                "--manuscript", str(manuscript),
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse((root / ".psychology-paper" / "PROJECT.md").exists())

    def test_init_creates_state_without_touching_manuscript(self) -> None:
        with tempfile.TemporaryDirectory(prefix="心理学项目-") as raw:
            root = Path(raw)
            manuscript = root / "当前稿件.txt"
            original = "不得修改的正文"
            manuscript.write_text(original, encoding="utf-8")
            result = run_script(
                INIT,
                "--project-root", str(root),
                "--manuscript", str(manuscript),
                "--confirm-create",
                "--journal", "Journal of Environmental Psychology",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(manuscript.read_text(encoding="utf-8"), original)
            state = root / ".psychology-paper" / "PROJECT.md"
            self.assertTrue(state.exists())
            validation = run_script(VALIDATE, "--project-root", str(root))
            self.assertEqual(validation.returncode, 0, validation.stdout + validation.stderr)

    def test_init_refuses_to_overwrite_existing_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manuscript = root / "paper.txt"
            manuscript.write_text("paper", encoding="utf-8")
            args = (
                "--project-root", str(root),
                "--manuscript", str(manuscript),
                "--confirm-create",
            )
            self.assertEqual(run_script(INIT, *args).returncode, 0)
            self.assertEqual(run_script(INIT, *args).returncode, 3)

    def test_validator_uses_shared_rule_sc_001(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            manuscript = root / "paper.txt"
            manuscript.write_text("paper", encoding="utf-8")
            self.assertEqual(
                run_script(
                    INIT,
                    "--project-root", str(root),
                    "--manuscript", str(manuscript),
                    "--confirm-create",
                ).returncode,
                0,
            )
            state_path = root / ".psychology-paper" / "PROJECT.md"
            text = state_path.read_text(encoding="utf-8")
            start = text.index("{")
            end = text.index("\n---", start)
            state = json.loads(text[start:end])
            state["current_action"] = {
                "decision_status": "CANDIDATE",
                "write_permission": "WRITE_ALLOWED",
                "source_role": "AUTHORITATIVE",
                "evidence_status": "ALIGNED",
                "evidence_boundary_applied": True,
                "patch_status": "NOT_APPLIED",
                "patch_receipt_present": False,
                "required_verification_complete": False,
                "new_patch_requested": False,
                "check_status": "NOT_APPLICABLE",
                "risk_level": "R4",
                "issue_resolved": True,
                "explicit_output_target": True
            }
            body = text[end + 5:]
            state_path.write_text(
                "---\n" + json.dumps(state, ensure_ascii=False, indent=2) + "\n---\n" + body,
                encoding="utf-8",
            )
            result = run_script(VALIDATE, "--project-root", str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn("SC-001", result.stdout)
            self.assertIn(str(RULES), result.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests and verify they fail because the tools do not exist**

Run:

```powershell
python ".\tests\test_project_tools.py" -v
```

Expected: all four tests fail or error because the state template and scripts are absent.

- [ ] **Step 3: Define the sole state-rule source**

Create `./skills/.shared/core/state-consistency.md`. Its JSON frontmatter must have this exact top-level schema:

```json
{
  "schema": "psychology-paper-state-rules",
  "version": 1,
  "rules": []
}
```

Populate `rules` with these definitions; the Markdown body explains that every runtime and validator must parse this frontmatter and must not maintain copied condition tables:

| ID | Scope | Condition | Block message | Components |
|---|---|---|---|---|
| `SC-001` | `current_action` | `write_permission == WRITE_ALLOWED` and `decision_status != APPROVED` | Writing requires an approved decision. | router, project-validator, document-patcher |
| `SC-002` | `current_action` | writing allowed, source role is RAW or HISTORICAL, and explicit output target is not true | Raw or historical sources require explicit redesignation before output. | router, project-validator, document-patcher |
| `SC-003` | `current_action` | decision is REJECTED or INTENTIONAL_HOLD and writing is allowed | Rejected or held decisions cannot be written. | router, project-validator, document-patcher |
| `SC-004` | `current_action` | evidence is CONTRADICTED or OUTSIDE_EVIDENCE, writing is allowed, and `evidence_boundary_applied` is not true | Unsupported claims require a bounded rewrite before approval. | router, project-validator, document-patcher |
| `SC-005` | `current_action` | patch status is PATCHED_UNVERIFIED or PATCHED_VISUAL_PENDING and no receipt exists | A patched state requires a receipt. | project-validator, document-patcher |
| `SC-006` | `current_action` | patch status is DELIVERY_VERIFIED and required verification is not complete | Delivery cannot be verified before required checks. | project-validator, document-patcher |
| `SC-007` | `current_action` | patch status is ROLLBACK_PENDING or ROLLBACK_FAILED and a new patch is requested | New writes are blocked until recovery is resolved. | router, project-validator, document-patcher |
| `SC-008` | `current_action` | check status is PASS, risk is R0 or R1, and issue is unresolved | Submission cannot be marked passed with unresolved R0/R1 risk. | router, project-validator |

Represent each condition with `all` and `any` arrays of atoms using only these operators: `eq`, `ne`, `in`, `not_in`, `exists`. Each atom has `path`, `op`, and `value` except `exists`, which uses a Boolean `value`. This is the only place where the condition atoms are stored.

- [ ] **Step 4: Create the valid empty project template**

Create `./assets/project-template/.psychology-paper/PROJECT.md` with JSON frontmatter containing exactly these keys and default values:

```json
{
  "schema": "psychology-paper-project",
  "schema_version": 1,
  "project_root": "",
  "current_stage": "INTAKE",
  "primary_module": null,
  "authoritative_manuscript": "",
  "sources": [],
  "optional_state_files": {
    "journal_profile": null,
    "literature_map": null,
    "analysis_registry": null,
    "style_delta": null
  },
  "paper_and_design_tags": [],
  "journal": {
    "name": null,
    "status": "UNCONFIRMED"
  },
  "formal_analysis_source": null,
  "current_action": null,
  "approved_decisions": [],
  "intentional_holds": [],
  "unresolved_issues": [],
  "next_action": null
}
```

The body must contain only these headings and explanations: `Authority`, `Approved decisions`, `Intentional holds and unresolved issues`, and `Next action`. It must say that the frontmatter is machine-readable, the prose is a compact human view, and rejected AI drafts or full chat history do not belong in this file.

- [ ] **Step 5: Implement the shared parser and evaluator**

Create `./scripts/project_state.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Violation:
    rule_id: str
    message: str
    source_path: Path


def extract_json_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"Missing JSON frontmatter: {path}")
    closing = text.find("\n---\n", 4)
    if closing < 0:
        raise ValueError(f"Unclosed JSON frontmatter: {path}")
    data = json.loads(text[4:closing])
    if not isinstance(data, dict):
        raise ValueError(f"Frontmatter must be an object: {path}")
    return data, text[closing + 5:]


def render_json_frontmatter(data: dict[str, Any], body: str) -> str:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    return f"---\n{payload}\n---\n{body.lstrip()}"


def load_state_rules(path: Path, expected_version: int = 1) -> dict[str, Any]:
    data, _ = extract_json_frontmatter(path)
    if data.get("schema") != "psychology-paper-state-rules":
        raise ValueError(f"Unsupported rule schema: {path}")
    if data.get("version") != expected_version:
        raise ValueError(f"Unsupported rule version: {path}")
    ids = [rule.get("id") for rule in data.get("rules", [])]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError(f"Rule IDs must be unique and non-empty: {path}")
    return data


def _value_at(record: dict[str, Any], path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def _atom_matches(record: dict[str, Any], atom: dict[str, Any]) -> bool:
    actual = _value_at(record, atom["path"])
    expected = atom.get("value")
    operation = atom["op"]
    if operation == "eq":
        return actual == expected
    if operation == "ne":
        return actual != expected
    if operation == "in":
        return actual in expected
    if operation == "not_in":
        return actual not in expected
    if operation == "exists":
        return (actual is not None) is bool(expected)
    raise ValueError(f"Unsupported rule operator: {operation}")


def evaluate_rules(
    context: dict[str, Any],
    rules: dict[str, Any],
    component: str,
    source_path: Path,
) -> list[Violation]:
    violations: list[Violation] = []
    for rule in rules["rules"]:
        if component not in rule["components"]:
            continue
        target = _value_at(context, rule["scope"])
        if not isinstance(target, dict):
            continue
        all_match = all(_atom_matches(target, atom) for atom in rule.get("all", []))
        any_atoms = rule.get("any", [])
        any_match = not any_atoms or any(_atom_matches(target, atom) for atom in any_atoms)
        if all_match and any_match:
            violations.append(Violation(rule["id"], rule["message"], source_path))
    return violations
```

The state-rule file must use only the supported operators and the `current_action` scope so this implementation is complete rather than speculative.

- [ ] **Step 6: Implement explicit project initialization**

Create `./scripts/init_project.py` as a CLI that:

1. Requires `--project-root`, `--manuscript`, and `--confirm-create`; missing confirmation returns exit code `2` without creating files.
2. Resolves the two explicit paths with `Path.resolve()`, requires the manuscript to be an existing file, and creates only `<project-root>/.psychology-paper/PROJECT.md`.
3. Refuses to overwrite an existing `PROJECT.md` with exit code `3`.
4. Loads the asset template, fills `project_root`, `authoritative_manuscript`, and `sources` with one record `{id: "current-manuscript", path: absolute_path, role: "AUTHORITATIVE"}`.
5. If `--journal` is provided, records its name with status `USER_CONFIRMED`; otherwise preserves `UNCONFIRMED`.
6. Writes UTF-8 and prints only `Created <absolute state path>`.
7. Never reads or writes manuscript contents and never enumerates files outside the provided project root.

Use `extract_json_frontmatter` and `render_json_frontmatter` from `project_state.py`; do not reimplement frontmatter parsing.

- [ ] **Step 7: Implement read-only project validation**

Create `./scripts/validate_project.py` as a CLI that:

1. Requires `--project-root` and reads `<project-root>/.psychology-paper/PROJECT.md`.
2. Loads `state-consistency.md` through `load_state_rules`; missing, invalid, or wrong-version rules return exit code `2`.
3. Verifies schema/version, an existing absolute authoritative manuscript path, exactly one source with role `AUTHORITATIVE`, and agreement between that source path and `authoritative_manuscript`.
4. Verifies every non-null path under `optional_state_files`; it does not discover or create optional files. Stage 1A permits only `journal_profile` and `style_delta` to become non-null because the literature and analysis modules are deferred.
5. Rejects empty template values in fields that initialization must fill.
6. Calls `evaluate_rules(..., component="project-validator", source_path=RULE_PATH)` and prints every violation as `<rule-id>: <message> [source: <rule-path>]`.
7. Returns `0` with `Project state valid`, `1` for invalid project state, and `2` for unreadable schema or rule infrastructure.
8. Never edits state or manuscript files.

- [ ] **Step 8: Run the project-tool tests**

Run:

```powershell
python ".\tests\test_project_tools.py" -v
```

Expected: four tests pass. The Chinese temporary path test confirms UTF-8/path handling; the `SC-001` test proves the validator reports the shared rule file as its source.

- [ ] **Step 9: Add one rule-integrity test**

Extend `test_project_tools.py` with a test that loads all rule IDs, asserts exactly `SC-001` through `SC-008`, asserts all IDs are unique, and asserts every rule uses only `eq`, `ne`, `in`, `not_in`, or `exists`. Run the file again and expect five passing tests.

- [ ] **Step 10: Commit the state authority and tools**

```powershell
git add -- "./skills/.shared/core/state-consistency.md" "./assets/project-template/.psychology-paper/PROJECT.md" "./scripts/project_state.py" "./scripts/init_project.py" "./scripts/validate_project.py" "./tests/test_project_tools.py"
git commit -m "feat: add approved project state workflow"
```

---

### Task 3: Add Shared Psychology, Authorization, Output, and Handoff Contracts

**Files:**
- Create: all remaining files under `./skills/.shared/`
- Create: `./tests/test_shared_contracts.py`

**Interfaces:**
- Consumes: state names and source roles defined in the design and Task 2.
- Produces: canonical shared references loaded by the four Stage 1A skills; no executable write capability.

- [ ] **Step 1: Write failing shared-contract tests**

Create `./tests/test_shared_contracts.py` with tests that:

1. Assert every path in the locked `.shared` map exists.
2. Assert `.shared/SKILL.md` does not exist.
3. Assert the four patch invariants occur exactly once, all in `authorization-and-state.md`.
4. Assert no file except `state-consistency.md` contains a JSON definition matching `"id": "SC-`.
5. Assert `candidate-format.md` contains the three exact output orders.
6. Assert `minimal-handoff.md` contains exactly the required packet keys and the three routing keys.
7. Assert `change-propagation.md` distinguishes `read_scope` from `write_scope` and contains `change-impact audit`.

Implement the tests by reading UTF-8 files with `Path.rglob("*.md")`; report missing fields by filename.

- [ ] **Step 2: Run the tests and verify all required shared contracts are missing**

Run:

```powershell
python ".\tests\test_shared_contracts.py" -v
```

Expected: failures list the nine missing shared files.

- [ ] **Step 3: Create the shared core rules with non-overlapping responsibilities**

Write the following exact content boundaries:

- `authorization-and-state.md`: define the user-language mappings, distinguish review/recalculation/adoption/write permissions, include the four patch invariants exactly once, and state that approval affects only the current candidate.
- `source-authority.md`: define `AUTHORITATIVE`, `VERIFICATION`, `HISTORICAL`, `REFERENCE`, `RAW`, `DERIVED`, and `UNKNOWN`; state that approval does not automatically change a source role and that one analysis has one authoritative source.
- `evidence-boundaries.md`: define observation, association, prediction, conditional effect, randomized manipulation effect, mechanism interpretation, cross-study synthesis, and generalization; require the claim ceiling to match the strongest direct evidence.
- `research-design-taxonomy.md`: define independent axes for paper type, design, observational unit, evidence source, and measurement technology; include survey, behavioral experiment, instrument-based study, qualitative study, review, meta-analysis, scale development, longitudinal, within-subject, between-subject, factorial, intensive longitudinal, multilevel, psychophysiology, eye tracking, EEG, and neuroimaging as selectable tags rather than one exhaustive single choice.
- `terminology-ledger.md`: define fields for Chinese name, English name, abbreviation, trait/state level, theoretical construct, manipulation, manipulation check, measured indicator, outcome indicator, noninterchangeable near-synonyms, source location, and confirmation status; require active author confirmation for ambiguous fields.
- `change-propagation.md`: define the trigger list, search-first escalation order, candidate-location output, `read_scope`/`write_scope` separation, and the rule that broader reading never authorizes broader writing.

Do not reproduce the `SC-001`–`SC-008` conditions in these files; link to `state-consistency.md` for machine-enforced combinations.

- [ ] **Step 4: Create the shared output contracts**

`candidate-format.md` must prescribe:

```text
English edit: Original English → Revised English → Chinese Translation
Chinese edit: Original Chinese → Revised Chinese → Necessary Notes
Chinese-to-English: Chinese Source → Revised English → Chinese Back-translation
```

It must also require TXT-ready plain text, separate problem annotations, paragraph/section chunking, and these budgets: paragraph `2,000–6,000`, section `8,000–18,000`, full manuscript cumulative `25,000–60,000` tokens but never generated as a single default response.

`risk-reporting.md` must define `R0` through `R4` exactly as in the approved design, honor a user-specified reporting threshold, report facts before recommendations, and avoid relisting intentional holds in ordinary rounds.

- [ ] **Step 5: Create the minimal handoff schema**

`minimal-handoff.md` must contain one canonical ordered packet:

```text
task
source_path
location
scope
paper_and_design_tags
authoritative_source
approved_constraints
evidence_ceiling
required_output
open_issue
PRIMARY_MODULE
SUPPORT_MODULES
STOP_CONDITION
```

Define each field in one sentence. State that a readable file is passed by path and location rather than copied; rejected drafts, full chats, unrelated sections, and repeated journal guidance are excluded.

- [ ] **Step 6: Run shared-contract tests**

Run:

```powershell
python ".\tests\test_shared_contracts.py" -v
```

Expected: all shared-contract tests pass and no state-rule definition is duplicated.

- [ ] **Step 7: Commit the shared contracts**

```powershell
git add -- "./skills/.shared" "./tests/test_shared_contracts.py"
git commit -m "feat: add shared psychology workflow contracts"
```

---

### Task 4: Implement the `psychology-paper` Orchestrator and Bidirectional Routing Scenarios

**Files:**
- Create: all files under `./skills/psychology-paper/`
- Create: `./tests/scenarios/routing.json`
- Create: `./tests/test_scenario_contracts.py`
- Modify: `./tests/test_plugin_structure.py`

**Interfaces:**
- Consumes: shared authorization, source, change-propagation, and minimal-handoff contracts.
- Produces: `PRIMARY_MODULE`, `SUPPORT_MODULES`, `STOP_CONDITION`, required shared loads, and either a direct local route or a `change-impact audit` route.

- [ ] **Step 1: Add failing skill and scenario structure tests**

Extend `test_plugin_structure.py` to require each implemented skill folder to contain `SKILL.md`, JSON-compatible `manifest.yaml`, and `agents/openai.yaml`. Add a helper that recursively resolves every path named in each manifest and fails on missing files.

Create `test_scenario_contracts.py` with a schema validator requiring every scenario object to contain:

```text
id
request
project_state
expected_primary_module
expected_scope
required_actions
forbidden_actions
expected_state_effect
manual_rubric
```

The test must also require unique scenario IDs and at least one case tagged `under_escalation_guard` and one tagged `over_escalation_guard`.

- [ ] **Step 2: Run the tests and verify the orchestrator assets are missing**

Run:

```powershell
python ".\tests\test_plugin_structure.py" -v
python ".\tests\test_scenario_contracts.py" -v
```

Expected: failures name the absent orchestrator and routing scenario files.

- [ ] **Step 3: Create the orchestrator entrypoint and UI metadata**

`./skills/psychology-paper/SKILL.md` must remain a short router with these sections: purpose, when to use, read-before-routing, routing sequence, approval gate, project-state rule, stop conditions, and links to conditional references. It must explicitly say that it never writes manuscript text, performs statistics, searches literature, or substitutes for a professional module.

Use this frontmatter:

```yaml
---
name: psychology-paper
description: Route multi-step psychology manuscript work across journal fit, evidence auditing, and bilingual writing while preserving user approval, source authority, and read-only Stage 1A boundaries.
---
```

`agents/openai.yaml` must be:

```yaml
interface:
  display_name: "Psychology Paper"
  short_description: "Route psychology manuscript work safely"
  default_prompt: "Use $psychology-paper to assess this manuscript request before making changes."
policy:
  allow_implicit_invocation: true
```

- [ ] **Step 4: Create the orchestrator progressive-load manifest**

Write `manifest.yaml` as a JSON object with:

```json
{
  "schema": "psychology-paper-skill-manifest",
  "version": 1,
  "skill": "psychology-paper",
  "always_load": [
    "./static/core/routing-principles.md",
    "./static/core/authorization.md"
  ],
  "conditional_loads": {
    "project_mode": ["./static/core/project-mode.md"],
    "ambiguous_route": ["./references/task-routing.md"],
    "module_handoff": ["./references/module-handoffs.md"],
    "recovery": ["./references/error-recovery.md"]
  },
  "shared_loads": {
    "authorization": ["../.shared/core/authorization-and-state.md"],
    "state_rules": ["../.shared/core/state-consistency.md"],
    "impact_scan": ["../.shared/core/change-propagation.md"],
    "handoff": ["../.shared/schemas/minimal-handoff.md"]
  }
}
```

- [ ] **Step 5: Write orchestrator core and references**

Keep responsibilities separated:

- `routing-principles.md`: adaptive semantic routing, one primary module, light task versus project mode, and no requirement that the user use system terminology.
- `authorization.md`: when to consult shared approval rules and how “discussion”, “approval”, and “write permission” remain separate.
- `project-mode.md`: enter project mode for full-manuscript work, reanalysis, peer-review revision, or submission; do not require it for a single isolated language edit.
- `task-routing.md`: a decision table mapping diagnosis, journal, evidence, literature, writing, review, submission, statistics, and document changes to modules; Stage 1A unavailable modules must return a bounded “not implemented in this stage” result rather than pretending to act.
- `module-handoffs.md`: use the canonical minimal packet, pass paths and locations, and prohibit copied full chat or rejected candidates.
- `error-recovery.md`: uncertain scope routes to evidence audit; absent authoritative source requests confirmation; missing files stop; intentional holds are not repeatedly raised; no manuscript mutation is attempted in Stage 1A.

All references to state combinations must point to `../.shared/core/state-consistency.md`; do not restate rule conditions.

- [ ] **Step 6: Create routing scenarios for both false-positive and false-negative scope errors**

Create `routing.json` with at least these ten concrete requests:

1. “把 address 改成 addressed，先不用看全文。” → `manuscript-writing`, sentence scope, `over_escalation_guard`, no project creation, no full read.
2. “把样本量 169 改成 171。” → `evidence-audit`, `change-impact audit`, `under_escalation_guard`, produce sync locations, no write.
3. “把 anticipated warm glow 全文改成 anticipated affect。” → `evidence-audit`, full impact scan, no direct replacement.
4. “先判断这个段落有没有问题，不要改。” → `evidence-audit`, local read-only, no candidate write.
5. “这个修改通过。” → orchestrator records approval only for the active candidate; no manuscript write permission.
6. “通读全文，准备投稿，但还没定期刊。” → `journal-fit-style`, project mode, manuscript profile plus candidates.
7. “目标期刊就是 JEP，不要换。” → `journal-fit-style`, confirmed-journal deep style route, no alternate journal substitution.
8. “作为审稿人审一下，只报初筛拒稿问题。” → `evidence-audit`, full read-only, threshold R0–R1.
9. “直接往原文件里改刚才通过的那一句。” → Stage 1A reports that manuscript writing is unavailable and prepares a future patch handoff; it may not modify the file.
10. “这个伦理问题先留着。” → record `INTENTIONAL_HOLD`; ordinary future scans do not relist it unless submission risk is explicitly requested.

Each scenario includes a short manual rubric that can be judged from a model response. Do not encode an expected final sentence; test decisions and forbidden actions.

- [ ] **Step 7: Run structural and scenario-schema tests**

Run:

```powershell
python ".\tests\test_plugin_structure.py" -v
python ".\tests\test_scenario_contracts.py" -v
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\psychology-paper"
```

Expected: manifests resolve, routing scenarios have both guard directions, and official skill validation passes.

- [ ] **Step 8: Commit the orchestrator**

```powershell
git add -- "./skills/psychology-paper" "./tests/scenarios/routing.json" "./tests/test_scenario_contracts.py" "./tests/test_plugin_structure.py"
git commit -m "feat: add psychology paper request router"
```

---

### Task 5: Implement `journal-fit-style`

**Files:**
- Create: all files under `./skills/journal-fit-style/`
- Create: `./tests/scenarios/journal-fit.json`
- Modify: `./tests/test_plugin_structure.py`

**Interfaces:**
- Consumes: manuscript path or supplied manuscript text, paper/design tags, journal status, user priorities, current official journal information, and published-article observations.
- Produces: a manuscript profile, three-tier journal candidates with light scans, or a confirmed `JOURNAL_PROFILE.md` candidate. It never changes the target journal without user approval.

- [ ] **Step 1: Extend structure tests and observe failure**

Add `journal-fit-style` to the implemented-skill list and require its manifest paths to resolve. Run:

```powershell
python ".\tests\test_plugin_structure.py" -v
```

Expected: failure identifies the missing skill.

- [ ] **Step 2: Create the skill entrypoint and UI metadata**

Use this frontmatter:

```yaml
---
name: journal-fit-style
description: Profile a psychology manuscript, recommend or assess target journals, and learn official requirements plus recent article organization before journal-directed revision.
---
```

The body routes among unspecified journal, candidate comparison, confirmed journal, and refresh. It must require web verification for current journal policies; separate official requirements from observed style; default to 1–2 close papers for candidate scans and 2–3 for confirmed deep study; expand only when observations conflict.

`agents/openai.yaml` must use display name `Journal Fit & Style`, a 25–64 character short description, implicit invocation enabled, and a default prompt beginning `Use $journal-fit-style`.

- [ ] **Step 3: Create the journal manifest**

The JSON-compatible `manifest.yaml` must define axes `journal_status` (`unspecified`, `candidates`, `confirmed`), `depth` (`light`, `deep`, `refresh`), and `output` (`manuscript_profile`, `candidate_set`, `journal_profile`). It must route each value to the exact fragment filenames in the locked file map and always load `journal-analysis.md`.

- [ ] **Step 4: Write the journal rules and schemas**

Required content:

- `journal-analysis.md`: scope, article type, readers, contribution level, evidence expectations, current policies, and style are distinct dimensions; matching vocabulary alone is not fit.
- `journal-unspecified.md`: build the manuscript profile before naming journals.
- `candidate-scan.md`: provide ambitious/balanced/safer tiers and ask which priority matters; each journal receives only a light 1–2-paper scan.
- `confirmed-journal.md`: assess fit without substituting another journal; surface choices only if mismatch is material.
- `light-style-scan.md`: inspect problem framing, section organization, and claim strength at low token cost.
- `deep-style-study.md`: inspect 2–3 highly similar recent papers for introduction logic, multi-study transitions, nonsignificant results, discussion integration, figures/tables, and supplementary organization.
- `profile-refresh.md`: reverify drift-prone official policies and clearly date the refresh.
- `manuscript-profile-schema.md`: fields for branch, article type, core question, contribution, evidence types, evidence ceiling, readers, strongest evidence, largest risk, completeness, and journal-direction suggestions.
- `journal-profile-schema.md`: separate `official_requirements`, `observed_style`, `manuscript_fit`, `revision_implications`, sources/URLs, and verification date.

- [ ] **Step 5: Add journal-fit behavior scenarios**

Create cases covering: no journal and full-manuscript request; confirmed JEP with no switching; a local sentence edit that does not trigger journal research; candidate light scan; confirmed deep scan; and stale profile refresh. Required forbidden actions include inventing policies, treating observed conventions as formal requirements, and imitating wording from a few articles.

- [ ] **Step 6: Validate and commit**

Run:

```powershell
python ".\tests\test_plugin_structure.py" -v
python ".\tests\test_scenario_contracts.py" -v
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\journal-fit-style"
```

Expected: all tests and official skill validation pass.

```powershell
git add -- "./skills/journal-fit-style" "./tests/scenarios/journal-fit.json" "./tests/test_plugin_structure.py"
git commit -m "feat: add journal fit and style analysis"
```

---

### Task 6: Implement Design-Adaptive `evidence-audit`

**Files:**
- Create: all files under `./skills/evidence-audit/`
- Create: `./tests/scenarios/evidence-audit.json`
- Modify: `./tests/test_plugin_structure.py`

**Interfaces:**
- Consumes: source path/location, paper and design tags, authoritative source, user risk threshold, and visible methods/results.
- Produces: evidence statuses (`ALIGNED`, `BOUNDED`, `CONDITIONAL`, `UNRESOLVED`, `CONTRADICTED`, `OUTSIDE_EVIDENCE`), R0–R4 issues, or a `change-impact audit` location list. It reports problems only; the user decides whether and how to act.

- [ ] **Step 1: Add the missing-skill test and verify failure**

Add `evidence-audit` to the implemented-skill list, run `test_plugin_structure.py`, and expect failure until the files exist.

- [ ] **Step 2: Create the entrypoint, metadata, and manifest**

Use frontmatter:

```yaml
---
name: evidence-audit
description: Read-only audit of psychology claims, constructs, research designs, measures, visible statistics, and cross-section consistency, adapted to the paper and design type.
---
```

The entrypoint must say: identify paper/design tags before loading checks; report problems rather than editing; do not recalculate without authorization; do not infer misconduct from inconsistency; and send a minimal handoff only after the user chooses a response.

The manifest must route by `paper_type`, multiple `design_tags`, `scope` (`local`, `section`, `full`, `change-impact`), and `risk_threshold` (`R0-R1`, `R0-R2`, `all`). Multiple design fragments may load together; paper type is not inferred solely from the presence of numbers.

- [ ] **Step 3: Write core audit principles and paper-type fragments**

`audit-principles.md` defines the seven evidence statuses, R0–R4, fact-versus-inference labeling, source authority, and “only report issues” boundary.

Paper-type fragments must be non-overlapping:

- `empirical.md`: hypotheses, methods, results, claims, and cross-section consistency.
- `qualitative.md`: sampling, reflexivity, analytic procedure, evidentiary grounding, and interpretive transfer; no quantitative-statistic checklist.
- `review.md`: search/selection transparency, synthesis logic, and scope of conclusions; no manipulation checks.
- `meta-analysis.md`: eligibility, coding, dependency, heterogeneity, publication-bias methods, and model/result coherence.
- `scale-development.md`: construct domain, item generation, factor strategy, reliability, validity, invariance, and overclaiming.

- [ ] **Step 4: Write design fragments that match the actual design**

- `survey.md`: observation unit, timing, common-source structure, sampling, measures, association/prediction ceiling.
- `experiment.md`: randomization, factors/levels, between/within structure, manipulation versus measured mediator, manipulation check, exclusions, and causal scope.
- `longitudinal.md`: occasions, attrition, temporal order, within/between separation, lag structure.
- `behavioral-task.md`: task behavior versus preference/choice/self-report, incentive/consequence status, trial aggregation.
- `instrument-based.md`: device, acquisition, preprocessing, artifact rejection, derived signals, and distance between physiological/neural measures and psychological interpretation; applicable to eye tracking, EEG, psychophysiology, and neuroimaging tags.

Every fragment must begin with an applicability statement and must not require irrelevant checks for other designs.

- [ ] **Step 5: Implement audit report and change-impact schemas**

`audit-report-schema.md` requires each reported issue to contain: location, observed fact, why it matters, evidence status, risk, affected claim, and unresolved author question. Recommendations remain optional and separate.

`change-impact-audit.md` implements:

```text
project state and terminology ledger
→ targeted text/heading/statistic search
→ context around matches
→ related sections
→ full manuscript only when coverage remains uncertain
→ synchronization list
→ user decision
```

It must explicitly list likely destinations: title, abstract, keywords, introduction end, hypotheses, methods, results, transitions, discussion, limitations, conclusion, tables, figures, captions, and supplements. It never writes or expands write scope.

- [ ] **Step 6: Add design-adaptive and propagation scenarios**

Create cases for: survey without manipulation-check requirements; randomized experiment with an unmanipulated mediator overclaimed as causal; qualitative study not receiving F/p checks; behavioral preference not renamed consequential behavior; instrument signal not automatically treated as a psychological construct; sample-size sentence escalating to a change-impact audit; spelling-only sentence staying local; “significant in one group but not another” not treated as a significant group difference; and inconsistent F/p/effect size marked for verification without misconduct accusation.

- [ ] **Step 7: Validate and commit**

Run:

```powershell
python ".\tests\test_plugin_structure.py" -v
python ".\tests\test_scenario_contracts.py" -v
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\evidence-audit"
```

Expected: all checks pass and every evidence-audit scenario has paper/design tags appropriate to its rubric.

```powershell
git add -- "./skills/evidence-audit" "./tests/scenarios/evidence-audit.json" "./tests/test_plugin_structure.py"
git commit -m "feat: add design adaptive evidence audit"
```

---

### Task 7: Implement Read-Only, Bilingual `manuscript-writing`

**Files:**
- Create: all files under `./skills/manuscript-writing/`
- Create: `./tests/scenarios/manuscript-writing.json`
- Modify: `./tests/test_plugin_structure.py`

**Interfaces:**
- Consumes: approved evidence ceiling, exact source passage/path, section type, language mode, target journal profile when available, and user style delta when confirmed.
- Produces: TXT-ready candidates in the approved order. It cannot write a manuscript in Stage 1A and cannot widen a claim already bounded by evidence audit.

- [ ] **Step 1: Add the missing-skill test and verify failure**

Add `manuscript-writing` to the implemented-skill list and run `test_plugin_structure.py`. Expected: failure until the skill exists.

- [ ] **Step 2: Create the short entrypoint, UI metadata, and manifest**

Use frontmatter:

```yaml
---
name: manuscript-writing
description: Draft or revise Chinese and English psychology manuscript sections as evidence-bounded, journal-aware, TXT-ready candidates; Stage 1A never writes source documents.
---
```

The entrypoint loads only one task fragment, one language fragment, the requested section fragment, core stance/output rules, a confirmed journal profile when present, and `references/style-delta-schema.md` only when an approved style delta exists. It must stop and ask for an evidence ceiling when the requested rewrite would change a central scientific claim.

The manifest must define axes:

```text
section: title, abstract, introduction, hypotheses, methods, results, study-transitions, discussion, limitations, conclusion
language: chinese, english, chinese-to-english
task: local-edit, section-rewrite, full-manuscript, translation
```

Each axis value maps to one exact fragment. `full-manuscript` must route to chunked section work and must never generate a one-shot full three-part manuscript.

The manifest must also define a conditional load named `confirmed_style_delta` pointing to `./references/style-delta-schema.md`; it must not load that reference for a one-off local preference.

- [ ] **Step 3: Write the five core rules**

- `writing-stance.md`: direct, factual, researcher-like prose; no invented facts/citations/statistics; claim strength follows evidence.
- `workflow.md`: read exact source and approved constraints, identify paragraph function, draft candidate, verify content/terminology/numbers, then await user approval.
- `evidence-boundary.md`: preserve `evidence_ceiling`; association, conditional pattern, manipulated effect, and mechanism are not interchangeable.
- `output-contract.md`: link to the shared candidate format, keep problem notes outside body text, and declare Stage 1A read-only.
- `paragraph-logic.md`: use problem → evidence → inference when appropriate; start from the paragraph’s role rather than a mechanical template; avoid repetitive meta-statements and excessive defensive negatives.

The style rules must retain the user's approved default: positive fact-led boundaries, theory-organized discussion, evidence before inference, and no automatic elevation of a temporary sentence preference into a permanent style rule. `workflow.md` must route an approved cross-paragraph preference to `references/style-delta-schema.md`; temporary sentence instructions remain task-local.

- [ ] **Step 4: Write all section fragments**

Each file begins with `Use when:` and contains section-specific checks:

- `title.md`: constructs, population/context, design claims, searchability, no mechanism stronger than evidence.
- `abstract.md`: problem, approach, key results, bounded contribution; numbers and conclusions synchronized.
- `introduction.md`: phenomenon/problem orientation, theoretical gap, construct sequence, literature support, and hypotheses earned by the argument.
- `hypotheses.md`: testable variables/directions/conditions aligned with design and analysis.
- `methods.md`: reproducible participants, design, materials, procedure, measures, exclusions, ethics, and analysis; report facts without inventing missing rules.
- `results.md`: analysis order, exact statistics, observed direction, interactions/simple effects, and minimal interpretation.
- `study-transitions.md`: identify the unresolved question and why the next design addresses it; no separate mini-discussion unless needed.
- `discussion.md`: organize by theoretical constructs/problems across studies; integrate stable, conditional, and inconsistent evidence; use external literature to support and explain differences.
- `limitations.md`: convert limitations into specific empirical next steps while retaining direct disclosure of material constraints.
- `conclusion.md`: answer the research question at the established evidence ceiling without replaying all results.

- [ ] **Step 5: Write language and task fragments**

Language fragments:

- `chinese.md`: natural academic Chinese, restrained transitions, clear subject choice, shorter clauses when nesting obscures logic.
- `english.md`: precise psychological terminology, controlled hedging, APA-compatible statistical prose, no forced native-speaker idioms.
- `chinese-to-english.md`: preserve scientific meaning first, produce English plus Chinese back-translation, and flag non-equivalent terms separately.

Task fragments:

- `local-edit.md`: read only the target and enough context; check propagation triggers; preserve untouched numbers/citations.
- `section-rewrite.md`: establish section function and evidence ceiling; output in manageable subsections.
- `full-manuscript.md`: process section by section, preserve one approved mainline, and use cumulative token budgets.
- `translation.md`: translate the approved source version, not an outdated or historical draft; do not silently edit facts during translation.

Create `references/style-delta-schema.md` with a compact record format containing `rule_id`, `user_wording`, `normalized_rule`, `scope`, `approved_on`, and `status`. Only `APPROVED` cross-paragraph preferences are written to `.psychology-paper/STYLE_DELTA.md`; rejected candidates, one-off phrasing requests, and rules already present in the shared baseline are excluded. When created, its path is recorded in `PROJECT.md` under `optional_state_files.style_delta`.

- [ ] **Step 6: Add writing scenarios and output-order assertions**

Create cases for: English paragraph edit, Chinese paragraph edit, Chinese-to-English translation, results paragraph with frozen numbers, discussion organized by theory rather than experiment replay, a central-claim rewrite requiring evidence audit, and a full-manuscript request requiring chunking.

Extend `test_scenario_contracts.py` so writing scenarios must include `expected_output_sections` and assert these exact orders:

```json
["Original English", "Revised English", "Chinese Translation"]
["Original Chinese", "Revised Chinese", "Necessary Notes"]
["Chinese Source", "Revised English", "Chinese Back-translation"]
```

- [ ] **Step 7: Validate and commit**

Run:

```powershell
python ".\tests\test_plugin_structure.py" -v
python ".\tests\test_scenario_contracts.py" -v
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\manuscript-writing"
```

Expected: all tests and official validation pass; no scenario authorizes manuscript writes.

```powershell
git add -- "./skills/manuscript-writing" "./tests/scenarios/manuscript-writing.json" "./tests/test_scenario_contracts.py" "./tests/test_plugin_structure.py"
git commit -m "feat: add bilingual psychology manuscript writing"
```

---

### Task 8: Close Stage 1A with Integration Checks, Documentation, and a Read-Only Trial

**Files:**
- Create: `./README.md`
- Create: `./LICENSE`
- Modify: `./tests/test_plugin_structure.py`
- Modify: `./tests/test_scenario_contracts.py`
- Modify: any Stage 1A file only when a failing validation identifies a concrete defect.

**Interfaces:**
- Consumes: all Stage 1A skills, shared rules, project tools, and scenario packs.
- Produces: a structurally valid plugin, a recorded read-only acceptance result, and a clear gate for Stage 1B. It does not create or invoke manuscript patching.

- [ ] **Step 1: Add final integration assertions before documentation exists**

Extend `test_plugin_structure.py` to assert:

1. Exactly four Stage 1A skills exist: `psychology-paper`, `journal-fit-style`, `evidence-audit`, `manuscript-writing`.
2. Every `SKILL.md` has matching folder/name frontmatter and a discriminating description.
3. Every JSON-compatible `manifest.yaml` has schema/version/skill and all referenced paths exist.
4. All production Markdown files under `.shared`, `static`, and `references` are reachable from at least one manifest or another reachable Markdown link.
5. The only state-rule definitions are in `state-consistency.md`; scenarios may cite rule IDs but may not define conditions.
6. No Stage 1A production file names or invokes `document-patcher` as an available capability; it may mention it only as a future handoff blocked in this stage.
7. `README.md` and `LICENSE` exist.

Run the tests and expect failure only for the missing final documentation or any newly exposed unreachable file.

- [ ] **Step 2: Write concise user and contributor documentation**

`README.md` must contain:

- what Stage 1A can do;
- what it deliberately cannot do;
- the four-skill architecture and one-primary-module rule;
- project initialization command and state-file meaning;
- validation commands;
- approved candidate output formats;
- the Stage 1A acceptance gate before Stage 1B;
- a warning that static validation does not prove scientific correctness or real-manuscript acceptance.

Do not add installation instructions for a marketplace because Stage 1A does not create one.

Use the standard MIT License text in `LICENSE` with copyright holder `Psychology Paper Contributors` and year `2026`.

- [ ] **Step 3: Run all automated tests**

Run:

```powershell
python -m unittest discover -s ".\tests" -v
```

Expected: every test passes. Record the exact count in the implementation report; do not hard-code the count into README because tests may grow during implementation.

- [ ] **Step 4: Run official validation for each skill and the plugin**

Run:

```powershell
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\psychology-paper"
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\journal-fit-style"
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\evidence-audit"
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" ".\skills\manuscript-writing"
python -X utf8 "$env:USERPROFILE\.codex\skills\.system\plugin-creator\scripts\validate_plugin.py" "."
```

Expected: five successful validations. A validator failure is fixed narrowly and rerun; it is not waived.

- [ ] **Step 5: Run repository hygiene checks**

Run:

```powershell
git diff --check
python -c "from pathlib import Path; terms=['TO'+'DO','TB'+'D','FIX'+'ME','[TO'+'DO:']; files=[p for p in Path('.').rglob('*') if p.is_file() and p.suffix.lower() in {'.md','.yaml','.json','.py'} and '.git' not in p.parts]; hits=[f'{p}: {term}' for p in files for term in terms if term in p.read_text(encoding='utf-8')]; print('\n'.join(hits)); raise SystemExit(bool(hits))"
```

Expected: no whitespace errors and no unfinished scaffold markers.

- [ ] **Step 6: Perform the first real-manuscript trial in read-only mode**

At execution time, ask the user to identify the authoritative manuscript only if `.psychology-paper/PROJECT.md` does not already identify it. After explicit approval, initialize project state with `init_project.py`; this is the only permitted write in the real manuscript directory.

Run one bounded workflow:

1. Build or refresh a target-journal profile using `journal-fit-style`.
2. Audit one user-selected section using `evidence-audit` at the requested risk threshold.
3. Produce one paragraph candidate using `manuscript-writing` in the approved three-part format.
4. Ask the user whether the journal profile, audit judgment, and candidate are acceptable.
5. If approved, record only those decisions and the next action in `PROJECT.md`; do not edit the manuscript.
6. Verify the manuscript hash before and after the trial is identical.

Use this acceptance record in the task response, not a new file:

```text
ROUTING: accepted / needs correction
EVIDENCE BOUNDARY: accepted / needs correction
OUTPUT FORMAT: accepted / needs correction
STATE MINIMALITY: accepted / needs correction
MANUSCRIPT HASH UNCHANGED: verified / not verified
STAGE 1A: accepted / not yet accepted
```

If any item needs correction, make a narrow change to the responsible skill, add or strengthen the corresponding scenario, rerun all tests, and repeat the same bounded trial. Do not start Stage 1B until all six lines are accepted or verified.

- [ ] **Step 7: Commit Stage 1A closeout**

```powershell
git add -- "./README.md" "./LICENSE" "./tests" "./skills" "./scripts" "./assets" "./.codex-plugin/plugin.json"
git commit -m "test: validate stage 1a read only workflow"
```

Before committing, inspect `git status --short` and confirm that the staged paths contain only `./`; do not add manuscript, data, or unrelated workspace files.

---

## Stage 1A Exit Gate

Stage 1A is complete only when all of the following are true:

- The plugin and four implemented skills pass official structure validation.
- All automated tests pass on Python 3.11+ using only the standard library.
- All manifest and Markdown references resolve and no shared production rule is orphaned.
- The orchestrator distinguishes discussion, approval, and write permission.
- Both scope-error directions pass: pure local edits stay local, and evidence-bearing local changes escalate to an impact scan.
- `state-consistency.md` is the sole definition source for illegal state combinations, and validators identify it in violations.
- Project initialization is explicit, non-overwriting, UTF-8 safe, and leaves manuscript contents unchanged.
- Journal analysis separates current official requirements from observed article style.
- Evidence auditing adapts to paper and design type and reports problems without making edits.
- Writing candidates use the approved bilingual order and observe the token/chunking contract.
- The real-manuscript trial leaves the manuscript hash unchanged and the user accepts routing, evidence boundary, output format, and state minimality.
- Stage 1B remains closed until this gate is met.

## Deferred Work Boundaries

The following work receives a separate plan only after Stage 1A acceptance:

- Stage 1B: `document-patcher`, temporary recovery transactions, `ROLLBACK_PENDING`, `ROLLBACK_FAILED`, DOCX/TXT/Markdown point patches, and visual milestone checks.
- Stage 2: `literature-map`, `analysis-adapter`, `LITERATURE_MAP.tsv`, `ANALYSIS_REGISTRY.md`, and external statistical-software adapters.
- Stage 3: `review-revision`, `submission-check`, response letters, anonymization, title pages, cover letters, and submission-system checks.

No deferred module may be partially scaffolded or advertised as available during Stage 1A.

---

## Approved Post-Stage-1A Regression: Deterministic Resource Loading

This correction addresses the observed clean-thread failure in which an Agent had already read the correct Skill entrypoint but guessed a different child path and then expanded into repository enumeration.

The correction is test-first and limited to resource loading:

1. Add failing tests for arbitrary working directories, Chinese paths, exact logical selectors, no directory traversal, no fuzzy fallback, plugin-root containment, and a bounded output budget.
2. Implement `scripts/load_skill_resources.py` using only the standard library. It derives the plugin root from its own file location, always includes the selected Skill's `always_load` group, resolves only explicit Manifest selectors, deduplicates declared files, and defaults to a 12,000-character output ceiling.
3. Replace direct child-resource links in all four Stage 1A `SKILL.md` entrypoints with the one shared loader and logical selectors.
4. Treat any runtime missing declared resource as installed-plugin corruption. Do not enumerate the repository, infer another path, or continue with an incomplete rule set.
5. Run the focused tests, full regression suite, official Skill validators, and plugin validator before committing.

Build-time integrity checks may inspect the plugin source without emitting its contents into model context. The installed Skill's runtime path must never use directory traversal for discovery or recovery.
