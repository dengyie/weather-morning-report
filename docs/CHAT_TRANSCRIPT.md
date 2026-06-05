# Weather Morning Report Planning Transcript

Date: 2026-06-06  
Participants: User and Codex  
Purpose: Preserve the product decisions made before development.

This record focuses on the weather morning report redesign discussion. It
captures the questions, recommendations, user answers, and confirmed decisions
that define the new standalone project.

## Starting Context

The existing VPS weather email was reported as too simple and lacking a clear
theme. The requested redesign should take inspiration from consumer weather
briefings such as Moji Weather, provide clothing advice based on temperature,
provide sunscreen advice based on ultraviolet intensity, and make the most
important action obvious.

The user requested a planning and challenge phase before development. The
project document should be written first, and implementation should follow the
approved document.

## Decision Transcript

### 1. Primary Goal

**Question**

What is the most important goal of the report?

- Action advice first
- Emotional companionship first
- Professional and comprehensive forecast first

**Codex recommendation**

Use action advice as the primary structure and a warm, natural tone for the
delivery. The recipient should understand what to wear, whether to carry an
umbrella, and whether sunscreen is needed within ten seconds.

**User answer**

Accepted.

**Confirmed decision**

Action advice is primary. Tone is warm and natural but not overly sentimental.

### 2. Relevant Time Range

**Question**

Which part of the day should the report analyze?

**Codex recommendation**

Focus on 07:00-22:00, especially:

- Morning commute: 07:00-10:00
- Evening commute: 17:00-20:00
- Daytime high temperature, UV peak, and precipitation risk

**User answer**

Accepted.

**Confirmed decision**

Recommendations cover 07:00-22:00 and prioritize commute and midday activity.

### 3. Commute Pattern

**Question**

How long is the recipient exposed outdoors during the commute?

**User answer**

The primary commute is by metro, with about ten minutes outdoors each way.

**Confirmed decision**

Umbrella advice should be useful but restrained. A small chance of rain should
not automatically trigger a strong umbrella recommendation.

Initial guidance:

- Recommend an umbrella when commute-period precipitation probability reaches
  approximately 45%, or when rain is explicitly forecast.
- Use a softer reminder for low-probability light rain.
- Escalate thunderstorms, heavy rain, and strong wind.

### 4. Heat and Clothing Preference

**Question**

Should clothing guidance assume sensitivity to cold, heat, or average
conditions?

**Codex recommendation**

Use light, layered clothing and mention a thin outer layer when useful.

**User answer**

Summer is approaching and the metro is generally warm. Accepted with a
summer-oriented assumption.

**Confirmed decision**

Summer clothing guidance should prioritize breathable, lightweight clothing
and avoid routinely warning about cold metro air conditioning.

### 5. Midday Outdoor Exposure and Sunscreen

**Question**

Does the recipient usually go outdoors around midday?

**Codex recommendation**

Assume 15-30 minutes outdoors around midday and use graded UV advice:

- UV 3+: recommend sunscreen
- UV 6+: emphasize sunscreen and shade
- UV 8+: strongly recommend protection and reapplication when outdoors

**User answer**

This matches the recipient's routine.

**Confirmed decision**

Sunscreen recommendations assume 15-30 minutes of midday outdoor exposure.

### 6. Risk-First Messaging

**Question**

Should severe weather override the normal warm opening?

**Codex recommendation**

Yes. Thunderstorms, heavy rain, strong wind, or dangerous heat should appear in
the subject and first line.

**User answer**

Accepted.

**Confirmed decision**

High-impact weather uses risk-first messaging. Normal weather retains a warm
opening.

### 7. Dynamic Subject

**Question**

What style should the email subject use?

**Codex recommendation**

Use an action-oriented dynamic subject that highlights one highest-priority
message, for example:

- `[下班有雨，记得带伞] 天气早报`
- `[紫外线很强，注意防晒] 天气早报`
- `[今天闷热，穿轻薄些] 天气早报`
- `[天气舒服，适合出门] 天气早报`

Priority:

1. Severe weather
2. Commute-period rain
3. High or low temperature
4. Strong UV
5. Comfortable conditions

**User answer**

Accepted.

**Confirmed decision**

The subject contains one highest-priority action.

### 8. Multiple Important Conditions

**What Codex found**

The existing weather provider exposes hourly temperature, feels-like
temperature, precipitation probability, thunder probability, wind, humidity,
and UV. A sample day showed strong midday UV and a high midday rain
probability, demonstrating that a single raw summary can miss important
actions.

**Question**

How should the report present multiple important conditions?

**Codex recommendation**

Keep one action in the subject, then show three conclusions at the top of the
body:

```text
今日重点：中午可能有小雨
带伞：建议带一把轻便伞
防晒：UV 10，仍需认真防晒
```

**User answer**

Accepted.

**Confirmed decision**

The body begins with today's focus, umbrella advice, and sunscreen advice.

### 9. Clothing Advice Detail

**Question**

How specific should clothing advice be?

**Codex recommendation**

Name garment categories without specifying colors or fashion style. Combine
feels-like temperature, daily temperature change, and precipitation risk.

Example:

```text
穿搭：短袖或薄衬衫配轻薄下装；下午可能有雨，避免容易吸水的鞋。
温差：早晚约 21°C，怕凉可以带一件很薄的外搭。
```

Do not provide makeup, hairstyle, or detailed styling suggestions.

**User answer**

Accepted the recommendation.

**Confirmed decision**

Clothing guidance should be concrete enough to name useful item categories but
must not prescribe personal style.

### 10. Air Quality

**Question**

Should air quality be included?

**Codex recommendation**

Include it at a low priority during normal conditions and promote it only when
pollution is meaningful.

**User answer**

Accepted.

**Confirmed decision**

Air quality belongs in the future report, but it is deferred until a reliable
data source is integrated.

### 11. Key Time Periods

**Question**

Should the report include a time-based forecast?

**Codex recommendation**

Show only three important periods instead of a full hourly list:

```text
早通勤 07:00-10:00
午间 11:00-14:00
晚通勤 17:00-20:00
```

**User answer**

Accepted.

**Confirmed decision**

The report shows three compact key periods.

### 12. Failure Handling

**Question**

What should happen when weather or air-quality sources fail?

**Codex recommendation**

Use two-level degradation:

1. Query a fallback source when the primary source fails.
2. Use the most recent successful snapshot when all sources fail.

If cached data is older than 12 hours, do not send action advice to the
recipient. Send a short failure notification only to the administrator.

**User answer**

Accepted.

**Confirmed decision**

Provider fallback, caching, a 12-hour stale threshold, and recipient-facing
failure silence are required.

### 13. Tone and Closing

**Question**

How personal should the report sound?

**Codex recommendation**

Use a warm but restrained tone:

- A fixed personal greeting configured outside the public repository
- Natural practical advice
- One short weather-aware closing
- No generated romantic language
- Do not impersonate the sender
- Do not add the sender's signature automatically

**User answer**

Accepted.

**Confirmed decision**

The report should feel considerate without pretending to be a personal message
written by the sender.

### 14. Weekday and Weekend Behavior

**Question**

Should workdays and weekends use the same structure?

**Codex recommendation**

Use commute-oriented periods on workdays and general outing periods on rest
days. Continue sending at 08:30.

**User answer**

Accepted.

**Confirmed decision**

Workday and rest-day structures differ.

### 15. Chinese Holidays and Adjusted Workdays

**Question**

Should Chinese public holidays and adjusted weekend workdays follow the actual
calendar?

**Codex recommendation**

Use a Chinese holiday calendar and fall back to Monday-Friday rules if it
fails.

**User answer**

Accepted.

**Confirmed decision**

Actual workday handling is required when a reliable holiday source becomes
available.

### 16. Email Format

**Question**

Should the project continue using plain-text email or move to HTML?

**Codex recommendation**

Use responsive HTML with a plain-text fallback:

- Strong visual hierarchy for today's focus
- Compact umbrella, sunscreen, and clothing sections
- A compact key-period table
- Clear risk emphasis
- Mobile and QQ Mail readability
- No decorative clutter

**User answer**

Accepted.

**Confirmed decision**

The project sends multipart HTML and plain-text email.

### 17. Weather Provider Strategy

**Question**

Should the project use a reliable China-local weather API?

**Codex recommendation**

Use QWeather as the future primary source and `wttr.in` as a fallback. Keep API
keys outside code and documentation.

**User answer**

Accepted.

**What Codex found**

QWeather's weather and essential services currently provide a free tier for
the first 50,000 requests per month. `wttr.in` is a public service without an
API key or paid SLA.

**Confirmed decision**

- Phase 1 uses `wttr.in` and `wttr.is`.
- Phase 2 adds QWeather as primary.
- Keys live only in environment configuration.

### 18. Additional Risk Notifications

**Question**

Should the project send additional alerts when the forecast changes after the
morning report?

**Codex recommendation**

Do not add hourly checks in Phase 1. First stabilize the daily 08:30 report,
then consider risk-change notifications.

**User answer**

Accepted.

**Confirmed decision**

Phase 1 sends only the daily 08:30 report.

### 19. Standalone Public Project

**User request**

Upgrade the weather automation into a project and synchronize it to GitHub.

**What Codex found**

- GitHub account: `dengyie`
- Git identity and authentication were confirmed locally.
- The target workspace was not yet a Git repository

**Question**

Should the public repository contain the real recipient name or email?

**Codex recommendation**

Fully anonymize the repository. Use environment variables and fictional sample
values.

**User answer**

Accepted.

**Confirmed decision**

The target public repository is `dengyie/weather-morning-report`, and it must
contain no real personal information or credentials.

### 20. Implementation Language

**Question**

Should the standalone project remain Bash or move to Python?

**Codex recommendation**

Use Python because the project needs multiple providers, normalized data,
caching, recommendation rules, HTML templates, and automated tests.

**User answer**

Accepted.

**Confirmed decision**

The standalone project is a Python project.

### 21. Delivery Phases

**Question**

Should development wait for a QWeather key?

**Codex recommendation**

Use two phases:

1. Build a complete, testable Phase 1 with `wttr.in`.
2. Add QWeather and advanced capabilities later.

**User answer**

Accepted.

**Confirmed decision**

Phase 1 development is not blocked by a QWeather key.

### 22. Relationship to Existing VPS Scripts

**Initial discussion**

Codex proposed replacing the old script after validation.

**User correction**

The new project is unrelated to the old script for now. Create the new project
first and leave the existing scripts unchanged.

**Confirmed decision**

The new project must not modify the existing VPS weather script, cron, or
`sendmail.py` until a separate deployment decision is made.

### 23. Phase 1 Visible Modules

**Question**

How should unavailable Phase 1 modules be handled?

**Codex recommendation**

Show only reliable weather, rain, temperature, clothing, UV, sunscreen, and
key-period information. Reserve air quality, warnings, and holiday interfaces
without displaying them.

**User answer**

Accepted.

**Confirmed decision**

Phase 1 hides modules that do not yet have reliable data.

### 24. Acceptance Criteria

**Question**

What should prove Phase 1 is ready?

**Codex recommendation**

Use fixed fixtures and automated tests for:

1. Sunny, hot, and strong UV
2. Rain during morning commute
3. Midday shower with dry commutes
4. Thunderstorm during evening commute
5. Warm and highly humid
6. Strong wind and cooling
7. Comfortable all day
8. Primary provider failure with valid cache
9. All provider data older than 12 hours

Additional acceptance requirements:

- HTML and plain text are readable.
- The public repository contains no credentials or personal information.
- All recommendation rules have automated tests.
- Existing VPS scripts and cron remain unchanged.

**User answer**

Accepted.

**Confirmed decision**

These scenarios and requirements define Phase 1 acceptance.

## Final Agreed Direction

- Create a new standalone Python project.
- Target public repository: `dengyie/weather-morning-report`.
- Keep the repository fully anonymized.
- Write and approve the design before implementation.
- Use `wttr.in` and `wttr.is` in Phase 1.
- Add QWeather and advanced modules in Phase 2.
- Send one daily report at 08:30.
- Prioritize action guidance, especially rain, clothing, and sunscreen.
- Render responsive HTML plus plain-text fallback.
- Use provider fallback, caching, and stale-data protection.
- Do not touch the existing VPS weather automation until separately approved.

## Related Document

See [DESIGN.md](./DESIGN.md) for the implementation-ready product and technical
specification derived from this discussion.
