# Weather Morning Report OpenPet JS 插件化重构总览

> **最新依据优先级：** 本项目插件化设计以 `/Users/mango/project/codex/OpenPet/docs/plugin-development.md`、`/Users/mango/project/codex/OpenPet/docs/plugin-ecosystem-rules.md`、`/Users/mango/project/codex/OpenPet/docs/plugin-submission-workflow-playbook.md` 以及 OpenPet `examples/plugins/*` 当前实现为准。若本仓库文档与 OpenPet 最新文档冲突，执行时必须优先服从 OpenPet 最新文档，并回修本仓库文档。

## 1. 项目结论

Weather Morning Report 已从 Python 自托管天气早报服务重构为 **OpenPet 原生 JavaScript 插件 / 扩展工程**。

这次重构的核心不是给旧服务包一层插件壳，而是切换到 OpenPet 的本地扩展形态：

- 兼容包继续支持 OpenPet 短生命周期 command runner。
- 统一扩展包使用 OpenPet `entries.commands`、`entries.setup`、`entries.services`、`entries.dashboards`。
- 交付物从 Python package / Docker / systemd 改为 `.openpet-plugin.zip` 与 `.openpet-extension.zip`。
- 配置入口包括 OpenPet `config.schema.json` 和扩展 service dashboard。
- 兼容命令持久化使用 OpenPet scoped `ctx.storage`；service/dashboard 使用 OpenPet 注入的 data/cache/log 目录。
- 用户触达包括 `ctx.pet.say()` 桌宠播报、命令返回值、Web dashboard、Email preview/send 和 scheduler。

旧 Python 服务端能力已经明确退出主线。后续开发只围绕 OpenPet 插件/扩展契约演进。

## 1.1 当前状态和 TODO

当前状态：

- 兼容插件包：`release/weather-morning-report.openpet-plugin.zip`，根目录来自 `openpet-plugin/`。
- 统一扩展包：`release/weather-morning-report.openpet-extension.zip`，根 manifest 来自 `extension/plugin.json`。
- 两个包都通过当前 OpenPet main 的 `npm run validate:plugin`。
- 统一扩展包已包含 active `commands/`、`service/`、`core/`、`rendering/`、`static/` 和 package metadata。
- 自动化覆盖 command、service、dashboard、SMTP、scheduler、secret rotation、artifact、OpenPet validator 和 runtime smoke。

当前 TODO：

1. 继续保持 unified extension zip 通过 OpenPet main validator，不再兼容旧的“不支持 entries”分支。
2. 做一次真实 Electron Control Center 视觉冒烟：安装扩展、打开 dashboard、启动/停止 service、查看 health/log、运行 command。
3. 增加发布签名元数据或签名策略：当前包仍是 unsigned，OpenPet validator 会标记为 review risk。
4. 明确 catalog/submission 目标：生成 submission bundle、maintainer approval record，并决定优先提交 `.openpet-extension.zip` 还是仅保留 legacy plugin 包。
5. 评估是否仍需要单独维护 `.openpet-plugin.zip`；在 OpenPet main 稳定支持 extension entries 后，legacy 包可以降级为兼容产物。

## 2. 文档分层

| 文档 | 定位 | 主要读者 | 何时更新 |
| --- | --- | --- | --- |
| `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md` | 战略总览、当前状态、文档路由 | 项目维护者、代码评审者 | 项目方向、文档结构或阶段状态变化时 |
| `docs/PLUGIN_CONTRACT.md` | 稳定兼容插件契约：manifest、权限、命令、配置、数据、网络、隐私 | 实现者、测试编写者、OpenPet 审核者 | 新增/修改兼容插件权限、命令、配置、host、返回结构、storage shape 前 |
| `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md` | 统一扩展边界：root manifest、entries、services、dashboards、lifecycle、data ownership | 扩展实现者、OpenPet 审核者 | 新增/修改 extension entries、service/dashboard、setup/cleanup、数据目录或宿主职责前 |
| `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` | Weather service/dashboard/Email/scheduler 迁移记录和运行能力说明 | 后续开发者、代码评审者 | service/dashboard/Email/scheduler 能力或 OpenPet runtime 适配变化时 |
| `docs/MIGRATION_NOTES.md` | 迁移台账与后续开发手册：删除范围、结构、构建、测试、release、风险 | 后续开发者、发布负责人 | 每个阶段完成、验证口径变化、发布流程变化时 |
| `docs/RELEASE.md` | 发布前检查清单 | 发布负责人 | release 命令或 artifact 变化时 |
| `docs/README.md` | 文档索引 | 所有人 | 文档增删或入口变化时 |

使用原则：

1. 先看 OpenPet 最新文档。
2. 兼容 command-plugin 行为看 `PLUGIN_CONTRACT.md`。
3. 统一 extension entries/service/dashboard 行为看 `OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md` 和 `WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md`。
4. 最后看 `MIGRATION_NOTES.md` 确认当前实现状态、验证命令和后续工作。

## 3. 当前插件决策

- 插件名称：`Weather Morning Report`。
- 插件 id：`com.weather-morning-report.openpet`。
- 首版版本：`1.0.0`。
- 包根目录：`openpet-plugin/`。
- 兼容发布产物：`release/weather-morning-report.openpet-plugin.zip`。
- 统一扩展产物：`release/weather-morning-report.openpet-extension.zip`。
- OpenPet 权限：`network`、`pet:say`、`storage`。
- 网络 allowlist：`wttr.in`、`wttr.is`。
- 命令：`refresh`、`announce`、`last`、`status`、`clear-cache`。
- 配置：地点名、地点查询、语言、报告时段、刷新后播报、缓存最大年龄、是否显示来源。
- 当前统一扩展已包含 service/dashboard/Email/scheduler 能力。
- 非目标：Python 双栈、Docker/systemd 主路径、AI 改写、默认 pet action、私有天气 API、OpenPet 外的后台 daemon workaround。

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
├── extension/
│   └── plugin.json
├── openpet-plugin/
│   ├── plugin.json
│   ├── config.schema.json
│   ├── index.js
│   └── README.md
├── commands/
├── core/
├── rendering/
├── service/
├── src/
│   ├── activate.js
│   └── commands.js
├── static/
├── scripts/
│   ├── build-plugin.js
│   ├── check-plugin-artifact.js
│   ├── check-extension-artifact.js
│   ├── package-extension.js
│   └── package-plugin.js
└── tests/
    └── *.test.js
```

结构规则：

- `core/` 和 `rendering/` 是 framework-neutral 天气、推荐和渲染逻辑。
- `commands/` 是统一扩展的声明式 command entry。
- `service/` 是 Fastify dashboard / Email / scheduler / secret 管理服务。
- `src/` 是 legacy OpenPet command adapter，可以使用 CommonJS 模块拆分。
- `extension/plugin.json` 是统一扩展 manifest source。
- `openpet-plugin/` 是 OpenPet 可安装包根目录，必须始终保持可验证。
- `openpet-plugin/index.js` 是构建产物，必须为单文件，不能依赖 runtime `require`。
- `release/` 是打包产物目录，不作为源码真相来源。

## 5. 后续开发顺序

任何后续功能都按以下顺序推进：

1. 读取 OpenPet 最新插件文档和示例。
2. 先更新对应契约文档：
   - 兼容 command-plugin manifest/config/命令/storage/network 变化更新 `docs/PLUGIN_CONTRACT.md`。
   - 统一 extension entries/service/dashboard/lifecycle/data ownership 变化更新 `docs/OPENPET_EXTENSION_ECOSYSTEM_BOUNDARY.md`。
3. 更新或补充测试，先覆盖契约变化。
4. 修改对应源码：`src/` 用于兼容 command adapter，`commands/` 用于 extension command entries，`service/` 用于 dashboard/Email/scheduler，`core/` 和 `rendering/` 用于共享业务逻辑。
5. 运行构建，刷新 `openpet-plugin/index.js`。
6. 打包两个 artifact 并运行 OpenPet 官方验证。
7. 更新 `docs/MIGRATION_NOTES.md` 与 `docs/WEATHER_MORNING_REPORT_EXTENSION_MIGRATION.md` 的实现记录、风险和完成状态。

新增能力必须优先回答：

- 是否需要新权限？
- 是否需要新 network host？
- 是否会让安装/更新后需要用户重新 enable？
- 是否会保存更多用户数据？
- 是否属于短生命周期 command runner、shell command entry、service/dashboard，还是共享 core/rendering？

## 6. 验证基线

本仓库本地验证：

```bash
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
npm run package:extension
npm run lint:extension
git diff --check
```

OpenPet 官方验证：

```bash
cd /Users/mango/project/codex/OpenPet
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/openpet-plugin
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-extension.zip
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
