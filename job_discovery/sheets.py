"""Signed Apps Script transport. No Google Cloud account or service account."""
import base64
import hashlib
import hmac
import json
import os
import re
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
import requests
from .model import fingerprint

SHEET_ID = '1z-zzj5IWsQXTjDL7QV8OYF2_Do_NSJdslh39G2RVHds'
TAB = '岗位数据库'
HEADERS = ['岗位ID', '公司', '岗位名称', '城市', '企业类型', '岗位方向', '固定年薪(万元)', '薪资公开状态', '匹配度', '招聘状态', '申请状态', '岗位链接', '来源', '发现日期', '最后核实', '匹配理由', '待确认问题']


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



def envelope(payload, secret, timestamp=None, request_id=None):
    if not re.fullmatch(r'[\x20-\x7E]{32,}', secret):
        raise ValueError('Shared secret must be at least 32 ASCII characters')
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
    body = base64.b64encode(raw).decode('ascii')
    stamp = int(time.time()) if timestamp is None else timestamp
    nonce = str(uuid.uuid4()) if request_id is None else request_id
    message = f'v1\n{stamp}\n{nonce}\n{body}'
    signature = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    result = {'version': 1, 'timestamp': stamp, 'request_id': nonce, 'payload_b64': body, 'signature': signature}
    encoded = json.dumps(result, separators=(',', ':'))
    if len(encoded.encode()) > 1500000:
        raise ValueError('Batch too large; no requests sent')
    return encoded


class WebAppError(RuntimeError):
    """Only a safe fixed code may be surfaced in logs."""


class Sheets:
    def __init__(self):
        self.url = os.environ['APPS_SCRIPT_WEB_APP_URL']
        if not re.fullmatch(r'https://script\.google\.com/macros/s/[A-Za-z0-9_-]+/exec', self.url):
            raise ValueError('Use the deployed HTTPS /exec URL without query parameters')
        self.secret = os.environ['APPS_SCRIPT_SHARED_SECRET']
        if not re.fullmatch(r'[\x20-\x7E]{32,}', self.secret):
            raise ValueError('Shared secret must be at least 32 ASCII characters')
        self.client = requests.Session()

    def call(self, payload):
        # Retries reuse exactly the same signed ID: server persists a nonce before
        # processing and caches the result. Ambiguous writes are never re-executed.
        body = envelope(payload, self.secret)
        for attempt in range(3):
            try:
                response = self.client.post(self.url, data=body.encode(),
                    headers={'Content-Type': 'text/plain; charset=utf-8'},
                    timeout=(10, 90), allow_redirects=False)
                if response.status_code in {302, 303}:
                    target = response.headers.get('Location', '')
                    parsed = urlsplit(target)
                    if (parsed.scheme != 'https' or parsed.hostname != 'script.googleusercontent.com'
                            or parsed.username or parsed.password or parsed.port not in (None, 443)):
                        raise WebAppError('unsafe_redirect')
                    # ContentService redirects are GET-only; never forward the signed
                    # POST body or secret to a redirect destination.
                    response = self.client.get(target, timeout=(10, 90), allow_redirects=False)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                if response.status_code != 200:
                    raise WebAppError('web_app_http_error')
                try:
                    result = response.json()
                except ValueError:
                    raise WebAppError('web_app_non_json') from None
                if not isinstance(result, dict) or result.get('ok') is not True:
                    code = result.get('code', '') if isinstance(result, dict) else ''
                    allowed = {'auth_failed', 'bad_request', 'writes_disabled', 'preview_required',
                        'preview_expired', 'sheet_changed', 'invalid_batch', 'invalid_headers',
                        'busy', 'replay_conflict', 'request_in_progress', 'capacity', 'internal_error'}
                    raise WebAppError(code if code in allowed else 'web_app_rejected')
                if result.get('request_id') != json.loads(body)['request_id']:
                    raise WebAppError('response_id_mismatch')
                return result
            except requests.RequestException:
                if attempt == 2:
                    raise WebAppError('web_app_network_error') from None
                time.sleep(2 ** attempt)
        raise WebAppError('web_app_unavailable')

    def sync(self, jobs, write=False, observed_keys=None, successful_sources=None):
        now = datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
        batch = {'jobs': [{'source_key': job.key, 'values': job_values(job, now)} for job in jobs],
                 'observed_keys': sorted(observed_keys or []),
                 'successful_sources': sorted(successful_sources or []), 'source_failures': []}
        preview = self.call({'operation': 'preview', 'batch': batch})
        if not write:
            return {k: preview[k] for k in ('new_rows', 'cell_updates', 'metadata_updates', 'skipped', 'written')}
        if os.environ.get('ENABLE_SHEETS_WRITE') != 'true':
            raise WebAppError('writes_disabled')
        result = self.call({'operation': 'write', 'batch': batch, 'preview_token': preview['preview_token']})
        return {k: result[k] for k in ('new_rows', 'cell_updates', 'metadata_updates', 'skipped', 'written')}
