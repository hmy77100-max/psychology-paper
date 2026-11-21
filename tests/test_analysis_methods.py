"""Direct-method contracts and actual numeric cases; no manuscript or model calls."""
import copy
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from test_analysis_contracts import candidate_spec

EXTENDED = ('factorial_anova','repeated_anova','mixed_anova',
            'linear_regression','binomial_regression','poisson_regression',
            'linear_mixed','binomial_mixed','poisson_mixed','mediation','moderation','cfa','sem')


def extended_spec(method='linear_regression'):
    s = candidate_spec()
    s['schema_version'] = 3
    names = ['id','y','x','z','group','time']
    s['design']['variables'] = [{'name': n, 'role': 'outcome' if n=='y' else 'predictor'} for n in names]
    s['field_map'] = [{'variable': n, 'column': n, 'confirmation_status': 'DOCUMENTED', 'evidence_ref': 'synthetic test'} for n in names]
    s['model'] = {'method': method, 'outcome':'y','predictors':['x'], 'covariates':[],
                  'factors':{}, 'interactions':[], 'intercept':True, 'center':{}, 'standard_error':'conventional'}
    s['analysis_context'] = {'inferential_status':'EXPLORATORY', 'analysis_role':'CANDIDATE',
                             'basis_ref':'observed retained fields','search_set_id':'test-search',
                             'parent_analysis_id':None, 'discovered_after_results':True}
    return s


class ExtendedContractTests(unittest.TestCase):
    def test_backend_inventory_cannot_certify_missing_model_terms(self):
        import analysis_contracts as c
        run={'schema_version':2,'scientific_spec':c.scientific_spec(extended_spec()),
             'results':[{'outcome_id':'y','term_id':'bogus','contrast_id':'coefficient','kind':'coefficient','estimate':0,'n':10}],
             'sample_audit':{'effective_n':10},'diagnostics':{'converged':True},
             'model_summary':{'expected_result_ids':[['y','bogus','coefficient']]},
             'execution_provenance':{'software':'R','version':'4.6.2'}}
        errors=[];c.validate_extended_result(run,lambda *x:errors.append(x))
        self.assertTrue(errors)

    def test_malformed_extended_containers_return_field_errors(self):
        import analysis_contracts as c
        for key,value in [('factors',None),('factors',[]),('center',[]),('interactions',[None])]:
            s=extended_spec();s['model']['center']={'x':0};s['model'][key]=value
            self.assertTrue(c.validate_spec(s))
    def test_capability_query_is_lazy_and_scoped(self):
        import analysis_contracts as c
        for name in EXTENDED:
            self.assertIn(name, c.METHODS)
            info=c.describe_method(name)
            self.assertEqual(info['backend'], 'R')
            self.assertFalse(info['execution_ready'])
        p=subprocess.run([sys.executable,'-S',str(ROOT/'scripts/analysis_runner.py'),'methods','--method','sem'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertLess(len(p.stdout),8000)

    def test_v3_linear_contract_and_unknown_option(self):
        import analysis_contracts as c
        s=extended_spec()
        self.assertEqual(c.validate_spec(s),[])
        s['model']['stepwise']=True
        self.assertTrue(c.validate_spec(s))

    def test_exploration_does_not_become_prespecified(self):
        import analysis_contracts as c
        s=extended_spec()
        self.assertEqual(c.validate_spec(s),[])
        s['analysis_context']['inferential_status']='PRESPECIFIED'
        self.assertTrue(c.validate_spec(s))
        s['analysis_context'].update(discovered_after_results=False,analysis_role='REPRODUCTION',basis_ref='original dated plan')
        self.assertEqual(c.validate_spec(s),[])
        del s['analysis_context']['basis_ref']
        self.assertTrue(c.validate_spec(s))

    def test_legacy_context_is_unknown_not_newly_prespecified(self):
        import analysis_contracts as c
        self.assertEqual(c.analysis_context(candidate_spec())['inferential_status'],'UNDETERMINED')

    def test_sem_and_random_structure_are_not_unvalidated_strings(self):
        import analysis_contracts as c
        s=extended_spec('linear_mixed')
        s['model'].update(random=[{'group':'id','slopes':['x'],'correlated':True}],estimation='REML')
        self.assertEqual(c.validate_spec(s),[])
        s['model']['random'][0]['group']='system("touch bad")'
        self.assertTrue(c.validate_spec(s))
        s=extended_spec('cfa')
        s['model']={'method':'cfa','latent':{'f':['y','x','z']},'paths':[], 'residual_covariances':[],
                    'ordered':{},'estimator':'ML','std_lv':True,'fixed_x':True}
        self.assertEqual(c.validate_spec(s),[])
        s['model']['syntax']='system("bad")'
        self.assertTrue(c.validate_spec(s))

    def test_comparison_family_is_explicit(self):
        import analysis_contracts as c
        s=extended_spec(); s['model'].update(predictors=['group'],factors={'group':['A','B']})
        s['inference']['comparisons']=[{'id':'group-A-B','factor':'group','levels':['A','B'],'by':{},'family_id':'primary'}]
        self.assertTrue(c.validate_spec(s))
        s['inference']['adjustments']={'primary':'holm'}
        self.assertEqual(c.validate_spec(s),[])

    def test_nested_test_requires_ml_and_submodel(self):
        import analysis_contracts as c
        s=extended_spec('linear_mixed')
        s['model'].update(random=[{'group':'id','slopes':[],'correlated':True}],estimation='ML')
        s['inference']['nested_test']={'predictors':[],'interactions':[]}
        self.assertEqual(c.validate_spec(s),[])
        s['model']['estimation']='REML';self.assertTrue(c.validate_spec(s))
        s['model']['estimation']='ML';s['inference']['nested_test']['predictors']=['z'];self.assertTrue(c.validate_spec(s))


class AttemptRecordTests(unittest.TestCase):
    def test_corrupt_neighbour_is_reported_without_losing_summary(self):
        import analysis_runner as r
        import uuid
        for malformed in ([],{'schema_version':2,'analysis_context':None},
                          {'schema_version':2,'analysis_context':{'search_set_id':'test-search'}}):
            p=self.root/'output'/str(uuid.uuid4());p.mkdir(parents=True)
            (p/'analysis-run.json').write_text(json.dumps(malformed),encoding='utf-8')
        info=r.summarize_attempts(self.root/'output',search_set_id='test-search')
        self.assertEqual(info['attempted'],0)
        self.assertEqual(info['unreadable_records'],3)

    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='分析扩展-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.data=self.root/'data.csv'
        self.data.write_text('score\n1\n2\n3\n4\n',encoding='utf-8')
        self.spec=candidate_spec(); self.spec['schema_version']=3
        self.spec['data'].update(path=str(self.data),sha256=hashlib.sha256(self.data.read_bytes()).hexdigest())
        self.spec['authorization']['output_dir']=str(self.root/'output')
        self.spec['analysis_context']=extended_spec()['analysis_context']

    @unittest.skipUnless(importlib.util.find_spec('scipy'),'optional Python numeric environment')
    def test_completed_and_failed_attempts_retained_without_adoption(self):
        import analysis_runner as r
        a=r.run_analysis(self.spec)
        self.assertEqual(a['status'],'COMPLETED',a)
        saved=json.loads(Path(a['artifacts'][0]['path']).read_text(encoding='utf-8'))
        self.assertEqual(saved['schema_version'],2)
        self.assertEqual(saved['analysis_context']['inferential_status'],'EXPLORATORY')
        bad=copy.deepcopy(self.spec);bad['sample']['filters']=[{'column':'score','op':'eq','value':'99'}]
        b=r.run_analysis(bad)
        self.assertFalse(b['result_complete'])
        self.assertTrue(b['artifacts'],b)
        summary=r.summarize_attempts(self.root/'output',search_set_id='test-search')
        self.assertEqual(summary['attempted'],2)
        self.assertEqual(summary['completed'],1)
        self.assertEqual(summary['failed'],1)
        self.assertEqual(summary['distinct_specifications'],2)
        self.assertIsNone(summary['adopted'])

    def test_denied_scope_never_creates_attempt(self):
        import analysis_runner as r
        self.spec['authorization']['compute']=False
        out=r.run_analysis(self.spec)
        self.assertFalse(out['result_complete'])
        self.assertFalse((self.root/'output').exists())


@unittest.skipUnless(os.environ.get('PSYCHOLOGY_PAPER_RSCRIPT') and importlib.util.find_spec('numpy'),
                     'optional R numeric environment must be configured explicitly')
class RNumericTests(unittest.TestCase):
    """Synthetic numerical checks through the public runner, not business acceptance."""
    def setUp(self):
        import numpy as np
        self.np=np
        self.rng=np.random.default_rng(1042)
        self.tmp=tempfile.TemporaryDirectory(prefix='R数值-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.counter=0

    def run_model(self,data,model,inference=None,missing='error',ok=True,filters=None):
        import analysis_runner as runner
        self.counter+=1
        data={k:list(v) for k,v in data.items()}
        path=self.root/f'data{self.counter}.csv'
        with path.open('w',encoding='utf-8',newline='') as f:
            writer=csv.writer(f);writer.writerow(data);writer.writerows(zip(*data.values()))
        spec=extended_spec(model['method']);spec['model']=model
        names=list(data)
        spec['design']['variables']=[{'name':n,'role':'outcome' if n==model.get('outcome') else 'predictor'} for n in names]
        spec['field_map']=[{'variable':n,'column':n,'confirmation_status':'DOCUMENTED','evidence_ref':'seeded synthetic numerical fixture'} for n in names]
        spec['data'].update(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        spec['authorization']['output_dir']=str(self.root/'results')
        spec['sample'].update(missing=missing,filters=filters or [])
        if inference:spec['inference'].update(inference)
        original=path.read_bytes();result=runner.run_analysis(spec)
        self.assertEqual(path.read_bytes(),original)
        if not ok:
            self.assertFalse(result['result_complete'],result)
            return result
        self.assertEqual(result['status'],'COMPLETED',result)
        run=json.loads(Path(result['artifacts'][0]['path']).read_text(encoding='utf-8'))
        self.assertEqual(run['analysis_context']['inferential_status'],'EXPLORATORY')
        self.assertEqual(run['execution_provenance']['software'],'R')
        return run

    def reg(self,method='linear_regression',**kw):
        m={'method':method,'outcome':'y','predictors':['x'],'covariates':[],
           'factors':{},'interactions':[],'intercept':True,'center':{},'standard_error':'conventional'}
        m.update(kw);return m

    def terms(self,run,kind='coefficient'):
        return {r['term_id']:r for r in run['results'] if r['kind']==kind}

    def test_ols_and_hc3_against_matrix_calculation(self):
        np=self.np;x=np.arange(12,dtype=float);y=2+.7*x+self.rng.normal(size=12)*(1+x/5)
        X=np.column_stack([np.ones(12),x]);inv=np.linalg.inv(X.T@X);b=inv@X.T@y;e=y-X@b
        for se_type in ('conventional','HC3'):
            run=self.run_model({'x':x,'y':y},self.reg(standard_error=se_type));t=self.terms(run)
            cov=inv*(e@e/10) if se_type=='conventional' else inv@(X.T@np.diag((e/(1-np.sum((X@inv)*X,axis=1)))**2)@X)@inv
            for i,name in enumerate(('(Intercept)','x')):
                self.assertAlmostEqual(t[name]['estimate'],b[i],places=10)
                self.assertAlmostEqual(t[name]['se'],np.sqrt(cov[i,i]),places=10)
        import analysis_contracts as c
        changed=copy.deepcopy(run);changed['scientific_spec']['sample']['n']=999;changed['spec_hash']=c.spec_hash(changed['scientific_spec'])
        self.assertTrue(c.validate_result(changed))
        changed=copy.deepcopy(run);changed['diagnostics']=[]
        self.assertTrue(c.validate_result(changed))

    def test_logistic_and_poisson_against_independent_likelihood(self):
        from scipy.optimize import minimize
        from scipy.special import expit
        np=self.np;x=np.linspace(-1.5,1.5,120);X=np.column_stack([np.ones(len(x)),x])
        for family in ('binomial','poisson'):
            y=self.rng.binomial(1,expit(-.2+.6*x)) if family=='binomial' else self.rng.poisson(np.exp(.3+.4*x))
            def objective(b):
                eta=X@b
                return np.sum(np.logaddexp(0,eta)-y*eta) if family=='binomial' else np.sum(np.exp(eta)-y*eta)
            def grad(b):return X.T@((expit(X@b) if family=='binomial' else np.exp(X@b))-y)
            ref=minimize(objective,[0.,0.],jac=grad,method='BFGS',options={'gtol':1e-9})
            self.assertLess(np.max(np.abs(grad(ref.x))),1e-5)
            run=self.run_model({'x':x,'y':y},self.reg(family+'_regression'));t=self.terms(run)
            for i,name in enumerate(('(Intercept)','x')):self.assertAlmostEqual(t[name]['estimate'],ref.x[i],places=6)

    def test_trials_and_log_offset(self):
        np=self.np;x=np.repeat([0.,1.],8);trials=np.repeat(10,16);y=np.tile([2,3,4,5,1,4,3,2],2)+x
        run=self.run_model({'x':x,'y':y,'trials':trials},self.reg('binomial_regression',trials='trials'))
        t=self.terms(run);p0=y[:8].sum()/80;p1=y[8:].sum()/80
        self.assertAlmostEqual(t['x']['estimate'],np.log(p1/(1-p1))-np.log(p0/(1-p0)),places=6)
        exposure=np.tile([1.,2.,3.,4.],4);offset=np.log(exposure);counts=np.tile([1,3,2,6],4)+(x*2)
        run=self.run_model({'x':x,'y':counts,'offset':offset},self.reg('poisson_regression',offset='offset'))
        ref=np.log(counts[8:].sum()/exposure[8:].sum())-np.log(counts[:8].sum()/exposure[:8].sum())
        self.assertAlmostEqual(self.terms(run)['x']['estimate'],ref,places=7)

    def test_factorial_anova_and_holm_family(self):
        fixture=json.loads((ROOT/'tests/fixtures/statistics-extended/anova.json').read_text())
        model={'method':'factorial_anova','outcome':'y','between':['g'],'within':[],
               'subject_id':None,'ss_type':'III','correction':'none','aggregation':'none','factors':{'g':['A','B']}}
        comparisons=[{'id':f'c{i}','factor':'g','levels':['A','B'],'by':{},'family_id':'four'} for i in range(4)]
        run=self.run_model({'g':fixture['group'],'y':fixture['outcome']},model,{'comparisons':comparisons,'adjustments':{'four':'holm'}})
        t=self.terms(run,'omnibus')['g'];self.assertAlmostEqual(t['statistic'],4.5,places=9)
        self.assertAlmostEqual(t['partial_eta_squared'],9/13,places=9)
        for r in run['results']:
            if r['kind']=='contrast':self.assertAlmostEqual(r['p_adjusted'],min(1,4*r['p']),places=10)

    def test_repeated_and_mixed_anova(self):
        np=self.np;n=18;ids=np.repeat(np.arange(n),3);time=np.tile(['a','b','c'],n)
        groups=np.repeat(['A']*9+['B']*9,3);y=np.repeat(self.rng.normal(size=n),3)+np.tile([0,.5,1.2],n)+self.rng.normal(size=n*3)
        model={'method':'repeated_anova','outcome':'y','between':[],'within':['time'],
               'subject_id':'id','ss_type':'III','correction':'none','aggregation':'none','factors':{'time':['a','b','c']}}
        run=self.run_model({'y':y,'time':time,'id':ids},model)
        mat=y.reshape(n,3);ss_time=n*np.sum((mat.mean(axis=0)-mat.mean())**2)
        residual=mat-mat.mean(axis=0)-mat.mean(axis=1)[:,None]+mat.mean();ss_error=np.sum(residual**2)
        self.assertAlmostEqual(self.terms(run,'omnibus')['time']['statistic'],(ss_time/2)/(ss_error/(2*(n-1))),places=8)
        model.update(method='mixed_anova',between=['g'],correction='GG');model['factors']['g']=['A','B']
        run=self.run_model({'y':y,'time':time,'id':ids,'g':groups},model)
        self.assertEqual(len(self.terms(run,'omnibus')),3)
        self.assertEqual(run['sample_audit']['n_subjects'],n)
        self.assertLessEqual(self.terms(run,'omnibus')['time']['df_num'],2)

    def test_mixed_families_and_random_slope(self):
        from scipy.special import expit
        np=self.np;n=24;repeats=12;ids=np.repeat(np.arange(n),repeats);x=np.tile(np.linspace(-1,1,repeats),n)
        u=np.repeat(self.rng.normal(0,.8,n),repeats);sl=np.repeat(self.rng.normal(0,.3,n),repeats)
        for family in ('linear','binomial','poisson'):
            eta=.3+(.6+sl)*x+u
            y=eta+self.rng.normal(0,.5,n*repeats) if family=='linear' else self.rng.binomial(1,expit(eta)) if family=='binomial' else self.rng.poisson(np.exp(eta))
            model=self.reg(family+'_mixed',random=[{'group':'id','slopes':['x'] if family=='linear' else [],'correlated':True}],estimation='ML')
            run=self.run_model({'id':ids,'x':x,'y':y},model)
            self.assertEqual(run['sample_audit']['n_groups']['id'],n)
            self.assertTrue(run['diagnostics']['converged']);self.assertIn('singular',run['diagnostics'])
            self.assertTrue(self.terms(run,'variance'))
            if family=='linear':
                # Balanced, identical within-cluster design gives the mean of cluster OLS slopes.
                slopes=[np.linalg.lstsq(np.column_stack([np.ones(repeats),x[:repeats]]),a,rcond=None)[0][1] for a in y.reshape(n,repeats)]
                self.assertAlmostEqual(self.terms(run)['x']['estimate'],np.mean(slopes),places=6)

    def test_moderation_conditional_slope_and_center(self):
        np=self.np;x=self.rng.normal(size=80);z=self.rng.normal(size=80);y=1+.4*x+.3*z+.8*x*z+self.rng.normal(size=80)
        model=self.reg('moderation',family='linear',predictors=['x','z'],interactions=[['x','z']],center={'z':1.2},standard_error='HC3')
        comparison={'id':'slope-z0','slope':'x','at':{'z':0},'family_id':'slope'}
        run=self.run_model({'y':y,'x':x,'z':z},model,{'comparisons':[comparison],'adjustments':{'slope':'none'}})
        X=np.column_stack([np.ones(80),x,z,x*z]);b=np.linalg.lstsq(X,y,rcond=None)[0]
        slope=next(r for r in run['results'] if r['contrast_id']=='slope-z0')
        self.assertAlmostEqual(slope['estimate'],b[1],places=7)

    def test_parallel_mediation_point_estimates_and_bootstrap_repeatability(self):
        np=self.np;n=80;x=self.rng.normal(size=n);m1=.5*x+self.rng.normal(size=n);m2=.7*x+self.rng.normal(size=n)
        y=.2*x+.6*m1-.3*m2+self.rng.normal(size=n)
        model={'method':'mediation','exposure':'x','outcome':'y','mediators':['m1','m2'],'covariates':[], 'mediator_covariances':True,'estimator':'ML'}
        inf={'bootstrap':{'replicates':40,'seed':173,'unit':'observation','ci_type':'percentile'}}
        data={'x':x,'y':y,'m1':m1,'m2':m2}
        first=self.run_model(data,model,inf);second=self.run_model(data,model,inf)
        t=self.terms(first,'indirect');b=np.linalg.lstsq(np.column_stack([np.ones(n),x,m1,m2]),y,rcond=None)[0]
        for i,m in enumerate((m1,m2),1):
            a=np.linalg.lstsq(np.column_stack([np.ones(n),x]),m,rcond=None)[0][1]
            self.assertAlmostEqual(t['indirect'+str(i)]['estimate'],a*b[i+1],places=5)
            self.assertEqual(t['indirect'+str(i)]['ci'],self.terms(second,'indirect')['indirect'+str(i)]['ci'])
        self.assertEqual(first['diagnostics']['bootstrap_failed'],0)

    def test_cfa_against_three_indicator_covariance_identity(self):
        np=self.np;n=400;f=self.rng.normal(size=n);items=np.column_stack([.8*f+self.rng.normal(size=n),1.1*f+self.rng.normal(size=n),.6*f+self.rng.normal(size=n)])
        model={'method':'cfa','latent':{'F':['i1','i2','i3']},'paths':[],'residual_covariances':[],'ordered':{},'estimator':'ML','std_lv':True,'fixed_x':True}
        run=self.run_model({f'i{i+1}':items[:,i] for i in range(3)},model)
        S=np.cov(items,rowvar=False,bias=True);l1=np.sqrt(S[0,1]*S[0,2]/S[1,2]);ref=[l1,S[0,1]/l1,S[0,2]/l1]
        t=self.terms(run,'loading')
        for i in range(3):self.assertAlmostEqual(t[f'F=~i{i+1}']['estimate'],ref[i],places=5)
        self.assertEqual(run['model_summary']['fit_measures']['df'],0)
        self.assertIn('cfi',run['model_summary']['unavailable_fit_measures'])
        from compare_analysis_results import compare_results
        self.assertEqual(compare_results(run,run,tolerance=1e-6)['status'],'ALIGNED')
        reordered=copy.deepcopy(run);reordered['results'].reverse();reordered['model_summary']['expected_result_ids'].reverse()
        self.assertEqual(compare_results(run,reordered,tolerance=1e-6)['status'],'ALIGNED')
        changed=copy.deepcopy(run);changed['model_summary']['fit_measures']['chisq']+=1
        self.assertEqual(compare_results(run,changed,tolerance=1e-6)['status'],'NUMERIC_DISCREPANCY')

    def test_sem_mlr_fiml_and_ordered_cfa(self):
        np=self.np;n=240;f=self.rng.normal(size=n);data={f'i{i}':(.6+i*.1)*f+self.rng.normal(size=n) for i in range(1,5)}
        data['y']=.7*f+self.rng.normal(size=n)
        model={'method':'sem','latent':{'F':['i1','i2','i3','i4']},'paths':[{'outcome':'y','predictors':['F']}],
               'residual_covariances':[],'ordered':{},'estimator':'MLR','std_lv':True,'fixed_x':True}
        data['i1']=list(data['i1']);data['i1'][0]=''
        run=self.run_model(data,model,missing='fiml');self.assertIn('y~F',self.terms(run))
        self.assertEqual(run['sample_audit']['effective_n'],n)
        ordered={k:np.digitize(np.asarray(v,dtype=float) if k!='i1' else np.array([0. if a=='' else a for a in v]),[-.6,.6])+1 for k,v in data.items() if k!='y'}
        model.update(method='cfa',paths=[],estimator='WLSMV',ordered={k:['1','2','3'] for k in ordered})
        run=self.run_model(ordered,model);self.assertEqual(len(self.terms(run,'loading')),4)

    def test_invalid_data_failures_are_retained(self):
        # Rank deficiency and separation are failures, not usable coefficient tables.
        a=self.run_model({'x':[0,1,2,3,4],'z':[0,2,4,6,8],'y':[1,3,2,5,6]},self.reg(predictors=['x','z']),ok=False)
        self.assertIn('RANK_DEFICIENT',str(a));self.assertTrue(a['artifacts'])
        a=self.run_model({'x':[-3,-2,-1,1,2,3],'y':[0,0,0,1,1,1]},self.reg('binomial_regression'),ok=False)
        self.assertIn('SEPARATION',str(a));self.assertTrue(a['artifacts'])
        a=self.run_model({'x':[0,1,2,3],'y':[1,'',3,5]},self.reg(),ok=False)
        self.assertIn('MISSING_DATA',str(a))

    def test_unbalanced_two_factor_ii_iii_against_projection(self):
        np=self.np;a=np.repeat([-1.,-1.,1.,1.],[5,8,11,7]);b=np.repeat([-1.,1.,-1.,1.],[5,8,11,7])
        y=2+a+.7*b+.8*a*b+self.rng.normal(size=len(a));X=np.column_stack([np.ones(len(a)),a,b,a*b])
        coef=np.linalg.lstsq(X,y,rcond=None)[0];mse=np.sum((y-X@coef)**2)/(len(a)-4);inv=np.linalg.inv(X.T@X)
        def sse(design):return np.sum((y-design@np.linalg.lstsq(design,y,rcond=None)[0])**2)
        model={'method':'factorial_anova','outcome':'y','between':['a','b'],'within':[],'subject_id':None,
               'ss_type':'III','correction':'none','aggregation':'none','factors':{'a':[-1,1],'b':[-1,1]}}
        refs={'III':coef[1]**2/(mse*inv[1,1]),'II':(sse(X[:,[0,2]])-sse(X[:,[0,1,2]]))/mse}
        for typ in ('II','III'):
            model['ss_type']=typ;run=self.run_model({'a':a.astype(int),'b':b.astype(int),'y':y},model)
            self.assertAlmostEqual(self.terms(run,'omnibus')['a']['statistic'],refs[typ],places=7)
        self.assertGreater(abs(refs['II']-refs['III']),.01)

    def test_hf_correction_and_repeated_design_failures(self):
        np=self.np;n=16;mat=self.rng.normal(size=(n,3))*[1,2,3]+[0,1,2];y=mat.ravel()
        data={'id':np.repeat(np.arange(n),3),'time':np.tile(['a','b','c'],n),'y':y}
        model={'method':'repeated_anova','outcome':'y','between':[],'within':['time'],'subject_id':'id',
               'ss_type':'III','correction':'HF','aggregation':'none','factors':{'time':['a','b','c']}}
        C=np.eye(3)-np.ones((3,3))/3;S=C@np.cov(mat,rowvar=False)@C;eps=np.trace(S)**2/(2*np.trace(S@S))
        hf=min(1,(n*2*eps-2)/(2*(n-1-2*eps)))
        run=self.run_model(data,model);self.assertAlmostEqual(self.terms(run,'omnibus')['time']['df_num'],2*hf,places=7)
        dup={k:list(v)+[list(v)[0]] for k,v in data.items()}
        self.assertIn('DUPLICATE_CELL',str(self.run_model(dup,model,ok=False)))
        cut={k:list(v)[1:] for k,v in data.items()}
        self.assertIn('INCOMPLETE_DESIGN',str(self.run_model(cut,model,ok=False)))
        model['aggregation']='mean';run=self.run_model(dup,model)
        self.assertEqual(run['sample_audit']['model_rows'],n*3)

    def test_crossed_mixed_and_nested_likelihood_ratio(self):
        from scipy.stats import chi2
        np=self.np;ns=16;ni=10;subject=np.repeat(np.arange(ns),ni);item=np.tile(np.arange(ni),ns)
        x=self.rng.normal(size=ns*ni);y=.5*x+np.repeat(self.rng.normal(size=ns),ni)+np.tile(self.rng.normal(0,.5,ni),ns)+self.rng.normal(0,.7,ns*ni)
        model=self.reg('linear_mixed',random=[{'group':'id','slopes':[],'correlated':True},{'group':'item','slopes':[],'correlated':True}],estimation='ML')
        run=self.run_model({'id':subject,'item':item,'x':x,'y':y},model,{'nested_test':{'predictors':[],'interactions':[]}})
        details=run['model_summary']['nested_test'];lrt=next(r for r in run['results'] if r['contrast_id']=='likelihood_ratio')
        statistic=2*(details['full_log_likelihood']-details['reduced_log_likelihood'])
        self.assertAlmostEqual(lrt['statistic'],statistic,places=8)
        self.assertAlmostEqual(lrt['p'],chi2.sf(statistic,1),places=9)
        self.assertEqual(details['shared_n'],ns*ni)
        self.assertEqual(run['sample_audit']['n_groups'],{'id':ns,'item':ni})

    def test_reference_levels_no_intercept_and_safe_labels(self):
        data={'g':['a']*5+['b']*5,'y':[1,3,2,5,3,4,6,7,5,8]}
        model=self.reg(predictors=['g'],factors={'g':['a','b']},intercept=False)
        run=self.run_model(data,model)
        self.assertAlmostEqual(self.terms(run)['ga']['estimate'],2.8,places=8)
        name='v2;system("not executable")'
        run=self.run_model({name:[0,1,2,3],'y':[2,2,4,8]},self.reg(predictors=[name]))
        self.assertAlmostEqual(self.terms(run)[name]['estimate'],2,places=8)

    def test_numeric_factor_labels_are_not_variable_ids(self):
        model=self.reg(predictors=['g'],factors={'g':[0,1]})
        run=self.run_model({'g':[0]*4+[1]*4,'y':[1,2,4,3,6,5,9,8]},model)
        self.assertAlmostEqual(self.terms(run)['g1']['estimate'],4.5,places=8)

    def test_sem_unidentified_or_degenerate_does_not_complete(self):
        model={'method':'cfa','latent':{'F':['i1','i2']},'paths':[],'residual_covariances':[],
               'ordered':{},'estimator':'ML','std_lv':True,'fixed_x':True}
        x=self.rng.normal(size=40);y=x+self.rng.normal(size=40)
        result=self.run_model({'i1':x,'i2':y},model,ok=False)
        self.assertTrue(result['artifacts'])

    def test_declared_missing_factor_levels_are_not_dropped(self):
        model={'method':'factorial_anova','outcome':'y','between':['g'],'within':[],'subject_id':None,
               'ss_type':'III','correction':'none','aggregation':'none','factors':{'g':['A','B','C']}}
        self.run_model({'g':['A']*4+['B']*4,'y':[1,2,3,4,5,6,7,8]},model,ok=False)


if __name__=='__main__': unittest.main()
