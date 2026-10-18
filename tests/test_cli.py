import json
from unittest.mock import Mock
from job_discovery import cli
from test_rules import job


def test_end_to_end_dry_run(tmp_path, monkeypatch):
    output = tmp_path / 'report.json'
    monkeypatch.setattr('sys.argv', ['cli', '--output', str(output)])
    monkeypatch.setattr(cli, 'fetch', lambda client, source: [job(board=source['board'])])
    monkeypatch.setattr(cli, 'verify', lambda client, job: '待核实')
    sheets = Mock()
    monkeypatch.setattr(cli, 'Sheets', sheets)
    assert cli.main() == 0
    report = json.loads(output.read_text())
    assert report['mode'] == 'dry-run' and len(report['jobs']) == 1
    assert report['jobs'][0]['salary'] == '未知'
    sheets.assert_not_called()


def test_failed_source_blocks_all_writes(tmp_path, monkeypatch):
    output = tmp_path / 'report.json'
    monkeypatch.setattr('sys.argv', ['cli', '--sheets', '--write', '--output', str(output)])
    monkeypatch.setenv('ENABLE_SHEETS_WRITE', 'true')
    def failed(*args):
        raise OSError('not available')
    monkeypatch.setattr(cli, 'fetch', failed)
    sheets = Mock()
    monkeypatch.setattr(cli, 'Sheets', sheets)
    assert cli.main() == 2
    sheets.assert_not_called()
    assert json.loads(output.read_text())['source_failures']


def test_write_needs_two_explicit_switches(monkeypatch):
    import pytest
    monkeypatch.setattr('sys.argv', ['cli', '--write', '--sheets'])
    monkeypatch.delenv('ENABLE_SHEETS_WRITE', raising=False)
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2
