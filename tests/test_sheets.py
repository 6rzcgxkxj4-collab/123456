import json
import pytest
from unittest.mock import Mock
from job_discovery.sheets import HEADERS, META, TAB, Sheets, plan, col
from job_discovery.rules import evaluate
from test_rules import job

NOW = '2026-10-18T01:00:00+00:00'


def candidate():
    j = job()
    evaluate(j)
    j.status = '在招（官方公开接口核实）'
    return j


def new_rows():
    headers = HEADERS + META
    result = plan([headers], [candidate()], NOW)
    return [headers] + result['appends']


def test_new_and_duplicate_idempotent():
    rows = new_rows()
    assert len(rows) == 2
    assert rows[1][HEADERS.index('申请状态')] == ''
    assert rows[1][HEADERS.index('固定年薪(万元)')] == '未知'
    assert plan(rows, [candidate()], NOW) == {'updates': [], 'appends': [], 'skipped': 0}


def test_manual_edits_permanently_released_and_application_never_written():
    rows = new_rows()
    rows[1][HEADERS.index('匹配理由')] = '手工备注'
    rows[1][HEADERS.index('申请状态')] = '已投递'
    result = plan(rows, [candidate()], NOW)
    assert len(result['updates']) == 1
    assert result['updates'][0]['range'] == "'岗位数据库'!S2"
    snapshot = json.loads(result['updates'][0]['values'][0][0])
    assert '匹配理由' not in snapshot and '申请状态' not in snapshot
    rows[1][-1] = result['updates'][0]['values'][0][0]
    assert plan(rows, [candidate()], NOW)['updates'] == []


def test_manual_and_ambiguous_rows_not_adopted():
    rows = new_rows()
    rows[1][-2:] = ['', '']
    assert plan(rows, [candidate()], NOW)['appends'] == []
    assert plan(rows, [candidate()], NOW)['updates'] == []
    rows = new_rows()
    rows.append(rows[1].copy())
    assert plan(rows, [candidate()], NOW)['skipped'] == 1


def test_tracking_parameters_and_same_title_dedup():
    j1, j2 = candidate(), candidate()
    j2.source_id = '2'
    j2.url += '?utm_source=linkedin'
    assert len(plan([HEADERS + META], [j1, j2], NOW)['appends']) == 1


def test_missing_headers_and_corrupt_metadata_fail_closed():
    with pytest.raises(ValueError):
        plan([HEADERS], [candidate()], NOW)
    with pytest.raises(ValueError):
        plan([HEADERS + META + ['公司']], [], NOW)
    rows = new_rows()
    rows[1][-1] = 'bad json'
    assert plan(rows, [candidate()], NOW)['updates'] == []


def test_dry_run_no_writes_and_concurrent_edit_aborts():
    sheets = Sheets.__new__(Sheets)
    sheets.read = Mock(return_value=[HEADERS + META])
    sheets.request = Mock()
    assert sheets.sync([candidate()])['new_rows'] == 1
    sheets.request.assert_not_called()
    sheets.read.side_effect = [[HEADERS + META], new_rows()]
    with pytest.raises(RuntimeError):
        sheets.sync([candidate()], write=True)
    sheets.request.assert_not_called()


def test_write_is_raw_append_only_target():
    sheets = Sheets.__new__(Sheets)
    sheets.read = Mock(return_value=[HEADERS + META])
    sheets.request = Mock(return_value={})
    result = sheets.sync([candidate()], write=True)
    assert result['written']
    args, kwargs = sheets.request.call_args
    assert args[1] == f"/values/'{TAB}'!A:S:append"
    assert kwargs['params'] == {'valueInputOption': 'RAW', 'insertDataOption': 'INSERT_ROWS'}


def test_formula_and_initialize_safety():
    sheets = Sheets.__new__(Sheets)
    sheets.read = Mock(return_value=[HEADERS, [''] * (len(HEADERS) + 1)])
    sheets.request = Mock()
    with pytest.raises(ValueError):
        sheets.initialize(write=True)
    sheets.request.assert_not_called()
    rows = new_rows()
    rows[1][HEADERS.index('匹配度')] = '=1+1'
    updates = plan(rows, [candidate()], NOW)['updates']
    assert all(u['range'] != "'岗位数据库'!I2" for u in updates)


def test_column_conversion():
    assert col(1) == 'A' and col(26) == 'Z' and col(27) == 'AA'


def test_absence_is_pending_and_failed_sources_do_not_change_rows():
    rows = new_rows()
    result = plan(rows, [], NOW, observed_keys=set(), successful_sources={'greenhouse:example'})
    assert result['updates'][0]['values'][0][0].startswith('待核实')
    assert '未确认关闭' in result['updates'][0]['values'][0][0]
    assert plan(rows, [], NOW, observed_keys=set(), successful_sources=set())['updates'] == []
    rows[1][HEADERS.index('招聘状态')] = '已关闭（人工核实）'
    result = plan(rows, [], NOW, observed_keys=set(), successful_sources={'greenhouse:example'})
    assert len(result['updates']) == 1 and result['updates'][0]['range'].endswith('S2')


def test_get_retries_but_append_does_not(monkeypatch):
    from job_discovery import sheets as module
    monkeypatch.setattr(module.time, 'sleep', Mock())
    sheets = Sheets.__new__(Sheets)
    sheets.base = 'https://sheets.googleapis.com/v4/spreadsheets/example'
    sheets.client = Mock()
    error = Mock(ok=False, status_code=429, headers={'Retry-After': '1'})
    success = Mock(ok=True, status_code=200)
    success.json.return_value = {'values': []}
    sheets.client.request.side_effect = [error, success]
    assert sheets.request('GET', "/values/'岗位数据库'") == {'values': []}
    assert sheets.client.request.call_count == 2
    sheets.client.request.reset_mock()
    sheets.client.request.side_effect = [error]
    with pytest.raises(RuntimeError):
        sheets.request('POST', '/values/append')
    assert sheets.client.request.call_count == 1


def test_initialization_writes_only_two_target_headers():
    sheets = Sheets.__new__(Sheets)
    sheets.read = Mock(return_value=[HEADERS])
    sheets.request = Mock()
    assert sheets.initialize() == META
    sheets.request.assert_not_called()
    assert sheets.initialize(write=True) == META
    args, kwargs = sheets.request.call_args
    assert args == ('PUT', "/values/'岗位数据库'!R1:S1")
    assert kwargs['json'] == {'values': [META]}
