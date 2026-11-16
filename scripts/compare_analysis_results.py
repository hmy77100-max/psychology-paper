from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any


def _valid_numbers(value, key=""):
    if isinstance(value, bool): return False
    if isinstance(value, (int, float)):
        return math.isfinite(value) and (key != "p" or 0 <= value <= 1)
    if isinstance(value, dict): return all(_valid_numbers(v, k) for k, v in value.items())
    if isinstance(value, list): return all(_valid_numbers(v, key) for v in value)
    return key not in {'p','F','t','r','df','df1','df2','n','estimate','se','statistic'}


def compare_results(authoritative, verification, *, tolerance, mode="verification"):
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int,float)) or not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be finite and non-negative")
    if mode not in ("verification", "candidates"): raise ValueError("unknown comparison mode")
    def engine(run):
        provenance=run.get("execution_provenance", {})
        if not isinstance(provenance,dict): return None
        return provenance.get("engine") or provenance.get("software")
    engines=(engine(authoritative),engine(verification))
    level="SAME_ENGINE_REPRODUCTION" if engines[0] and engines[0]==engines[1] else "INDEPENDENCE_NOT_ESTABLISHED"
    base = {"authoritative_preserved": True, "adoption_status": "CANDIDATE", "verification_level": level}
    def report(status, reason, mismatched=None, differences=None):
        return {**base, "status": status, "reason": reason,
                "mismatched_fields": mismatched or [], "differences": differences or {}}
    if not authoritative.get("analysis_id") or authoritative.get("analysis_id") != verification.get("analysis_id"):
        return report("NOT_COMPARABLE", "analysis identity differs")
    modern = "scientific_spec" in authoritative or "scientific_spec" in verification
    if modern:
        from analysis_contracts import validate_result
        if validate_result(authoritative) or validate_result(verification):
            return report("NOT_COMPARABLE", "invalid or incomplete run")
    auth_spec = authoritative.get("scientific_spec" if modern else "specification")
    verify_spec = verification.get("scientific_spec" if modern else "specification")
    if not isinstance(auth_spec, dict) or not auth_spec or not isinstance(verify_spec, dict) or not verify_spec:
        return report("NOT_COMPARABLE", "analysis specification is missing")
    # Legacy execution metadata is provenance, not a scientific difference.
    ignored={"execution_provenance", "execution_environment", "software_version", "run_id", "timestamp"}
    missing=object()
    mismatch=sorted(k for k in set(auth_spec)|set(verify_spec) if k not in ignored and auth_spec.get(k,missing)!=verify_spec.get(k,missing))
    if mismatch:
        return report("CANDIDATE_SPECIFICATION_CHANGED" if mode=="candidates" else "SPECIFICATION_MISMATCH", "analysis specification differs", mismatch)
    left=authoritative.get("results" if modern else "statistics")
    right=verification.get("results" if modern else "statistics")
    if not left or not right or not _valid_numbers(left) or not _valid_numbers(right):
        return report("NOT_COMPARABLE", "statistics are missing or invalid")
    if modern:
        def indexed(rows):
            return {json.dumps([r.get(k) for k in ("outcome_id","term_id","contrast_id")]):r for r in rows}
        left=indexed(left);right=indexed(right)
        if len(left)!=len(authoritative["results"]) or len(right)!=len(verification["results"]): return report("NOT_COMPARABLE","duplicate result identity")
    if not isinstance(left,dict) or not isinstance(right,dict): return report("NOT_COMPARABLE", "statistics are invalid")
    if not modern:
        def has_statistic(value):
            if not isinstance(value,dict): return False
            return any((k in {'F','t','r','estimate','statistic','p'} and type(v) in (int,float)) or has_statistic(v) for k,v in value.items())
        if not has_statistic(left) or not has_statistic(right): return report('NOT_COMPARABLE','legacy payload has no identifiable numerical statistics')
    differences={}
    def equal(a,b,key=''):
        if type(a) is not type(b) and not (type(a) in (int,float) and type(b) in (int,float)): return False
        if isinstance(a,(int,float)):
            if key in {'n','n_by_group'}: return a==b
            if key=='p': return math.isclose(a,b,abs_tol=0,rel_tol=1e-6)
            return math.isclose(a,b,abs_tol=tolerance,rel_tol=0)
        if isinstance(a,dict): return set(a)==set(b) and all(equal(a[k],b[k],k) for k in a)
        if isinstance(a,list): return len(a)==len(b) and all(equal(x,y,key) for x,y in zip(a,b))
        return a==b
    for key in sorted(set(left)|set(right)):
        if key not in left or key not in right or not equal(left[key],right[key],key):
            differences[key]={"authoritative":left.get(key),"verification":right.get(key)}
    return report("NUMERIC_DISCREPANCY" if differences else "ALIGNED", "numeric results differ" if differences else "results align", differences=differences)


def _load(path: str) -> dict[str, Any]:
    value = json.loads(Path(path).expanduser().resolve().read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("analysis result must be a JSON object")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compare two outputs for one analysis.")
    parser.add_argument("--authoritative", required=True)
    parser.add_argument("--verification", required=True)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--mode", choices=("verification", "candidates"), default="verification")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not math.isfinite(args.tolerance) or args.tolerance < 0:
        print("tolerance must be non-negative", file=sys.stderr)
        return 2
    try:
        result = compare_results(
            _load(args.authoritative),
            _load(args.verification),
            tolerance=args.tolerance,
            mode=args.mode,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
