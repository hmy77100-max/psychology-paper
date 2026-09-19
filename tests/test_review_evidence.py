import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    path = ROOT / 'scripts' / (name + '.py')
    if not path.is_file():
        raise AssertionError(f'Missing review support: {path.name}')
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def evidence_note():
    return {
        'issue_id': 'REVIEW-01',
        'question': 'Does the adapted measure support the construct label?',
        'manuscript_location': 'Methods 2.1; Appendix B',
        'search_note': 'Compared original and adapted versions supplied by author.',
        'sources': [{
            'source_id': 'SOURCE-01',
            'reference': 'https://example.org/original-measure',
            'access_level': 'full_text',
            'locator': 'Methods, Measures, paragraph 2',
            'observed_support': 'The original defines occupational recovery.',
            'applicability': 'Different adaptation; transfer remains uncertain.',
            'relation': 'qualifies',
        }],
        'counterevidence': 'No comparable validation of this adaptation located.',
        'evidence_status': 'UNRESOLVED',
        'conclusion': 'Confirm the actual adaptation before recommending a name.',
        'coverage_limit': 'Adapted version validation unavailable.',
        'stop_reason': 'Available sources do not resolve adaptation validity.',
    }


class ReviewEvidenceTests(unittest.TestCase):
    def test_full_review_does_not_require_project_or_allow_writing(self):
        guards = module('workflow_guards')
        for active in (False, True):
            with self.subTest(active=active):
                result = guards.decide_project_mode(task='evidence_audit', scope='full_manuscript',
                    journal_status='USER_CONFIRMED', project_mode_active=active)
                self.assertEqual(result.status, 'READ_ONLY_AUDIT')
                self.assertFalse(result.writing_allowed)

    def test_external_resources_are_conditional_and_under_budget(self):
        loader = module('load_skill_resources')
        base = loader.load_skill_resources(skill='evidence-audit', selectors=[])
        self.assertTrue(any(r.relative_path.endswith('review-workflow.md') for r in base.resources))
        self.assertFalse(any(r.relative_path.endswith('external-evidence.md') for r in base.resources))
        full = loader.load_skill_resources(skill='evidence-audit', selectors=[
            'axes.paper_type.empirical', 'axes.design_tags.survey', 'axes.design_tags.experiment',
            'axes.design_tags.behavioral-task', 'axes.scope.full', 'axes.risk_threshold.all',
            'conditional_loads.external_evidence', 'shared_loads.evidence', 'shared_loads.source_authority'])
        self.assertLessEqual(full.total_chars, 12000)
        self.assertTrue(any(r.relative_path.endswith('external-evidence.md') for r in full.resources))
        self.assertTrue(any(r.relative_path.endswith('evidence-note.md') for r in full.resources))
        self.assertFalse(any('journal-fit-style' in r.relative_path for r in full.resources))

    def test_complete_record_does_not_claim_scientific_verification(self):
        result = module('review_evidence').validate_record(evidence_note())
        self.assertTrue(result['record_complete'], result)
        self.assertFalse(result['scientific_verification'])
        self.assertTrue(result['limitations'])

    def test_missing_source_locator_cannot_be_complete(self):
        record = evidence_note()
        record['sources'][0]['locator'] = ''
        result = module('review_evidence').validate_record(record)
        self.assertFalse(result['record_complete'])
        self.assertTrue(any('locator' in error for error in result['errors']))

    def test_duplicate_source_ids_are_rejected(self):
        record = evidence_note()
        record['sources'].append(copy.deepcopy(record['sources'][0]))
        result = module('review_evidence').validate_record(record)
        self.assertFalse(result['record_complete'])

    def test_abstract_and_snippet_access_are_disclosed_not_reclassified(self):
        for access in ('abstract', 'snippet'):
            record = evidence_note()
            record['sources'][0]['access_level'] = access
            original = copy.deepcopy(record)
            result = module('review_evidence').validate_record(record)
            self.assertTrue(result['record_complete'], result)
            self.assertTrue(any(access in item for item in result['limitations']))
            self.assertEqual(record, original)

    def test_unavailable_source_does_not_require_fabricated_support(self):
        record = evidence_note()
        record['sources'][0].update(access_level='unavailable', locator='', observed_support='')
        result = module('review_evidence').validate_record(record)
        self.assertTrue(result['record_complete'], result)
        record['sources'][0]['observed_support'] = 'Pretended full-text result'
        self.assertFalse(module('review_evidence').validate_record(record)['record_complete'])

    def test_offline_unresolved_note_can_be_complete_without_sources(self):
        record = evidence_note()
        record.update(sources=[], search_note='User requested offline review.',
                      coverage_limit='No external verification performed.')
        result = module('review_evidence').validate_record(record)
        self.assertTrue(result['record_complete'], result)
        self.assertFalse(result['scientific_verification'])

    def test_validator_does_not_choose_or_overwrite_model_conclusion(self):
        for status in ('ALIGNED', 'BOUNDED', 'CONDITIONAL', 'UNRESOLVED', 'CONTRADICTED', 'OUTSIDE_EVIDENCE'):
            record = evidence_note()
            record['evidence_status'] = status
            original = copy.deepcopy(record)
            result = module('review_evidence').validate_record(record)
            self.assertTrue(result['record_complete'], result)
            self.assertEqual(record, original)
            self.assertNotIn('recommended_action', result)

    def test_malformed_records_return_diagnostics(self):
        for record in (None, [], {}, {'sources': 1}, {'sources': [None]}):
            with self.subTest(record=record):
                self.assertFalse(module('review_evidence').validate_record(record)['record_complete'])

    def test_invalid_controlled_fields_are_rejected(self):
        for field, value in [('access_level', 'read_it_somewhere'), ('relation', 'definitely_true')]:
            record = evidence_note()
            record['sources'][0][field] = value
            self.assertFalse(module('review_evidence').validate_record(record)['record_complete'])
        record = evidence_note()
        record['evidence_status'] = 'ACCEPTED_BY_JOURNAL'
        self.assertFalse(module('review_evidence').validate_record(record)['record_complete'])

    def test_cli_reads_stdin_without_creating_files(self):
        script = ROOT / 'scripts' / 'review_evidence.py'
        self.assertTrue(script.is_file(), 'Missing evidence-note CLI')
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, '-X', 'utf8', str(script), '--record', '-'],
                input=json.dumps(evidence_note()), text=True, encoding='utf-8', capture_output=True, cwd=tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(tmp).iterdir()), [])
            self.assertFalse(json.loads(result.stdout)['scientific_verification'])

    def test_cli_invalid_json_is_bounded(self):
        script = ROOT / 'scripts' / 'review_evidence.py'
        self.assertTrue(script.is_file(), 'Missing evidence-note CLI')
        result = subprocess.run([sys.executable, '-X', 'utf8', str(script), '--record', '-'],
            input='{', text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
