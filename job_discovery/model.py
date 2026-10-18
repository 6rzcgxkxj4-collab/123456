from dataclasses import dataclass, asdict
from hashlib import sha256
import html
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode


def plain(value):
    decoded = html.unescape(html.unescape(str(value or '')))
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', decoded)).strip()


def normalize(value):
    return re.sub(r'[^\w\u4e00-\u9fff]', '', plain(value).casefold())


def canonical_url(value):
    p = urlsplit(value)
    if p.scheme != 'https' or not p.hostname or p.username or p.password:
        raise ValueError('Job URL must be public HTTPS without credentials')
    query = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in {'source', 'ref', 'gh_src', 'lever-source'}]
    return urlunsplit(('https', p.netloc.lower(), p.path.rstrip('/'), urlencode(sorted(query)), ''))


def fingerprint(company, title, city):
    return sha256('|'.join(normalize(x) for x in (company, title, city)).encode()).hexdigest()


@dataclass
class Job:
    provider: str
    board: str
    source_id: str
    company: str
    title: str
    location: str
    url: str
    description: str
    published: str = ''
    salary: str = '未知'
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = ''
    salary_interval: str = ''
    city: str = ''
    status: str = '待核实'
    reason: str = ''
    score: int = 0

    @property
    def key(self):
        return f'{self.provider}:{self.board}:{self.source_id}'

    def to_dict(self):
        return asdict(self) | {'key': self.key}
