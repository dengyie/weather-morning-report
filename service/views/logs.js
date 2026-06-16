const { escapeHtml, renderPage } = require('./layout')

const renderLogsPage = ({ lines }) => renderPage({
  title: '天气早报服务日志',
  activePath: '/logs',
  body: `<section class="hero">
    <p class="eyebrow">Service Logs</p>
    <h1>服务日志</h1>
    <p>查看最近的 companion service 运行记录。</p>
  </section>
  <section class="card">
    ${lines.length === 0
      ? '<p class="muted">暂无服务日志</p>'
      : `<pre>${lines.map(escapeHtml).join('\n')}</pre>`}
  </section>`
})

module.exports = { renderLogsPage }
