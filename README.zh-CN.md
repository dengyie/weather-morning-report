# 天气早报

[English](README.md) | [简体中文](README.zh-CN.md)

天气早报是一个可自行部署的天气简报生成与邮件投递服务。它会把天气预报转换为简洁、以行动建议为重点的信息，帮助收件人快速判断是否需要带伞、如何穿衣、是否需要防晒，以及一天中哪些时段存在值得注意的天气风险。

你既可以每天给自己发送一封私人天气早报，也可以为家人、同事、订阅用户或其他有需要的人批量发送个性化报告。每位收件人都可以配置独立的称呼、邮箱和天气地区。同一地区只会获取一次天气数据，但每个人都会收到单独生成的邮件，不会看到其他收件人的邮箱信息。

当前天气数据来自 `wttr.in`，失败时会自动回退至 `wttr.is`。项目使用与天气服务无关的 Provider 架构，后续可以继续增加可配置的天气 API 与凭据。应用还会为不同地区保存带时效校验的独立天气缓存，并发送响应式 HTML 与纯文本邮件。

## 下载与安装

可以从 [GitHub Releases](https://github.com/dengyie/weather-morning-report/releases/latest)
下载最新的 wheel 安装包或源码压缩包。使用 Python 3.12 或更高版本安装下载的 wheel：

```bash
python3.12 -m pip install ./weather_morning_report-*.whl
weather-report --help
```

也可以直接从 GitHub 安装指定版本：

```bash
python3.12 -m pip install \
  git+https://github.com/dengyie/weather-morning-report.git@v0.2.0
```

如需进行开发或使用 Docker 部署，请克隆仓库：

```bash
git clone https://github.com/dengyie/weather-morning-report.git
cd weather-morning-report
```

这是一个 Python 应用，因此不通过 npm 分发。后续计划将同一 Python 包发布至 PyPI；目前 GitHub Release 提供的 wheel 已可直接安装使用。

## 使用 Docker 快速开始

推荐使用 Docker 部署，需要安装 Docker Engine 和 Docker Compose。

```bash
cp .env.example .env
docker compose build
docker compose run --rm report preview
```

发送邮件前，请编辑 `.env`：

```dotenv
TIMEZONE=Asia/Shanghai
LOCATION_NAME=Changning District, Shanghai
LOCATION_QUERY=Changning,Shanghai

RECIPIENT_NAME=
RECIPIENT_EMAIL=recipient@example.com
# 配置多位收件人时，使用单行 JSON，并删除上面的兼容单人字段：
# RECIPIENTS_JSON=[{"name":"Alice","email":"alice@example.com","location_name":"Shanghai","location_query":"Shanghai"}]
ADMIN_EMAIL=admin@example.com
SENDER_EMAIL=sender@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=sender@example.com
SMTP_PASSWORD=replace-me
SMTP_SECURITY=starttls
```

验证天气服务和邮件投递配置，然后发送天气早报：

```bash
docker compose run --rm report validate-config
docker compose run --rm report send
```

Docker Compose 会使用持久化的 `weather-report-data` 数据卷保存设置与天气缓存。

## Docker 设置页面

也可以通过浏览器配置邮件投递参数：

```bash
docker compose up settings
```

打开 <http://127.0.0.1:8766>，保存设置、测试 SMTP，然后使用 `Ctrl+C` 停止容器。

设置页面仅发布到宿主机回环地址，支持配置多位人物及其独立地区。如果使用设置页面，请删除 `.env` 中空白的 `RECIPIENT_*`、`RECIPIENTS_JSON`、`ADMIN_EMAIL`、`SENDER_EMAIL` 和 `SMTP_*` 配置，因为环境变量的优先级高于已保存的设置。

## 定时执行 Docker 任务

可以通过宿主机定时任务运行一次性报告容器。例如，宿主机使用 `Asia/Shanghai` 时区时，可添加：

```cron
30 8 * * * cd /opt/weather-morning-report && /usr/bin/docker compose run --rm report send >> /var/log/weather-morning-report.log 2>&1
```

启用定时任务前，请确认宿主机调度器时区，并先完成一次手动发送。更新和运维说明请参阅 [Docker 部署文档](docs/docker-deployment.md)。

## 原生 Python 安装

需要 Python 3.12 或更高版本。

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/pytest
```

通过已安装的 CLI 执行命令：

```bash
.venv/bin/weather-report preview
.venv/bin/weather-report preview --format html > report.html
.venv/bin/weather-report validate-config
.venv/bin/weather-report send
.venv/bin/weather-report settings
```

如需使用每日 systemd 定时器进行原生生产部署，请参阅 [原生 systemd 部署文档](docs/deployment.md)。

## 命令说明

| 命令 | 用途 |
| --- | --- |
| `weather-report preview` | 获取天气并渲染纯文本报告，不发送邮件 |
| `weather-report preview --format html` | 渲染响应式 HTML 报告 |
| `weather-report validate-config` | 验证完整邮件配置和天气服务访问 |
| `weather-report send` | 生成并发送 HTML 与纯文本邮件 |
| `weather-report settings` | 打开本地邮件设置页面 |

`preview` 不要求 SMTP 配置有效；`validate-config` 和 `send` 需要完整的邮件投递配置。

## 可靠性

应用会先请求 `wttr.in`，失败后请求 `wttr.is`。成功获取并规范化的天气快照会以原子方式保存。

如果两个天气服务均不可用：

- 使用不超过 `CACHE_MAX_AGE_HOURS` 的缓存快照，并在报告中明确标注。
- 如果没有可用缓存，则不会向收件人发送报告，只会向管理员发送失败通知。

## 配置

运行时默认值和支持的环境变量记录在 [`.env.example`](.env.example) 中。

- 环境变量会覆盖通过浏览器设置页面保存的配置。
- `RECIPIENTS_JSON` 用于配置多位收件人及其对应地区。
- 旧的 `RECIPIENT_NAME` 和 `RECIPIENT_EMAIL` 仍然可用于单个收件人，并使用默认的 `LOCATION_NAME` 与 `LOCATION_QUERY`。
- 原生部署的设置保存在 `var/settings.json`，文件权限为 `600`。
- Docker 设置和天气快照保存在 `weather-report-data` 数据卷中。
- `.env`、运行时数据、凭据和生成文件不会提交到 Git。

## 项目结构

```text
src/weather_morning_report/
├── delivery/          # 邮件构建与 SMTP 投递
├── providers/         # 天气服务接口与 wttr 实现
├── recommendations/   # 时段选择与行动建议
├── rendering/         # HTML 与纯文本报告
├── cache.py           # 带时效校验的规范化天气快照缓存
├── cli.py             # 命令行接口
├── config.py          # 运行时环境配置
├── models.py          # 与天气服务无关的领域模型
├── service.py         # 应用流程编排
├── settings.py        # 邮件投递设置持久化
└── webui.py           # 本地设置页面
```

天气服务响应会先转换为统一模型，再进入推荐与渲染逻辑。推荐阈值和失败处理均有自动化测试覆盖。

## 后续计划

- 支持配置不同天气 API 服务及其凭据
- 增加由天气服务提供的预警和空气质量数据
- 增加更多定时发送与收件人分组能力

## 版本里程碑

项目目前可以按五个开发里程碑理解。完整的后来者导览请看
[版本历史](docs/VERSION_HISTORY.md)。

| 里程碑 | 重点 | 主要能力 |
| --- | --- | --- |
| V1 | 天气简报 Demo | wttr 获取、统一天气模型、行动建议、纯文本预览 |
| V2 | 可靠 CLI 投递 | 缓存回退、HTML 邮件、SMTP、本地设置页、多收件人投递、Docker/systemd 部署 |
| V3 | 自托管服务基础 | FastAPI 管理后台、SQLite/Alembic、加密凭据、任务队列、Worker、运行历史、备份 |
| V4 | 新用户默认值 | 默认收件人与计划设置、本地验证记录 |
| V5 | 配置工作台 | 重新设计的配置 UI、收件人邮件模板偏好、静态 UI 预览 |

## 服务化开发基础

已批准的 v3 破坏性重构方案记录在
[docs/V3_ARCHITECTURE.md](docs/V3_ARCHITECTURE.md)。SQLite、Alembic、外部密钥加密、
管理员认证、配置中心、任务队列、调度、重试状态机和单 Worker 租约已经开始开发；
现有 v0.2 命令仍可继续使用。Worker 会通过 SQLite Online Backup API 幂等创建备份，
默认保留 7 份每日备份和 4 份每周备份；管理员可从控制台下载数据库备份，外部密钥必须
单独备份。

自动投递在调用 SMTP 前会持久化进入 `dispatching` 状态；如果 Worker 在该窗口停止，
系统会抑制自动重发并将结果标记为不确定，以避免重复邮件。缺少原外部密钥时执行恢复会
生成替代密钥，并清空无法解密的凭据以便重新录入。

交互式初始化新的 v3 数据目录：

```bash
WEATHER_REPORT_DB_PATH=var/weather-report.db \
WEATHER_REPORT_SECRET_KEY_FILE=var/secret.key \
.venv/bin/weather-report setup
```

数据库维护和本地管理员命令：

```bash
.venv/bin/weather-report setup upgrade
.venv/bin/weather-report setup restore /path/to/weather-report.db
.venv/bin/weather-report admin reset-password
.venv/bin/weather-report serve-ui
.venv/bin/weather-report serve-worker
```

v3 Docker Compose 使用独立的长期运行 UI 和 Worker 服务：

```bash
docker compose run --rm setup
docker compose up -d ui worker
```

UI 仅发布到 <http://127.0.0.1:8766>，Worker 不暴露网络端口。

原生部署可以通过设置 `WEB_BIND=0.0.0.0` 开启 HTTP 直连。配置方式和安全注意事项请
参阅 [原生 systemd 部署](docs/deployment.md)。

## 文档

- [版本历史](docs/VERSION_HISTORY.md)
- [当前设计与行为](docs/DESIGN.md)
- [已批准的 v3 架构](docs/V3_ARCHITECTURE.md)
- [V4 本地验证记录](docs/V4_VALIDATION.md)
- [V5 配置工作台开发记录](docs/V5_DEVELOPMENT.md)
- [Docker 部署](docs/docker-deployment.md)
- [原生 systemd 部署](docs/deployment.md)
