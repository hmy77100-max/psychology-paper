"""Controlled numerical analyses. Source rows are never mutated."""
from __future__ import annotations
import math
import platform
import numpy as np
import scipy
from scipy import stats

SUPPORTED_METHODS = {'descriptive', 'scale_score', 'welch_t', 'student_t', 'paired_t', 'pearson'}

class BackendError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code

def compute(spec, rows, columns):
    def fail(code, message): raise BackendError(code, message)
    model = spec['model']; method = model.get('method')
    if spec['sample'].get('missing') not in ('complete_case','error'): fail('INVALID_SPEC','Unsupported missing policy')
    if method not in SUPPORTED_METHODS: fail('UNSUPPORTED_METHOD', str(method))
    mapping = {x['variable']: x['column'] for x in spec['field_map']}
    def col(variable):
        if variable not in mapping or mapping[variable] not in columns:
            fail('MISSING_COLUMN', 'No source column for '+str(variable))
        return mapping[variable]
    missing = spec.get('data', {}).get('read_options', {}).get('missing_values', [''])
    if not isinstance(missing, list): fail('INVALID_SPEC', 'missing_values must be a list')
    def absent(value): return value is None or value in missing
    def number(row, variable):
        value = row.get(col(variable))
        if isinstance(value, bool): fail('INVALID_NUMERIC', 'Boolean value requires explicit recoding for '+variable)
        if absent(value): return None
        try: result = float(value)
        except (TypeError, ValueError): fail('INVALID_NUMERIC', 'Non-numeric value for '+variable)
        if not math.isfinite(result): fail('INVALID_NUMERIC', 'Nonfinite value for '+variable)
        return result
    selected = list(enumerate(rows)); filter_audit=[]
    for rule in spec['sample']['filters']:
        if not isinstance(rule, dict): fail('INVALID_FILTER', 'Filter must be an object')
        column = col(rule['variable']) if 'variable' in rule else rule.get('column')
        if column not in columns: fail('MISSING_COLUMN', 'Unknown filter column')
        op=rule.get('op')
        if op not in ('eq','in','not_in'): fail('INVALID_FILTER', 'Unsupported filter operator')
        values = [rule.get('value')] if op=='eq' else rule.get('values')
        if not isinstance(values,list): fail('INVALID_FILTER', 'Filter values must be a list')
        before=len(selected)
        selected=[(i,r) for i,r in selected if ((r.get(column) in values) != (op=='not_in'))]
        filter_audit.append({'column':column,'op':op,'before':before,'after':len(selected),'excluded':before-len(selected)})
    inference=spec['inference']; alternative=inference['alternative']; confidence=inference['confidence_level']
    if alternative not in ('two-sided','less','greater') or not 0<confidence<1 or not 0<inference['alpha']<1:
        fail('INVALID_SPEC','Invalid inference configuration')
    diagnostics=[]; derived=[]; results=[]; dropped=[]
    if 'missing_values' not in spec.get('data',{}).get('read_options',{}):
        diagnostics.append({'code':'DEFAULT_MISSING_VALUE','message':'Empty string and None are treated as missing.'})
    def collect(variables):
        for v in variables: col(v)
        good=[]
        for index,row in selected:
            values=[number(row,v) for v in variables]
            if any(v is None for v in values):
                if spec['sample']['missing']=='error': fail('MISSING_DATA','Missing required value at row '+str(index))
                dropped.append(index)
            else: good.append((index,row,values))
        return good
    def base(outcome,term,contrast,n,estimate):
        return {'outcome_id':outcome,'term_id':term,'contrast_id':contrast,'n':n,'estimate':float(estimate)}
    def summary(values, outcome):
        if len(values)<2: fail('INSUFFICIENT_SAMPLE','At least two observations required')
        sd=float(np.std(values,ddof=1)); se=sd/math.sqrt(len(values)); mean=float(np.mean(values))
        result=base(outcome,'mean','overall',len(values),mean)
        result.update(sd=sd,se=se,df=len(values)-1,ci=[mean-stats.t.ppf((1+confidence)/2,len(values)-1)*se,mean+stats.t.ppf((1+confidence)/2,len(values)-1)*se])
        return result
    scoring=spec['scoring']
    if scoring.get('method') not in ('none','scale'): fail('UNSUPPORTED_SCORING','Unsupported scoring method')
    if scoring.get('method')=='scale' and method!='scale_score': fail('UNSUPPORTED_SCORING','Run scale_score separately; source columns are not implicitly replaced')
    if method=='scale_score':
        if scoring.get('method')!='scale': fail('INVALID_SPEC','scale_score requires scale scoring')
        items=scoring.get('items',[]); reverse=scoring.get('reverse_items',[])
        low=scoring.get('minimum'); high=scoring.get('maximum'); aggregation=scoring.get('aggregation'); minimum=scoring.get('min_answered')
        if not items or len(items)!=len(set(items)) or not set(reverse)<=set(items) or not isinstance(minimum,int) or isinstance(minimum,bool) or not 1<=minimum<=len(items) or aggregation not in ('mean','sum'):
            fail('INVALID_SCORING','Invalid scale specification')
        if not isinstance(low,(float,int)) or not isinstance(high,(float,int)) or not math.isfinite(low) or not math.isfinite(high) or low>=high: fail('INVALID_SCORING','Invalid item bounds')
        for v in items: col(v)
        scores=[]
        for index,row in selected:
            answered=[]
            for v in items:
                value=number(row,v)
                if value is None:
                    if spec['sample']['missing']=='error': fail('MISSING_DATA','Missing scale item')
                    continue
                if not low<=value<=high: fail('INVALID_SCORING','Scale item outside declared bounds')
                answered.append(low+high-value if v in reverse else value)
            if len(answered)<minimum: dropped.append(index); continue
            score=sum(answered)/(len(answered) if aggregation=='mean' else 1)
            derived.append({'row_index':index,'score':score,'answered_items':len(answered)})
            scores.append(score)
        results=[summary(scores,'score')]
    elif method=='descriptive':
        names=model['columns']; good=collect(names)
        results=[summary([g[2][j] for g in good],v) for j,v in enumerate(names)]
    elif method in ('welch_t','student_t'):
        outcome=model['outcome']; group=model['group']; order=model['group_order']; group_col=col(group)
        if len(order)!=2 or order[0]==order[1]: fail('INVALID_SPEC','Two distinct group labels required')
        for index,row in selected:
            label=row.get(group_col)
            if not absent(label) and label not in order: fail('UNKNOWN_GROUP','Undeclared group label at row '+str(index))
        good=collect([outcome]); groups=[[],[]]
        for index,row,values in good:
            label=row.get(group_col)
            if absent(label):
                if spec['sample']['missing']=='error': fail('MISSING_DATA','Missing group')
                dropped.append(index); continue
            groups[order.index(label)].append(values[0])
        a,b=groups
        if min(len(a),len(b))<2: fail('INSUFFICIENT_SAMPLE','Each group requires at least two observations')
        va,vb=np.var(a,ddof=1),np.var(b,ddof=1)
        if va<=0 or vb<=0: fail('ZERO_VARIANCE','Each group must vary')
        if method=='welch_t':
            se=math.sqrt(va/len(a)+vb/len(b)); df=(va/len(a)+vb/len(b))**2/((va/len(a))**2/(len(a)-1)+(vb/len(b))**2/(len(b)-1))
        else:
            df=len(a)+len(b)-2; se=math.sqrt(((len(a)-1)*va+(len(b)-1)*vb)/df*(1/len(a)+1/len(b)))
        estimate=float(np.mean(a)-np.mean(b)); test=stats.ttest_ind(a,b,equal_var=method=='student_t',alternative=alternative)
        result=base(outcome,'group',str(order[0])+' - '+str(order[1]),len(a)+len(b),estimate)
        result.update(n_by_group=[len(a),len(b)],se=se,df=float(df),statistic_name='t',statistic=float(test.statistic),p=float(test.pvalue),ci=[estimate-stats.t.ppf((1+confidence)/2,df)*se,estimate+stats.t.ppf((1+confidence)/2,df)*se])
        results=[result]
    else:
        names=[model['x'],model['y']]
        if method=='paired_t':
            subject=model.get('subject_id')
            if not subject: fail('MISSING_SUBJECT_ID','Paired analysis requires explicit subject_id')
            subject_col=col(subject); ids=[]
            for index,row in selected:
                value=row.get(subject_col)
                if absent(value): fail('MISSING_SUBJECT_ID','Missing subject identity')
                if value in ids: fail('DUPLICATE_SUBJECT_ID','Subject identity must be unique')
                ids.append(value)
        good=collect(names); a=np.array([g[2][0] for g in good]); b=np.array([g[2][1] for g in good]); n=len(a)
        if method=='paired_t':
            if n<2: fail('INSUFFICIENT_SAMPLE','At least two complete pairs required')
            delta=a-b; sd=float(np.std(delta,ddof=1))
            if sd<=0: fail('ZERO_VARIANCE','Paired differences must vary')
            estimate=float(np.mean(delta)); se=sd/math.sqrt(n); df=n-1; test=stats.ttest_rel(a,b,alternative=alternative)
            result=base(model['x'],'paired_difference',model['x']+' - '+model['y'],n,estimate)
            result.update(sd=sd,se=se,df=df,statistic_name='t',statistic=float(test.statistic),p=float(test.pvalue),ci=[estimate-stats.t.ppf((1+confidence)/2,df)*se,estimate+stats.t.ppf((1+confidence)/2,df)*se])
        else:
            if n<4: fail('INSUFFICIENT_SAMPLE','Pearson Fisher interval requires n >= 4')
            if np.std(a)==0 or np.std(b)==0: fail('ZERO_VARIANCE','Pearson variables must vary')
            test=stats.pearsonr(a,b,alternative=alternative); estimate=float(test.statistic)
            if abs(estimate)>=1: interval=[estimate,estimate]
            else:
                z=np.arctanh(estimate); margin=stats.norm.ppf((1+confidence)/2)/math.sqrt(n-3); interval=[float(np.tanh(z-margin)),float(np.tanh(z+margin))]
            result=base(model['x'],'correlation',model['x']+' ~ '+model['y'],n,estimate)
            result.update(df=n-2,statistic_name='r',statistic=estimate,p=float(test.pvalue),ci=interval)
        results=[result]
    for result in results:
        result['ci_method'] = 'fisher_z' if method=='pearson' else 'student_t'
        result['ci_alternative'] = 'two-sided'
        result['confidence_level'] = confidence
        result['test_alternative'] = alternative
    return {'results':results,'sample_audit':{'input_n':len(rows),'after_filters_n':len(selected),'filtered_n':len(rows)-len(selected),'missing_excluded_n':len(set(dropped)),'missing_excluded_row_indices':sorted(set(dropped)),'effective_n':results[0]['n'],'filters':filter_audit,'missing_policy':spec['sample']['missing']},'diagnostics':diagnostics,'derived_rows':derived,'backend_versions':{'python':platform.python_version(),'numpy':np.__version__,'scipy':scipy.__version__}}
