#!/usr/bin/env python3
"""Publish a small, non-media pointer to the latest GitHub Actions review.

Candidate MP4 files remain in GitHub Actions artifacts, not Git history.
This index is public when the repository is public. It is NOT a rights approval.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Any


def manifest_from_audit(audit: dict[str, Any] | None, *, repo: str,
                        run_id: int, run_number: int, run_attempt: int,
                        result: str, event: str) -> dict[str, Any]:
    if not repo or '/' not in repo or run_id < 1 or run_number < 1:
        raise ValueError('Valid repository, run ID and run number are required')
    audit = audit if isinstance(audit, dict) else None
    rows = audit.get('candidates', []) if audit else []
    if not isinstance(rows, list):
        rows = []
    candidates = []
    for row in rows[:12]:
        if not isinstance(row, dict):
            continue
        moments = row.get('moments', [])
        if not isinstance(moments, list):
            moments = []
        safe_moments = []
        for m in moments[:3]:
            if not isinstance(m, dict):
                continue
            start = m.get('start_sec')
            seconds = m.get('preview_duration_sec', 5.0)
            if (type(start) in (int, float) and type(seconds) in (int, float)
                    and 0 <= start <= 240 and 0 < seconds <= 5.0):
                safe_moments.append({
                    'start_sec': round(float(start), 2),
                    'preview_duration_sec': round(float(seconds), 2),
                })
        candidates.append({
            'title': str(row.get('title', ''))[:300],
            'source_page': str(row.get('source_page', ''))[:1200],
            'license_metadata': str(row.get('license', ''))[:80],
            'author_metadata': str(row.get('author', ''))[:300],
            'width': row.get('width'),
            'height': row.get('height'),
            'preview_count': len(moments),
            'review_moments': safe_moments,
            'duration_sec': row.get('duration_sec'),
            'action_group_filename_hint': str(row.get('group', 'other'))[:80],
            'publication_approved': False,
        })
    raw = audit.get('raw_license_filtered_pool', 0) if audit else 0
    relevant = audit.get('cat_relevance_pool', 0) if audit else 0
    status = ('READY_FOR_MANUAL_QA' if candidates and result == 'success'
              else 'NO_QUALIFIED_PREVIEWS' if audit and not candidates and result == 'success'
              else 'WORKFLOW_ERROR_OR_MISSING_AUDIT')
    return {
        'schema_version': 1,
        'repository': repo,
        'workflow': '.github/workflows/top5.yml',
        'run_id': run_id,
        'run_number': run_number,
        'run_attempt': run_attempt,
        'workflow_build_result': result,
        'event': event,
        'review_status': status,
        'raw_cc_metadata_pool': raw,
        'cat_relevance_candidate_pool': relevant,
        'candidate_count': len(candidates),
        'preview_file_count': sum(c['preview_count'] for c in candidates),
        'license_and_content_human_review_complete': False,
        'approved_for_publication': False,
        'artifact_name': f'TOP5-shorts-review-{run_number}',
        'artifact_web_page': f'https://github.com/{repo}/actions/runs/{run_id}#artifacts',
        'candidates': candidates,
        'notice': ('Public metadata index only. Source video previews remain in '
                   'Actions artifact. Metadata licenses and motion scores do not '
                   'establish ownership, humor, or YouTube monetization eligibility.'),
    }


def write_index(manifest: dict[str, Any], directory: Path) -> bool:
    directory.mkdir(parents=True, exist_ok=True)
    latest = directory / 'latest.json'
    if latest.exists():
        try:
            existing = json.loads(latest.read_text(encoding='utf-8'))
            if int(existing.get('run_number', 0)) > manifest['run_number']:
                print('SKIP: newer workflow run already indexed')
                return False
            if (int(existing.get('run_number', 0)) == manifest['run_number']
                and int(existing.get('run_attempt', 0)) > manifest['run_attempt']):
                print('SKIP: newer attempt already indexed')
                return False
        except (ValueError, TypeError, json.JSONDecodeError):
            raise RuntimeError('Existing latest.json malformed; refuse overwrite')
    payload = json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'
    latest.write_text(payload, encoding='utf-8')
    runs = directory / 'runs'
    runs.mkdir(exist_ok=True)
    (runs / f"{manifest['run_id']}.json").write_text(payload, encoding='utf-8')
    # Human-editable template is regenerated only for the matching run.
    # Neither this template nor the source index authorizes publication.
    from v18_editorial_handoff import review_template
    editorial = json.dumps(review_template(manifest), ensure_ascii=False, indent=2) + '\n'
    (directory / 'latest_editorial_template.json').write_text(editorial, encoding='utf-8')
    templates = directory / 'templates'
    templates.mkdir(exist_ok=True)
    (templates / f"{manifest['run_id']}.json").write_text(editorial, encoding='utf-8')
    print(f"INDEXED: #{manifest['run_number']} run_id={manifest['run_id']} "
          f"candidate_count={manifest['candidate_count']}")
    return True


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--audit', default='output/V17_CANDIDATE_AUDIT.json')
    p.add_argument('--index-dir', default='review')
    p.add_argument('--repo', required=True)
    p.add_argument('--run-id', required=True, type=int)
    p.add_argument('--run-number', required=True, type=int)
    p.add_argument('--run-attempt', default=1, type=int)
    p.add_argument('--result', default='unknown')
    p.add_argument('--event', default='unknown')
    args = p.parse_args()
    f = Path(args.audit)
    audit = json.loads(f.read_text(encoding='utf-8')) if f.exists() else None
    manifest = manifest_from_audit(audit, repo=args.repo,
        run_id=args.run_id, run_number=args.run_number,
        run_attempt=args.run_attempt, result=args.result, event=args.event)
    write_index(manifest, Path(args.index_dir))


if __name__ == '__main__':
    main()
