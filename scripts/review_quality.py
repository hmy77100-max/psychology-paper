"""Check model-authored review records without judging science or writing state."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

KINDS = ('DEMONSTRATED_ERROR', 'REPORTING_GAP', 'UNRESOLVED_CHECK', 'BOUNDED_LIMITATION', 'AUTHOR_CHOICE')
STATUSES = ('OPEN', 'AWAITING_MATERIAL', 'HELD', 'RESOLVED', 'WITHDRAWN', 'REOPENED')


def validate_review(record: object) -> dict:
    """Validate explicit identity/state fields, never infer duplicates or closure."""
    errors: list[str] = []

    def text(value: object, field: str) -> None:
        if not isinstance(value, str) or not value.strip():
            errors.append(f'{field}: non-empty text required')

    items: list = []
    if not isinstance(record, dict):
        errors.append('record: object required')
    else:
        for field in ('manuscript_version', 'coverage'):
            text(record.get(field), field)
        if not isinstance(record.get('issues'), list):
            errors.append('issues: list required')
        else:
            items = record['issues']

    by_id: dict[str, dict] = {}
    for index, item in enumerate(items):
        prefix = f'issues[{index}]'
        if not isinstance(item, dict):
            errors.append(f'{prefix}: object required')
            continue
        for field in ('issue_id', 'location', 'claim', 'analysis_identity', 'basis', 'status_basis'):
            text(item.get(field), f'{prefix}.{field}')
        identity = item.get('issue_id')
        if isinstance(identity, str) and identity.strip():
            identity = identity.strip()
            if identity in by_id:
                errors.append(f'{prefix}.issue_id: duplicate identifier')
            by_id[identity] = item
        if item.get('kind') not in KINDS:
            errors.append(f'{prefix}.kind: unknown classification')
        status = item.get('status')
        if status not in STATUSES:
            errors.append(f'{prefix}.status: unknown status')
        refs = item.get('evidence_refs')
        if not isinstance(refs, list) or not refs:
            errors.append(f'{prefix}.evidence_refs: non-empty list required')
        else:
            for position, ref in enumerate(refs):
                text(ref, f'{prefix}.evidence_refs[{position}]')
        if status in ('RESOLVED', 'WITHDRAWN'):
            text(item.get('resolution_evidence'), f'{prefix}.resolution_evidence')
        previous = item.get('previous_status')
        if previous is not None and previous not in STATUSES:
            errors.append(f'{prefix}.previous_status: unknown status')
        if status == 'REOPENED':
            if previous not in ('RESOLVED', 'WITHDRAWN', 'HELD'):
                errors.append(f'{prefix}.previous_status: reopening requires a closed or held prior status')
            text(item.get('change_basis'), f'{prefix}.change_basis')
        if previous in ('RESOLVED', 'WITHDRAWN', 'HELD') and status in ('OPEN', 'AWAITING_MATERIAL'):
            errors.append(f'{prefix}.status: record REOPENED with change_basis instead of silently resetting history')

    for index, item in enumerate(items):
        if not isinstance(item, dict) or 'duplicate_of' not in item:
            continue
        prefix = f'issues[{index}].duplicate_of'
        target = item['duplicate_of']
        if not isinstance(target, str) or target.strip() not in by_id:
            errors.append(f'{prefix}: existing canonical issue ID required')
            continue
        canonical = by_id[target.strip()]
        if canonical is item or 'duplicate_of' in canonical:
            errors.append(f'{prefix}: must point directly to another canonical issue, not self or an alias')
        if canonical.get('status') != item.get('status'):
            errors.append(f'{prefix}: conflicting duplicate statuses require model reconciliation')

    return {'record_complete': not errors, 'scientific_verification': False, 'errors': errors,
            'limitations': ['Model/author judgment is required for issue identity, evidence applicability and resolution. '
                            'This checker does not compare manuscripts, detect semantic duplicates, save history or predict acceptance.']}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', required=True, help='Existing JSON record path, or - for stdin')
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
    try:
        content = sys.stdin.read() if args.record == '-' else Path(args.record).read_text(encoding='utf-8-sig')
        result = validate_review(json.loads(content))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f'review record error: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['record_complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
