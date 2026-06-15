# Weather Morning Report OpenPet JS 插件化重构总览

> **最新依据优先级：** 本项目插件化设计以 `/Users/mango/project/codex/OpenPet/docs/plugin-development.md`、`/Users/mango/project/codex/OpenPet/docs/plugin-ecosystem-rules.md`、`/Users/mango/project/codex/OpenPet/docs/plugin-submission-workflow-playbook.md` 以及 OpenPet `examples/plugins/*` 当前实现为准。若本仓库文档与 OpenPet 最新文档冲突，执行时必须优先服从 OpenPet 最新文档，并回修本仓库文档。

## 1. 项目结论

Weather Morning Report 已从 Python 自托管天气早报服务重构为 **OpenPet 原生 JavaScript 插件工程**。

这次重构的核心不是给旧服务包一层插件壳，而是完全切换产品形态：

- 运行模型从后台服务改为 OpenPet 短生命周期 command runner。
- 交付物从 Python package / Docker / systemd 改为 `.openpet-plugin.zip`。
- 配置入口从 Web UI / env 改为 OpenPet Control Center 的 `config.schema.json`。
- 持久化从 SQLite / 文件缓存改为 OpenPet scoped `ctx.storage`。
- 用户触达从 SMTP / Web 页面改为 `ctx.pet.say()` 桌宠播报与命令返回值。

旧 Python 服务端能力已经明确退出主线。后续开发只围绕 OpenPet 插件契约演进。

## 2. 文档分层

| 文档 | 定位 | 主要读者 | 何时更新 |
| --- | --- | --- | --- |
| `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md` | 战略总览、当前状态、文档路由 | 项目维护者、代码评审者 | 项目方向、文档结构或阶段状态变化时 |
| `docs/PLUGIN_CONTRACT.md` | 稳定插件契约：manifest、权限、命令、配置、数据、网络、隐私 | 实现者、测试编写者、OpenPet 审核者 | 新增/修改权限、命令、配置、host、返回结构、storage shape 前 |
| `docs/MIGRATION_NOTES.md` | 迁移台账与后续开发手册：删除范围、结构、构建、测试、release、风险 | 后续开发者、发布负责人 | 每个阶段完成、验证口径变化、发布流程变化时 |
| `docs/RELEASE.md` | 发布前检查清单 | 发布负责人 | release 命令或 artifact 变化时 |
| `docs/README.md` | 文档索引 | 所有人 | 文档增删或入口变化时 |

使用原则：

1. 先看 OpenPet 最新文档。
2. 再看 `PLUGIN_CONTRACT.md` 确认不可破坏的插件边界。
3. 最后看 `MIGRATION_NOTES.md` 确认当前实现状态、验证命令和后续工作。

## 3. 当前插件决策

- 插件名称：`Weather Morning Report`。
- 插件 id：`com.weather-morning-report.openpet`。
- 首版版本：`1.0.0`。
- 包根目录：`openpet-plugin/`。
- 首选发布产物：`release/weather-morning-report.openpet-plugin.zip`。
- OpenPet 权限：`network`、`pet:say`、`storage`。
- 网络 allowlist：`wttr.in`、`wttr.is`。
- 命令：`refresh`、`announce`、`last`、`status`、`clear-cache`。
- 配置：地点名、地点查询、语言、报告时段、刷新后播报、缓存最大年龄、是否显示来源。
- 非目标：后台 daemon、SMTP、Webhook、AI 改写、默认 pet action、私有天气 API、localhost bridge、用户 secret。

## 4. 当前仓库形态

```text
weather-morning-report/
├── package.json
├── README.md
├── README.zh-CN.md
├── docs/
│   ├── OPENPET_PLUGIN_REFACTOR_PLAN.md
│   ├── PLUGIN_CONTRACT.md
│   ├── MIGRATION_NOTES.md
│   ├── RELEASE.md
│   └── README.md
├── openpet-plugin/
│   ├── plugin.json
│   ├── config.schema.json
│   ├── index.js
│   └── README.md
├── src/
│   ├── activate.js
│   ├── commands.js
│   ├── config.js
│   ├── weather-provider.js
│   ├── wttr-parser.js
│   ├── recommendation-engine.js
│   ├── period-schedule.js
│   └── text-renderer.js
├── scripts/
│   ├── build-plugin.js
│   ├── check-plugin-artifact.js
│   └── package-plugin.js
└── tests/
    └── *.test.js
```

结构规则：

- `src/` 是开发源码，可以使用 CommonJS 模块拆分。
- `openpet-plugin/` 是 OpenPet 可安装包根目录，必须始终保持可验证。
- `openpet-plugin/index.js` 是构建产物，必须为单文件，不能依赖 runtime `require`。
- `release/` 是打包产物目录，不作为源码真相来源。

## 5. 后续开发顺序

任何后续功能都按以下顺序推进：

1. 读取 OpenPet 最新插件文档和示例。
2. 更新 `docs/PLUGIN_CONTRACT.md`，明确 manifest/config/命令/storage/network 变化。
3. 更新或补充测试，先覆盖契约变化。
4. 修改 `src/` 源码。
5. 运行构建，刷新 `openpet-plugin/index.js`。
6. 打包并运行 OpenPet 官方验证。
7. 更新 `docs/MIGRATION_NOTES.md` 的实现记录、风险和完成状态。

新增能力必须优先回答：

- 是否需要新权限？
- 是否需要新 network host？
- 是否会让安装/更新后需要用户重新 enable？
- 是否会保存更多用户数据？
- 是否仍适合 OpenPet 短生命周期 command runner？

## 6. 验证基线

本仓库本地验证：

```bash
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
git diff --check
```

OpenPet 官方验证：

```bash
cd /Users/mango/project/codex/OpenPet
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/openpet-plugin
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip
```

提交 OpenPet catalog 或第三方审核前，还需要按 `docs/MIGRATION_NOTES.md` 的 submission workflow 生成 report、PR packet 和 bundle。

## 7. 执行纪律

- OpenPet 最新文档优先于本仓库文档。
- `PLUGIN_CONTRACT.md` 优先于实现代码；契约改动先行。
- 不使用 OpenPet 内部未文档化 API 作为运行依赖。
- 不引入 localhost bridge、后台 daemon、shell、任意 filesystem、Electron globals 或用户 secret。
- 不扩大权限或 allowlist 来“预留未来能力”。
- 不把 release zip 当作唯一可复现来源；源码、脚本、测试必须能重新生成它。
- 旧 Python 服务端代码不再作为主线产品维护；如需对照，只从 git history 或测试 fixture 中追溯。
