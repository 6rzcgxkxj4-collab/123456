import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from .http import session
from .sources import fetch, verify
from .rules import evaluate
from .model import canonical_url, fingerprint
from .sheets import Sheets

LOG = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sources', default='config/sources.json')
    parser.add_argument('--output', default='reports/latest.json')
    parser.add_argument('--sheets', action='store_true', help='Read-only Sheets preflight unless --write is supplied')
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--initialize-columns', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if args.write and (not args.sheets or os.environ.get('ENABLE_SHEETS_WRITE') != 'true'):
        parser.error('--write requires --sheets and ENABLE_SHEETS_WRITE=true')
    sources = json.loads(Path(args.sources).read_text())['sources']
    client = session()
    matches, failures, stats, rejected, seen = [], [], [], Counter(), set()
    observed_keys, successful_sources = set(), set()
    enabled = [s for s in sources if s.get('enabled', True)]
    if not enabled:
        raise ValueError('At least one enabled source is required')
    for source in enabled:
        label = f"{source['provider']}/{source['board']}"
        try:
            jobs = fetch(client, source)
        except Exception as exc:
            LOG.error('Source failed: %s (%s)', label, type(exc).__name__)
            failures.append(label)
            continue
        observed_keys.update(j.key for j in jobs)
        successful_sources.add(f"{source['provider']}:{source['board']}")
        count = 0
        for job in jobs:
            accepted, reason = evaluate(job)
            if not accepted:
                rejected[reason] += 1
                continue
            keys = {('source', job.key), ('url', canonical_url(job.url)), ('fp', fingerprint(job.company, job.title, job.city))}
            if seen & keys:
                continue
            seen |= keys
            job.status = verify(client, job)
            matches.append(job)
            count += 1
        stats.append({'source': label, 'listed': len(jobs), 'matched': count})
        LOG.info('%s: listed=%d matched=%d', label, len(jobs), count)
    matches.sort(key=lambda j: (-j.score, j.key))
    report = {'run_at': datetime.now(timezone.utc).isoformat(), 'mode': 'write' if args.write else 'dry-run',
              'sources': stats, 'source_failures': failures, 'rejected': dict(rejected),
              'jobs': [j.to_dict() for j in matches], 'sheets': 'not accessed'}
    exit_code = 1 if failures else 0
    if args.sheets:
        try:
            if failures and args.write:
                raise RuntimeError('Partial source failure: all sheet writes blocked for this run')
            sheet = Sheets()
            missing = sheet.initialize(write=args.write and args.initialize_columns)
            if missing and not (args.write and args.initialize_columns):
                report['sheets'] = {'blocked': 'Missing automation columns', 'required_columns': missing}
                exit_code = 2
            else:
                report['sheets'] = sheet.sync(matches, write=args.write, observed_keys=observed_keys, successful_sources=successful_sources)
        except Exception as exc:
            # Credentials and server response bodies must never reach logs/artifacts.
            LOG.error('Sheets preflight/write failed (%s)', type(exc).__name__)
            report['sheets'] = {'error_type': type(exc).__name__}
            exit_code = 2
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    LOG.info('Report saved: %s; matches=%d; source_failures=%d', path, len(matches), len(failures))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
