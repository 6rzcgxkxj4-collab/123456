import base64
import hashlib
import hmac
import json
from unittest.mock import Mock
import pytest
import requests
from job_discovery.sheets import Sheets, WebAppError, envelope, job_values
from test_rules import job

SECRET = 'test-key-only-never-use-in-production-12345'
URL = 'https://script.google.com/macros/s/deployment_123/exec'


def response(data=None, status=200, location=None):
    result = Mock(status_code=status, headers={'Location': location} if location else {})
    result.json.return_value = data
    return result


def setup(monkeypatch):
    monkeypatch.setenv('APPS_SCRIPT_WEB_APP_URL', URL)
    monkeypatch.setenv('APPS_SCRIPT_SHARED_SECRET', SECRET)
    result = Sheets()
    result.client = Mock()
    return result


def test_signature_signs_exact_utf8_payload():
    encoded = envelope({'text': '上海岗位'}, SECRET, timestamp=1700000000, request_id='aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')
    env = json.loads(encoded)
    message = f"v1\n{env['timestamp']}\n{env['request_id']}\n{env['payload_b64']}"
    assert hmac.compare_digest(env['signature'], hmac.new(SECRET.encode(), message.encode(), hashlib.sha256).hexdigest())
    assert json.loads(base64.b64decode(env['payload_b64'])) == {'text': '上海岗位'}
    assert SECRET not in encoded


def test_cross_language_fixture_matches_current_python_signer():
    from pathlib import Path
    fixture = json.loads(Path('tests/fixtures/signed_preview.json').read_text())
    signed = fixture['envelope']
    payload = json.loads(base64.b64decode(signed['payload_b64']))
    assert json.loads(envelope(payload, fixture['secret'], timestamp=signed['timestamp'], request_id=signed['request_id'])) == signed


def test_redirect_get_only_and_no_header_auth(monkeypatch):
    s = setup(monkeypatch)
    def post(url, **kwargs):
        request_id = json.loads(kwargs['data'])['request_id']
        s.client.get.return_value = response({'ok': True, 'request_id': request_id})
        assert url == URL and '?' not in url
        assert kwargs['headers'] == {'Content-Type': 'text/plain; charset=utf-8'}
        return response(status=302, location='https://script.googleusercontent.com/macros/echo?result=x')
    s.client.post.side_effect = post
    assert s.call({'operation': 'preview'})['ok']
    args, kwargs = s.client.get.call_args
    assert 'data' not in kwargs and 'headers' not in kwargs and kwargs['allow_redirects'] is False


@pytest.mark.parametrize('location', ['https://evil.example/steal', 'http://script.googleusercontent.com/x', 'https://script.google.com/accounts/login', 'https://script.googleusercontent.com.evil/x'])
def test_reject_untrusted_redirect(monkeypatch, location):
    s = setup(monkeypatch)
    s.client.post.return_value = response(status=302, location=location)
    with pytest.raises(WebAppError, match='unsafe_redirect'):
        s.call({})
    s.client.get.assert_not_called()


def test_retry_reuses_exact_signed_envelope(monkeypatch):
    s = setup(monkeypatch)
    monkeypatch.setattr('job_discovery.sheets.time.sleep', Mock())
    count = 0
    def post(url, **kwargs):
        nonlocal count
        count += 1
        if count == 1:
            raise requests.Timeout('ambiguous write result')
        return response({'ok': True, 'request_id': json.loads(kwargs['data'])['request_id']})
    s.client.post.side_effect = post
    assert s.call({'operation': 'write'})['ok']
    assert s.client.post.call_args_list[0] == s.client.post.call_args_list[1]


def test_application_errors_even_with_http_200(monkeypatch):
    s = setup(monkeypatch)
    s.client.post.return_value = response({'ok': False, 'code': 'writes_disabled'})
    with pytest.raises(WebAppError, match='writes_disabled'):
        s.call({})
    s.client.post.return_value = response({'ok': True, 'request_id': 'wrong'})
    with pytest.raises(WebAppError, match='response_id_mismatch'):
        s.call({})


def test_non_json_is_not_success(monkeypatch):
    s = setup(monkeypatch)
    s.client.post.return_value.json.side_effect = ValueError('HTML login page')
    s.client.post.return_value.status_code = 200
    with pytest.raises(WebAppError, match='web_app_non_json'):
        s.call({})


def test_no_url_secrets_or_short_keys(monkeypatch):
    s = setup(monkeypatch)
    monkeypatch.setenv('APPS_SCRIPT_WEB_APP_URL', URL + '?key=secret')
    with pytest.raises(ValueError):
        Sheets()
    with pytest.raises(ValueError):
        envelope({}, 'short')
    with pytest.raises(ValueError):
        envelope({'x': 'a' * 1500000}, SECRET)


def test_write_requires_successful_preview_and_gate(monkeypatch):
    s = setup(monkeypatch)
    summary = {'new_rows': 1, 'cell_updates': 0, 'metadata_updates': 0, 'skipped': 0, 'written': False, 'preview_token': 'token'}
    s.call = Mock(return_value=summary)
    assert not s.sync([job()])['written']
    assert s.call.call_count == 1 and s.call.call_args.args[0]['operation'] == 'preview'
    with pytest.raises(WebAppError, match='writes_disabled'):
        s.sync([job()], write=True)
    monkeypatch.setenv('ENABLE_SHEETS_WRITE', 'true')
    s.call.reset_mock()
    s.call.side_effect = [summary, summary | {'written': True}]
    assert s.sync([job()], write=True)['written']
    preview, write = [c.args[0] for c in s.call.call_args_list]
    assert write['batch'] == preview['batch']
    assert write['preview_token'] == 'token' and write['operation'] == 'write'


def test_job_values_exclude_application_and_unknown_salary():
    values = job_values(job(), '2026-10-18T09:17:00+08:00')
    assert len(values) == 16 and '申请状态' not in values
    assert values['固定年薪(万元)'] == '未知'
