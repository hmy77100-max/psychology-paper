"""Shared local candidate runner. Never adopts results or writes manuscripts.

The host supplies actual user authorization; this interface checks its scope.
It is not a sandbox for other shell tools or a substitute for host permissions.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import uuid

from analysis_contracts import METHODS, R_METHODS, analysis_context, context_hash, describe_method, scientific_spec, spec_hash, validate_result, validate_spec

PLUGIN_ROOT = Path(__file__).resolve().parents[1]


class RunError(ValueError):
    def __init__(self, code, message, field=''):
        super().__init__(message)
        self.code, self.field = code, field


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def response(operation, status, *, spec=None, errors=None, artifacts=None, complete=False):
    return {'schema':'psychology-paper-analysis-response','schema_version':1,
            'operation':operation,'status':status,
            'execution_ready':status=='READY_FOR_ANALYSIS',
            'analysis_allowed':status=='READY_FOR_ANALYSIS',
            'result_complete':complete,
            'analysis_id':spec.get('analysis_id') if isinstance(spec,dict) else None,
            'errors':errors or [],'artifacts':artifacts or [],'warnings':[]}


def _absolute(value, field):
    path=Path(value).expanduser()
    if not path.is_absolute():
        raise RunError('INVALID_SPEC','Use an explicit absolute location independent of working directory.',field)
    return path.resolve()


def _output_scope(spec):
    auth=spec['authorization']
    output=_absolute(auth['output_dir'],'authorization.output_dir')
    source=_absolute(spec['data']['path'],'data.path')
    protected=[PLUGIN_ROOT, source]
    for value in auth.get('protected_paths',[]):
        protected.append(_absolute(value,'authorization.protected_paths'))
    if output == Path(output.anchor) or any(output==p or output.is_relative_to(p) for p in protected):
        raise RunError('PERMISSION_DENIED','Candidate output overlaps a protected source, plugin, or volume root.')
    if output.exists() and not output.is_dir():
        raise RunError('PERMISSION_DENIED','Candidate output location is an existing file.')
    # Explicitly reject link/junction components rather than following an alias
    # to a directory the author may not have meant to authorize.
    original=Path(auth['output_dir']).expanduser()
    for part in (original,*original.parents):
        if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):
            raise RunError('PERMISSION_DENIED','Candidate output must not traverse a link or junction.')
    return output


def _read_table(spec):
    data=spec['data']; source=_absolute(data['path'],'data.path')
    raw=source.read_bytes()
    if digest(raw)!=data['sha256'].lower():
        raise RunError('INPUT_CHANGED','Data content differs from the approved candidate specification.','data.sha256')
    opts=data['read_options']
    if data['format']=='csv':
        reader=csv.reader(io.StringIO(raw.decode(opts['encoding'])),delimiter=opts['delimiter'])
        records=list(reader)
    else:
        # Cached values are an explicit choice: the runner never evaluates formulas.
        if opts.get('formula_policy')!='cached_values':
            raise RunError('INVALID_SPEC','XLSX requires explicit formula_policy=cached_values.','data.read_options.formula_policy')
        try:
            import openpyxl
        except ImportError as exc:
            raise RunError('DEPENDENCY_UNAVAILABLE','openpyxl is required for XLSX.') from exc
        book=openpyxl.load_workbook(io.BytesIO(raw),read_only=True,data_only=True,keep_links=False)
        try:
            sheet=opts['sheet_name']
            sheet=book.worksheets[sheet] if type(sheet) is int else book[sheet]
            records=list(sheet.iter_rows(values_only=True))
        finally:
            book.close()
    if not records:
        raise RunError('INVALID_DATA','The selected table is empty.')
    columns=[str(v) if v is not None else '' for v in records[0]]
    if any(not v for v in columns) or len(columns)!=len(set(columns)):
        raise RunError('INVALID_DATA','Column names must be nonempty and unique.')
    if any(len(row)!=len(columns) for row in records[1:]):
        raise RunError('INVALID_DATA','Table rows have inconsistent lengths.')
    needed={r['column'] for r in spec['field_map']}
    if not needed.issubset(columns):
        raise RunError('INVALID_DATA','Mapped columns missing: '+', '.join(sorted(needed-set(columns))))
    rows=[dict(zip(columns,('' if v is None else v for v in row))) for row in records[1:]]
    if not rows:
        raise RunError('INVALID_DATA','The table contains no observations.')
    return source,raw,columns,rows


class _RBackend:
    """Optional local bridge; no shell interpolation, install, or implicit fallback."""
    def __init__(self,spec,output):
        self.output=output
        chosen=spec.get('execution',{}).get('rscript') or os.environ.get('PSYCHOLOGY_PAPER_RSCRIPT') or shutil.which('Rscript')
        if not chosen or not Path(chosen).is_file():
            raise RunError('DEPENDENCY_UNAVAILABLE','Rscript unavailable. Configure an existing executable; nothing was installed.')
        self.executable=str(Path(chosen).resolve())
        m=spec['model'];method=m['method']
        profiles=json.loads((PLUGIN_ROOT/'requirements-statistics-r.json').read_text(encoding='utf-8'))['profiles']
        groups=['bridge']
        if method.endswith('_anova'):groups+=['anova']
        elif method.endswith('_mixed'):groups+=['mixed']
        elif method=='mediation':groups+=['mediation']
        elif method in ('cfa','sem'):groups+=['sem']
        else:
            groups+=['regression']
            if m.get('standard_error')=='HC3':groups+=['regression_hc3']
            if method=='binomial_regression' or (method=='moderation' and m.get('family')=='binomial'):groups+=['binomial_regression']
        packages=sorted({name for g in groups for name in profiles[g]} | ({'emmeans'} if spec['inference'].get('comparisons') else set()))
        # This expression is fixed code; only known package names are data arguments.
        code='a<-commandArgs(TRUE); missing<-a[!vapply(a,requireNamespace,logical(1),quietly=TRUE)]; if(length(missing)) {cat(paste(missing,collapse=",")); quit(status=42)}; cat(jsonlite::toJSON(list(R=as.character(getRversion()),packages=as.list(setNames(vapply(a,function(p)as.character(packageVersion(p)),""),a))),auto_unbox=TRUE))'
        proc=subprocess.run([self.executable,'--vanilla','-e',code,*packages],capture_output=True,text=True,encoding='utf-8',errors='replace')
        if proc.returncode:
            raise RunError('DEPENDENCY_UNAVAILABLE','R dependency check failed: '+(proc.stdout+proc.stderr).strip())
        try:self.versions=json.loads(proc.stdout)
        except ValueError as exc:raise RunError('INVALID_RUNTIME_RESPONSE','R preflight returned malformed JSON.') from exc
        if not isinstance(self.versions,dict) or not isinstance(self.versions.get('R'),str):raise RunError('INVALID_RUNTIME_RESPONSE','Missing R runtime identity.')

    def compute(self,spec,rows,columns):
        self.output.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.r-run-',dir=self.output) as directory:
            request=Path(directory)/'input.json'; target=Path(directory)/'output.json'
            request.write_text(json.dumps({'spec':scientific_spec(spec),'rows':rows,'columns':columns},ensure_ascii=False,allow_nan=False),encoding='utf-8')
            proc=subprocess.Popen([self.executable,'--vanilla',str(PLUGIN_ROOT/'scripts/analysis_backend_r.R'),str(request),str(target)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
            try:stdout,stderr=proc.communicate()
            except BaseException:
                proc.terminate();proc.wait();raise
            if proc.returncode or not target.is_file():raise RunError('BACKEND_FAILED','R did not produce a result: '+stderr[-3000:])
            try:result=json.loads(target.read_text(encoding='utf-8'))
            except ValueError as exc:raise RunError('INVALID_RUNTIME_RESPONSE','R result was not valid JSON.') from exc
            if not isinstance(result,dict):raise RunError('INVALID_RUNTIME_RESPONSE','R result must be an object.')
            if result.get('status')!='COMPLETED':raise RunError(result.get('status','BACKEND_FAILED'),json.dumps(result.get('errors',[]),ensure_ascii=False))
            result.setdefault('diagnostics',{})['runtime_stderr']=stderr[-5000:]
            result['backend_versions']=self.versions
            return result


def _prepare(spec):
    errors=validate_spec(spec,for_execution=True)
    if errors:
        status='UNSUPPORTED_METHOD' if any(e['field']=='model.method' for e in errors) else 'INVALID_SPEC'
        return response('preflight',status,spec=spec,errors=errors),None
    if spec['intent']=='METHOD_REVIEW':
        return response('preflight','METHOD_REVIEW_READY',spec=spec),None
    if spec['intent']=='FORMAL_ANALYSIS':
        formal=next(s for s in spec['sources'] if s['role']=='AUTHORITATIVE')
        engines=('r',) if spec['model']['method'] in R_METHODS else ('python','python/scipy')
        if formal['software'].strip().lower() not in engines:
            raise RunError('FORMAL_BACKEND_MISMATCH','Preserve the selected formal software; this method uses '+engines[0]+'. Use candidate or verification intent for another engine.','sources')
    output=_output_scope(spec)
    source,raw,columns,rows=_read_table(spec)
    if spec['model']['method'] in R_METHODS:
        backend=_RBackend(spec,output)
    else:
        try:
            import analysis_backends as backend
            for name in ('numpy','scipy'):importlib.import_module(name)
        except ImportError as exc:
            raise RunError('DEPENDENCY_UNAVAILABLE',f'Statistics dependency unavailable: {exc.name}. No installation was attempted.') from exc
    result=response('preflight','READY_FOR_ANALYSIS',spec=spec)
    result['spec_hash']=spec_hash(spec)
    result['input_hash']=digest(raw)
    result['observations']=len(rows)
    return result,(output,source,raw,columns,rows,backend)


def evaluate_runtime_preflight(spec):
    try:
        return _prepare(spec)[0]
    except (RunError,OSError,UnicodeError,LookupError,TypeError,ValueError) as exc:
        return _failure('preflight',spec,exc)


def _failure(operation,spec,exc):
    status=getattr(exc,'code','INVALID_DATA')
    return response(operation,status,spec=spec,errors=[{'code':status,'field':getattr(exc,'field',''),'message':str(exc)}])


def run_analysis(spec):
    attempt_file=None;attempt=None
    try:
        if isinstance(spec,dict) and spec.get('schema_version')==3 and spec.get('intent')!='METHOD_REVIEW':
            errors=validate_spec(spec,for_execution=True)
            if errors:return response('run','INVALID_SPEC',spec=spec,errors=errors)
            safe_output=_output_scope(spec)
            attempt_id=str(uuid.uuid4());folder=safe_output/attempt_id
            folder.mkdir(parents=True,exist_ok=False)
            attempt_file=folder/'analysis-run.json'
            context=analysis_context(spec)
            attempt={'schema_version':2,'analysis_id':spec['analysis_id'],'revision':spec['revision'],
                     'run_id':attempt_id,'intent':spec['intent'],'spec_hash':spec_hash(spec),
                     'input_hash':spec['data']['sha256'],'scientific_spec':scientific_spec(spec),
                     'method_id':spec['model']['method'],'analysis_context':context,'context_hash':context_hash(context),
                     'status':'STARTED','result_complete':False,'adoption_status':'CANDIDATE',
                     'started_at_utc':datetime.now(timezone.utc).isoformat()}
            _write_attempt(attempt_file,attempt,exclusive=True)
        ready,prepared=_prepare(spec)
        if prepared is None:
            ready['operation']='run'
            return _finish_attempt_failure(ready,attempt_file,attempt)
        output,source,raw,columns,rows,backend=prepared
        computed=backend.compute(spec,rows,columns)
        if source.read_bytes()!=raw:
            raise RunError('INPUT_CHANGED','Source changed during calculation; no successful run was saved.')
        if _output_scope(spec)!=output:
            raise RunError('PERMISSION_DENIED','Output scope changed during calculation.')
        run_id=attempt['run_id'] if attempt else str(uuid.uuid4())
        run_dir=output/run_id
        run_file=run_dir/'analysis-run.json'
        provenance={'engine':'python-scipy','software':'Python','python':sys.version.split()[0],'executable':sys.executable,
                    'platform':platform.platform(),'host':spec.get('execution',{}).get('host','local-cli'),
                    'host_version':spec.get('execution',{}).get('host_version','unreported'),
                    'plugin_version':json.loads((PLUGIN_ROOT/'.codex-plugin/plugin.json').read_text(encoding='utf-8'))['version'],
                    'started_at_utc':datetime.now(timezone.utc).isoformat(),
                    'backend_versions':computed['backend_versions'],
                    'code_hashes':{name:digest((PLUGIN_ROOT/'scripts'/name).read_bytes()) for name in ('analysis_runner.py','analysis_backends.py','analysis_contracts.py')},
                    'input_path':str(source),'authorization_reference':spec['authorization']['reference']}
        if isinstance(backend,_RBackend):
            provenance.update(engine='r',software='R',version=backend.versions['R'],executable=backend.executable)
            provenance.pop('python',None)
            code_files=[PLUGIN_ROOT/'scripts/analysis_backend_r.R',PLUGIN_ROOT/'requirements-statistics-r.json',*(PLUGIN_ROOT/'scripts/analysis_r').glob('*.R')]
            provenance['code_hashes'].update({str(p.relative_to(PLUGIN_ROOT)):digest(p.read_bytes()) for p in code_files})
        run={'schema_version':2 if attempt else 1,'analysis_id':spec['analysis_id'],'revision':spec['revision'],
             'run_id':run_id,'intent':spec['intent'],'spec_hash':spec_hash(spec),'input_hash':digest(raw),
             'scientific_spec':scientific_spec(spec),'method_id':spec['model']['method'],
             'status':'COMPLETED','result_complete':True,'adoption_status':'CANDIDATE',
             'sources':spec.get('sources',[]),'results':computed['results'],
             'sample_audit':computed['sample_audit'],'diagnostics':computed['diagnostics'],
             'execution_provenance':provenance,'artifact_refs':[{'kind':'run','path':str(run_file)}]}
        if attempt:run.update(analysis_context=attempt['analysis_context'],context_hash=attempt['context_hash'])
        if 'model_summary' in computed:run['model_summary']=computed['model_summary']
        derived=computed.get('derived_rows',[])
        derived_text=None
        if derived:
            text=io.StringIO(newline='')
            writer=csv.DictWriter(text,fieldnames=list(derived[0]))
            writer.writeheader();writer.writerows(derived)
            derived_text=text.getvalue()
            run['artifact_refs'].append({'kind':'derived','path':str(run_dir/'derived.csv'),'sha256':digest(derived_text.encode('utf-8'))})
        invalid=validate_result(run)
        if invalid:
            return _finish_attempt_failure(response('run','INVALID_RESULT',spec=spec,errors=invalid),attempt_file,attempt)
        # Unique directory and exclusive file creation prevent replacing an old run.
        output.mkdir(parents=True,exist_ok=True)
        if not attempt:run_dir.mkdir(exist_ok=False)
        payload=json.dumps(run,ensure_ascii=False,indent=2,allow_nan=False)
        if derived_text is not None:
            with (run_dir/'derived.csv').open('x',encoding='utf-8',newline='') as stream:
                stream.write(derived_text)
        if attempt:_write_attempt(run_file,run)
        else:
            with run_file.open('x',encoding='utf-8',newline='\n') as stream:
                stream.write(payload);stream.flush();os.fsync(stream.fileno())
        artifacts=[{'kind':'run','path':str(run_file),'sha256':digest(run_file.read_bytes())}]
        result=response('run','COMPLETED',spec=spec,artifacts=artifacts,complete=True)
        result.update(spec_hash=run['spec_hash'],input_hash=run['input_hash'],run_id=run_id,adoption_status='CANDIDATE')
        if attempt:result['search_summary']=summarize_attempts(output,search_set_id=attempt['analysis_context']['search_set_id'])
        return result
    except (RunError,OSError,UnicodeError,LookupError,TypeError,ValueError,ImportError) as exc:
        return _finish_attempt_failure(_failure('run',spec,exc),attempt_file,attempt)
    except KeyboardInterrupt:
        return _finish_attempt_failure(response('run','ABORTED',spec=spec,errors=[{'code':'ABORTED','message':'Run interrupted.'}]),attempt_file,attempt)


def _write_attempt(path,value,exclusive=False):
    text=json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)
    if exclusive:
        with path.open('x',encoding='utf-8') as f:f.write(text);f.flush();os.fsync(f.fileno())
    else:
        tmp=path.with_suffix('.tmp')
        with tmp.open('x',encoding='utf-8') as f:f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)


def _finish_attempt_failure(result,path,attempt):
    if path is None or attempt is None:return result
    attempt.update(status=result['status'],errors=result.get('errors',[]),result_complete=False,
                   ended_at_utc=datetime.now(timezone.utc).isoformat())
    try:
        _write_attempt(path,attempt)
        result['artifacts']=[{'kind':'attempt','path':str(path),'sha256':digest(path.read_bytes())}]
        result['search_summary']=summarize_attempts(path.parent.parent,search_set_id=attempt['analysis_context']['search_set_id'])
    except OSError as exc:
        result['warnings'].append('Attempt remains incomplete; persistence failed: '+str(exc))
    return result


def summarize_attempts(output,*,search_set_id):
    """Only observed candidate artifacts; no claim about unseen exploration/adoption."""
    root=Path(output).resolve();records=[];unreadable=0
    for directory in root.iterdir() if root.is_dir() else []:
        if directory.is_symlink() or (hasattr(directory,'is_junction') and directory.is_junction()):continue
        try:uuid.UUID(directory.name)
        except ValueError:continue
        path=directory/'analysis-run.json'
        if not path.is_file() or path.is_symlink():continue
        try:row=json.loads(path.read_text(encoding='utf-8'))
        except (OSError,ValueError):unreadable+=1;continue
        if not isinstance(row,dict) or not isinstance(row.get('analysis_context'),dict) or any(not isinstance(row.get(k),str) for k in ('spec_hash','method_id','status')):
            unreadable+=1;continue
        if row.get('schema_version')==2 and row['analysis_context'].get('search_set_id')==search_set_id:records.append(row)
    complete=sum(r.get('result_complete') is True and r.get('status')=='COMPLETED' for r in records)
    incomplete=sum(r.get('status') in ('STARTED','ABORTED') for r in records)
    return {'scope':'Observed run artifacts in the authorized candidate directory only; considered/unobserved work and adoption are not inferred.',
            'attempted':len(records),'completed':complete,'failed':len(records)-complete-incomplete,
            'interrupted_or_running':incomplete,'distinct_specifications':len({r['spec_hash'] for r in records}),
            'executed_methods':sorted({r['method_id'] for r in records}), 'unreadable_records':unreadable,'considered':None,'adopted':None}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('preflight','run','methods'))
    parser.add_argument('--spec')
    parser.add_argument('--method', choices=METHODS, help='With methods, show only this method\'s field contract.')
    args=parser.parse_args(argv)
    if args.method and args.operation!='methods':
        parser.error('--method is only valid with methods')
    if args.operation=='methods':
        info=describe_method(args.method) if args.method else {'methods':list(METHODS),'status':'CAPABILITY_LIST','learning_scope':'open','numeric_validation':'see validation record','details':'methods --method <name>'}
        print(json.dumps(info))
        return 0
    if not args.spec:
        parser.error('--spec is required')
    try:
        spec=json.loads(Path(args.spec).read_text(encoding='utf-8'))
    except (OSError,ValueError) as exc:
        print(json.dumps(response(args.operation,'INVALID_REQUEST',errors=[{'code':'INVALID_REQUEST','message':str(exc)}]),ensure_ascii=False))
        return 2
    result=evaluate_runtime_preflight(spec) if args.operation=='preflight' else run_analysis(spec)
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))
    return 0


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
