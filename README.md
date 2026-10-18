# 每日求职岗位发现：GitHub Actions + Apps Script

Python规则筛选招聘岗位，GitHub Actions每天执行，通过Google Apps Script Web App写入现有Google Sheets。
**不需要Google Cloud信用卡、服务账号JSON或付费OpenAI API。** 默认测试模式，默认禁止正式写表。

## 当前功能与范围

- Greenhouse、Lever、Ashby公开招聘接口适配器；初始配置Samsara、Formlabs两个Greenhouse board。
- 每天北京时间09:17重新查询企业清单，筛选目标城市、营销职位和经验要求，排除销售、高管、纯投流等。
- 上海优先，深圳、重庆其次，兼顾苏州、无锡、杭州；不从描述猜测办公地点。
- 结合国际B2B、MarCom、展会、渠道及APAC经验生成匹配理由；规则分不是录用概率。
- 使用官方来源ID、招聘链接、公司/职位/城市指纹去重。匹配到已有人工岗位只跳过，不自动接管。
- 官方详情接口核实Greenhouse/Lever；Ashby明确标注列表核实、详情页待核实。
- 薪资未公开为未知，不推测固定薪资或发布日期；更新时间不冒充发布日期。
- 公开Lever人民币年薪上限低于30万会排除；总包、OTE、外币不折算为固定人民币年薪。
- 从成功读取的官方列表消失，仅标待核实，不声称关闭，不删除历史岗位。
- 不绕过验证码、登录、付费墙或访问限制，不自动申请或发邮件。

这是指定企业清单监测，初始覆盖很小，不是全网搜索；可能长期零匹配。Workday尚未实现。
企业成熟度、欧美/日企归属、薪资构成、语言和资历要求需人工复核，不由程序编造。
职业背景依据：奈良女子大学硕士；Figaro Engineering Japan 2022-10至2026-06国际B2B营销；
OutIn 2026-06至2026-10日本/APAC渠道市场；中文母语、JLPT N1、TOEIC875。
固定年薪目标35–40万、底线30万；未知薪资保留待确认，不代表已经符合底线。

## 一、Google Apps Script：新建独立项目，不动Gmail同步项目

**推荐使用新的独立Apps Script项目。** 仍然操作同一份表格，但与现有Gmail同步脚本、触发器、权限和入口完全隔离。
无需打开Google Cloud Console或启用结算，使用Apps Script自带SpreadsheetApp服务和你的Google账号授权。

1. 打开 [script.google.com](https://script.google.com/)，新建项目，命名如 `JobDiscoveryWriter`。
2. 新增两个脚本文件，粘贴本仓库对应内容：
   - `apps_script/JobDiscovery.gs`：签名校验、预览、去重、安全写入。
   - `apps_script/WebAppEntry.gs`：唯一的 `doPost(e)` 入口。
   新项目默认的空 `myFunction` 可以保留，无需改动任何Gmail文件。
3. 在项目设置 → **脚本属性（Script properties）** 中新增：

   | 属性名 | 值 |
   | --- | --- |
   | `JD_SHARED_SECRET` | 本地生成的至少32字符ASCII随机密钥 |
   | `JD_ALLOW_WRITES` | `false` |

   密钥可在可信本地终端生成：`python -c 'import secrets; print(secrets.token_urlsafe(32))'`。
   不要发送到聊天、提交仓库、放到URL或执行日志中。同一密钥稍后放到GitHub Secret。
4. 部署 → 新部署 → 类型选 **Web应用**：
   - 执行身份：**我**（拥有目标表编辑权限的账号）。
   - 访问权限：**任何人 / Anyone**，允许不登录Google的GitHub runner调用。
   - 按Google提示授权你自己新建的脚本访问表格；复制部署的 `/exec` HTTPS URL。
   - 不要使用 `/dev` URL，不要在URL后添加密钥或其他参数。
5. 脚本固定打开下面的表格ID，并且只获取「岗位数据库」：
   `1z-zzj5IWsQXTjDL7QV8OYF2_Do_NSJdslh39G2RVHds`。
   不读取或修改「投递记录」「邮件事件」「求职面板」「筛选规则」。

如果组织策略禁止匿名Web App，不能用“任何Google账号用户”代替：Actions会收到登录页。
需要管理员允许该部署方式，否则此方案存在外部配置阻碍，程序不会绕过登录限制。
Apps Script免费额度、执行时间和Spreadsheet配额仍适用；不保证永久无中断。

### 已有Apps Script的Gmail功能如何保留

本仓库没有访问或修改你现有的Apps Script项目。`JobDiscovery.gs`无Gmail调用，不创建触发器，
不清理或修改无关脚本属性。优先部署到上面的独立项目，不要把整个Gmail项目替换成这些文件。

如果坚持放在已有项目中，只新增 `JobDiscovery.gs`，先检查是否已有 `doPost`。
若已经存在，**不要复制WebAppEntry.gs、不要定义第二个doPost、不要替换原入口**；改用独立项目。
Apps Script同项目所有`.gs`共享全局作用域，文件独立不代表入口隔离。
后续更新脚本代码后，部署 → 管理部署 → 编辑 → 选择新版本，才会更新 `/exec` 的线上代码。
只修改脚本属性的开关或密钥不需要重新发布代码版本。

## 二、GitHub配置：两个Secrets，正式写入前先测试

在 [仓库Settings → Secrets and variables → Actions](https://github.com/6rzcgxkxj4-collab/123456/settings/secrets/actions) 新增：

| GitHub Actions Secret | 值 |
| --- | --- |
| `APPS_SCRIPT_WEB_APP_URL` | 上一步的 `https://script.google.com/macros/s/.../exec` |
| `APPS_SCRIPT_SHARED_SECRET` | 与 `JD_SHARED_SECRET` 完全相同的随机密钥 |

无需服务账号凭证。旧的Google服务账号JSON Secret不再使用，可从仓库Secrets删除；如曾创建旧密钥，可在Google端撤销。
**把旧的仓库变量 `ENABLE_SHEETS_WRITE` 删除或先设为 `false`**，尤其是从旧版迁移时。
服务端 `JD_ALLOW_WRITES=false` 是独立门禁，默认阻止写入。

### 先测试，再启用

1. 仓库默认分支启用Actions。打开 [Discover jobs](https://github.com/6rzcgxkxj4-collab/123456/actions/workflows/discover.yml)，手动运行 `mode=dry-run`。
   此模式只测试招聘发现，不请求Web App、不读写表格。
2. 下载Artifact中的 `latest.json`，核对真实招聘源数量、候选、核实状态、失败项。
   任一招聘源失败都不能当作“没有岗位”。
3. 再手动运行 `mode=preflight`。这会向Web App发送签名请求，读取目标表并计算新增/更新/跳过数量，
   **不写任何表格单元格或备注**；只在脚本属性中记录防重放及短期预览凭据。
4. 检查Actions日志和Artifact：`sheets` 应包含 `new_rows`、`cell_updates`、`metadata_updates`（备注更新数）、`skipped`、`written:false`，
   不应出现 `error_type`。零候选且零更新只能验证连接和预检，不能证明真实写入已成功。
5. 确认测试结果正确、需要正式启用时：
   - Apps Script脚本属性 `JD_ALLOW_WRITES` 改为 `true`。
   - GitHub **Variables** 新增/修改 `ENABLE_SHEETS_WRITE=true`（不是Secret）。
   - 手动运行 `mode=write`；程序先做同批数据的服务端preview，再携一次性预览凭据提交。
   - 核对目标表新增记录及未受影响的人工数据，确认本次实际效果。
6. 之后每天北京时间 **09:17** 自动运行；只有GitHub开关开启才请求正式同步，否则schedule只做dry-run。
   push始终dry-run，PR只跑测试，不接触凭证。调度可能延迟，私有仓库注意Actions额度。

停止写入：GitHub变量设false，或者Apps Script `JD_ALLOW_WRITES=false`，任一开关关闭就不会正式写入。
停止所有定时任务：Actions中Disable workflow。公开仓库长期无活动可能被GitHub暂停调度，请每月检查。
失败查看Actions默认通知和Artifact；报告保留30天。工作流文件存在不等于云端已经成功执行。

## 三、保留17列、人工数据与Gmail同步

现有表头保持不变，可调整顺序，但不能重复或缺失：

```text
岗位ID 公司 岗位名称 城市 企业类型 岗位方向 固定年薪(万元) 薪资公开状态 匹配度 招聘状态 申请状态 岗位链接 来源 发现日期 最后核实 匹配理由 待确认问题
```

新版本**不增加列、不增加工作表**。将自动化来源ID与快照存入自动新增记录「岗位ID」单元格的备注，
以 `JOB_DISCOVERY_V1` 开头。不要手动清空这些系统备注；损坏或替换备注会使该行成为只读人工记录。
既有人工备注不会覆盖。更改岗位ID/公司/职位/城市/链接等身份字段后，整行停止自动接管。

如果旧版本已经生成「自动化来源ID」「自动化快照」两列，本版可在空备注的旧自动记录上读取并迁移快照到备注，
**不会更新、清空或删除旧两列**。不需要手动删列，也不强制增加这两列。

- 已有人工岗位：不更新，匹配则跳过，不重复新增。
- 自动岗位：只更新仍等于上次快照的字段；发现人工修改后永久释放该字段。
- 「申请状态」永不自动更新；新行留空，Gmail/人工填写的状态保持原样。
- 发现日期与岗位ID不随日常更新变化；核实失败不清空上次成功核实时间。
- 备注绑定的身份不一致、重复行冲突、快照损坏：安全跳过，不清表重建。
- 所有写入使用RichText字面文本，`=...` 等招聘文本不会被解释为公式。

服务器使用ScriptLock锁和预览快照检测，提交前重新读取表格，逐字段更新前检查旧值、备注前检查旧备注。
Apps Script锁无法锁住人工或**另一个项目**的Gmail同步进程；Sheets不支持比较交换事务。
请避免Gmail同步、人工编辑与09:17写入窗口重叠，不要只排序部分列（备注会与数据错位）。
不能保证检查与提交之间的并发修改绝对零覆盖，也不能保证多次Spreadsheet操作全部原子提交。
异常可能发生部分写入：不会重新执行同一请求；下一轮重新读取、去重，冲突字段宁可停止接管。

## 四、请求协议与安全边界

Apps Script Web App事件不提供常规自定义请求头，因此不使用Authorization或X-API-Key鉴权。
通过HTTPS POST，`Content-Type: text/plain; charset=utf-8`，请求体为JSON信封：

```text
version, timestamp, request_id, payload_b64, signature
```

`payload_b64` 是UTF-8 JSON字节的标准Base64（用于精确定义签名字节，**不是加密**）。
签名为 `HMAC-SHA256(shared_secret, "v1\\n" + timestamp + "\\n" + request_id + "\\n" + payload_b64)` 的小写hex；
这里的分隔符代表实际换行。密钥本身不会传输，不放URL、不放请求头、不记录日志。

服务端要求时间戳在±300秒内、常量时间比较签名、ScriptLock下持久化nonce到ScriptProperties。
nonce保存660秒，不依赖可能被提前淘汰的CacheService。重复相同请求返回原结果，不重复执行；
相同ID不同签名拒绝；已记录处理中但无结果则拒绝重执行。客户端重试使用完全相同的签名信封。
普通失败不显示原始服务端异常、请求体或部署URL，避免凭证泄漏。

preview生成15分钟内有效的一次性凭据，绑定整个批次和目标表快照。正式写入还要求服务端开关，
数据或表格变化、凭据过期/复用都会拒绝。每次自动写入都会先做新的preview。
最多每批200个候选、50,000个观测ID、1.5MB请求体、20,000行目标表；超限失败，不静默截断。

ContentService通常HTTP200也会返回业务错误，客户端必须验证JSON的`ok`和请求ID。
ContentService返回302/303时，仅跟随到 `script.googleusercontent.com` 的HTTPS GET，
不会把签名POST体发送到重定向目标；登录页、其他重定向、非JSON不算成功。
Web App匿名入口仍可能受恶意流量耗尽Apps Script配额；共享密钥保护写权限，不能消除平台配额风险。

## 五、本地开发、测试与扩展

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
node --test tests/apps_script.test.cjs
python -m job_discovery.cli
```

Apps Script JavaScript在Node测试中使用Google服务模拟器。测试覆盖Python/JS签名互通、鉴权、重放、预览门禁、
去重、人工修改保护、旧列迁移、Gmail无关属性保护、17列结构和公式字面值。
**模拟器通过不代表真实Apps Script授权、部署、重定向和表格写入已经验证。** 必须做上面的真实preflight和首次write。
真实联调需要你自行部署Web App并配置Secrets，本仓库不能替你完成Google账号授权。

安全注入 `APPS_SCRIPT_WEB_APP_URL` 和 `APPS_SCRIPT_SHARED_SECRET` 后，本地预检：

```bash
python -m job_discovery.cli --sheets
```

输出 `reports/latest.json`。退出码0表示流程成功，不保证有岗位；1为来源失败；2为Web App/写入门禁失败。
错误码参考：

| code | 检查 |
| --- | --- |
| `auth_failed` | 两处密钥是否相同且至少32字符，runner时钟是否正确 |
| `web_app_non_json` / `unsafe_redirect` | 是否为/exec、访问权限是否为Anyone，是否部署了新版本 |
| `writes_disabled` | Apps Script与GitHub两个开关 |
| `invalid_headers` | 17列表头是否完整，是否有重复/无标题数据列 |
| `sheet_changed` | 暂停同期人工/Gmail写入，重新预检 |
| `preview_required` / `preview_expired` | 不复用旧凭据，重新跑完整流程 |
| `request_in_progress` | 上次可能中断，先检查目标表；下一轮重新读取再去重 |
| `capacity` / `internal_error` | 查看Apps Script执行状态和配额，勿输出密钥或完整请求体 |

编辑 `config/sources.json` 扩充真实企业官方board，支持greenhouse、lever、ashby。
先从企业官网核对其ATS归属，再dry-run；初始两个源在先前受限环境中未成功联网验证，不把源失败称作零岗位。
`rules.py:evaluate(job)` 是未来AI匹配扩展点；AI只能辅助排序与理由，不得更改来源事实或安全写入逻辑。
`reports/`、虚拟环境及常见凭证文件已忽略；不要提交其他命名的密钥文件。
云环境如需联调，需允许 `script.google.com`、`script.googleusercontent.com` 和所用招聘API出站；
GitHub托管runner的网络配置与此开发环境分别独立。
