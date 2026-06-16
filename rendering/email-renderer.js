const { emailTemplateLabel, normalizeEmailTemplate } = require('./email-template-options')

const TEMPLATE_CLASSES = {
  1: 'email-warm',
  2: 'email-action',
  3: 'email-glass-gradient',
  4: 'email-minimal',
  5: 'email-dashboard'
}

const REPORT_TYPE_LABELS = {
  'zh-CN': {
    morning: '晨间早报',
    midday: '午间提醒',
    evening: '晚间提醒'
  },
  en: {
    morning: 'Morning report',
    midday: 'Midday report',
    evening: 'Evening report'
  }
}

const LABELS = {
  'zh-CN': {
    greeting: '你好',
    focus: '今日重点',
    umbrella: '带伞',
    sunscreen: '防晒',
    clothing: '穿搭',
    current: '当前天气',
    periods: '关键时段',
    range: '温度范围',
    feels: '体感',
    wind: '风速',
    uv: 'UV',
    risk: '风险等级',
    source: '数据源',
    cached: '当前内容可能来自缓存。'
  },
  en: {
    greeting: 'Hello',
    focus: 'Focus',
    umbrella: 'Umbrella',
    sunscreen: 'Sun protection',
    clothing: 'Clothing',
    current: 'Current conditions',
    periods: 'Key periods',
    range: 'Temperature range',
    feels: 'Feels like',
    wind: 'Wind',
    uv: 'UV',
    risk: 'Risk level',
    source: 'Source',
    cached: 'This report may be based on cached data.'
  }
}

const escapeHtml = (value = '') => String(value)
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const formatMetric = (value, suffix = '') => value == null || value === ''
  ? '-'
  : `${value}${suffix}`

const languageFor = (recipient = {}) => recipient.language === 'en' ? 'en' : 'zh-CN'

const subjectFor = ({ advice, branding, reportType, language }) => {
  const reportLabel = REPORT_TYPE_LABELS[language][reportType] || REPORT_TYPE_LABELS[language].morning
  const title = String(branding?.reportTitle || '').trim()
  return advice.subject || [title, reportLabel].filter(Boolean).join(' · ')
}

const renderPlainText = ({ snapshot, advice, recipient, branding, reportType, cached, language }) => {
  const labels = LABELS[language]
  const lines = [
    subjectFor({ advice, branding, reportType, language }),
    `${labels.greeting}${recipient.name ? `, ${recipient.name}` : ''}`,
    `${labels.focus}: ${advice.focus}`,
    `${labels.umbrella}: ${advice.umbrella}`,
    `${labels.sunscreen}: ${advice.sunscreen}`,
    `${labels.clothing}: ${advice.clothing}`,
    `${labels.current}: ${snapshot.current.description}, ${formatMetric(snapshot.current.temperatureC, '°C')}, ${labels.feels} ${formatMetric(snapshot.current.feelsLikeC, '°C')}`,
    `${labels.periods}:`,
    ...advice.periods.map((period) => `- ${period.label}: ${period.summary}`),
    advice.closing
  ]
  if (cached) lines.splice(2, 0, labels.cached)
  if (branding?.footerText) lines.push(branding.footerText)
  return lines.filter(Boolean).join('\n')
}

const renderPeriodRows = (periods) => periods.map((period) => `<tr><th>${escapeHtml(period.label)}</th><td>${escapeHtml(period.summary)}</td></tr>`).join('')

const renderHtml = ({ snapshot, advice, recipient, branding, reportType, cached, templateId, templateLabel, language }) => {
  const labels = LABELS[language]
  const reportLabel = REPORT_TYPE_LABELS[language][reportType] || REPORT_TYPE_LABELS[language].morning
  const greeting = language === 'en'
    ? `${labels.greeting}${recipient.name ? `, ${recipient.name}` : ''}.`
    : `${recipient.name ? `${recipient.name}，` : ''}${labels.greeting}`
  const source = snapshot.source?.host || ''
  const accent = /^#[0-9a-fA-F]{6}$/.test(branding?.accentColor || '') ? branding.accentColor : '#4266a8'
  const footer = String(branding?.footerText || '').trim()
  const showGreeting = branding?.greetingVisible !== false
  const showSource = branding?.dataSourceVisible !== false

  return `<!doctype html>
<html lang="${language === 'en' ? 'en' : 'zh-CN'}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(subjectFor({ advice, branding, reportType, language }))}</title>
  <style>
    body { margin: 0; background: #f4f6fb; color: #172033; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    .email-shell { max-width: 680px; margin: 0 auto; padding: 28px; }
    .email-card { background: #fff; border-radius: 24px; padding: 28px; border-top: 8px solid ${escapeHtml(accent)}; box-shadow: 0 20px 60px rgba(23, 32, 51, .12); }
    .email-warm .email-card { background: #fff8ef; }
    .email-action .email-card { border-radius: 12px; }
    .email-glass-gradient { background: linear-gradient(135deg, #e0f2fe, #ede9fe); }
    .email-minimal .email-card { box-shadow: none; border: 1px solid #d7dde8; border-top: 4px solid ${escapeHtml(accent)}; }
    .email-dashboard .metric-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
    h1 { margin: 0 0 8px; font-size: 28px; }
    h2 { margin-top: 26px; font-size: 18px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border-bottom: 1px solid #e6eaf2; padding: 10px; text-align: left; vertical-align: top; }
    .muted { color: #657088; }
    .metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
    .metric { background: rgba(66, 102, 168, .08); border-radius: 16px; padding: 12px; }
    .notice { border-radius: 14px; padding: 12px; background: #fff4ce; }
  </style>
</head>
<body class="${TEMPLATE_CLASSES[templateId]}" data-email-template="${escapeHtml(templateId)}">
  <main class="email-shell">
    <article class="email-card">
      <p class="muted">${escapeHtml(templateLabel)} · ${escapeHtml(reportLabel)}</p>
      <h1>${escapeHtml(subjectFor({ advice, branding, reportType, language }))}</h1>
      ${showGreeting ? `<p>${escapeHtml(greeting)}</p>` : ''}
      ${cached ? `<p class="notice">${escapeHtml(labels.cached)}</p>` : ''}
      <h2>${escapeHtml(labels.focus)}</h2>
      <p>${escapeHtml(advice.focus)}</p>
      <div class="metric-grid">
        <div class="metric"><strong>${escapeHtml(labels.umbrella)}</strong><br>${escapeHtml(advice.umbrella)}</div>
        <div class="metric"><strong>${escapeHtml(labels.sunscreen)}</strong><br>${escapeHtml(advice.sunscreen)}</div>
        <div class="metric"><strong>${escapeHtml(labels.clothing)}</strong><br>${escapeHtml(advice.clothing)}</div>
        <div class="metric"><strong>${escapeHtml(labels.risk)}</strong><br>${escapeHtml(advice.signals?.highestRiskLevel ?? 0)}</div>
      </div>
      <h2>${escapeHtml(labels.current)}</h2>
      <p>${escapeHtml(snapshot.location.name)} · ${escapeHtml(snapshot.current.description)}</p>
      <div class="metric-grid">
        <div class="metric">${escapeHtml(formatMetric(snapshot.current.temperatureC, '°C'))}</div>
        <div class="metric">${escapeHtml(labels.feels)} ${escapeHtml(formatMetric(snapshot.current.feelsLikeC, '°C'))}</div>
        <div class="metric">${escapeHtml(labels.range)} ${escapeHtml(formatMetric(snapshot.daily.minimumTemperatureC, '°C'))} / ${escapeHtml(formatMetric(snapshot.daily.maximumTemperatureC, '°C'))}</div>
        <div class="metric">${escapeHtml(labels.wind)} ${escapeHtml(formatMetric(snapshot.current.windSpeedKph, ' kph'))} · ${escapeHtml(labels.uv)} ${escapeHtml(formatMetric(snapshot.daily.uvIndex))}</div>
      </div>
      <h2>${escapeHtml(labels.periods)}</h2>
      <table>${renderPeriodRows(advice.periods || [])}</table>
      <p>${escapeHtml(advice.closing)}</p>
      ${footer ? `<p class="muted">${escapeHtml(footer)}</p>` : ''}
      ${showSource ? `<p class="muted">${escapeHtml(labels.source)}: ${escapeHtml(source)} · ${escapeHtml(snapshot.fetchedAt)}</p>` : ''}
    </article>
  </main>
</body>
</html>`
}

const renderEmailReport = ({ snapshot, advice, recipient = {}, branding = {}, reportType = 'morning', cached = false }) => {
  const language = languageFor(recipient)
  const templateId = normalizeEmailTemplate(recipient.emailTemplate)
  const templateLabel = emailTemplateLabel(templateId)
  const subject = subjectFor({ advice, branding, reportType, language })
  return {
    subject,
    text: renderPlainText({ snapshot, advice, recipient, branding, reportType, cached, language }),
    html: renderHtml({ snapshot, advice, recipient, branding, reportType, cached, templateId, templateLabel, language }),
    templateId,
    templateLabel,
    actionSummary: {
      umbrella: advice.umbrella,
      sunscreen: advice.sunscreen,
      clothing: advice.clothing,
      riskLevel: advice.signals?.highestRiskLevel ?? 0
    }
  }
}

module.exports = { escapeHtml, renderEmailReport }
