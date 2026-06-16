const { escapeHtml, renderPage } = require('./layout')

const renderManualPreviewPage = ({ recipient, reportType }) => {
  const subject = `Weather Morning Report · ${reportType} · ${recipient.name}`
  const previewText = `收件人 ${recipient.name} 将收到 ${reportType} 天气早报预览。Phase 4 只生成预览，不发送 Email。`
  return renderPage({
    title: '手动发送预览',
    activePath: '/',
    body: `<section class="hero">
      <p class="eyebrow">发送前检查</p>
      <h1>手动发送预览</h1>
      <p>${escapeHtml(subject)}</p>
    </section>
    <section class="card">
      <div class="section-head"><div><h2>纯文本预览</h2><p class="muted">收件人无法显示 HTML 时会看到此版本。</p></div></div>
      <pre>${escapeHtml(previewText)}</pre>
    </section>
    <section class="card">
      <div class="section-head"><div><h2>确认加入发送队列</h2><p class="muted">Phase 4 不发送邮件，后续 Email 阶段会接入发送队列。</p></div></div>
      <div class="button-row"><button type="button" disabled>确认并加入发送队列</button><a class="button-link secondary" href="/">取消并返回</a></div>
    </section>`
  })
}

module.exports = { renderManualPreviewPage }
