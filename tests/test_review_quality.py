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
        raise AssertionError('Missing ' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def record():
    return {'manuscript_version': 'version-2',
            'coverage': 'Methods and appendix inspected; data not supplied.',
            'issues': [{'issue_id': 'I-1', 'location': 'Methods 2.1',
                        'claim': 'Unit independence', 'analysis_identity': 'cluster trial primary model',
                        'kind': 'REPORTING_GAP', 'status': 'OPEN',
                        'basis': 'No clustering description in inspected methods.',
                        'evidence_refs': ['Methods 2.1'], 'status_basis': 'Await author model output.'}]}


class ReviewQualityTests(unittest.TestCase):
    def validate(self, value):
        return module('review_quality').validate_review(value)

    def test_valid_standalone_note_does_not_require_history_or_scientific_verdict(self):
        result = self.validate(record())
        self.assertTrue(result['record_complete'], result)
        self.assertFalse(result['scientific_verification'])
        self.assertTrue(result['limitations'])

    def test_methods_and_quality_load_only_when_selected(self):
        loader = module('load_skill_resources')
        base = loader.load_skill_resources(skill='evidence-audit', selectors=[])
        for selector, filename in [('methods_review', 'methods-review.md'), ('quality_review', 'quality-review.md')]:
            self.assertFalse(any(x.relative_path.endswith(filename) for x in base.resources))
            selected = loader.load_skill_resources(skill='evidence-audit', selectors=['conditional_loads.' + selector])
            self.assertTrue(any(x.relative_path.endswith(filename) for x in selected.resources))
            self.assertLessEqual(selected.total_chars, 12000)

    def test_mixed_design_methods_load_stays_within_default_budget(self):
        loader = module('load_skill_resources')
        result = loader.load_skill_resources(skill='evidence-audit', selectors=[
            'axes.paper_type.empirical','axes.design_tags.survey','axes.design_tags.experiment',
            'axes.design_tags.longitudinal','axes.design_tags.behavioral-task',
            'axes.scope.full','axes.risk_threshold.all','conditional_loads.methods_review'])
        self.assertLessEqual(result.total_chars, 12000)

    def test_unknown_kind_or_status_is_rejected(self):
        for key in ('kind', 'status'):
            value = record()
            value['issues'][0][key] = 'AUTO_ACCEPT'
            self.assertFalse(self.validate(value)['record_complete'])

    def test_all_model_classifications_allowed_without_changing_them(self):
        for kind in ('DEMONSTRATED_ERROR', 'REPORTING_GAP', 'UNRESOLVED_CHECK', 'BOUNDED_LIMITATION', 'AUTHOR_CHOICE'):
            value = record()
            value['issues'][0]['kind'] = kind
            before = copy.deepcopy(value)
            result = self.validate(value)
            self.assertTrue(result['record_complete'], result)
            self.assertEqual(value, before)

    def test_missing_basis_and_evidence_are_rejected(self):
        for key, missing in [('basis',''), ('evidence_refs',[]), ('status_basis','')]:
            value = record()
            value['issues'][0][key] = missing
            self.assertFalse(self.validate(value)['record_complete'])

    def test_duplicate_ids_are_rejected(self):
        value = record()
        value['issues'].append(copy.deepcopy(value['issues'][0]))
        self.assertFalse(self.validate(value)['record_complete'])

    def test_hold_requires_author_basis_but_never_means_resolved(self):
        value = record()
        item = value['issues'][0]
        item.update(status='HELD', status_basis='Author asked to retain as limitation.')
        result = self.validate(value)
        self.assertTrue(result['record_complete'], result)
        self.assertEqual(item['status'], 'HELD')
        self.assertNotIn('submission_ready', result)

    def test_resolution_needs_inspected_resolution_evidence(self):
        value = record()
        value['issues'][0]['status'] = 'RESOLVED'
        self.assertFalse(self.validate(value)['record_complete'])
        value['issues'][0]['resolution_evidence'] = 'Appendix B now inspected: model includes class effects.'
        self.assertTrue(self.validate(value)['record_complete'])

    def test_reopened_record_requires_prior_status_and_change_basis(self):
        value = record()
        item = value['issues'][0]
        item['status'] = 'REOPENED'
        self.assertFalse(self.validate(value)['record_complete'])
        item.update(previous_status='RESOLVED', change_basis='Version-2 changed scoring; original resolution no longer applies.')
        self.assertTrue(self.validate(value)['record_complete'])

    def test_closed_to_open_cannot_silently_reset_history(self):
        value = record()
        value['issues'][0]['previous_status'] = 'RESOLVED'
        self.assertFalse(self.validate(value)['record_complete'])

    def test_explicit_duplicate_link_is_accepted_without_semantic_merging(self):
        value = record()
        alias = copy.deepcopy(value['issues'][0])
        alias.update(issue_id='I-9', duplicate_of='I-1')
        value['issues'].append(alias)
        before = copy.deepcopy(value)
        result = self.validate(value)
        self.assertTrue(result['record_complete'], result)
        self.assertEqual(value, before)

    def test_duplicate_link_requires_existing_canonical_with_same_status(self):
        for target in ('MISSING', 'I-9'):
            value = record()
            alias = copy.deepcopy(value['issues'][0])
            alias.update(issue_id='I-9', duplicate_of=target)
            value['issues'].append(alias)
            self.assertFalse(self.validate(value)['record_complete'])
        value = record()
        alias = copy.deepcopy(value['issues'][0])
        alias.update(issue_id='I-9', duplicate_of='I-1', status='HELD')
        value['issues'].append(alias)
        self.assertFalse(self.validate(value)['record_complete'])

    def test_empty_issue_list_does_not_imply_acceptance(self):
        value = record()
        value['issues'] = []
        result = self.validate(value)
        self.assertTrue(result['record_complete'])
        self.assertFalse(result['scientific_verification'])

    def test_malformed_records_return_errors_not_tracebacks(self):
        for value in (None, [], {}, {'issues': 3}, {'issues': [None]}):
            self.assertFalse(self.validate(value)['record_complete'])

    def test_cli_stdin_does_not_create_project_files(self):
        script = ROOT / 'scripts/review_quality.py'
        self.assertTrue(script.is_file(), 'Missing review-quality checker')
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, '-X','utf8',str(script),'--record','-'],
                input=json.dumps(record()), capture_output=True, text=True, encoding='utf-8', cwd=tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)['scientific_verification'])
            self.assertEqual(list(Path(tmp).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
