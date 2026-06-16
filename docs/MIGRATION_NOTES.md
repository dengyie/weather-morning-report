# Weather Morning Report OpenPet Migration Notes

> **最新依据优先级：** 本迁移文档以 `/Users/mango/project/codex/OpenPet/docs/plugin-development.md`、`/Users/mango/project/codex/OpenPet/docs/plugin-ecosystem-rules.md`、`/Users/mango/project/codex/OpenPet/docs/plugin-submission-workflow-playbook.md` 以及 OpenPet `examples/plugins/*` 当前实现为准。若本文档与 OpenPet 最新文档冲突，执行时必须优先服从 OpenPet 最新文档，并回修本文档。

## 1. 迁移原则

本仓库已经从 Python 自托管天气早报服务切换为 OpenPet 原生 JS 插件工程。后续维护遵循：

- 保留天气早报的核心业务价值。
- 不把服务端能力伪装成 OpenPet 插件能力。
- 删除无用代码，而不是维护双产品形态。
- 任何实现以 `docs/PLUGIN_CONTRACT.md` 为稳定契约。
- OpenPet 官方验证优先于本项目自写假验证。

## 2. 能力取舍台账

### 2.1 已迁移的核心能力

| 旧 Python 能力 | 新 JS/OpenPet 落点 | 当前状态 |
| --- | --- | --- |
| wttr `format=j1` provider | `core/weather-provider.js`、`core/wttr-parser.js` | 已迁移 |
| `wttr.in` / `wttr.is` fallback | `core/weather-provider.js` | 已迁移 |
| 防御性字段解析 | `core/wttr-parser.js` | 已迁移 |
| 推荐阈值与风险信号 | `core/recommendation-engine.js` | 已迁移 |
| 早/中/晚重点时段 | `core/period-schedule.js` | 已迁移 |
| 文本报告 | `rendering/text-renderer.js` | 已迁移为宠物 summary 和 detail |
| 缓存 | `ctx.storage` in `src/commands.js` | 已迁移为小型 scoped storage |
| 命令入口 | `src/activate.js`、`src/commands.js` | 已迁移 |

### 2.2 已删除且不迁移的能力

| 删除范围 | 删除原因 | 后续替代 |
| --- | --- | --- |
| SMTP / 邮件投递 | OpenPet 插件不是邮件投递服务 | `ctx.pet.say()` 与命令返回值 |
| FastAPI / Web UI / HTML templates / static assets | OpenPet 配置由 Control Center schema 承载 | `config.schema.json` |
| SQLite / SQLAlchemy / Alembic | 插件没有数据库迁移生命周期 | `ctx.storage` 小对象 |
| jobs / worker / 后台调度 | OpenPet 当前是 command-style 短生命周期插件 | 用户或宿主触发命令 |
| Docker / compose / systemd | 插件通过 Control Center 安装 | `.openpet-plugin.zip` |
| Python package / CLI 发布链路 | 目标产物不再是 Python 包 | npm scripts + OpenPet validation |

这些删除是产品形态切换，不是暂时隐藏。后续不应恢复双栈维护。

## 3. 当前仓库结构

```text
weather-morning-report/
├── package.json
├── README.md
├── README.zh-CN.md
├── LICENSE
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
├── core/
│   ├── config.js
│   ├── weather-provider.js
│   ├── wttr-parser.js
│   ├── recommendation-engine.js
│   └── period-schedule.js
├── rendering/
│   └── text-renderer.js
├── src/
│   ├── activate.js
│   └── commands.js
├── scripts/
│   ├── build-plugin.js
│   ├── check-plugin-artifact.js
│   └── package-plugin.js
└── tests/
    ├── commands-integration.test.js
    ├── openpet-build.test.js
    ├── openpet-bundle-runtime.test.js
    ├── openpet-phase1.test.js
    ├── openpet-scripts.test.js
    ├── openpet-validate-zip.test.js
    ├── package-plugin.test.js
    ├── period-schedule.test.js
    ├── recommendation-engine.test.js
    ├── text-renderer.test.js
    ├── weather-provider.test.js
    └── wttr-parser.test.js
```

职责边界：

- `core/`：framework-neutral 天气、配置、provider、parser、推荐与时段逻辑。
- `rendering/`：framework-neutral 文案/视图模型渲染逻辑。
- `src/`：OpenPet command adapter，只保留宿主 `ctx`、storage、pet say、命令编排。
- `openpet-plugin/`：OpenPet 可安装包根目录，必须始终能被 OpenPet `validate:plugin` 检查。
- `openpet-plugin/index.js`：构建产物，必须为单文件，不依赖 runtime `require`。
- `scripts/`：构建、打包、产物检查。
- `tests/`：单元、集成、OpenPet 官方验证、打包验证。
- `release/`：构建生成的分发产物，不能手写维护。

## 4. 开发流程

### 4.1 修改契约

当需求涉及以下任何一项，必须先改 `docs/PLUGIN_CONTRACT.md`：

- 新命令或命令语义变化。
- 新配置字段或默认值变化。
- 新权限。
- 新 network host。
- storage key / shape 变化。
- 命令返回结构变化。
- 隐私边界变化。

### 4.2 修改源码

推荐顺序：

1. 写或更新测试。
2. 修改 `core/`、`rendering/` 或 `src/` 源码。
3. 运行 `npm test`。
4. 运行 `npm run build` 刷新 `openpet-plugin/index.js`。
5. 运行 artifact 检查和 OpenPet 验证。
6. 更新本文档的实现记录或风险清单。

### 4.3 构建

```bash
npm run build
```

产物要求：

- 输出 `openpet-plugin/index.js`。
- 单文件 JS。
- 导出 `activate(ctx)`。
- 不包含 runtime `require(`。
- 不访问 `process`、`fs`、Electron globals。
- 不使用 `eval` / `new Function`。
- 通过 `node --check openpet-plugin/index.js`。

当前 `scripts/build-plugin.js` 是项目内轻量 bundler。若未来换成正式 bundler，必须保留禁止 token 检查和 runtime smoke test。

### 4.4 打包

```bash
npm run package:plugin
```

输出：

```text
release/weather-morning-report.openpet-plugin.zip
```

zip 根目录必须是：

```text
plugin.json
config.schema.json
index.js
README.md
signature.json        # optional
```

不得包含：

- `src/`
- `tests/`
- `node_modules/`
- Python 源码。
- Docker/deploy 文件。
- `.git/`
- 临时文件。

## 5. 验证策略

### 5.1 本项目验证

```bash
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
git diff --check
```

覆盖目标：

- config normalization。
- wttr URL 构造与 encode。
- `wttr.in` 成功解析。
- `wttr.in` 失败后 fallback `wttr.is`。
- 非 2xx、空响应、坏 JSON、字段缺失。
- 数值 clamp：百分比、UV、风速、温度。
- hourly 缺失。
- 降雨、雷暴、强风、危险高温、UV、湿度阈值。
- morning/midday/evening period selection。
- zh-CN/en 文案。
- summary 长度与 detail 内容。
- cache freshness。
- 命令返回值 JSON-serializable。
- zip 白名单内容。
- bundle 禁止 runtime `require` / `process` / `fs` / `electron` / `eval`。

### 5.2 OpenPet 官方验证

```bash
cd /Users/mango/project/codex/OpenPet
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/openpet-plugin
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip
```

验证目标：

- `PluginInstallService` 可 inspect 插件目录。
- `PluginInstallService` 可 inspect `.openpet-plugin.zip`。
- manifest、paths、permissions、network allowlist 符合 OpenPet 当前规则。
- zip entry、symlink、path traversal 等安全规则由 OpenPet 官方逻辑兜底。

### 5.3 OpenPet 提交包 rehearsal

准备 OpenPet 插件提交包：

```bash
cd /Users/mango/project/codex/OpenPet
npm run create-plugin-submission-report -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip --output /Users/mango/project/codex/weather-morning-report/release/plugin-submission-report.md
npm run create-plugin-submission-pr -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip --output /Users/mango/project/codex/weather-morning-report/release/plugin-submission-pr.md
npm run create-plugin-submission-bundle -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip --output-dir /Users/mango/project/codex/weather-morning-report/release/plugin-submission-bundle
npm run validate-plugin-submission-bundle -- /Users/mango/project/codex/weather-morning-report/release/plugin-submission-bundle --require-ready
```

如果 release 需要严格 hash metadata，再按 OpenPet 最新命令增加 `--require-signature`。当前 OpenPet 文档说明 `signature.json` 只证明 hash metadata 覆盖，不建立公钥信任链。

## 6. 分阶段实施记录

### Phase 0：设计冻结

产物：

- `docs/OPENPET_PLUGIN_REFACTOR_PLAN.md`
- `docs/PLUGIN_CONTRACT.md`
- `docs/MIGRATION_NOTES.md`

结果：已完成。插件 id、权限、命令、配置和删除范围已明确。

### Phase 1：JS 插件骨架

产物：

- `package.json`
- `src/activate.js`
- `src/commands.js`
- `core/config.js`
- `openpet-plugin/plugin.json`
- `openpet-plugin/config.schema.json`
- `openpet-plugin/index.js`
- 基础测试

结果：已完成。仓库切入 npm scripts，插件 manifest/schema/entrypoint 可验证。

### Phase 2：Provider 与 parser

产物：

- `core/weather-provider.js`
- `core/wttr-parser.js`
- provider/parser tests

结果：已完成。实现 wttr 双 host fallback、防御解析和规范化快照。

### Phase 3：推荐引擎与文案

产物：

- `core/recommendation-engine.js`
- `core/period-schedule.js`
- `rendering/text-renderer.js`
- recommendation/period/render tests

结果：已完成。实现天气风险信号、时段摘要、zh-CN/en summary/detail。

### Phase 4：OpenPet SDK 集成

产物：

- `src/commands.js` 完整命令 handlers
- `tests/commands-integration.test.js`
- `tests/openpet-bundle-runtime.test.js`

结果：已完成。`refresh`、`announce`、`last`、`status`、`clear-cache` 可通过 fake OpenPet context 执行；provider 失败时支持新鲜缓存降级。

当前实现说明：

- 缓存逻辑在 `src/commands.js` 内实现，没有单独 storage 模块。
- `refresh` 在 `announceOnRefresh=false` 时默认不播报；若本次返回 cached report，可播报缓存摘要解释降级。
- 统计会记录刷新成功/失败时间、刷新次数和播报次数；`last` 也会复用同一播报计数。

### Phase 5：包与提交工作流

产物：

- `scripts/build-plugin.js`
- `scripts/check-plugin-artifact.js`
- `scripts/package-plugin.js`
- `openpet-plugin/README.md`
- `release/weather-morning-report.openpet-plugin.zip`
- package / OpenPet validation tests

结果：已完成。release zip 只包含 `plugin.json`、`config.schema.json`、`index.js`、`README.md`。

未做：

- `signature.json` 生成脚本暂未实现；当前按 OpenPet 文档属于 optional hash metadata，且 release 流程会在打包前重新构建 `openpet-plugin/index.js`。
- submission report / PR packet / bundle 可由 OpenPet sibling repo 命令生成，不在源码中手写。

### Phase 6：删除旧 Python 服务

删除：

- `src/weather_morning_report/`
- Python tests。
- `pyproject.toml`。
- `Dockerfile`。
- `compose.yaml`。
- `deploy/`。
- 旧 Python 服务相关文档。

结果：已完成。仓库不再暴露 Python 服务入口，README 只描述 OpenPet 插件安装、配置、隐私和验证。

### Phase 7：Core/Rendering 边界抽取

产物：

- `core/config.js`
- `core/weather-provider.js`
- `core/wttr-parser.js`
- `core/recommendation-engine.js`
- `core/period-schedule.js`
- `rendering/text-renderer.js`
- `tests/architecture-boundary.test.js`

结果：已完成。天气、配置、provider、parser、推荐、时段和文本渲染已从 OpenPet adapter 中抽出；`src/commands.js` 只负责 OpenPet `ctx`、storage、pet say 和命令编排。当前 command-plugin bundle 仍由 `scripts/build-plugin.js` 生成，并继续通过 OpenPet validator。

## 7. 生产级风险清单

| 风险 | 等级 | 触发条件 | 缓解 |
| --- | --- | --- | --- |
| OpenPet 契约变化 | P1 | sibling OpenPet 更新 manifest/runtime 规则 | 每次开发先读 OpenPet 最新 docs；CI 和本地使用 OpenPet validation |
| JS 重写规则漂移 | P1 | 新规则偏离旧 Python 核心天气风险判断 | 保留针对关键天气场景的 JS tests；必要时从 git history 补 fixture |
| runtime `require` 泄漏 | P1 | bundle 产物依赖 Node runtime | `check-plugin-artifact`、`node --check`、bundle runtime tests |
| provider 不稳定 | P2 | wttr host down 或返回坏 JSON | 双 host fallback、新鲜缓存、短错误摘要 |
| storage 超配额 | P2 | 保存 raw payload 或历史累积 | 只保存 normalized snapshot 和短文本；覆盖写 |
| 网络 allowlist 不合规 | P1 | 写入 URL/path/private host | manifest tests + OpenPet `validate:plugin` |
| 用户位置隐私 | P2 | `locationQuery` 包含精确地址 | README 明示会发送给 wttr，建议城市级查询 |
| 宠物播报噪音 | P3 | 用户频繁触发 `refresh` | `announceOnRefresh` 可关闭；debug 不走 `pet.say` |
| 更新后权限变化 | P2 | 后续新增 `pet:event` / `ai:chat` / 新 host | 先改契约和 README，接受 OpenPet update review / re-enable 流程 |
| 打包产物与源码不一致 | P2 | 手动编辑 `openpet-plugin/index.js` 或 release zip | 以 `core/` + `rendering/` + `src/` + build script 为源；发布前重新 build/package/validate |

## 8. 完成定义

当前重构完成必须同时满足：

- 仓库是 JS/OpenPet 插件工程，不再是 Python 服务工程。
- `openpet-plugin/plugin.json`、`config.schema.json`、`index.js` 可被 OpenPet 安装服务检查。
- `.openpet-plugin.zip` 可通过 OpenPet `validate:plugin`。
- `refresh`、`announce`、`last`、`status`、`clear-cache` 全部可运行。
- `wttr.in` 失败时 fallback `wttr.is`。
- 两个 provider 都失败时优先使用新鲜缓存。
- 无缓存且 provider 失败时错误短、清晰、无敏感信息。
- storage 不保存 raw payload，不超过 OpenPet 配额。
- README 明确隐私边界与安装方式。
- zip 包不包含旧 Python 服务端文件。
- CI 覆盖 npm test、artifact 检查、build、package、OpenPet validation。

提交 OpenPet catalog 前额外满足：

- 生成 submission report。
- 生成 PR packet。
- 生成 submission bundle。
- `validate-plugin-submission-bundle --require-ready` 通过。
- 若审核方要求签名元数据，补充 `signature.json` 并使用 `--require-signature`。

## 9. 后续演进建议

优先级从高到低：

1. 增加 wttr fixtures，覆盖晴天高 UV、小雨、大雨、雷暴、强风、高温、hourly 缺失。
2. 把 storage 读写抽成 `service/storage/` 或当前 adapter 内的独立模块，便于未来 shape migration。
3. 生成可选 `signature.json` hash metadata，并纳入 release preflight。
4. 如 OpenPet 后续支持调度能力，再评估定时早报；在官方能力出现前不做 daemon workaround。

## 10. 执行纪律

- OpenPet 最新文档优先于本仓库文档。
- `PLUGIN_CONTRACT.md` 优先于实现代码；契约改动先行。
- 不使用 OpenPet 内部未文档化 API 作为运行依赖。
- 不为绕过当前插件限制引入 localhost bridge、后台 daemon、外部代理服务、shell、任意 filesystem 或 secret config。
- 每次 release 前重新生成 `openpet-plugin/index.js` 和 `.openpet-plugin.zip`。
- 若发现本文档与实现不一致，要么修实现，要么先明确修改契约，不能让两者长期漂移。
