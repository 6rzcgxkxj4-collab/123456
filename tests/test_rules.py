import pytest
from job_discovery.model import Job, canonical_url
from job_discovery.rules import evaluate


def job(**kwargs):
    return Job(**({'provider': 'greenhouse', 'board': 'example', 'source_id': '1', 'company': 'Example',
                  'title': 'APAC Marketing Communications Manager', 'location': 'Shanghai, China',
                  'url': 'https://example.com/jobs/1', 'description': '4 years experience. International events and channel marketing.'} | kwargs))


def test_good_match_and_unknown_salary():
    j = job()
    assert evaluate(j)[0]
    assert j.city == '上海' and j.salary == '未知'
    assert '国际B2B' in j.reason


@pytest.mark.parametrize('title', ['Sales Manager', 'Marketing Director', 'Performance Marketing Manager', 'Head of Marketing', 'Business Development Marketing Manager'])
def test_excluded_title(title):
    assert not evaluate(job(title=title))[0]


@pytest.mark.parametrize('description', ['Requires 8 years of experience', 'Minimum of 10 years experience', '8+ years of relevant experience', '至少8年营销经验', 'Own the P&L', 'Cold calling and sales quota'])
def test_excluded_requirements(description):
    assert not evaluate(job(description=description))[0]


def test_company_age_not_experience_and_location_not_description():
    assert evaluate(job(description='Founded 10 years ago. Requires 4 years experience.'))[0]
    assert not evaluate(job(location='Tokyo', description='Marketing for Shanghai customers'))[0]
    assert evaluate(job(description='5–8 years of marketing experience'))[0]
    assert not evaluate(job(description='8–10 years of B2B marketing experience'))[0]


def test_salary_filter_only_explicit_annual_rmb():
    assert not evaluate(job(salary_max=290000, salary_currency='CNY', salary_interval='year'))[0]
    assert evaluate(job(salary_max=100000, salary_currency='USD', salary_interval='year'))[0]
    assert evaluate(job(salary_max=30000, salary_currency='CNY', salary_interval='month'))[0]


def test_url_canonicalization():
    assert canonical_url('https://example.com/jobs/1/?utm_source=x&job=42') == 'https://example.com/jobs/1?job=42'
    assert canonical_url('https://example.com/job?gh_jid=12') != canonical_url('https://example.com/job?gh_jid=13')
    with pytest.raises(ValueError):
        canonical_url('http://example.com')
