const { escapeHtml, renderPage } = require('./layout')

const renderEmailPreviewPage = ({ rendered, recipient }) => renderPage({
  title: '邮件预览',
  activePath: '/',
  body: `<section class="hero">
    <p class="eyebrow">Email Preview</p>
    <h1>邮件预览</h1>
    <p>${escapeHtml(recipient.name)} · ${escapeHtml(recipient.email)} · ${escapeHtml(rendered.templateLabel)}</p>
  </section>
  <section class="card">
    <div class="section-head"><div><h2>主题</h2><p class="muted">${escapeHtml(rendered.subject)}</p></div></div>
    <pre>${escapeHtml(rendered.text)}</pre>
  </section>
  <section class="card email-preview-card">
    <div class="section-head"><div><h2>HTML 预览</h2><p class="muted">Phase 5 只在明确 send-now 时发送，预览不会触发 Email transport。</p></div></div>
    <iframe sandbox="" title="Email HTML preview" class="email-preview-frame" srcdoc="${escapeHtml(rendered.html)}"></iframe>
  </section>`
})

module.exports = { renderEmailPreviewPage }
