# Contribution and revision-options validation

## Implemented scope

Steps 4 and 5 add conditional contribution/journal comparison and revision-options guidance within evidence-audit. They reuse existing context, distinguish requirements from examples/inference, and organize model-generated advice by benefits, evidence needs, resources and dependencies. No new decision script, journal-profile store, positioning prerequisite or editing execution is introduced.

## Regression evidence

Two resource tests were added before production guidance. They initially produced three missing-selector errors. After implementation, all 108 tests pass. During integration, the new scenario file initially used an incompatible object wrapper; the existing scenario-contract tests caught this, and the fixture was converted to the established list/schema without weakening those tests.

Official plugin and evidence-audit Skill validators pass. Default resource ceiling remains 12,000 characters: contribution plus full report/risk is 7,615; options plus full report/risk is 7,746; both new resources plus local report is 9,903. These are content character counts, not measured conversation-token savings.

## Behavioral baseline

A fresh-context agent read the old rules and simulated confirmed-target review, resource-constrained causal-claim revision, and alternative framing followed by assent. It already gave appropriate advice in all three; no behavioral failure is claimed. It identified missing explicit contracts for official requirements versus examples/inference, resource-sensitive option ordering, and discussion versus adoption of a different stance.

The baseline agent also attempted an oversized external/authority/quality/impact load (12,618 characters); the loader rejected it and the agent stopped that invocation. Its observations therefore cover only successfully loaded old resources. This is evidence of a bounded load failure, not scientific review completion. Revised-stage testing uses focused loads rather than raising the limit.

## Revised behavioral rehearsal

A separate fresh-context agent used focused canonical loads and produced concrete responses for all nine fixtures. It distinguished official rules from sample practices; recommended bounded claims under resource limits; kept proposed framing separate from adoption; limited missing-target/local review; compared conflicting profile sources without overwriting state; rejected unsupported novelty and concealment; ordered scoring before dependent conclusions and audience fit; asked full versus targeted scope on the explicit ambiguous edit request; and honored issues-only scope. No substantive conflict among the new guidance and quality rules was found.

The agent reported one harness instruction violation: its initial read batch attempted an undeclared root `manifest.json` before reading the prescribed Skill manifest. The path was absent; subsequent canonical loads succeeded. No directory enumeration or mutation occurred. This is not counted as full resource-resolution compliance and remains a model-adherence limitation, despite correct scenario answers. Fixtures 004 and 009 supply no actual manuscript text, so responses appropriately avoided invented substantive findings.

## Limits

Scenario fixtures expose expected behavior and are synthetic. They cannot establish blind-test reliability, improved acceptance rates or long-run model stability. This increment does not perform live journal-policy verification, inspect a real manuscript or execute a downstream revision. Previous increments' live lookup evidence is not relabeled as validation of this work. All six review responsibilities now have initial guidance; longitudinal evaluation remains outstanding.
