const escapeHtml = (value = '') => String(value)
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;')

const checked = (value) => (value ? ' checked' : '')
const selected = (actual, expected) => (actual === expected ? ' selected' : '')

const injectDashboardToken = (body, dashboardToken) => {
  if (!dashboardToken) return body
  const input = `<input type="hidden" name="dashboard_token" value="${escapeHtml(dashboardToken)}">`
  return String(body).replace(/(<form\b[^>]*\bmethod="post"[^>]*>)/gi, `$1${input}`)
}

const renderPage = ({ title, activePath = '/', body, dashboardToken }) => `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>${escapeHtml(title)}</title>
  <link rel="stylesheet" href="/static/app.css">
</head>
<body>
  <main class="shell dashboard-shell">
    <header class="topbar">
      <a class="brand" href="/"><span class="brand-mark" aria-hidden="true">W</span><span>Weather Morning Report</span></a>
      <nav class="nav-links" aria-label="主导航">
        <a href="/"${activePath === '/' ? ' aria-current="page"' : ''}>仪表盘</a>
        <a href="/configuration"${activePath === '/configuration' ? ' aria-current="page"' : ''}>配置中心</a>
        <a href="/scheduler"${activePath === '/scheduler' ? ' aria-current="page"' : ''}>调度</a>
        <a href="/logs"${activePath === '/logs' ? ' aria-current="page"' : ''}>日志</a>
      </nav>
    </header>
    ${injectDashboardToken(body, dashboardToken)}
  </main>
</body>
</html>`

module.exports = { checked, escapeHtml, renderPage, selected }
