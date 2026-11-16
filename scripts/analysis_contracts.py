"""Pure scientific specification and result contracts; no file access."""
from __future__ import annotations
import hashlib
import json
import math

INTENTS = ('METHOD_REVIEW', 'CANDIDATE_ANALYSIS', 'FORMAL_ANALYSIS', 'VERIFICATION')
METHODS = ('descriptive', 'scale_score', 'welch_t', 'student_t', 'paired_t', 'pearson')
MODEL_FIELDS = {
    'descriptive': ('columns',), 'scale_score': ('columns',),
    'welch_t': ('outcome', 'group', 'group_order'),
    'student_t': ('outcome', 'group', 'group_order'),
    'paired_t': ('x', 'y', 'subject_id'), 'pearson': ('x', 'y'),
}
VARIABLE_ROLES = ('outcome','independent','dependent','predictor','group','factor','covariate',
                  'subject','subject_id','item','mediator','moderator','identifier','time','within','between')

def describe_method(method):
    """Small public field contract, sharing the validator's actual field lists."""
    if method not in METHODS:
        raise ValueError('method unsupported by controlled runner')
    info = {
        'status': 'METHOD_CONTRACT', 'schema_version': 2, 'method': method,
        'execution_ready': False, 'required_model_fields': list(MODEL_FIELDS[method]),
        'variable_roles': list(VARIABLE_ROLES),
        'field_mapping': 'Model fields use variable names; map each to its data column with evidence.',
        'optional_model_fields': {'covariates': 'Only [] supported; no covariate adjustment.'},
        'inference': {'alpha': '0 < value < 1', 'confidence_level': '0 < value < 1',
                      'alternative': ['two-sided', 'less', 'greater'], 'intervals': 'two-sided'},
        'sample': {'missing': ['complete_case', 'error'], 'filters': 'Explicit list; eq/in/not_in only.'},
        'scope': 'Field information only; not method recommendation, runtime readiness or authorization.',
    }
    if method in ('paired_t', 'pearson'):
        info['contrast'] = 'x - y' if method == 'paired_t' else 'Pearson association of x and y'
    if method == 'paired_t':
        info['structure'] = 'One paired row per unique subject_id; x/y mapped to numeric columns.'
    if method in ('welch_t', 'student_t'):
        info['group_order'] = 'Exactly two distinct observed labels; first minus second.'
    if method == 'scale_score':
        info['scoring'] = {'method': 'scale', 'items': 'Same ordered list as model.columns',
                           'reverse_items': 'Explicit subset of items', 'minimum': 'Scale lower bound',
                           'maximum': 'Scale upper bound', 'aggregation': ['mean','sum'],
                           'min_answered': 'Explicit integer from 1 through item count'}
    else:
        info['scoring'] = {'accepted_methods': ['none', 'scale'],
                           'execution': 'Uses mapped input values without re-scoring; scale scoring is performed only by scale_score.'}
    return info

def normalize_design_tags(tags):
    result = []
    for tag in tags if isinstance(tags, list) else []:
        if not isinstance(tag, str):
            continue
        for value in [tag] + ([x for x in ('within-subjects', 'between-subjects', 'factorial') if x.rstrip('s') in tag]):
            if value not in result:
                result.append(value)
    return result

def scientific_spec(spec):
    data = spec.get('data', {})
    return {'design': spec.get('design'),
            'data': {k: data[k] for k in ('sha256', 'format', 'read_options') if k in data},
            'field_map': [{k: row[k] for k in ('variable', 'column') if k in row} for row in spec.get('field_map', []) if isinstance(row, dict)],
            **{k: spec[k] for k in ('scoring', 'sample', 'model', 'inference') if k in spec}}

def spec_hash(spec):
    return hashlib.sha256(json.dumps(scientific_spec(spec), sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()

def _text(v):
    return isinstance(v, str) and bool(v.strip())

def _number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)

def validate_spec(spec, for_execution=False, *, _scientific_only=False):
    errors=[]
    def need(ok, field, message='required or invalid', code='INVALID_SPEC'):
        if not ok: errors.append({'code':code, 'field':field, 'message':message})
    if not isinstance(spec, dict):
        return [{'code':'INVALID_SPEC','field':'spec','message':'must be an object'}]
    intent=spec.get('intent')
    if not _scientific_only:
        need(spec.get('schema_version') == 2, 'schema_version')
        need(_text(spec.get('analysis_id')), 'analysis_id')
        need(type(spec.get('revision')) is int and spec['revision'] > 0, 'revision')
        need(intent in INTENTS, 'intent')
    if intent == 'METHOD_REVIEW' and not _scientific_only: return errors
    design=spec.get('design', {})
    if not isinstance(design, dict): design={}
    for key in ('design_tags','observation_unit','research_question_type','variables'):
        need(bool(design.get(key)), 'design.'+key)
    need(isinstance(design.get('design_tags'),list) and all(_text(t) for t in design.get('design_tags',[])), 'design.design_tags')
    variables=design.get('variables', [])
    need(isinstance(variables,list) and all(isinstance(v,dict) and _text(v.get('name')) and _text(v.get('role')) for v in variables), 'design.variables')
    for variable in variables if isinstance(variables,list) else []:
        if isinstance(variable,dict): need(variable.get('role') in VARIABLE_ROLES, 'design.variables.role')
    data=spec.get('data', {}); data=data if isinstance(data,dict) else {}
    if not _scientific_only: need(_text(data.get('path')), 'data.path')
    digest=data.get('sha256',''); need(isinstance(digest,str) and len(digest)==64 and all(c in '0123456789abcdefABCDEF' for c in digest), 'data.sha256')
    need(data.get('format') in ('csv','xlsx'), 'data.format')
    opts=data.get('read_options'); need(isinstance(opts,dict), 'data.read_options')
    if isinstance(opts,dict):
        allowed={'encoding','delimiter','missing_values'} if data.get('format')=='csv' else {'sheet_name','formula_policy','missing_values'}
        need(not(set(opts)-allowed),'data.read_options','unsupported reading option')
        if data.get('format')=='csv':
            need(_text(opts.get('encoding')), 'data.read_options.encoding')
            need(isinstance(opts.get('delimiter'),str) and len(opts['delimiter'])==1, 'data.read_options.delimiter')
        elif data.get('format')=='xlsx': need(_text(opts.get('sheet_name')) or type(opts.get('sheet_name')) is int, 'data.read_options.sheet_name')
    fields=spec.get('field_map',[]); need(isinstance(fields,list) and bool(fields), 'field_map')
    fields=fields if isinstance(fields,list) else []
    names=[]
    for i,row in enumerate(fields):
        if not isinstance(row,dict): need(False,f'field_map.{i}'); continue
        names.append(row.get('variable') if isinstance(row.get('variable'),str) else None)
        for key in ('variable','column'): need(_text(row.get(key)),f'field_map.{i}.{key}')
        if not _scientific_only:
            need(_text(row.get('evidence_ref')),f'field_map.{i}.evidence_ref')
            need(row.get('confirmation_status') in ('USER_CONFIRMED','DOCUMENTED','CANDIDATE_INFERRED'),f'field_map.{i}.confirmation_status')
    need(len(names)==len(set(names)), 'field_map', 'duplicate variable mapping')
    for v in variables if isinstance(variables,list) else []:
        if isinstance(v,dict): need(v.get('name') in names, 'field_map', 'each design variable needs an evidenced column')
    for key in ('scoring','sample','model','inference') + (() if _scientific_only else ('authorization',)):
        need(isinstance(spec.get(key),dict),key)
    scoring, sample, model, inference, auth = [spec[k] if isinstance(spec.get(k),dict) else {} for k in ('scoring','sample','model','inference','authorization')]
    need(scoring.get('method') in ('none','scale'), 'scoring.method')
    need(sample.get('missing') in ('complete_case','error'), 'sample.missing')
    need(isinstance(sample.get('filters'),list), 'sample.filters')
    for rule in sample.get('filters',[]) if isinstance(sample.get('filters'),list) else []:
        if not isinstance(rule,dict): need(False,'sample.filters','filter object required'); continue
        op=rule.get('op')
        expected={'op','value' if op=='eq' else 'values','variable' if 'variable' in rule else 'column'}
        need(set(rule)==expected and op in ('eq','in','not_in'),'sample.filters','unsupported or conflicting filter fields')
        name=rule.get('variable',rule.get('column'))
        need(_text(name),'sample.filters','filter variable or column required')
        if op in ('in','not_in'): need(isinstance(rule.get('values'),list),'sample.filters.values')
        values=[rule.get('value')] if op=='eq' else rule.get('values',[])
        if isinstance(values,list): need(all(isinstance(v,(str,int,float)) and not isinstance(v,bool) and (not isinstance(v,(int,float)) or math.isfinite(v)) for v in values),'sample.filters','scalar filter values required')
    method=model.get('method'); method=method if isinstance(method,str) else ''; need(method in METHODS, 'model.method', 'method unsupported by controlled runner')
    required=MODEL_FIELDS.get(method,())
    need(not(set(model)-set(required)-{'method','covariates'}),'model','unsupported model option')
    if 'covariates' in model: need(model['covariates']==[],'model.covariates','these methods do not adjust covariates')
    need(not(set(sample)-{'missing','filters','n'}),'sample','unsupported sampling option')
    if 'n' in sample: need(type(sample['n']) is int and sample['n']>0,'sample.n','positive integer required')
    need(not(set(inference)-{'alpha','confidence_level','alternative'}),'inference','unsupported inference option')
    allowed_scoring={'method'} if scoring.get('method')=='none' else {'method','items','reverse_items','minimum','maximum','aggregation','min_answered'}
    need(not(set(scoring)-allowed_scoring),'scoring','unsupported scoring option')
    for key in required:
        value=model.get(key); need(bool(value), 'model.'+key)
        if key=='columns': need(isinstance(value,list) and bool(value), 'model.columns')
        elif key!='group_order': need(_text(value), 'model.'+key)
        if key=='group_order': need(isinstance(value,list) and len(value)==2 and value[0]!=value[1], 'model.group_order')
        else:
            for name in value if isinstance(value,list) else [value]: need(name in names, 'model.'+key, 'model variable must have an evidenced mapping')
    if method == 'scale_score':
        need(scoring.get('method') == 'scale' and scoring.get('items') == model.get('columns'), 'scoring', 'scale items must equal model columns')
    for key in ('alpha','confidence_level'): need(_number(inference.get(key)) and 0<inference[key]<1, 'inference.'+key)
    need(inference.get('alternative') in ('two-sided','less','greater'), 'inference.alternative')
    if _scientific_only: return errors
    for key in ('data_read','compute'): need(auth.get(key) is True, 'authorization.'+key, 'explicit scope authorization required')
    for key in ('output_dir','reference'): need(_text(auth.get(key)), 'authorization.'+key)
    sources=spec.get('sources',[]); need(isinstance(sources,list),'sources')
    sources=sources if isinstance(sources,list) else []
    source_ids=[]
    for i,s in enumerate(sources):
        need(isinstance(s,dict) and all(_text(s.get(k)) for k in ('source_id','role','software')), f'sources.{i}')
        if isinstance(s,dict):
            need(s.get('role') in ('AUTHORITATIVE','VERIFICATION','DATA_ONLY','CANDIDATE','DERIVED'), f'sources.{i}.role')
            if _text(s.get('source_id')): source_ids.append(s['source_id'])
    need(len(source_ids)==len(set(source_ids)), 'sources', 'duplicate source IDs')
    if intent in ('FORMAL_ANALYSIS','VERIFICATION'):
        need(sum(isinstance(s,dict) and s.get('role')=='AUTHORITATIVE' for s in sources)==1,'sources','exactly one authoritative source required')
        need(sum(isinstance(s,dict) and s.get('role')=='VERIFICATION' for s in sources)<=1,'sources','at most one verification source')
        try: confirmed=auth.get('formal_spec_hash')==spec_hash(spec)
        except (ValueError,TypeError): confirmed=False
        need(confirmed,'authorization.formal_spec_hash','author must confirm this scientific specification')
    return errors

def validate_result(run):
    errors=[]
    def fail(field,message): errors.append({'code':'INVALID_RESULT','field':field,'message':message})
    if not isinstance(run,dict): return [{'code':'INVALID_RESULT','field':'run','message':'must be an object'}]
    for key in ('analysis_id','run_id','spec_hash','input_hash'):
        if not _text(run.get(key)): fail(key,'nonempty identity required')
    if run.get('schema_version')!=1: fail('schema_version','must be 1')
    if type(run.get('revision')) is not int or run['revision']<1: fail('revision','positive integer required')
    if run.get('intent') not in INTENTS[1:]: fail('intent','computational intent required')
    if run.get('status')!='COMPLETED' or run.get('result_complete') is not True: fail('status','complete run required')
    if run.get('adoption_status')!='CANDIDATE': fail('adoption_status','computation never adopts findings')
    for key in ('scientific_spec','sample_audit','execution_provenance','artifact_refs'):
        if not run.get(key): fail(key,'nonempty record required')
    scientific=run.get('scientific_spec')
    if not isinstance(scientific,dict):
        fail('scientific_spec','scientific specification object required')
        return errors
    scientific_errors=validate_spec(scientific,_scientific_only=True)
    if scientific_errors:
        fail('scientific_spec','invalid scientific specification: '+json.dumps(scientific_errors))
        return errors
    if isinstance(scientific,dict):
        try:
            expected=hashlib.sha256(json.dumps(scientific,sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()
        except (ValueError,TypeError): expected=None
        if run.get('spec_hash') != expected: fail('spec_hash','scientific specification hash mismatch')
        data=scientific.get('data')
        if not isinstance(data,dict) or run.get('input_hash') != data.get('sha256'): fail('input_hash','input content hash mismatch')
    for key in ('spec_hash','input_hash'):
        digest=run.get(key)
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest): fail(key,'SHA256 required')
    rows=run.get('results')
    if not isinstance(rows,list) or not rows: fail('results','nonempty results required'); return errors
    model=scientific['model']; method=model['method']
    if run.get('method_id')!=method: fail('method_id','run method must match scientific specification')
    if method=='descriptive': expected={(v,'mean','overall') for v in model['columns']}
    elif method=='scale_score': expected={('score','mean','overall')}
    elif method in ('welch_t','student_t'): expected={(model['outcome'],'group',str(model['group_order'][0])+' - '+str(model['group_order'][1]))}
    elif method=='paired_t': expected={(model['x'],'paired_difference',model['x']+' - '+model['y'])}
    else: expected={(model['x'],'correlation',model['x']+' ~ '+model['y'])}
    actual=[tuple(row.get(k) for k in ('outcome_id','term_id','contrast_id')) for row in rows if isinstance(row,dict)]
    try:
        if len(actual)!=len(rows) or len(set(actual))!=len(rows) or set(actual)!=expected: fail('results','results must exactly cover requested identities')
    except TypeError: fail('results','invalid result identity type')
    audit=run.get('sample_audit')
    if not isinstance(audit,dict): fail('sample_audit','sample audit object required')
    for i,row in enumerate(rows):
        if not isinstance(row,dict): fail(f'results.{i}','object required'); continue
        for key in ('outcome_id','term_id','contrast_id'):
            if not _text(row.get(key)): fail(f'results.{i}.{key}','identity required')
        model = scientific.get('model', {}) if isinstance(scientific,dict) else {}
        method = model.get('method') if isinstance(model,dict) else None
        required = ['estimate','n']
        if method in ('descriptive','scale_score'): required += ['sd','se','df','ci']
        if method in ('welch_t','student_t','paired_t','pearson'): required += ['df','statistic','p','ci','statistic_name']
        if method in ('welch_t','student_t','paired_t'): required += ['se']
        if method in ('welch_t','student_t'): required += ['n_by_group']
        for key in required:
            if key not in row: fail(f'results.{i}.{key}','required for method')
        if 'n' in row and (type(row['n']) is not int or row['n']<1): fail(f'results.{i}.n','positive sample size required')
        if isinstance(audit,dict) and row.get('n')!=audit.get('effective_n'): fail(f'results.{i}.n','sample audit does not match result')
        if 'n' in scientific['sample'] and row.get('n')!=scientific['sample']['n']: fail(f'results.{i}.n','declared sample size does not match effective sample')
        if 'df' in row and _number(row['df']) and row['df']<=0: fail(f'results.{i}.df','positive degrees of freedom required')
        if method in ('descriptive','scale_score'):
            if type(row.get('n')) is not int or row['n']<2 or row.get('df')!=row['n']-1: fail(f'results.{i}.df','summary interval requires n>=2 and df=n-1')
        if method in ('welch_t','student_t'):
            counts=row.get('n_by_group')
            if not isinstance(counts,list) or len(counts)!=2 or any(type(v) is not int or v<1 for v in counts) or sum(counts)!=row.get('n'): fail(f'results.{i}.n_by_group','two positive integer group counts summing to n required')
        if method in ('welch_t','student_t','paired_t','pearson') and 'test_alternative' in row and row['test_alternative']!=scientific['inference']['alternative']: fail(f'results.{i}.test_alternative','test direction must match scientific specification')
        if method in ('welch_t','student_t','paired_t') and row.get('statistic_name')!='t': fail(f'results.{i}.statistic_name','t statistic required')
        if method=='pearson':
            if row.get('statistic_name')!='r': fail(f'results.{i}.statistic_name','r statistic required')
            if not _number(row.get('estimate')) or not -1<=row['estimate']<=1 or row.get('statistic')!=row.get('estimate'): fail(f'results.{i}.estimate','correlation must be between -1 and 1')
            if type(row.get('n')) is not int or row['n']<4 or row.get('df')!=row['n']-2: fail(f'results.{i}.df','Pearson interval requires n>=4 and df=n-2')
            if isinstance(row.get('ci'),list) and any(not _number(v) or not -1<=v<=1 for v in row['ci']): fail(f'results.{i}.ci','correlation interval out of range')
        if 'ci' in row and (row.get('confidence_level')!=scientific['inference']['confidence_level'] or row.get('ci_alternative')!='two-sided'): fail(f'results.{i}.ci','confidence level and interval direction must be explicit')
        if 'se' in row and _number(row['se']) and row['se']<0: fail(f'results.{i}.se','nonnegative standard error required')
        if 'sd' in row and _number(row['sd']) and row['sd']<0: fail(f'results.{i}.sd','nonnegative standard deviation required')
        if not any(_number(row.get(k)) for k in ('estimate','statistic')): fail(f'results.{i}','numeric estimate or statistic required')
        for key in ('estimate','sd','se','df','statistic','p','n'):
            if key in row and (not _number(row[key]) or (key=='p' and not 0<=row[key]<=1)):
                fail(f'results.{i}.{key}','finite valid number required')
        if 'ci' in row and (not isinstance(row['ci'],list) or len(row['ci'])!=2 or not all(_number(v) for v in row['ci']) or row['ci'][0]>row['ci'][1]): fail(f'results.{i}.ci','ordered finite interval required')
    return errors
