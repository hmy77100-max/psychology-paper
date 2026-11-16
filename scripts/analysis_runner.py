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
import sys
import uuid

from analysis_contracts import METHODS, describe_method, scientific_spec, spec_hash, validate_result, validate_spec

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


def _prepare(spec):
    errors=validate_spec(spec,for_execution=True)
    if errors:
        status='UNSUPPORTED_METHOD' if any(e['field']=='model.method' for e in errors) else 'INVALID_SPEC'
        return response('preflight',status,spec=spec,errors=errors),None
    if spec['intent']=='METHOD_REVIEW':
        return response('preflight','METHOD_REVIEW_READY',spec=spec),None
    if spec['intent']=='FORMAL_ANALYSIS':
        formal=next(s for s in spec['sources'] if s['role']=='AUTHORITATIVE')
        if formal['software'].strip().lower() not in ('python','python/scipy'):
            raise RunError('FORMAL_BACKEND_MISMATCH','This runner uses Python. Preserve the selected formal software; use candidate or verification intent for a separate Python run.','sources')
    output=_output_scope(spec)
    source,raw,columns,rows=_read_table(spec)
    try:
        import analysis_backends as backend
        for name in ('numpy','scipy'):
            importlib.import_module(name)
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
    try:
        ready,prepared=_prepare(spec)
        if prepared is None:
            ready['operation']='run'
            return ready
        output,source,raw,columns,rows,backend=prepared
        computed=backend.compute(spec,rows,columns)
        if source.read_bytes()!=raw:
            raise RunError('INPUT_CHANGED','Source changed during calculation; no successful run was saved.')
        if _output_scope(spec)!=output:
            raise RunError('PERMISSION_DENIED','Output scope changed during calculation.')
        run_id=str(uuid.uuid4())
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
        run={'schema_version':1,'analysis_id':spec['analysis_id'],'revision':spec['revision'],
             'run_id':run_id,'intent':spec['intent'],'spec_hash':spec_hash(spec),'input_hash':digest(raw),
             'scientific_spec':scientific_spec(spec),'method_id':spec['model']['method'],
             'status':'COMPLETED','result_complete':True,'adoption_status':'CANDIDATE',
             'sources':spec.get('sources',[]),'results':computed['results'],
             'sample_audit':computed['sample_audit'],'diagnostics':computed['diagnostics'],
             'execution_provenance':provenance,'artifact_refs':[{'kind':'run','path':str(run_file)}]}
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
            return response('run','INVALID_RESULT',spec=spec,errors=invalid)
        # Unique directory and exclusive file creation prevent replacing an old run.
        output.mkdir(parents=True,exist_ok=True)
        run_dir.mkdir(exist_ok=False)
        payload=json.dumps(run,ensure_ascii=False,indent=2,allow_nan=False)
        if derived_text is not None:
            with (run_dir/'derived.csv').open('x',encoding='utf-8',newline='') as stream:
                stream.write(derived_text)
        with run_file.open('x',encoding='utf-8',newline='\n') as stream:
            stream.write(payload);stream.flush();os.fsync(stream.fileno())
        artifacts=[{'kind':'run','path':str(run_file),'sha256':digest(run_file.read_bytes())}]
        result=response('run','COMPLETED',spec=spec,artifacts=artifacts,complete=True)
        result.update(spec_hash=run['spec_hash'],input_hash=run['input_hash'],run_id=run_id,adoption_status='CANDIDATE')
        return result
    except (RunError,OSError,UnicodeError,LookupError,TypeError,ValueError,ImportError) as exc:
        return _failure('run',spec,exc)


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
