# 天气早报

[English](README.md) | [简体中文](README.zh-CN.md)

天气早报现在是一个 **OpenPet JavaScript 扩展 / 插件**，用于输出简短的天气简报。

它从白名单天气源获取公开天气数据，再把结果转换成简洁、行动导向的建议，让 OpenPet 用桌宠气泡提醒用户是否需要带伞、防晒、调整穿搭，以及关注通勤、午间、晚间等关键时段风险。

## 状态

仓库现在已经包含插件实现、打包流程和迁移文档。

- 插件契约：`docs/PLUGIN_CONTRACT.md`
- 迁移计划：`docs/MIGRATION_NOTES.md`
- 总览：`docs/OPENPET_PLUGIN_REFACTOR_PLAN.md`
- 文档索引：`docs/README.md`

## 插件摘要

- 插件名称：`Weather Morning Report`
- 插件 id：`com.weather-morning-report.openpet`
- 兼容插件包：`.openpet-plugin.zip`
- 统一扩展包：`.openpet-extension.zip`
- 权限：`network`、`pet:say`、`storage`
- 网络 allowlist：`wttr.in`、`wttr.is`
- 命令：`refresh`、`announce`、`last`、`status`、`clear-cache`
- 扩展入口：commands、setup、loopback service、dashboard

## 开发

```bash
npm test
npm run build
npm run lint
npm run typecheck
npm run package:plugin
npm run package:extension
```

OpenPet 验证：

```bash
cd /Users/mango/project/codex/OpenPet
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/openpet-plugin
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-plugin.zip
npm run validate:plugin -- /Users/mango/project/codex/weather-morning-report/release/weather-morning-report.openpet-extension.zip
```

## 说明

- 兼容插件包使用单文件 `openpet-plugin/index.js` 作为入口。
- 统一扩展包面向当前 OpenPet main 声明 `entries.commands`、`entries.setup`、`entries.services` 和 `entries.dashboards`。
- 兼容 release 压缩包只包含 `plugin.json`、`config.schema.json`、`index.js` 和 `README.md`。
- 旧的 Python 服务代码已经作为迁移的一部分移除。
