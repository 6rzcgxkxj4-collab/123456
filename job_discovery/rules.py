"""Replaceable matching boundary: later semantic matchers can implement evaluate(job)."""
import re

CITIES = {
    '上海': (100, r'上海|\bshanghai\b'),
    '深圳': (85, r'深圳|\bshenzhen\b'),
    '重庆': (80, r'重庆|\bchongqing\b'),
    '苏州': (65, r'苏州|\bsuzhou\b'),
    '无锡': (60, r'无锡|\bwuxi\b'),
    '杭州': (60, r'杭州|\bhangzhou\b'),
}
ROLE = r'marketing|marcom|市场|营销'
EXCLUDE_TITLE = r'\b(sales|business development|director|vice president|vp|head of|chief|performance marketing|paid media|media buyer)\b|销售|业务拓展|总监|投流|首席'
EXPERIENCE = r'(?:at least|minimum(?: of)?|requires?|required|minimum experience[: ]*)\s*(?:of\s*)?(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\+?\s*years?|\b(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\+?\s*years?\s+(?:of\s+)?(?:[a-z0-9/-]+\s+){0,5}experience|(?:至少|最低|要求)\s*(\d{1,2})\s*年|\b(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\s*年以上'
HARD_SALES = r'cold call|cold prospect|sales quota|own(?:ing)? (?:a |the )?p\s*&\s*l|陌生客户开发|销售指标|销售业绩考核|利润中心负责人'


def evaluate(job):
    if not re.search(ROLE, job.title, re.I):
        return False, '非目标营销岗位'
    if re.search(EXCLUDE_TITLE, job.title, re.I):
        return False, '排除销售/高管/纯投流职位'
    cities = [city for city, (_, pattern) in CITIES.items() if re.search(pattern, job.location, re.I)]
    if not cities:
        return False, '非目标城市；不从职位描述推测办公地点'
    if re.search(HARD_SALES, job.description, re.I):
        return False, '职位明确包含陌生开发/销售指标/P&L职责（保守排除）'
    for match in re.finditer(EXPERIENCE, job.description, re.I):
        number = next((int(x) for x in match.groups() if x), 0)
        if number >= 8:
            return False, '明确要求至少8年相关经验'
    # Only compare an explicit structured annual base range in RMB.
    if (job.salary_currency.upper() in {'CNY', 'RMB'} and
            job.salary_interval.lower() in {'year', 'yearly', 'annual', 'per-year'} and
            job.salary_max is not None and job.salary_max < 300000):
        return False, '公开人民币年薪上限低于30万'
    job.city = '、'.join(cities)
    job.score = max(CITIES[city][0] for city in cities)
    reasons = ['目标城市：' + job.city, '目标营销职位', '企业公开招聘源']
    for pattern, reason in [
        (r'marcom|communications|传播', '可匹配MarCom/网站/LinkedIn经验'),
        (r'event|field|展会|活动', '可匹配国际展会全流程经验'),
        (r'channel|partner|渠道|代理商', '可匹配日本/APAC渠道及代理商支持经验'),
        (r'apac|regional|international|亚太|国际', '可匹配国际B2B及中日英语言背景'),
        (r'product marketing|产品营销', '产品营销方向；技术领域要求需人工复核'),
    ]:
        if re.search(pattern, job.title + ' ' + job.description, re.I):
            reasons.append(reason)
            job.score += 5
    reasons += ['薪资：' + job.salary, '固定薪资构成、资历和语言硬要求需人工复核']
    job.reason = '；'.join(reasons)
    return True, job.reason
