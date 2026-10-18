"""Restricted single-tab writes, RAW values, no deletion and no bulk replacement.

The API has no compare-and-swap: avoid editing the tab during a write run.
Detected human changes are permanently released from automated ownership.
"""
import json
import os
import time
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
from datetime import datetime, timezone
import google.auth.transport.requests
from google.oauth2 import service_account
from .model import canonical_url, fingerprint

SHEET_ID = '1z-zzj5IWsQXTjDL7QV8OYF2_Do_NSJdslh39G2RVHds'
TAB = '岗位数据库'
HEADERS = ['岗位ID', '公司', '岗位名称', '城市', '企业类型', '岗位方向', '固定年薪(万元)', '薪资公开状态', '匹配度', '招聘状态', '申请状态', '岗位链接', '来源', '发现日期', '最后核实', '匹配理由', '待确认问题']
META = ['自动化来源ID', '自动化快照']


def col(index):
    result = ''
    while index:
        index, n = divmod(index - 1, 26)
        result = chr(65 + n) + result
    return result


def get(row, headers, name):
    i = headers.index(name)
    return str(row[i]) if i < len(row) else ''


def identities(row, headers):
    keys = set()
    url = get(row, headers, '岗位链接')
    if url:
        try:
            keys.add(('url', canonical_url(url)))
        except ValueError:
            pass
    fields = [get(row, headers, x) for x in ['公司', '岗位名称', '城市']]
    if all(fields):
        keys.add(('fingerprint', fingerprint(*fields)))
    if META[0] in headers:
        source = get(row, headers, META[0])
        if source:
            keys.add(('source', source))
    return keys


def job_values(job, now):
    return {
        '岗位ID': 'AUTO-' + fingerprint(job.company, job.title, job.city)[:20],
        '公司': job.company, '岗位名称': job.title, '城市': job.city,
        '企业类型': '企业官方源；企业背景待人工确认', '岗位方向': job.title,
        # Public total/OTE ranges must not be represented as fixed base salary.
        '固定年薪(万元)': '未知',
        '薪资公开状态': '未公开' if job.salary == '未知' else '已公开（固定构成待核实）',
        '匹配度': f'规则分 {job.score}（非概率）', '招聘状态': job.status,
        '岗位链接': job.url, '来源': f'{job.provider}/{job.board}',
        '发现日期': now[:10], '最后核实': now if job.status != '待核实' else '',
        '匹配理由': job.reason,
        '待确认问题': f'固定年薪目标35–40万元、底线30万元；公开薪资：{job.salary}；发布日期：{job.published or "未知"}；语言/年限/工作地点及公司成熟度需人工确认',
    }


def validate_headers(headers):
    if len(headers) != len(set(headers)) or any(not h for h in headers):
        raise ValueError('Blank or duplicate headers; refusing writes')
    missing = set(HEADERS) - set(headers)
    if missing:
        raise ValueError('Missing required headers: ' + ', '.join(sorted(missing)))


def plan(rows, jobs, now, observed_keys=None, successful_sources=None):
    if not rows:
        raise ValueError('Target worksheet must already contain its headers')
    headers = rows[0]
    validate_headers(headers)
    if any(x not in headers for x in META):
        raise ValueError('Automation columns missing; initialize them explicitly first')
    index = {}
    for n, row in enumerate(rows[1:], 2):
        for key in identities(row, headers):
            index.setdefault(key, set()).add(n)
    updates, appends = [], []
    skipped = 0
    seen = set()
    for job in jobs:
        keys = {('source', job.key), ('url', canonical_url(job.url)), ('fingerprint', fingerprint(job.company, job.title, job.city))}
        if keys & seen:
            skipped += 1
            continue
        seen |= keys
        matches = set().union(*(index.get(key, set()) for key in keys))
        values = job_values(job, now)
        if matches:
            if len(matches) != 1:
                skipped += 1
                continue
            n = next(iter(matches))
            old = rows[n - 1]
            # Manual rows are not adopted, even if their URL matches exactly.
            if get(old, headers, META[0]) != job.key:
                skipped += 1
                continue
            try:
                snapshot = json.loads(get(old, headers, META[1]))
                if not isinstance(snapshot, dict) or any(k not in HEADERS or k == '申请状态' or not isinstance(v, str) for k, v in snapshot.items()):
                    raise ValueError('Invalid snapshot')
            except (ValueError, TypeError):
                skipped += 1
                continue
            next_snapshot = {}
            for name, previous in snapshot.items():
                current = get(old, headers, name)
                if current != previous:
                    continue  # Human edit: permanently relinquish this field.
                value = values.get(name, previous)
                if name in {'发现日期', '岗位ID'}:
                    value = previous
                if name == '最后核实' and job.status == '待核实':
                    value = previous
                next_snapshot[name] = value
                if current != value:
                    updates.append({'range': f"'{TAB}'!{col(headers.index(name)+1)}{n}", 'values': [[value]]})
            encoded = json.dumps(next_snapshot, ensure_ascii=False, sort_keys=True)
            if encoded != get(old, headers, META[1]):
                updates.append({'range': f"'{TAB}'!{col(headers.index(META[1])+1)}{n}", 'values': [[encoded]]})
        else:
            record = values | {META[0]: job.key, META[1]: json.dumps(values, ensure_ascii=False, sort_keys=True)}
            appends.append([record.get(h, '') for h in headers])
    # Check previously discovered jobs even when they disappear from the feed.
    # Absence can mean a location change or unpublished record, not confirmed closure.
    for n, row in enumerate(rows[1:], 2):
        source_key = get(row, headers, META[0])
        if (observed_keys is None or not successful_sources or not source_key or
                source_key in observed_keys or source_key.rsplit(':', 1)[0] not in successful_sources):
            continue
        try:
            snapshot = json.loads(get(row, headers, META[1]))
            if not isinstance(snapshot, dict):
                continue
        except (ValueError, TypeError):
            continue
        name = '招聘状态'
        if name not in snapshot:
            continue
        current = get(row, headers, name)
        if current != snapshot[name]:
            del snapshot[name]
        else:
            pending = '待核实（本次官方列表未出现；未确认关闭）'
            if current == pending:
                continue
            updates.append({'range': f"'{TAB}'!{col(headers.index(name)+1)}{n}", 'values': [[pending]]})
            snapshot[name] = pending
        updates.append({'range': f"'{TAB}'!{col(headers.index(META[1])+1)}{n}", 'values': [[json.dumps(snapshot, ensure_ascii=False, sort_keys=True)]]})
    return {'updates': updates, 'appends': appends, 'skipped': skipped}


class Sheets:
    def __init__(self):
        # No credential values or API response bodies are logged.
        info = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT_JSON'])
        credentials = service_account.Credentials.from_service_account_info(info, scopes=['https://www.googleapis.com/auth/spreadsheets'])
        self.client = google.auth.transport.requests.AuthorizedSession(credentials)
        self.base = f'https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}'

    def request(self, method, suffix, **kwargs):
        for attempt in range(4):
            try:
                response = self.client.request(method, self.base + suffix, timeout=(10, 45), **kwargs)
            except OSError:
                if method != 'GET' or attempt == 3:
                    raise
                time.sleep(2 ** attempt)
                continue
            if method != 'GET' or response.status_code not in {429, 500, 502, 503, 504} or attempt == 3:
                break
            delay = 2 ** attempt
            retry_after = response.headers.get('Retry-After', '')
            if retry_after:
                try:
                    delay = max(delay, float(retry_after))
                except ValueError:
                    try:
                        delay = max(delay, (parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds())
                    except (ValueError, TypeError):
                        pass
            # Long quota waits should be retried by the next scheduled run.
            if delay > 60:
                raise RuntimeError('Sheets read rate-limited; retry on a later run')
            time.sleep(delay)
        if not response.ok:
            # POST append must not be blindly retried after ambiguous failures.
            raise RuntimeError(f'Sheets {method} failed (HTTP {response.status_code}); rerun after inspection')
        return response.json()

    def read(self):
        # FORMULA preserves manually entered formulas for conflict detection.
        return self.request('GET', f"/values/'{TAB}'", params={'valueRenderOption': 'FORMULA'}) .get('values', [])

    def initialize(self, write=False):
        rows = self.read()
        if not rows:
            raise ValueError('Missing existing target headers')
        validate_headers(rows[0])
        missing = [h for h in META if h not in rows[0]]
        if not missing:
            return []
        # Do not write into an existing data column with a blank header.
        if any(len(r) > len(rows[0]) for r in rows[1:]):
            raise ValueError('Data exists beyond headers; refusing initialization')
        if write:
            if self.read() != rows:
                raise RuntimeError('Worksheet changed during preflight')
            start, end = len(rows[0]) + 1, len(rows[0]) + len(missing)
            self.request('PUT', f"/values/'{TAB}'!{col(start)}1:{col(end)}1", params={'valueInputOption': 'RAW'}, json={'values': [missing]})
        return missing

    def sync(self, jobs, write=False, observed_keys=None, successful_sources=None):
        before = self.read()
        result = plan(before, jobs, datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(), observed_keys, successful_sources)
        if write:
            if self.read() != before:
                raise RuntimeError('Worksheet changed during preflight; no job writes performed')
            if result['updates']:
                self.request('POST', '/values:batchUpdate', json={'valueInputOption': 'RAW', 'data': result['updates']})
            if result['appends']:
                # INSERT_ROWS preserves existing rows and all other worksheets.
                self.request('POST', f"/values/'{TAB}'!A:{col(len(before[0]))}:append", params={'valueInputOption': 'RAW', 'insertDataOption': 'INSERT_ROWS'}, json={'values': result['appends']})
        return {'new_rows': len(result['appends']), 'cell_updates': len(result['updates']), 'skipped': result['skipped'], 'written': write}
