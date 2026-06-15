# Weather Morning Report OpenPet Plugin Contract

> **最新依据优先级：** 本契约以 `/Users/mango/project/codex/OpenPet/docs/plugin-development.md`、`/Users/mango/project/codex/OpenPet/docs/plugin-ecosystem-rules.md`、`/Users/mango/project/codex/OpenPet/docs/plugin-submission-workflow-playbook.md` 以及 OpenPet `examples/plugins/*` 当前实现为准。若本文档与 OpenPet 最新文档冲突，执行时必须优先服从 OpenPet 最新文档，并回修本文档。

## 1. 契约目标

本文档定义 Weather Morning Report 作为 OpenPet JS 插件时对宿主、用户、测试和后续实现者承诺的稳定边界。

产品定位：桌宠天气助手，把公开天气数据转成短、明确、行动导向的提醒，例如带伞、防晒、穿搭、通勤/午间/晚间风险。

所有实现、测试、README、CI、打包脚本和 release artifact 都必须遵守本文档。

## 2. OpenPet 宿主边界

### 2.1 插件包形态

OpenPet 当前支持：

```text
my-plugin/
├── plugin.json
├── index.js
├── config.schema.json   # optional
└── signature.json       # optional
```

支持安装来源：

- 插件目录。
- `.openpet-plugin.zip`，当前首选公开格式。
- `.ibot-plugin.zip`，仅作为旧包兼容。

安装前 OpenPet 会检查：

- 根目录存在 `plugin.json`。
- `main`、`configSchema` 是安全相对路径。
- zip entry、绝对路径、`..`、NUL、逃逸 symlink 均被拒绝。
- 权限、网络 allowlist、命令、签名 hash metadata、文件 hash、package hash。
- 安装或更新后默认 disabled，需要用户手动 enable。

### 2.2 运行时模型

OpenPet local plugin runner 当前是短生命周期隔离 runner：

- 只在用户或宿主触发命令时运行。
- 入口必须导出 `activate(ctx)`。
- 支持 CommonJS `module.exports = function activate(ctx) {}`。
- 也接受 ESM 风格 `export default function activate(ctx) {}`。
- 可以返回 command handler map，也可以通过 `ctx.commands.register()` 注册命令。
- 每次命令运行都应重新计算瞬态状态。
- 不能依赖 module-level 内存跨命令保留。
- 命令结果必须 JSON-serializable。
- 插件不能依赖 runtime `require`、`process`、Electron globals、shell 或任意 filesystem。
- OpenPet runner 实际读取 manifest `main` 文件；本项目发布前必须把模块化源码 bundle 为单个 `openpet-plugin/index.js`。

### 2.3 SDK 与权限

OpenPet 当前允许权限：

- `pet:say`
- `pet:action`
- `pet:event`
- `ai:chat`
- `storage`
- `network`
- `commands`

本插件第一版只申请：

```json
["network", "pet:say", "storage"]
```

权限理由：

| Permission | 使用原因 |
| --- | --- |
| `network` | 通过 `ctx.network.fetch()` 请求 wttr 公网天气 JSON |
| `pet:say` | 用桌宠气泡播报天气摘要 |
| `storage` | 缓存最近一次精简天气结果、建议、错误摘要和统计 |

暂不申请：

- `pet:action`：不同 pet pack 的 action id 不稳定，不能假设动作存在。
- `pet:event`：首版没有必须被宿主结构化消费的事件。
- `ai:chat`：天气规则可本地确定，不引入 AI 调用成本与隐私面。
- `commands`：manifest commands 已足够，不需要运行时动态注册额外命令。

新增权限必须先更新本文档，并在 README / release notes 中说明用户影响。

### 2.4 网络规则

OpenPet 网络代理硬规则：

- 需要 `network` 权限。
- 只允许 HTTPS。
- host 必须命中 `network.allowlist`。
- allowlist 只写公共 DNS host，可选显式端口，例如 `api.example.com` 或 `api.example.com:8443`。
- allowlist 不能包含 scheme、path、query、credentials。
- 不允许 `localhost`、私有 IP、裸 IPv4/IPv6 host、非 HTTPS。
- method 只支持 `GET`、`POST`。
- 敏感 header 如 `authorization`、`cookie` 会被拒绝。
- request body、response body 有大小限制。
- redirect 必须仍落在 allowlisted HTTPS host。

本插件只访问公开天气源：

```json
{
  "network": {
    "allowlist": ["wttr.in", "wttr.is"]
  }
}
```

不得要求用户在 config 中粘贴 API key、bearer token、cookie 或私有服务地址。

### 2.5 配置规则

OpenPet config schema 当前只支持 object properties：

- `string`
- `number`
- `boolean`

支持字段：

- `title`
- `description`
- `default`
- `enum`
- `required`

配置是普通应用设置，不是 secret store。本插件配置必须保持人类可编辑、默认可运行、无秘密信息。

### 2.6 Storage 规则

`ctx.storage` 是唯一持久化能力：

- 每插件总量 64KB。
- 单 value 16KB。
- key 只能使用安全字符。
- 只保存小型 normalized state。
- 不保存 raw wttr payload、历史归档、二进制、secret。
- storage shape 必须有版本意识，便于未来懒迁移。

## 3. Manifest 契约

`openpet-plugin/plugin.json`：

```json
{
  "id": "com.weather-morning-report.openpet",
  "name": "Weather Morning Report",
  "version": "1.0.0",
  "description": "Action-oriented weather reports for OpenPet, with umbrella, sunscreen, clothing, and period risk reminders.",
  "main": "index.js",
  "configSchema": "config.schema.json",
  "permissions": ["network", "pet:say", "storage"],
  "network": {
    "allowlist": ["wttr.in", "wttr.is"]
  },
  "commands": [
    { "id": "refresh", "title": "Refresh weather report" },
    { "id": "announce", "title": "Announce weather report" },
    { "id": "last", "title": "Announce last report" },
    { "id": "status", "title": "Show plugin status" },
    { "id": "clear-cache", "title": "Clear cached weather" }
  ]
}
```

Manifest 兼容规则：

- `id` 发布后视为稳定身份，不改名。
- `commands[].id` 发布后视为用户和宿主可见 API，不做破坏性改名。
- 新增命令必须 additive。
- 新增权限或 host 会触发 OpenPet 更新审查和用户重新 enable，应避免“预留式”申请。
- Catalog metadata 如后续提交到 OpenPet catalog，应使用 `openpetApiVersion`，具体值以 OpenPet catalog 最新文档为准。

## 4. 命令契约

| Command id | Title | 行为 | `pet.say` | Storage 副作用 |
| --- | --- | --- | --- | --- |
| `refresh` | Refresh weather report | 拉取天气、生成 summary/detail/advice | 仅当 `announceOnRefresh=true`；如果 provider 失败但使用缓存，可播报缓存摘要以解释降级 | 写入最近成功快照、建议、摘要、详情、统计；失败时写短错误摘要 |
| `announce` | Announce weather report | 拉取天气并播报；失败时尝试新鲜缓存 | 是 | 同 `refresh` |
| `last` | Announce last report | 读取最近成功报告并播报 | 是；无缓存时播报缺少缓存提示 | 不改变天气缓存；可递增轻量统计 |
| `status` | Show plugin status | 返回缓存年龄、最近成功/失败、配置摘要 | 否 | 无 |
| `clear-cache` | Clear cached weather | 清空插件私有 storage | 否，除非后续契约明确增加短提示 | 清空 |

通用命令要求：

- handler 返回 JSON-serializable 小对象。
- 错误消息短、可读、无 raw response、无敏感 header。
- 不做无限重试。
- 不依赖命令之间的内存状态。

## 5. 首版非目标

- 不做自动定时后台播报，因为 OpenPet 当前插件不是 long-lived daemon。
- 不做邮箱、Webhook、推送。
- 不做 AI 改写；规则引擎保持 deterministic。
- 不默认触发 pet action。
- 不连接私有天气 API 或需要 key 的商业天气服务。
- 不通过 localhost bridge、外部代理服务或 shell 绕过 OpenPet 权限模型。

## 6. 配置契约

`openpet-plugin/config.schema.json`：

| Key | Type | Default | Enum | 说明 |
| --- | --- | --- | --- | --- |
| `locationName` | `string` | `Shanghai` | 无 | 展示给用户和宠物的地点名 |
| `locationQuery` | `string` | `Shanghai` | 无 | 发送给 wttr 的查询值 |
| `language` | `string` | `zh-CN` | `["zh-CN", "en"]` | 输出语言 |
| `reportType` | `string` | `morning` | `["morning", "midday", "evening"]` | 重点时段 |
| `announceOnRefresh` | `boolean` | `true` | 无 | `refresh` 后是否播报 |
| `cacheMaxAgeMinutes` | `number` | `120` | `[30, 60, 120, 240]` | provider 失败时可接受的新鲜缓存时间 |
| `includeSource` | `boolean` | `false` | 无 | summary 是否显示数据源 host |

校验与归一化：

- `locationQuery` 空白时回退 `locationName`。
- `locationName` 空白时回退 `locationQuery`。
- `language` 非法时回退 `zh-CN`。
- `reportType` 非法时回退 `morning`。
- `cacheMaxAgeMinutes` 非法时回退 `120`。
- `announceOnRefresh` 只有显式 `false` 才关闭。
- `includeSource` 只有显式 `true` 才开启。
- 不允许 config 包含 API key、token、cookie、localhost URL。

## 7. 数据模型契约

### 7.1 标准化天气快照

只保存与推荐和展示相关的字段：

```js
{
  schemaVersion: 1,
  location: {
    name: "Shanghai",
    query: "Shanghai"
  },
  source: {
    host: "wttr.in",
    url: "https://wttr.in/Shanghai?format=j1"
  },
  fetchedAt: "2026-06-16T00:00:00.000Z",
  current: {
    condition: "Partly cloudy",
    description: "Partly cloudy",
    temperatureC: 27,
    feelsLikeC: 29,
    humidityPercent: 78,
    windSpeedKph: 15,
    uvIndex: 7
  },
  daily: {
    date: "2026-06-16",
    minimumTemperatureC: 24,
    maximumTemperatureC: 31,
    uvIndex: 8
  },
  hourly: [
    {
      forecastAtHour: 900,
      condition: "Light rain",
      description: "Light rain",
      temperatureC: 26,
      feelsLikeC: 28,
      precipitationProbabilityPercent: 70,
      precipitationMm: 1.2,
      thunderProbabilityPercent: 30,
      humidityPercent: 82,
      windSpeedKph: 18,
      uvIndex: 3
    }
  ]
}
```

### 7.2 推荐结果

```js
{
  schemaVersion: 1,
  subject: "天气早报 · 上海",
  focus: "今天午后有降雨风险，通勤建议带伞。",
  umbrella: "建议带伞。",
  sunscreen: "午间紫外线偏强，注意防晒。",
  clothing: "短袖外加轻薄外套即可。",
  closing: "出门前再看一眼天空，宠物也会替你盯着。",
  periods: [
    { "label": "通勤", "summary": "有小雨概率，路面可能湿滑。" },
    { "label": "午间", "summary": "紫外线偏强，户外注意防晒。" },
    { "label": "晚间", "summary": "降雨转弱，体感闷热。" }
  ],
  signals: {
    "highestRiskLevel": 2,
    "umbrellaLevel": 2,
    "sunscreenLevel": 2,
    "clothingLevel": 1,
    "targetPrecipitationLevel": 2,
    "thunderstorm": false,
    "strongWind": false,
    "dangerousHeat": false
  }
}
```

### 7.3 命令返回值

成功：

```js
{
  "ok": true,
  "cached": false,
  "summary": "天气早报 · 上海 · 27°C/体感29°C · 建议带伞 · 注意防晒",
  "detail": "今日重点：...\n带伞：...\n防晒：...",
  "snapshot": {},
  "advice": {},
  "source": "wttr.in",
  "fetchedAt": "2026-06-16T00:00:00.000Z",
  "warnings": []
}
```

可恢复失败：

```js
{
  "ok": false,
  "reason": "missing-cache"
}
```

provider 全失败且无缓存时可以抛出短错误，例如 `Weather providers unavailable: ...`，由 OpenPet 记录插件日志。

## 8. Storage 契约

Storage keys：

| Key | Value | 限制 |
| --- | --- | --- |
| `state:schemaVersion` | number | 当前为 `1` |
| `last:snapshot` | normalized snapshot | 不保存 raw wttr payload |
| `last:advice` | normalized advice | 不保存冗余历史 |
| `last:summary` | string | 控制在 500 字以内 |
| `last:detail` | string | 控制在 3000 字以内 |
| `last:error` | `{ message, at, providerHosts }` | 不包含 raw response |
| `stats` | `{ refreshCount, announceCount, lastSuccessAt, lastFailureAt }` | 小对象 |

写入策略：

- 每次成功刷新覆盖 `last:*`，不累积历史。
- provider 失败时只写短错误摘要。
- `clear-cache` 调用 `ctx.storage.clear()`。
- 未来 storage shape 变更时，在命令开始时执行懒迁移。
- 若统计字段未来扩展，必须保持缺字段可读、可默认化。

## 9. Provider 契约

### 9.1 请求策略

按顺序尝试：

1. `https://wttr.in/${encodeURIComponent(locationQuery)}?format=j1`
2. `https://wttr.is/${encodeURIComponent(locationQuery)}?format=j1`

请求 options：

```js
{
  "headers": {
    "accept": "application/json"
  }
}
```

不得发送 user-agent、authorization、cookie 或任何敏感 header。

### 9.2 失败策略

一次命令内：

1. 请求 `wttr.in`。
2. 网络错误、非 2xx、JSON parse 失败、必需字段缺失都记为 provider failure。
3. 请求 `wttr.is`。
4. 两者都失败：
   - 若 `last:snapshot` 在 `cacheMaxAgeMinutes` 内，返回 cached report，`warnings` 包含 provider failure 摘要。
   - 若无新鲜缓存，写入 `last:error` 并抛出短错误。

不做无限重试；OpenPet 命令应快速结束。

### 9.3 字段防御解析

wttr 是外部数据源，必须全部 defensive parsing：

- `toFiniteNumber(value, fallback)` 处理空值、字符串、非数字。
- 百分比 clamp 到 `0..100`。
- UV clamp 到 `0..30`。
- 温度允许负值，但非数字回退 `0` 或 `null`。
- wind speed 非数字回退 `0`。
- hourly 缺失时返回空数组，period summary 显示“暂无可靠分时数据”或对应英文。
- description 缺失时使用 `Unknown` / `未知天气`。
- JSON 体过大由 OpenPet 网络代理限制；插件不额外存 raw payload。

## 10. 推荐引擎契约

### 10.1 核心阈值

```js
const THUNDER_PROBABILITY_THRESHOLD = 40
const MEANINGFUL_PRECIPITATION_MM = 0.5
const STRONG_WIND_KPH = 40
const DANGEROUS_HEAT_C = 38
```

推荐等级：

- `0`：无明显风险。
- `1`：轻微提醒。
- `2`：建议采取行动。
- `3`：强风险，需要明确警告。

### 10.2 时段规则

`morning`：

- 通勤：`700..1000`
- 午间：`1100..1500`
- 晚间：`1700..2100`

`midday`：

- 下午：`1300..1700`
- 晚间：`1700..2100`

`evening`：

- 晚间：`1800..2300`
- 夜间：`2300..2400`
- 次日早晨：若 wttr 提供足够数据再启用；首版不强承诺。

### 10.3 信号生成

必须覆盖：

- 降雨概率。
- 降雨量。
- 雷暴概率。
- 紫外线。
- 强风。
- 危险高温。
- 体感温度。
- 湿度导致的闷热提示。

优先级：

1. 雷暴与危险高温优先于普通带伞/穿搭。
2. 强风会提高出行风险，但不等同于降雨。
3. 紫外线建议只在午间或 UV 高时明显输出。
4. 无 hourly 时仍基于 current/daily 给出保守建议。

### 10.4 多语言输出

首版支持：

- `zh-CN`
- `en`

语言影响：

- subject。
- focus。
- umbrella / sunscreen / clothing / closing。
- period label。
- missing cache / provider failure 等用户可见消息。

不使用 AI 翻译，避免命令结果不稳定。

## 11. 文本渲染契约

### 11.1 宠物气泡 summary

中文：

```text
天气早报 · 上海 · 27°C/体感29°C · 建议带伞 · 注意防晒
```

英文：

```text
Weather report · Shanghai · 27°C, feels 29°C · Bring an umbrella · Use sunscreen
```

约束：

- 默认 120 字以内。
- 不包含完整 JSON。
- 不包含 raw URL。
- `includeSource=true` 时最多只显示 provider host。
- 多风险时最多保留 3 个行动建议。

### 11.2 detail 文本

用于命令返回、Control Center 展示或调试：

```text
今日重点：午后有降雨风险，通勤建议带伞。
带伞：建议带伞。
防晒：午间紫外线偏强，注意防晒。
穿搭：短袖外加轻薄外套即可。
关键时段：
- 通勤：有小雨概率，路面可能湿滑。
- 午间：紫外线偏强，户外注意防晒。
- 晚间：降雨转弱，体感闷热。
```

约束：

- 面向用户，不输出 debug 堆栈。
- 不输出 raw provider URL，除非明确需要 source host。
- 控制在 OpenPet storage 单 value 限制内。

## 12. 安全、隐私与滥用边界

必须满足：

- 不收集邮箱、SMTP、管理员密码、OpenPet 内部状态。
- 不需要 API key。
- 不把 token、cookie、私有 URL 放入 config 或 header。
- 只把 `locationQuery` 发给 `wttr.in` / `wttr.is`。
- 错误日志不包含 raw response、用户完整配置 dump、敏感 header。
- storage 不保存 raw payload，不保存多日历史。
- 网络 allowlist 只包含天气源 host。
- 命令返回 JSON-serializable 小对象。

README 必须说明：

- 用户配置的地点查询会发送给 wttr 公网服务。
- 插件本地只保存最近一次精简天气结果和统计。
- 用户如介意精确位置隐私，应使用城市级或区域级查询。

## 13. 可观测性契约

OpenPet 已记录插件命令开始、完成、失败。本插件通过命令返回值补充可观测信息：

- `ok`
- `cached`
- `source`
- `fetchedAt`
- `warnings`
- `lastError`
- `hasCache`
- `cachedAt`

插件内部不使用 `pet.say()` 输出 debug 信息。

## 14. 构建与产物契约

`npm run build` 必须生成：

```text
openpet-plugin/index.js
```

产物要求：

- 单文件 JS。
- 导出 `activate(ctx)`。
- 不包含 runtime `require(`。
- 不访问 `process`、`fs`、`child_process`、Electron globals。
- 不使用 `eval` / `new Function`。
- 通过 `node --check openpet-plugin/index.js`。

`npm run package:plugin` 必须生成：

```text
release/weather-morning-report.openpet-plugin.zip
```

zip 根目录只允许包含：

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

## 15. 兼容性与升级契约

- patch/minor 升级不得删除已有命令。
- 新增命令必须 additive。
- 新增权限或 host 必须升级版本、更新 README、更新本文档，并接受 OpenPet 更新审查。
- storage shape 变更必须懒迁移，不能要求用户手动清空缓存。
- 不能把旧 Python 服务能力重新引回插件主线，除非 OpenPet 平台新增相应官方能力。

