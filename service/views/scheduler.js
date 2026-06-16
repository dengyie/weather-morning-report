const { escapeHtml, renderPage } = require('./layout')

const metric = (label, value) => `<article class="card"><p class="eyebrow">${escapeHtml(label)}</p><p class="metric-value">${escapeHtml(value)}</p></article>`

const renderSchedulerPage = ({ status }) => renderPage({
  title: '天气早报调度队列',
  activePath: '/scheduler',
  body: `<section class="hero">
    <p class="eyebrow">Scheduler Queue</p>
    <h1>调度队列</h1>
    <p>查看自动发送队列、重试状态和 worker lease。Phase 6 提供显式入队与状态面板，常驻 worker 生命周期留给统一扩展阶段。</p>
    <form method="post" action="/scheduler/enqueue-due"><button type="submit">检查当前分钟并入队</button></form>
  </section>
  <section class="grid" aria-label="队列状态">
    ${metric('Pending', status.pending)}
    ${metric('Running', status.running)}
    ${metric('Retrying', status.retrying)}
    ${metric('Sent', status.sent)}
    ${metric('Skipped', status.skipped)}
    ${metric('Failed', status.failed)}
    ${metric('Unknown', status.unknown)}
    ${metric('Total', status.total)}
  </section>
  <section class="card">
    <div class="section-head"><div><h2>Worker status</h2><p class="muted">${status.workerActive ? 'Worker active' : 'Worker inactive'}</p></div></div>
    <p>Instance: ${escapeHtml(status.workerInstanceId || 'none')}</p>
    <p>Heartbeat: ${escapeHtml(status.workerHeartbeatAt || 'none')}</p>
  </section>`
})

module.exports = { renderSchedulerPage }
