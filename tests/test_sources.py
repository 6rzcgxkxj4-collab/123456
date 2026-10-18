from unittest.mock import Mock
import pytest
import requests
from job_discovery.sources import fetch, verify
from job_discovery.http import session
from test_rules import job


def client(data):
    result = Mock()
    result.get.return_value.json.return_value = data
    return result


def test_greenhouse_updated_not_published_and_html_decoding():
    c = client({'jobs': [{'id': 1, 'title': 'Marketing', 'location': {'name': 'Shanghai'},
                         'absolute_url': 'https://example.com/1', 'updated_at': '2026-10-18', 'content': '<p>Events &amp; MarCom</p>'}]})
    result = fetch(c, {'provider': 'greenhouse', 'board': 'example', 'company': 'Example'})[0]
    assert not result.published
    assert result.description == 'Events & MarCom'


def test_lever_salary_and_posting_date():
    c = client([{'id': 'a', 'text': 'Marketing', 'categories': {'location': 'Shanghai'},
                 'hostedUrl': 'https://example.com/1', 'createdAt': 1700000000000,
                 'salaryRange': {'min': 100, 'max': 200, 'currency': 'CNY', 'interval': 'year'}}])
    result = fetch(c, {'provider': 'lever', 'board': 'example', 'company': 'Example'})[0]
    assert result.salary_max == 200 and result.published.startswith('2023')


def test_ashby_unlisted_excluded():
    c = client({'jobs': [{'isListed': False}, {'id': 'a', 'title': 'Marketing', 'location': 'Shanghai',
                                           'jobUrl': 'https://example.com/1', 'descriptionPlain': 'Events'}]})
    assert len(fetch(c, {'provider': 'ashby', 'board': 'example', 'company': 'Example'})) == 1


def test_failed_verification_is_pending_not_closed():
    c = Mock()
    c.get.side_effect = requests.HTTPError('404')
    assert verify(c, job()) == '待核实'
    assert verify(client({'id': 1, 'absolute_url': 'https://example.com/jobs/1'}), job()).startswith('在招')


def test_invalid_board_and_retry_only_reads():
    with pytest.raises(ValueError):
        fetch(Mock(), {'provider': 'greenhouse', 'board': '../private', 'company': 'Example'})
    retry = session().get_adapter('https://').max_retries
    assert retry.total == 3 and retry.allowed_methods == frozenset(['GET'])
