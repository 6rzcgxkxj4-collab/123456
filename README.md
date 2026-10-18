# AI 求职岗位自动发现

Python 3.12、GitHub Actions、Google Sheets。第一版使用规则，无付费 OpenAI API。
默认只生成测试报告，不访问或修改 Google Sheets，不替你申请或发送邮件。

## 功能与实际边界

- 支持公开 Greenhouse、Lever、Ashby 接口。初始启用 Samsara、Formlabs 两个 Greenhouse board。
- 每天重新查询清单中的企业职位，上海优先，其次深圳、重庆，兼顾苏州、无锡、杭州。
- 按营销方向、地点、经验要求排除销售、高管、纯投流等；用展会、MarCom、渠道、国际营销经验生成理由。
- 公司/职位/城市指纹、官方链接、ATS 来源 ID 三种方式去重。
- Greenhouse/Lever 通过官方详情接口核实；Ashby 明确标注官方列表核实、详情页待核实。
- 无法核实写待核实，官方列表不再出现只标待核实，不据此宣称关闭。永不删除历史岗位。
- 薪资、发布日期不推测，更新时间不会冒充发布日期；总包、OTE、外币不推算为人民币固定年薪。
- Lever 明确的人民币年度薪资上限不足30万时排除。其他薪资和固定部分需人工复核。
- 企业成熟度、欧美/日企归属应在添加来源前人工确认；规则分不是录用概率。
- 这是**企业清单监测**，不是全网搜索。初始覆盖很小，可能连续多天零匹配。
- Workday 尚未实现，后续须逐企业核实公开查询方式和条款；不会绕过验证码、登录或访问限制。

职业依据：奈良女子大学硕士；Figaro Engineering Japan 2022-10 至2026-06 的国际B2B营销；
OutIn 2026-06 至2026-10 日本/APAC渠道市场；中文母语、JLPT N1、TOEIC875。
匹配理由覆盖国际展会、MarCom、网站、LinkedIn、渠道支持。语言硬要求和资历仍需人工确认。
固定年薪目标35–40万、底线30万；未公开薪资的岗位保留复核，不能声称已满足底线。

## 本地运行

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
python -m job_discovery.cli
```

检查 `reports/latest.json` 的来源数量、排除原因、候选、核实结果和来源失败。
退出码0表示流程成功（不保证有匹配）；1为来源失败；2为写入门禁或表格预检失败。
模拟测试通过不代表真实招聘接口、Sheets授权或Actions运行通过。

## 现有表格的保护机制

固定表格ID：`1z-zzj5IWsQXTjDL7QV8OYF2_Do_NSJdslh39G2RVHds`。
固定工作表：`岗位数据库`。所有读取和写入范围只指向此表，不修改其他工作表。
要求已有以下17列，可调整顺序，不允许重复或缺失：

```text
岗位ID 公司 岗位名称 城市 企业类型 岗位方向 固定年薪(万元) 薪资公开状态 匹配度 招聘状态 申请状态 岗位链接 来源 发现日期 最后核实 匹配理由 待确认问题
```

首次正式运行显式选择 `initialize_columns=true`，在目标表右侧增加两个持久化列：

- `自动化来源ID`：ATS标识。
- `自动化快照`：上次自动写入值，辨认人工修改。

不清空、不重建表；若新列区域已有数据，初始化拒绝执行。
不自动收养人工录入行；匹配到人工记录则跳过，不追加重复岗位。
「申请状态」新增时留空，之后永不写入。歧义重复行、损坏快照安全跳过。
已有自动记录仅更新仍与快照一致的字段；发现人工修改后永久释放对应字段。
发现日期和岗位ID不随日常更新变化。核实失败不抹除上次成功核实时间。
所有值以RAW提交，网站文本不会当作表格公式执行。

Actions有单写入者锁，写入前重新读取目标表检查变化。
**Sheets没有比较交换事务**，检查和提交间仍存在短暂竞态。正式运行期间请勿同时编辑目标表，
也不要让其他程序写入同一目标；不能保证并发人工编辑时绝对零覆盖。
服务账号获授权的是整份文件；单tab限制由代码实现，并非Google的单tab授权机制。
如需更强隔离，可另行保护其他tab（程序不会自动修改这些tab）。

读请求采用指数退避重试，429尊重Retry-After；append写请求不盲目重试，避免响应丢失导致重复追加。
重新运行时先读取现有记录再去重。任一来源失败会阻止本轮全部表格写入。

## Google凭证：只存GitHub Secrets

1. Google Cloud建立项目，启用 **Google Sheets API**。
2. 建立专用服务账号并生成JSON密钥，不需要授予项目Owner/Editor角色。
3. 将现有表格共享给JSON中的 `client_email`，授予文件编辑权限。
4. 仓库 → Settings → Secrets and variables → Actions → **Secrets** → New repository secret。
   名称：`GOOGLE_SERVICE_ACCOUNT_JSON`；值：完整JSON。不要发到聊天、输出到日志或提交到仓库。
5. 如需本地预检，安全注入同名进程环境变量，运行：

```bash
python -m job_discovery.cli --sheets
```

预检只读；缺少两个自动化列时报告待初始化，退出2，不会改表。
不需要Drive API或模型密钥；密钥轮换在Google Cloud和GitHub Secrets完成。

## GitHub Actions部署和启用顺序

工作流为 `.github/workflows/discover.yml`，测试成功后运行发现任务。

1. 文件需推入默认分支，仓库启用Actions。私有仓库关注Actions免费额度和Artifact配额。
2. Actions → **Discover jobs** → Run workflow，选 `mode=dry-run`。
3. 下载 `job-discovery-...` Artifact，审查真实来源数量、候选和失败项；源失败不等于没有岗位。
4. 配好Secret后，运行 `mode=preflight`，核对授权及现有表头；此步骤不写入。
5. 结果确认正确后，在 Settings → Secrets and variables → Actions → **Variables** 添加
   `ENABLE_SHEETS_WRITE=true`。
6. 首次手动运行 `mode=write`、`initialize_columns=true`，增加两列并同步候选。
7. 此后每天**北京时间09:17**运行。变量未启用则定时仅测试运行，GitHub调度可能延迟。

写入同时要求 `--write --sheets` 和 `ENABLE_SHEETS_WRITE=true`。
push触发始终dry-run，PR只测试，不接触凭证；只有手动write和启用后的schedule会写入。
停止自动写入：删除变量或设为false；停止所有任务：Actions中Disable workflow。
失败通过Actions默认通知查看；报告保留30天，不含历史表格内容或凭证。
公开仓库长期无活动时GitHub可能暂停定时工作流；请每月检查Actions并按需重新启用。
不依赖个人电脑，但不能承诺云调度永不中断。

## 来源扩展和未来AI

编辑 `config/sources.json`，添加前确认企业官网确实链接对应ATS board，再dry-run。

```json
{"sources": [{"provider": "lever", "board": "official-board-token", "company": "企业真实名称", "enabled": true}]}
```

示例token不是有效源。provider支持greenhouse、lever、ashby，board必须是官方ATS标识，不是搜索词。
错误源报错，不回退到绕过访问限制的爬虫。两个初始源在当前云环境尚未成功联网验证，
请以首次GitHub dry-run响应为准。逐步补充在目标城市招聘的工业/制造/B2B欧美和日企官方源。

`job_discovery/rules.py:evaluate(job)` 是可替换匹配接口。未来AI只用于排序和理由，
不改变来源事实、薪资、核实结论、去重键和写入保护。当前不调用任何模型服务。

## 排障与已知限制

- 403、429、超时、接口变更：查看source_failures，不绕过限制。
- Google401/403：检查Sheets API、密钥、文件共享及Secret，不打印私钥。
- 表头重复/缺失、快照损坏：停止写入或跳过冲突，人工确认后处理，不会清表重建。
- 固定年薪列在未确认固定构成时保持未知；文本薪资提取尚未实现。
- 两个源不能代表中国市场全部目标岗位。发布日期缺失时保持未知（记录在待确认问题中）。
- 不删除过期记录，不在未经证实时标关闭，不自动申请岗位。
- reports、本地虚拟环境和常见凭证文件被忽略；其他命名的密钥也不要放入仓库。
- 云环境联调需允许 `boards-api.greenhouse.io`、`api.lever.co`、`api.ashbyhq.com`、
  `sheets.googleapis.com`、`oauth2.googleapis.com` 出站。此配置不等同于GitHub runner网络。
