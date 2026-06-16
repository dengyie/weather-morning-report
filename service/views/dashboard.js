const { escapeHtml, renderPage } = require('./layout')

const renderDashboardPage = ({ configuration }) => renderPage({
  title: '天气早报控制台',
  activePath: '/',
  body: `<section class="hero">
    <p class="eyebrow">OpenPet Companion Service</p>
    <h1>Weather Morning Report</h1>
    <p>Fastify service is ready. Web dashboard, Email preview, SMTP delivery, and scheduler controls will be promoted here phase by phase.</p>
    <div class="button-row"><a class="button-link" href="/configuration">管理配置</a><a class="button-link secondary" href="/logs">查看日志</a></div>
  </section>
  <section class="grid" aria-label="服务状态">
    <article class="card"><p class="eyebrow">Recipients</p><p class="metric-value">${configuration.recipients.length}</p></article>
    <article class="card"><p class="eyebrow">Schedules</p><p class="metric-value">${configuration.schedules.length}</p></article>
  </section>
  <section class="card">
    <div class="section-head"><div><h2>手动生成天气早报</h2><p class="muted">选择收件人与报告时段，预览确认后再进入后续发送流程。</p></div></div>
    ${configuration.recipients.length === 0
      ? '<p class="muted">还没有收件人。请先进入配置中心添加收件人。</p>'
      : `<form class="form-grid" method="post" action="/manual/preview">
        <label>收件人<select name="recipient_id">${configuration.recipients.map((recipient) => `<option value="${escapeHtml(recipient.id)}">${escapeHtml(recipient.name)}</option>`).join('')}</select></label>
        <label>报告类型<select name="report_type"><option value="morning">晨间早报</option><option value="midday">午间提醒</option><option value="evening">晚间提醒</option></select></label>
        <button type="submit">生成报告预览</button>
      </form>`}
  </section>
  <section class="card">
    <div class="section-head"><div><h2>最近运行历史</h2><p class="muted">Phase 4 先展示空状态；Email 发送历史会在后续阶段接入。</p></div></div>
    <p class="muted">暂无运行历史</p>
  </section>`
})

module.exports = { renderDashboardPage }
