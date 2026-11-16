"""Controlled candidate executions, input protection, and analytic references."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from test_analysis_contracts import candidate_spec


class RunnerTests(unittest.TestCase):
    def test_method_query_is_compact_read_only_and_needs_no_optional_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, '-S', str(ROOT/'scripts/analysis_runner.py'),
                                     'methods', '--method', 'paired_t'], cwd=folder,
                                    capture_output=True, text=True, encoding='utf-8')
            self.assertEqual(result.returncode, 0, result.stderr)
            info = json.loads(result.stdout)
            self.assertEqual(info['status'], 'METHOD_CONTRACT')
            self.assertEqual(info['required_model_fields'], ['x', 'y', 'subject_id'])
            self.assertFalse(info['execution_ready'])
            self.assertIn('subject_id', info['variable_roles'])
            self.assertLess(len(result.stdout), 5000)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_method_query_fields_match_actual_validation(self):
        import analysis_contracts as c
        for method in c.METHODS:
            info = c.describe_method(method)
            for field in info['required_model_fields']:
                spec = candidate_spec()
                spec['model'] = {'method': method}
                errors = c.validate_spec(spec)
                self.assertIn('model.' + field, [e['field'] for e in errors])
        with self.assertRaises(ValueError):
            c.describe_method('unimplemented')

    def test_method_query_does_not_misstate_existing_scoring_metadata(self):
        import analysis_contracts as c
        info = c.describe_method('paired_t')
        self.assertEqual(info['scoring']['accepted_methods'], ['none', 'scale'])
        self.assertIn('without re-scoring', info['scoring']['execution'])

    def test_method_query_cannot_be_used_to_skip_run_validation(self):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/analysis_runner.py'),
                                 'run', '--method', 'paired_t'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('--method is only valid with methods', result.stderr)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='分析运行-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / 'source.csv'
        self.data.write_text('id,score,group,second\n1,1,A,0\n2,2,A,1\n3,3,A,1\n4,4,A,2\n5,2,B,1\n6,4,B,2\n7,6,B,3\n8,8,B,4\n', encoding='utf-8')
        self.original = self.data.read_bytes()
        self.spec = candidate_spec()
        self.spec['data']['path'] = str(self.data)
        self.spec['data']['sha256'] = hashlib.sha256(self.original).hexdigest()
        self.spec['data']['read_options']['missing_values'] = ['']
        self.spec['authorization']['output_dir'] = str(self.root / 'candidates')

    def call(self, operation, spec=None):
        path = self.root / 'request.json'
        path.write_text(json.dumps(spec or self.spec), encoding='utf-8')
        result = subprocess.run([sys.executable, '-X', 'utf8', str(ROOT/'scripts/analysis_runner.py'), operation, '--spec', str(path)], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        return json.loads(result.stdout)

    def test_entry_exists(self):
        self.assertTrue((ROOT/'scripts/analysis_runner.py').is_file())

    @unittest.skipUnless(importlib.util.find_spec('scipy'), 'optional statistics environment')
    def test_candidate_executes_without_formal_source_and_preserves_input(self):
        result = self.call('run')
        self.assertEqual(result['status'], 'COMPLETED')
        run_path = Path(result['artifacts'][0]['path'])
        run = json.loads(run_path.read_text(encoding='utf-8'))
        self.assertEqual(run['adoption_status'], 'CANDIDATE')
        self.assertEqual(run['results'][0]['n'], 8)
        self.assertAlmostEqual(run['results'][0]['estimate'], 3.75)
        self.assertEqual(self.data.read_bytes(), self.original)
        self.assertFalse((self.root/'.psychology-paper').exists())

    def test_changed_data_is_blocked_before_output(self):
        self.data.write_text('score\n99\n', encoding='utf-8')
        result = self.call('run')
        self.assertEqual(result['status'], 'INPUT_CHANGED')
        self.assertFalse((self.root/'candidates').exists())

    def test_missing_column_is_not_ready(self):
        self.spec['field_map'][0]['column'] = 'missing_column'
        result = self.call('preflight')
        self.assertEqual(result['status'], 'INVALID_DATA')
        self.assertFalse(result['execution_ready'])

    def test_compute_permission_is_not_inferred(self):
        self.spec['authorization']['compute'] = False
        result = self.call('run')
        self.assertFalse(result['result_complete'])
        self.assertFalse((self.root/'candidates').exists())

    def test_plugin_directory_cannot_be_output(self):
        self.spec['authorization']['output_dir'] = str(ROOT/'candidates-forbidden')
        result = self.call('run')
        self.assertEqual(result['status'], 'PERMISSION_DENIED')
        self.assertFalse((ROOT/'candidates-forbidden').exists())

    def test_unknown_method_is_not_silently_replaced(self):
        self.spec['model']['method'] = 'unconfigured_method'
        result = self.call('run')
        self.assertEqual(result['status'], 'UNSUPPORTED_METHOD')
        self.assertFalse((self.root/'candidates').exists())

    def test_method_review_does_not_require_data_or_create_output(self):
        result = self.call('preflight', {'schema_version':2,'analysis_id':'consultation','revision':1,'intent':'METHOD_REVIEW'})
        self.assertEqual(result['status'], 'METHOD_REVIEW_READY')
        self.assertFalse(result['execution_ready'])

    def test_formal_source_is_not_silently_changed_to_python(self):
        import analysis_contracts as contracts
        self.spec['intent']='FORMAL_ANALYSIS'
        self.spec['sources']=[{'source_id':'original','role':'AUTHORITATIVE','software':'SPSS','version':'29'}]
        self.spec['authorization']['formal_spec_hash']=contracts.spec_hash(self.spec)
        result=self.call('run')
        self.assertEqual(result['status'],'FORMAL_BACKEND_MISMATCH')
        self.assertFalse((self.root/'candidates').exists())

    @unittest.skipUnless(importlib.util.find_spec('scipy'), 'optional statistics environment')
    def test_welch_reference_is_analytic_not_runner_generated(self):
        self.spec['field_map'].append({'variable':'group','column':'group','confirmation_status':'DOCUMENTED','evidence_ref':'synthetic design'})
        self.spec['model']={'method':'welch_t','outcome':'score','group':'group','group_order':['A','B']}
        result = self.call('run')
        self.assertEqual(result['status'],'COMPLETED',result)
        run = json.loads(Path(result['artifacts'][0]['path']).read_text(encoding='utf-8'))
        row=run['results'][0]
        # A=[1,2,3,4], B=[2,4,6,8]. Sample variances 5/3 and 20/3.
        self.assertAlmostEqual(row['estimate'],-2.5,places=12)
        self.assertAlmostEqual(row['se'],math.sqrt(25/12),places=12)
        self.assertAlmostEqual(row['df'],75/17,places=12)
        self.assertAlmostEqual(row['statistic'],-math.sqrt(3),places=12)


    @unittest.skipUnless(importlib.util.find_spec('scipy'), 'optional statistics environment')
    def test_independent_wolfram_references_via_controlled_runner(self):
        reference = json.loads((ROOT/'tests/fixtures/analysis/independent-reference.json').read_text(encoding='utf-8'))
        for method, expected in reference['cases'].items():
            with self.subTest(method=method):
                if method in ('welch_t', 'student_t'):
                    records = [(i+1, x, '', 'A') for i, x in enumerate(expected['x'])]
                    records += [(i+5, y, '', 'B') for i, y in enumerate(expected['y'])]
                    model = {'method':method, 'outcome':'x', 'group':'group', 'group_order':['A','B']}
                else:
                    records = [(i+1, x, y, '') for i,(x,y) in enumerate(zip(expected['x'],expected['y']))]
                    model = {'method':method, 'x':'x', 'y':'y'}
                    if method == 'paired_t':
                        model['subject_id'] = 'id'
                self.data.write_text('id,x,y,group\n' + ''.join(','.join(map(str,row))+'\n' for row in records), encoding='utf-8')
                spec = copy.deepcopy(self.spec)
                spec['data']['sha256'] = hashlib.sha256(self.data.read_bytes()).hexdigest()
                spec['field_map'] = [{'variable':name,'column':name,'confirmation_status':'DOCUMENTED','evidence_ref':'independent controlled reference'} for name in ('id','x','y','group')]
                spec['model'] = model
                spec['design']['variables'] = [{'name':'x','role':'outcome'}]
                result = self.call('run', spec)
                self.assertEqual(result['status'],'COMPLETED',result)
                run = json.loads(Path(result['artifacts'][0]['path']).read_text(encoding='utf-8'))
                actual = run['results'][0]
                for key in ('estimate','se','df','statistic','p'):
                    if key in expected:
                        self.assertAlmostEqual(actual[key],expected[key],delta=1e-10,msg=method+' '+key)
                for actual_limit, expected_limit in zip(actual['ci'],expected['ci']):
                    self.assertAlmostEqual(actual_limit,expected_limit,delta=1e-9,msg=method+' CI')
                self.assertEqual(actual['ci_alternative'],'two-sided')
                self.assertEqual(run['adoption_status'],'CANDIDATE')

    @unittest.skipUnless(importlib.util.find_spec('scipy'), 'optional statistics environment')
    def test_descriptive_and_scale_scores_match_hand_arithmetic(self):
        # Independent arithmetic: [1,2,3] mean=2, sample variance=1, SE=1/sqrt(3).
        self.data.write_text('a,b\n1,5\n2,3\n3,1\n', encoding='utf-8')
        spec = copy.deepcopy(self.spec)
        spec['data']['sha256'] = hashlib.sha256(self.data.read_bytes()).hexdigest()
        spec['field_map'] = [{'variable':name,'column':name,'confirmation_status':'DOCUMENTED','evidence_ref':'synthetic hand arithmetic'} for name in ('a','b')]
        spec['model'] = {'method':'descriptive','columns':['a']}
        spec['design']['variables'] = [{'name':'a','role':'outcome'},{'name':'b','role':'predictor'}]
        result = self.call('run',spec)
        self.assertEqual(result['status'],'COMPLETED',result)
        run = json.loads(Path(result['artifacts'][0]['path']).read_text(encoding='utf-8'))
        row = run['results'][0]
        self.assertEqual(row['n'],3)
        self.assertAlmostEqual(row['estimate'],2)
        self.assertAlmostEqual(row['sd'],1)
        self.assertAlmostEqual(row['se'],1/math.sqrt(3))
        # Reverse b on 1..5: [1,3,5]; row means with a: [1,2.5,4].
        spec['model'] = {'method':'scale_score','columns':['a','b']}
        spec['scoring'] = {'method':'scale','items':['a','b'],'reverse_items':['b'],'minimum':1,'maximum':5,'aggregation':'mean','min_answered':2}
        result = self.call('run',spec)
        self.assertEqual(result['status'],'COMPLETED',result)
        run = json.loads(Path(result['artifacts'][0]['path']).read_text(encoding='utf-8'))
        row = run['results'][0]
        self.assertEqual(row['n'],3)
        self.assertAlmostEqual(row['estimate'],2.5)
        self.assertAlmostEqual(row['sd'],1.5)
        self.assertAlmostEqual(row['se'],1.5/math.sqrt(3))
        import csv
        derived = next(a['path'] for a in run['artifact_refs'] if a['kind']=='derived')
        with Path(derived).open(encoding='utf-8',newline='') as stream:
            scores = [float(r['score']) for r in csv.DictReader(stream)]
        self.assertEqual(scores,[1,2.5,4])


if __name__ == '__main__':
    unittest.main()
