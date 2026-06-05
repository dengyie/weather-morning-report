# Weather Morning Report Design

Status: Approved for implementation  
Target repository: `dengyie/weather-morning-report` (public)  
Initial implementation language: Python  
Document date: 2026-06-06

## 1. Product Goal

Build a personal weather morning report that helps the recipient make useful
decisions within ten seconds:

- Do I need an umbrella?
- What should I wear?
- Do I need sunscreen or extra sun protection?
- Is there a weather risk during my commute or daytime activities?

The report should prioritize action over raw weather data while keeping the
language warm, natural, and restrained.

## 2. Recipient Context

The recommendation engine is initially tuned for this routine:

- Location: Changning District, Shanghai, China
- Primary commute: metro
- Outdoor commute exposure: about 10 minutes each way
- Midday outdoor exposure: usually 15-30 minutes
- Summer metro conditions: generally warm
- Report delivery time: 08:30 Asia/Shanghai

No real recipient name, email address, SMTP credential, or API key may appear
in the public repository.

## 3. Product Principles

1. Lead with the day's most important action.
2. Prefer useful recommendations over a list of measurements.
3. Never invent advice when the underlying data is unavailable or stale.
4. Show only the time periods relevant to the recipient's day.
5. Use calm, direct language; do not generate romantic messages or impersonate
   the sender.
6. Make risks prominent without making ordinary weather sound alarming.

## 4. Report Scope

### 4.1 Time Range

Recommendations cover 07:00-22:00.

Workday report periods:

- Morning commute: 07:00-10:00
- Midday: 11:00-14:00
- Evening commute: 17:00-20:00

Rest-day report periods:

- Morning: 08:00-11:00
- Afternoon: 12:00-17:00
- Evening: 18:00-22:00

Phase 1 uses weekday/weekend behavior only for internal architecture and does
not display holiday-sensitive wording until a reliable holiday source exists.

Phase 2 uses a Chinese holiday calendar to distinguish actual workdays,
holidays, and adjusted weekend workdays. If that source fails, it falls back
to the normal Monday-Friday rule.

### 4.2 Phase 1 Visible Content

Phase 1 displays only data reliably available from `wttr.in`:

- Dynamic subject
- Today's top action
- Umbrella recommendation
- Sunscreen recommendation
- Clothing recommendation
- Current condition and feels-like temperature
- Daily temperature range
- Three key time periods
- Humidity and wind when relevant
- A short weather-aware closing sentence

### 4.3 Deferred Content

These modules are designed but hidden until QWeather is integrated:

- Air quality and health guidance
- Official severe-weather warnings
- Chinese holiday calendar behavior
- Minute-level precipitation

## 5. Email Information Hierarchy

### 5.1 Dynamic Subject

The subject contains exactly one highest-priority action:

- `[下班有雨，记得带伞] 天气早报`
- `[紫外线很强，注意防晒] 天气早报`
- `[今天闷热，穿轻薄些] 天气早报`
- `[天气舒服，适合出门] 天气早报`

Subject priority:

1. Severe weather
2. Commute-period rain
3. High or low temperature
4. Strong ultraviolet exposure
5. General comfort

### 5.2 Body Structure

The HTML and plain-text versions use the same hierarchy:

1. Personal greeting
2. Risk-first opening sentence when needed
3. Three-line summary:
   - Today's focus
   - Umbrella
   - Sunscreen
4. Clothing recommendation
5. Three key time periods
6. Supporting weather details
7. Short natural closing

Example:

```text
早上好。

今日重点：午间可能有阵雨
带伞：建议带一把轻便伞
防晒：UV 8，午间外出注意防晒

穿搭：短袖或薄衬衫搭配轻薄下装；避免容易吸水的鞋。

关键时段
早通勤：多云，基本无雨，体感 24°C
午间：阵雨概率较高，UV 很强
晚通勤：多云，降雨概率低，体感 26°C

下午可能下雨，回家路上慢一点。
```

## 6. Recommendation Rules

All thresholds must live in configuration or dedicated rule modules and must
be covered by automated tests.

### 6.1 Umbrella Rules

The recipient has about ten minutes of outdoor exposure per commute, so advice
should be useful but not overly cautious.

Recommend carrying an umbrella when any condition is true:

- Morning or evening commute precipitation probability is at least 45%.
- Forecast description indicates rain, shower, drizzle, or thunder during a
  commute period.
- Expected precipitation during a commute period is meaningful.
- Severe precipitation or thunderstorm risk exists during 07:00-22:00.

Use a softer reminder when:

- Non-commute rain probability is 20-44%.
- Light rain is possible only around midday.

Do not recommend an umbrella solely because rain occurred before 07:00.

### 6.2 Sunscreen Rules

Recommendations assume 15-30 minutes of midday outdoor exposure.

- UV 0-2: no special sunscreen reminder
- UV 3-5: recommend normal sunscreen
- UV 6-7: emphasize sunscreen and shade
- UV 8+: strongly recommend sunscreen, shade, and reapplication if outdoors

Cloud or rain does not suppress the recommendation when forecast UV remains
high.

### 6.3 Clothing Rules

Advice should name garment categories without specifying colors or fashion
style.

Inputs:

- Feels-like temperature by relevant period
- Daily minimum and maximum
- Temperature change across the day
- Humidity
- Wind
- Rain risk

Initial summer-oriented rules:

- Feels-like >= 32°C: short sleeves or a breathable thin top with lightweight
  bottoms; emphasize heat and ventilation.
- Feels-like 27-31°C: short sleeves or a thin shirt with lightweight bottoms.
- Feels-like 22-26°C: short sleeves or a thin shirt; mention a very light layer
  only when morning/evening temperature is notably lower.
- Feels-like < 22°C: recommend a light outer layer.
- High humidity plus warm temperature: mention breathable, quick-drying
  fabrics.
- Meaningful rain risk: advise against shoes or garments that absorb water
  easily.
- Strong wind: recommend practical outerwear and secure loose items.

The wording must avoid repeating the same generic sentence every day.

### 6.4 Weather Risk Rules

Risk-first messaging overrides the normal warm opening when any high-impact
condition exists:

- Thunderstorm
- Heavy rain
- Strong wind
- Dangerous heat
- Official warning, once QWeather is enabled

Normal conditions retain a calm greeting before recommendations.

### 6.5 Closing Sentence

Generate one short closing based on the day's strongest useful context:

- Rain: `下午可能下雨，回家路上慢一点。`
- Heat: `今天会有些热，记得及时喝水。`
- Strong UV: `午间阳光强，出门记得做好防晒。`
- Comfortable: `今天天气还算舒服，祝你一天顺利。`

Do not generate romantic language or add a sender signature.

## 7. Data Sources

### 7.1 Phase 1

Primary source:

- `wttr.in` JSON API

Fallback source:

- `wttr.is`, the documented equivalent endpoint

Required Phase 1 fields:

- Current temperature and feels-like temperature
- Daily minimum and maximum temperature
- Hourly or three-hourly temperature
- Hourly precipitation probability and amount
- Thunder probability
- Humidity
- Wind speed
- UV index
- Weather description

### 7.2 Phase 2

Primary source:

- QWeather API

QWeather capabilities to enable:

- Current conditions
- Hourly forecast
- Daily forecast
- Weather indices
- Air quality
- Official weather warnings
- Minute-level precipitation when useful

QWeather credentials must be supplied only through environment variables.

## 8. Reliability and Failure Handling

### 8.1 Fetch Strategy

1. Query the primary provider.
2. Validate that required fields are present and timestamps are reasonable.
3. On failure, query the fallback provider.
4. On success, normalize data and save the latest valid snapshot.
5. On total provider failure, use the cached snapshot only if it is no more
   than 12 hours old.

### 8.2 Stale Data Policy

- Cache age <= 12 hours: generate the report and clearly label the data time.
- Cache age > 12 hours: do not generate recipient-facing action advice.
- If all sources fail and cache is stale, notify only the administrator.
- Do not send a low-value failure email to the recipient.

### 8.3 Phase 1 Scheduling

- Generate and send one report daily at 08:30 Asia/Shanghai.
- Do not implement hourly risk-change checks in Phase 1.

## 9. Architecture

Recommended package structure:

```text
weather-morning-report/
├── pyproject.toml
├── README.md
├── .env.example
├── src/weather_morning_report/
│   ├── cli.py
│   ├── config.py
│   ├── models.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── wttr.py
│   │   └── qweather.py
│   ├── recommendations/
│   │   ├── umbrella.py
│   │   ├── sunscreen.py
│   │   ├── clothing.py
│   │   ├── subject.py
│   │   └── periods.py
│   ├── rendering/
│   │   ├── html.py
│   │   └── text.py
│   ├── delivery/
│   │   └── smtp.py
│   ├── cache.py
│   └── service.py
├── templates/
│   ├── report.html
│   └── report.txt
├── tests/
│   ├── fixtures/
│   └── ...
└── docs/
    └── deployment.md
```

### 9.1 Normalized Weather Model

Provider-specific responses must be converted into a common model before any
recommendation logic runs.

Core model concepts:

- Location
- Observation timestamp
- Forecast source
- Current conditions
- Hourly forecast points
- Daily forecast
- UV data
- Optional air-quality data
- Optional warnings

Recommendation modules must not parse raw provider JSON.

### 9.2 CLI

Expected commands:

```text
weather-report preview
weather-report send
weather-report validate-config
```

- `preview` renders HTML and plain text without sending.
- `send` fetches, recommends, renders, caches, and sends.
- `validate-config` verifies required environment variables and connectivity.

## 10. Configuration and Security

The public repository must not include:

- Real names
- Real email addresses
- SMTP credentials
- API keys
- Production `.env` files
- Cached production weather data

Expected environment variables:

```text
TIMEZONE=Asia/Shanghai
LOCATION_NAME=Changning District, Shanghai
LOCATION_LATITUDE=
LOCATION_LONGITUDE=
RECIPIENT_NAME=
RECIPIENT_EMAIL=
ADMIN_EMAIL=
SMTP_HOST=
SMTP_PORT=
SMTP_USERNAME=
SMTP_PASSWORD=
QWEATHER_API_KEY=
```

Production configuration lives in a VPS `.env` file with permission `600`.

## 11. Email Rendering

The email must be multipart:

- Responsive HTML version
- Plain-text fallback

HTML requirements:

- Mobile-first and readable in QQ Mail
- One clear top-level focus
- Compact summary areas for umbrella, sunscreen, and clothing
- A small three-period table
- Clear risk emphasis without decorative clutter
- No remote tracking pixels
- No dependency on JavaScript

## 12. Testing and Acceptance

Every recommendation rule must have automated tests.

Required fixed-weather scenarios:

1. Sunny, hot, and strong UV
2. Rain during morning commute
3. Midday shower with dry commutes
4. Thunderstorm during evening commute
5. Warm and highly humid
6. Strong wind and cooling
7. Comfortable all day
8. Primary provider failure with valid cache
9. All provider data older than 12 hours

Acceptance criteria:

- Dynamic subject matches the highest-priority action.
- Umbrella advice uses commute-aware thresholds.
- Sunscreen advice matches UV thresholds.
- Clothing advice names useful garment categories.
- Workday and rest-day period structures are supported.
- HTML and plain-text messages remain readable.
- Provider failures follow the documented degradation policy.
- Automated tests cover all decision rules.
- Repository scanning finds no secrets, real names, or real email addresses.
- The new project does not modify the existing VPS weather script, cron, or
  `sendmail.py` until a separate deployment decision is made.

## 13. Delivery Plan

### Phase 1

- Create public GitHub repository `dengyie/weather-morning-report`.
- Build Python project structure.
- Implement normalized weather model.
- Implement `wttr.in` primary and `wttr.is` fallback providers.
- Implement cache and stale-data behavior.
- Implement recommendation engine.
- Implement HTML and plain-text rendering.
- Implement SMTP delivery from environment configuration.
- Add fixed fixtures and automated tests.
- Document local usage and future VPS deployment.
- Do not alter the existing VPS weather script or cron.

### Phase 2

- Add QWeather provider and make it primary.
- Enable air quality, official warnings, weather indices, and holiday-aware
  wording.
- Validate QWeather usage remains within the free monthly request allowance.
- Decide separately when to deploy and replace the existing VPS script.

## 14. Confirmed Decisions

- Action advice is the primary goal; tone is warm but restrained.
- Relevant time range is 07:00-22:00.
- Recommendations account for a metro commute with about ten minutes outdoors.
- Sunscreen advice assumes 15-30 minutes outdoors around midday.
- Severe risks override the normal greeting.
- Subject lines contain one highest-priority action.
- The body begins with today's focus, umbrella advice, and sunscreen advice.
- Clothing recommendations identify garment categories without prescribing
  style or color.
- Three key periods are shown instead of a full hourly list.
- Workdays and rest days use different period framing.
- Chinese holiday handling is deferred until a reliable source is integrated.
- Reports use responsive HTML with a plain-text fallback.
- Phase 1 sends only one report at 08:30.
- The new project is public and fully anonymized.
- The implementation language is Python.
- The new project is independent from the current VPS scripts.

