"""Only documented public job-list endpoints. No HTML crawling or login bypass."""
import re
from datetime import datetime, timezone
from .http import get_json
from .model import Job, plain, canonical_url


def timestamp(value, milliseconds=False):
    if not value:
        return ''
    if milliseconds:
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
    return str(value)


def fetch(client, source):
    provider, board = source['provider'], source['board']
    if not re.fullmatch(r'[A-Za-z0-9_-]+', board):
        raise ValueError('Invalid board identifier')
    if provider == 'greenhouse':
        data = get_json(client, f'https://boards-api.greenhouse.io/v1/boards/{board}/jobs', params={'content': 'true'})
        records = data['jobs']
    elif provider == 'lever':
        records = []
        previous_ids = set()
        for offset in range(0, 10000, 100):
            page = get_json(client, f'https://api.lever.co/v0/postings/{board}', params={'mode': 'json', 'limit': 100, 'skip': offset})
            if not isinstance(page, list):
                raise ValueError('Unexpected Lever schema')
            ids = {str(item['id']) for item in page}
            if ids & previous_ids:
                raise ValueError('Repeated Lever page; refusing incomplete results')
            previous_ids |= ids
            records.extend(page)
            if len(page) < 100:
                break
        else:
            raise ValueError('Lever pagination limit exceeded')
    elif provider == 'ashby':
        data = get_json(client, f'https://api.ashbyhq.com/posting-api/job-board/{board}', params={'includeCompensation': 'true'})
        records = data['jobs']
    else:
        raise ValueError(f'Unsupported provider: {provider}')
    if not isinstance(records, list):
        raise ValueError('Unexpected job listing schema')
    jobs = []
    for item in records:
        if provider == 'greenhouse':
            # updated_at is NOT a publication date.
            job = Job(provider, board, str(item['id']), source['company'], plain(item['title']),
                      plain(item['location']['name']), canonical_url(item['absolute_url']), plain(item.get('content')))
        elif provider == 'lever':
            categories = item.get('categories') or {}
            locations = categories.get('allLocations') or [categories.get('location', '')]
            details = item.get('descriptionPlain', '') + ' ' + item.get('additionalPlain', '')
            details += ' ' + ' '.join(plain(x.get('content', '')) for x in item.get('lists', []))
            job = Job(provider, board, str(item['id']), source['company'], plain(item['text']),
                      plain(', '.join(locations)), canonical_url(item['hostedUrl']), plain(details), timestamp(item.get('createdAt'), True))
            salary = item.get('salaryRange') or {}
            if salary:
                job.salary_min, job.salary_max = salary.get('min'), salary.get('max')
                job.salary_currency, job.salary_interval = salary.get('currency', ''), salary.get('interval', '')
                job.salary = f"{job.salary_currency} {job.salary_min}–{job.salary_max} / {job.salary_interval}"
        else:
            if item.get('isListed') is False:
                continue
            job = Job(provider, board, str(item['id']), source['company'], plain(item['title']),
                      plain(', '.join([item.get('location', '')] + [x.get('location', '') for x in item.get('secondaryLocations', [])])),
                      canonical_url(item['jobUrl']), plain(item.get('descriptionPlain') or item.get('descriptionHtml')),
                      timestamp(item.get('publishedAt')))
            compensation = item.get('compensation') or {}
            if compensation.get('compensationTierSummary'):
                job.salary = plain(compensation['compensationTierSummary'])
        jobs.append(job)
    return jobs


def verify(client, job):
    """A successful authoritative detail lookup is evidence of an active listing.

    Unknown failures remain unverified; 404 alone never marks a stored job closed.
    Listing absence is NOT sufficient evidence of closure.
    """
    try:
        if job.provider == 'greenhouse':
            data = get_json(client, f'https://boards-api.greenhouse.io/v1/boards/{job.board}/jobs/{job.source_id}')
            if str(data.get('id')) == job.source_id and canonical_url(data['absolute_url']) == job.url:
                return '在招（官方公开接口核实）'
        elif job.provider == 'lever':
            data = get_json(client, f'https://api.lever.co/v0/postings/{job.board}/{job.source_id}', params={'mode': 'json'})
            if str(data.get('id')) == job.source_id and canonical_url(data['hostedUrl']) == job.url:
                return '在招（官方公开接口核实）'
        # Ashby public board has no public detail API; complete board membership
        # is authoritative listing evidence, but is not individual page verification.
        elif job.provider == 'ashby':
            return '在招（官方公开列表核实；详情页待核实）'
    except (ValueError, KeyError, TypeError, OSError) as exc:
        import logging
        logging.getLogger(__name__).warning('Verification failed: %s (%s)', job.key, type(exc).__name__)
    return '待核实'
