# 天气早报

[English](README.md) | [简体中文](README.zh-CN.md)

天气早报会生成并发送一封简洁、以行动建议为重点的个人天气邮件，帮助你快速判断是否需要带伞、如何穿衣、是否需要防晒，以及一天中哪些时段存在值得注意的天气风险。

应用使用 `wttr.in` 获取天气，并自动回退至 `wttr.is`；同时提供带时效校验的本地天气快照缓存，并发送响应式 HTML 与纯文本邮件。

## 下载

```bash
git clone https://github.com/dengyie/weather-morning-report.git
cd weather-morning-report
```

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

设置页面仅发布到宿主机回环地址。如果使用设置页面，请删除 `.env` 中空白的 `RECIPIENT_*`、`ADMIN_EMAIL`、`SENDER_EMAIL` 和 `SMTP_*` 配置，因为环境变量的优先级高于已保存的设置。

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

## 文档

- [当前设计与行为](docs/DESIGN.md)
- [Docker 部署](docs/docker-deployment.md)
- [原生 systemd 部署](docs/deployment.md)
