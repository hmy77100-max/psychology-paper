import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

class ContractTests(unittest.TestCase):
    def test_summary_and_inference_consistency(self):
        import analysis_contracts as c
        for method in ('descriptive','scale_score'):
            run=valid_descriptive_run()
            if method=='scale_score':
                spec=run['scientific_spec'];spec['model']={'method':method,'columns':['score']}
                spec['scoring']={'method':'scale','items':['score'],'reverse_items':[],'minimum':1,'maximum':5,'aggregation':'mean','min_answered':1}
                run['method_id']=method;run['spec_hash']=c.spec_hash(spec)
            row=run['results'][0]
            row.update(sd=1,se=.577,df=2,ci=[-1.48,3.48],confidence_level=.95,ci_alternative='two-sided')
            self.assertEqual(c.validate_result(run),[])
            for key,value in [('sd',-1),('sd',True),('se',float('nan')),('n',1),('df',3),('confidence_level',.9),('ci_alternative','greater'),('ci',[2,1])]:
                bad=copy.deepcopy(run);bad['results'][0][key]=value
                with self.subTest(method=method,key=key,value=value): self.assertTrue(c.validate_result(bad))
            for key in ('sd','se','df','ci'):
                bad=copy.deepcopy(run);del bad['results'][0][key]
                self.assertTrue(c.validate_result(bad))
        for method in ('welch_t','student_t'):
            run=valid_descriptive_run();spec=run['scientific_spec']
            spec['model']={'method':method,'outcome':'score','group':'score','group_order':['A','B']}
            run['method_id']=method;run['spec_hash']=c.spec_hash(spec);run['sample_audit']['effective_n']=6
            run['results']=[{'outcome_id':'score','term_id':'group','contrast_id':'A - B','estimate':1,'n':6,'n_by_group':[3,3],'se':1,'df':4,'statistic':1,'statistic_name':'t','p':.37,'ci':[-1.77,3.77],'confidence_level':.95,'ci_alternative':'two-sided','test_alternative':'two-sided'}]
            self.assertEqual(c.validate_result(run),[])
            for key,value in [('test_alternative','greater'),('n_by_group',[3,2]),('n_by_group',[True,5]),('n_by_group',[0,6]),('n_by_group',[6]),('n_by_group','3,3')]:
                bad=copy.deepcopy(run);bad['results'][0][key]=value
                with self.subTest(method=method,key=key,value=value): self.assertTrue(c.validate_result(bad))
            bad=copy.deepcopy(run);del bad['results'][0]['n_by_group'];self.assertTrue(c.validate_result(bad))

    def test_descriptive_completeness_is_required_even_when_two_runs_match(self):
        import analysis_contracts as c
        from compare_analysis_results import compare_results
        run=valid_descriptive_run()
        for key in ('sd','se','df','ci'):
            bad=copy.deepcopy(run)
            bad['results'][0].pop(key,None)
            with self.subTest(key=key):
                self.assertTrue(c.validate_result(bad))
                self.assertEqual(compare_results(bad,bad,tolerance=1e-6)['status'],'NOT_COMPARABLE')

    def test_filter_options_are_fully_understood(self):
        import analysis_contracts as c
        for rule in ({'column':'score','op':'eq','value':1,'negate':True},
                     {'column':'score','variable':'score','op':'eq','value':1},
                     {'column':'score','op':'eq','value':1,'values':[2]}):
            s=candidate_spec();s['sample']['filters']=[rule]
            self.assertTrue(c.validate_spec(s))

    def test_scientific_snapshot_cannot_claim_review_to_skip_validation(self):
        import analysis_contracts as c
        self.assertTrue(c.validate_spec({'intent':'METHOD_REVIEW'},_scientific_only=True))

    def test_declared_sample_size_must_match_result(self):
        import analysis_contracts as c
        run=valid_descriptive_run()
        run['scientific_spec']['sample']['n']=200
        run['spec_hash']=c.spec_hash(run['scientific_spec'])
        self.assertTrue(c.validate_result(run))

    def test_boolean_is_not_a_numeric_observation(self):
        import importlib.util
        if not importlib.util.find_spec('scipy'): self.skipTest('optional statistics environment')
        import analysis_backends as b
        with self.assertRaises(b.BackendError):
            b.compute(candidate_spec(), [{'score':True},{'score':2},{'score':3}], ['score'])

    def test_unsupported_options_are_not_silently_ignored(self):
        import analysis_contracts as c
        for field,key,value in [('model','weights','w'),('data','read_options',{'encoding':'utf-8','delimiter':',','skip_rows':5})]:
            s=candidate_spec();s[field][key]=value
            self.assertTrue(c.validate_spec(s))

    def test_result_scientific_shape_and_requested_coverage(self):
        import analysis_contracts as c
        run=valid_descriptive_run()
        run['scientific_spec']='fake'
        self.assertTrue(c.validate_result(run))
        run=valid_descriptive_run()
        run['results'][0]['outcome_id']='unrequested'
        self.assertTrue(c.validate_result(run))

    def test_contract_api_and_review(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('analysis_contracts'))
        import analysis_contracts as c
        self.assertEqual(c.validate_spec({'schema_version':2,'analysis_id':'review','revision':1,'intent':'METHOD_REVIEW'}), [])

    def test_candidate_and_hash(self):
        import analysis_contracts as c
        s = candidate_spec()
        self.assertEqual(c.validate_spec(s, for_execution=True), [])
        t = copy.deepcopy(s)
        t['authorization']['output_dir']='elsewhere'
        t['data']['path']='moved.csv'
        t['field_map'][0]['confirmation_status']='USER_CONFIRMED'
        self.assertEqual(c.spec_hash(s), c.spec_hash(t))
        t['data']['read_options']['delimiter']=';'
        self.assertNotEqual(c.spec_hash(s), c.spec_hash(t))
        self.assertIn('within-subjects', c.normalize_design_tags(['factorial-within-subjects']))

    def test_formal_confirmation_and_empty_mapping(self):
        import analysis_contracts as c
        s=candidate_spec(); s['field_map'][0]['column']=''
        self.assertTrue(c.validate_spec(s, True))
        s=candidate_spec(); s['intent']='FORMAL_ANALYSIS'
        self.assertTrue(c.validate_spec(s, True))
        s['sources']=[{'source_id':'a','role':'AUTHORITATIVE','software':'Python'}]
        s['authorization']['formal_spec_hash']=c.spec_hash(s)
        self.assertEqual(c.validate_spec(s, True), [])


def candidate_spec():
    return {'schema_version':2,'analysis_id':'synthetic','revision':1,'intent':'CANDIDATE_ANALYSIS',
        'design':{'design_tags':['survey'],'observation_unit':'participant','research_question_type':'description','variables':[{'name':'score','role':'outcome'}]},
        'data':{'path':'synthetic.csv','sha256':'a'*64,'format':'csv','read_options':{'encoding':'utf-8','delimiter':','}},
        'field_map':[{'variable':'score','column':'score','confirmation_status':'CANDIDATE_INFERRED','evidence_ref':'controlled fixture'}],
        'scoring':{'method':'none'},'sample':{'missing':'complete_case','filters':[]},'model':{'method':'descriptive','columns':['score']},
        'inference':{'alpha':.05,'confidence_level':.95,'alternative':'two-sided'},'sources':[],
        'authorization':{'data_read':True,'compute':True,'output_dir':'output','reference':'user approved controlled fixture'}}

def valid_descriptive_run():
    import analysis_contracts as c
    s=candidate_spec()
    return {'schema_version':1,'analysis_id':'a','revision':1,'run_id':'r','method_id':'descriptive','intent':'CANDIDATE_ANALYSIS','spec_hash':c.spec_hash(s),'input_hash':s['data']['sha256'],'scientific_spec':c.scientific_spec(s),'status':'COMPLETED','result_complete':True,'adoption_status':'CANDIDATE','results':[{'outcome_id':'score','term_id':'mean','contrast_id':'overall','estimate':1,'n':3,'sd':1,'se':0.5773502691896258,'df':2,'ci':[-1.484137711719546,3.484137711719546],'confidence_level':.95,'ci_alternative':'two-sided'}], 'sample_audit':{'effective_n':3},'execution_provenance':{'software':'Python'},'artifact_refs':['run.json']}

class ContractRobustnessTests(unittest.TestCase):
    def test_malformed_objects_return_errors(self):
        import analysis_contracts as c
        for field in ('scoring','sample','model','inference','authorization'):
            s=candidate_spec();s[field]=['bad']
            self.assertTrue(c.validate_spec(s))
        s=candidate_spec();s['field_map'][0]['variable']=['bad']
        self.assertTrue(c.validate_spec(s))

    def test_incomplete_and_invalid_results_are_rejected(self):
        import analysis_contracts as c
        self.assertTrue(c.validate_result({}))
        run={'schema_version':1,'analysis_id':'a','revision':1,'run_id':'r','method_id':'descriptive','intent':'CANDIDATE_ANALYSIS','spec_hash':'a','input_hash':'b','scientific_spec':{'model':{}},'status':'COMPLETED','result_complete':True,'adoption_status':'CANDIDATE','results':[{'outcome_id':'score','term_id':'mean','contrast_id':'overall','estimate':1,'n':3,'sd':1,'se':0.5773502691896258,'df':2,'ci':[-1.484137711719546,3.484137711719546],'confidence_level':.95,'ci_alternative':'two-sided'}], 'sample_audit':{'effective_n':3},'execution_provenance':{'software':'Python'},'artifact_refs':['run.json']}
        run['scientific_spec']=c.scientific_spec(candidate_spec());run['spec_hash']=c.spec_hash(candidate_spec());run['input_hash']=candidate_spec()['data']['sha256']
        self.assertEqual(c.validate_result(run), [])
        run['results'][0]['estimate']=True
        self.assertTrue(c.validate_result(run))

class NumericResultCompletenessTests(unittest.TestCase):
    def test_identity_only_result_is_incomplete(self):
        import analysis_contracts as c
        run={'schema_version':1,'analysis_id':'a','revision':1,'run_id':'r','method_id':'descriptive','intent':'CANDIDATE_ANALYSIS','spec_hash':'a','input_hash':'b','scientific_spec':{'model':{}},'status':'COMPLETED','result_complete':True,'adoption_status':'CANDIDATE','results':[{'outcome_id':'score','term_id':'mean','contrast_id':'overall'}], 'sample_audit':{'effective_n':3},'execution_provenance':{'software':'Python'},'artifact_refs':['run.json']}
        self.assertTrue(c.validate_result(run))

class StrictContractTests(unittest.TestCase):
    def test_shapes_names_sources_and_paired_identity(self):
        import analysis_contracts as c
        for key,value in [('model',{'method':[]}),('sources',[{'source_id':'a','role':'UNKNOWN','software':'Python'}]),('design',{'design_tags':['survey'],'observation_unit':'p','research_question_type':'x','variables':[{'name':[],'role':'outcome'}]})]:
            s=candidate_spec();s[key]=value
            self.assertTrue(c.validate_spec(s))
        s=candidate_spec();s['sources']=[{'source_id':'a','role':'DATA_ONLY','software':'Python'}]*2
        self.assertTrue(c.validate_spec(s))
        s=candidate_spec();s['model']={'method':'paired_t','x':'score','y':'score'}
        self.assertTrue(c.validate_spec(s))
        self.assertIn('within-subjects',c.normalize_design_tags(['factorial-within-subject']))

    def test_result_hash_consistency(self):
        import analysis_contracts as c
        s=candidate_spec()
        run={'schema_version':1,'analysis_id':'a','revision':1,'run_id':'r','method_id':'descriptive','intent':'CANDIDATE_ANALYSIS','spec_hash':'a'*64,'input_hash':'b'*64,'scientific_spec':c.scientific_spec(s),'status':'COMPLETED','result_complete':True,'adoption_status':'CANDIDATE','results':[{'outcome_id':'score','term_id':'mean','contrast_id':'overall','estimate':1,'n':3,'sd':1,'se':0.5773502691896258,'df':2,'ci':[-1.484137711719546,3.484137711719546],'confidence_level':.95,'ci_alternative':'two-sided'}], 'sample_audit':{'effective_n':3},'execution_provenance':{'software':'Python'},'artifact_refs':['run.json']}
        self.assertTrue(c.validate_result(run))
        run['spec_hash']=c.spec_hash(s);run['input_hash']=s['data']['sha256']
        self.assertEqual(c.validate_result(run),[])

class MethodResultTests(unittest.TestCase):
    def test_inference_row_missing_p_and_bad_n_are_incomplete(self):
        import analysis_contracts as c
        s=candidate_spec();s['model']={'method':'welch_t','outcome':'score','group':'score','group_order':['A','B']}
        run={'schema_version':1,'analysis_id':'a','revision':1,'run_id':'r','method_id':'descriptive','intent':'CANDIDATE_ANALYSIS','spec_hash':c.spec_hash(s),'input_hash':s['data']['sha256'],'scientific_spec':c.scientific_spec(s),'status':'COMPLETED','result_complete':True,'adoption_status':'CANDIDATE','results':[{'outcome_id':'score','term_id':'mean','contrast_id':'overall','estimate':1,'n':True}], 'sample_audit':{'effective_n':3},'execution_provenance':{'software':'Python'},'artifact_refs':['run.json']}
        self.assertTrue(c.validate_result(run))
        run['results'][0]['n']=3
        self.assertTrue(c.validate_result(run))

class ShapeSafetyTests(unittest.TestCase):
    def test_wrong_design_and_model_shapes_are_errors(self):
        import analysis_contracts as c
        for change in ({'design_tags':'survey'}, {'variables':[{'name':'score','role':'totally_unknown'}]}):
            s=candidate_spec();s['design'].update(change)
            self.assertTrue(c.validate_spec(s))
        s=candidate_spec();s['model']['columns']='score'
        self.assertTrue(c.validate_spec(s))
        s=candidate_spec();s['scoring']['method']='guess'
        self.assertTrue(c.validate_spec(s))

class PearsonResultTests(unittest.TestCase):
    def test_pearson_fisher_interval_does_not_require_standard_error(self):
        import analysis_contracts as c
        s=candidate_spec();s['model']={'method':'pearson','x':'score','y':'other'};s['field_map'].append({'variable':'other','column':'other','confirmation_status':'DOCUMENTED','evidence_ref':'fixture'})
        run={'schema_version':1,'analysis_id':'a','revision':1,'run_id':'r','method_id':'descriptive','intent':'CANDIDATE_ANALYSIS','spec_hash':c.spec_hash(s),'input_hash':s['data']['sha256'],'scientific_spec':c.scientific_spec(s),'status':'COMPLETED','result_complete':True,'adoption_status':'CANDIDATE','results':[{'outcome_id':'score','term_id':'correlation','contrast_id':'score ~ other','estimate':.5,'n':10,'df':8,'statistic_name':'r','statistic':.5,'p':.14,'ci':[-.2,.8],'confidence_level':.95,'ci_alternative':'two-sided'}], 'sample_audit':{'effective_n':10},'execution_provenance':{'software':'Python'},'artifact_refs':['run.json']}
        run['method_id']='pearson'
        self.assertEqual(c.validate_result(run),[])
