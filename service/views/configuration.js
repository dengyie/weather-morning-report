const { LANGUAGES, REPORT_TYPES, SEND_POLICIES, SMTP_SECURITY_MODES } = require('../configuration/defaults')
const { checked, escapeHtml, renderPage, selected } = require('./layout')
const { SMTP_OPERATION_ACTIONS, SMTP_OPERATION_STATUSES } = require('../storage/smtp-operation-history-store')

const REPORT_TYPE_LABELS = {
  morning: '晨间早报',
  midday: '午间提醒',
  evening: '晚间提醒'
}

const SEND_POLICY_LABELS = {
  always: '总是发送',
  changes_only: '仅天气有变化时发送'
}

const LANGUAGE_LABELS = {
  'zh-CN': '中文',
  en: 'English'
}

const SMTP_SECURITY_LABELS = {
  starttls: 'STARTTLS',
  ssl: 'SSL/TLS',
  plain: 'Plain'
}

const SMTP_OPERATION_ACTION_LABELS = {
  all: '全部操作',
  'test-connection': 'SMTP 连接测试',
  'test-email': '测试邮件'
}

const SMTP_OPERATION_STATUS_LABELS = {
  all: '全部状态',
  connected: '已连接',
  sent: '已发送',
  failed: '失败'
}

const SECRET_HEALTH_LABELS = {
  'not-configured': '尚未配置受管 SMTP 密码',
  'backup-unconfirmed': '需要确认密钥备份',
  healthy: '本地密钥已确认备份',
  unhealthy: '密钥或受管密码状态异常'
}

const renderOptions = (options, currentValue, labels = {}) => options
  .map((option) => `<option value="${escapeHtml(option)}"${selected(currentValue, option)}>${escapeHtml(labels[option] || option)}</option>`)
  .join('')

const renderSection = (title, description, body = '') => `<section class="card workbench-card">
  <div class="section-head"><div><h2>${escapeHtml(title)}</h2><p class="muted">${escapeHtml(description)}</p></div></div>
  ${body}
</section>`

const renderRecipients = (recipients) => `<section class="card workbench-card">
  <div class="section-head"><div><h2>收件人工作台</h2><p class="muted">维护收件人、地点、语言与邮件模板。</p></div></div>
  ${recipients.length === 0
    ? '<p class="muted">还没有收件人。</p>'
    : recipients.map((recipient) => `<article class="record-card">
      <h3>${escapeHtml(recipient.name)}</h3>
      <p>${escapeHtml(recipient.email)}</p>
      <p class="muted">${escapeHtml(recipient.locationName)} · ${escapeHtml(recipient.language)}</p>
    </article>`).join('')}
</section>`

const renderSmtpOperations = (operations = []) => `<div class="history-list">
  ${operations.length === 0
    ? '<p class="muted">暂无 SMTP 操作历史。</p>'
    : operations.slice(-5).reverse().map((operation) => `<article class="record-card">
      <h3>${escapeHtml(operation.action)} · ${escapeHtml(operation.status)}</h3>
      <p class="muted">${escapeHtml(operation.createdAt)}</p>
      ${operation.recipientEmail ? `<p>${escapeHtml(operation.recipientName)} · ${escapeHtml(operation.recipientEmail)}</p>` : ''}
      ${operation.messageId ? `<p>Message ID: ${escapeHtml(operation.messageId)}</p>` : ''}
      ${operation.error ? `<p>${escapeHtml(operation.error)}</p>` : ''}
    </article>`).join('')}
</div>`

const renderSmtpOperationFilters = (filters = {}, recipients = []) => {
  const query = new URLSearchParams({
    format: 'json',
    smtp_action: filters.action || 'all',
    smtp_status: filters.status || 'all',
    smtp_recipient_id: filters.recipientId || 'all'
  }).toString()
  const csvQuery = new URLSearchParams({
    format: 'csv',
    smtp_action: filters.action || 'all',
    smtp_status: filters.status || 'all',
    smtp_recipient_id: filters.recipientId || 'all'
  }).toString()

  return `<form class="form-grid" method="get" action="/configuration">
    <label>操作类型<select name="smtp_action">${renderOptions(SMTP_OPERATION_ACTIONS, filters.action || 'all', SMTP_OPERATION_ACTION_LABELS)}</select></label>
    <label>执行状态<select name="smtp_status">${renderOptions(SMTP_OPERATION_STATUSES, filters.status || 'all', SMTP_OPERATION_STATUS_LABELS)}</select></label>
    <label>收件人<select name="smtp_recipient_id"><option value="all"${selected(filters.recipientId || 'all', 'all')}>全部收件人</option>${recipients.map((recipient) => `<option value="${escapeHtml(recipient.id)}"${selected(filters.recipientId, recipient.id)}>${escapeHtml(recipient.name)} · ${escapeHtml(recipient.email)}</option>`).join('')}</select></label>
    <div class="button-row">
      <button type="submit">筛选历史</button>
      <a class="button-link secondary" href="/configuration/smtp/history/export?${escapeHtml(query)}">导出 JSON</a>
      <a class="button-link secondary" href="/configuration/smtp/history/export?${escapeHtml(csvQuery)}">导出 CSV</a>
    </div>
  </form>`
}

const renderNotices = (notices = [], type) => notices.length === 0
  ? ''
  : `<div class="notice notice-${escapeHtml(type)}">${notices.map((notice) => `<p>${escapeHtml(notice)}</p>`).join('')}</div>`

const renderErrors = (errors = []) => errors.length === 0
  ? ''
  : `<div class="notice notice-warning">${errors.map((error) => `<p>${escapeHtml(error)}</p>`).join('')}</div>`

const renderDefaultsForm = (values) => renderSection('新用户默认值', '默认地点、语言、报告类型与发送策略。', `<form class="form-grid" method="post" action="/configuration/defaults">
  <label>默认地点名称<input name="location_name" value="${escapeHtml(values.locationName)}" required></label>
  <label>默认 Provider 查询<input name="location_query" value="${escapeHtml(values.locationQuery)}" required></label>
  <label>默认时区<input name="timezone" value="${escapeHtml(values.timezone)}" required></label>
  <label>默认发送时间<input name="local_send_time" value="${escapeHtml(values.localSendTime)}" placeholder="08:30" required></label>
  <label>报告语言<select name="language">${renderOptions(LANGUAGES, values.language, LANGUAGE_LABELS)}</select></label>
  <label>报告类型<select name="report_type">${renderOptions(REPORT_TYPES, values.reportType, REPORT_TYPE_LABELS)}</select></label>
  <label>发送策略<select name="send_policy">${renderOptions(SEND_POLICIES, values.sendPolicy, SEND_POLICY_LABELS)}</select></label>
  <label class="checkbox"><input type="checkbox" name="schedule_enabled"${checked(values.scheduleEnabled)}>默认启用计划</label>
  <button type="submit">保存默认值</button>
</form>`)

const renderRecipientForm = (values = {}) => `<form class="quick-create" method="post" action="/configuration/recipients">
  <label>称呼<input name="name" value="${escapeHtml(values.name)}" placeholder="例如：Mango" required></label>
  <label>邮箱<input type="email" name="email" value="${escapeHtml(values.email)}" placeholder="name@example.com" required></label>
  <label>地点<input name="location_name" value="${escapeHtml(values.locationName)}" required></label>
  <label>查询<input name="location_query" value="${escapeHtml(values.locationQuery)}" required></label>
  <label>时区<input name="timezone" value="${escapeHtml(values.timezone)}" required></label>
  <label>语言<select name="language">${renderOptions(LANGUAGES, values.language || 'zh-CN', LANGUAGE_LABELS)}</select></label>
  <label>邮件模板<select name="email_template"><option value="1">1 · 标准早报</option></select></label>
  <label class="checkbox"><input type="checkbox" name="enabled"${checked(values.enabled !== false)}>启用</label>
  <button type="submit">添加收件人</button>
</form>`

const renderSchedules = (configuration, values = {}) => renderSection('发送计划', '配置本地发送时间、报告类型和发送策略。', `<form class="form-grid" method="post" action="/configuration/schedules">
    <label>收件人<select name="recipient_id"${configuration.recipients.length === 0 ? ' disabled' : ''}>${configuration.recipients.map((recipient) => `<option value="${escapeHtml(recipient.id)}"${selected(values.recipientId, recipient.id)}>${escapeHtml(recipient.name)}</option>`).join('')}</select></label>
    <label>发送时间<input name="local_send_time" value="${escapeHtml(values.localSendTime || configuration.newUserDefaults.localSendTime)}" placeholder="08:30" required></label>
    <label>报告类型<select name="report_type">${renderOptions(REPORT_TYPES, values.reportType || configuration.newUserDefaults.reportType, REPORT_TYPE_LABELS)}</select></label>
    <label>发送策略<select name="send_policy">${renderOptions(SEND_POLICIES, values.sendPolicy || configuration.newUserDefaults.sendPolicy, SEND_POLICY_LABELS)}</select></label>
    <label class="checkbox"><input type="checkbox" name="enabled"${checked(values.enabled !== false)}>启用</label>
    <button type="submit"${configuration.recipients.length === 0 ? ' disabled' : ''}>添加计划</button>
  </form>
  ${configuration.recipients.length === 0 ? '<p class="muted">添加收件人后即可创建发送计划。</p>' : ''}
  ${configuration.schedules.length === 0
    ? '<p class="muted">暂无发送计划。</p>'
    : configuration.schedules.map((schedule) => `<article class="record-card">
      <h3>${escapeHtml(schedule.localSendTime)} · ${escapeHtml(REPORT_TYPE_LABELS[schedule.reportType] || schedule.reportType)}</h3>
      <p>${escapeHtml(SEND_POLICY_LABELS[schedule.sendPolicy] || schedule.sendPolicy)} · ${schedule.enabled ? '启用' : '停用'}</p>
    </article>`).join('')}`)

const renderSmtpForm = (values, recipients = []) => renderSection('邮件服务', 'SMTP 连接元数据和发件身份。', `<p class="muted">密码状态：${values.passwordSaved ? '已保存，留空保持不变' : '尚未保存 SMTP 密码'}</p>
<form class="form-grid" method="post" action="/configuration/smtp">
  <label>SMTP Host<input name="host" value="${escapeHtml(values.host)}"></label>
  <label>端口<input name="port" value="${escapeHtml(values.port)}" inputmode="numeric" required></label>
  <label>用户名<input name="username" value="${escapeHtml(values.username)}"></label>
  <label>新密码<input type="password" name="password" value="" autocomplete="new-password"></label>
  <label>安全方式<select name="security">${renderOptions(SMTP_SECURITY_MODES, values.security, SMTP_SECURITY_LABELS)}</select></label>
  <label>发件邮箱<input type="email" name="sender_email" value="${escapeHtml(values.senderEmail)}"></label>
  <button type="submit">保存邮件服务</button>
</form>
<div class="quick-actions">
  <form method="post" action="/configuration/smtp/test-connection">
    <input type="hidden" name="page_mode" value="configuration">
    <button type="submit">测试 SMTP 连接</button>
  </form>
  ${values.hasManagedPassword
    ? `<form method="post" action="/configuration/smtp/clear-password">
    <input type="hidden" name="page_mode" value="configuration">
    <button type="submit">清除已保存密码</button>
  </form>`
    : ''}
  <form method="post" action="/email/test">
    <input type="hidden" name="page_mode" value="configuration">
    <label>测试收件人<select name="recipient_id"${recipients.length === 0 ? ' disabled' : ''}>${recipients.map((recipient) => `<option value="${escapeHtml(recipient.id)}">${escapeHtml(recipient.name)} · ${escapeHtml(recipient.email)}</option>`).join('')}</select></label>
    <button type="submit"${recipients.length === 0 ? ' disabled' : ''}>发送测试邮件</button>
  </form>
</div>
${recipients.length === 0 ? '<p class="muted">添加收件人后即可发送测试邮件。</p>' : ''}`)

const renderProviders = (providers) => renderSection('天气数据源', 'Provider 优先级与健康状态。', providers
  .map((provider) => `<article class="record-card">
    <h3>${escapeHtml(provider.name)}</h3>
    <p class="muted">优先级 ${escapeHtml(provider.priority)} · ${provider.enabled ? '启用' : '停用'} · ${escapeHtml(provider.health)}</p>
    ${provider.lastError ? `<p>${escapeHtml(provider.lastError)}</p>` : ''}
  </article>`)
  .join(''))

const renderBrandingForm = (values) => renderSection('报告品牌', '标题、强调色、页脚和可见性设置。', `<form class="form-grid" method="post" action="/configuration/branding">
  <label>报告标题<input name="report_title" value="${escapeHtml(values.reportTitle)}"></label>
  <label>强调色<input name="accent_color" value="${escapeHtml(values.accentColor)}" placeholder="#4266a8" required></label>
  <label>页脚文案<input name="footer_text" value="${escapeHtml(values.footerText)}"></label>
  <label class="checkbox"><input type="checkbox" name="greeting_visible"${checked(values.greetingVisible)}>显示问候语</label>
  <label class="checkbox"><input type="checkbox" name="data_source_visible"${checked(values.dataSourceVisible)}>显示数据源</label>
  <button type="submit">保存报告品牌</button>
</form>`)

const renderSecretHealth = (secretHealth = {}) => {
  const masterKey = secretHealth.masterKey || {}
  const managedPassword = secretHealth.managedSmtpPassword || {}
  const status = secretHealth.status || 'not-configured'

  return renderSection('密钥与备份状态', '本地受管 SMTP 密钥的可见状态与备份确认。', `<article class="record-card">
    <h3>${escapeHtml(SECRET_HEALTH_LABELS[status] || status)}</h3>
    ${secretHealth.warning ? `<p class="notice-inline">${escapeHtml(secretHealth.warning)}</p>` : ''}
    <p class="muted">本地密钥：${masterKey.present ? '存在' : '尚未生成'} · ${masterKey.valid ? '有效' : '未验证或无效'}</p>
    <p class="muted">受管 SMTP 密码：${managedPassword.present ? '已保存' : '未保存'} · ${managedPassword.healthy ? '可解密' : '未验证或不可用'}</p>
    ${managedPassword.updatedAt ? `<p class="muted">最近更新：${escapeHtml(managedPassword.updatedAt)}</p>` : ''}
    <div class="quick-actions">
      ${secretHealth.backupConfirmed
        ? `<form method="post" action="/configuration/secrets/revoke-backup-confirmation">
          <button type="submit">撤销备份确认</button>
        </form>`
        : `<form method="post" action="/configuration/secrets/confirm-backup">
          <button type="submit"${managedPassword.present ? '' : ' disabled'}>标记已备份密钥</button>
        </form>`}
    </div>
  </article>`)
}

const renderNotificationsForm = (values) => renderSection('通知与数据保留', '管理员通知、保留时间和密钥备份确认。', `<form class="form-grid" method="post" action="/configuration/notifications">
  <label>管理员邮箱<input type="email" name="admin_email" value="${escapeHtml(values.adminEmail)}"></label>
  <label>Webhook URL<input name="webhook_url" value="${escapeHtml(values.webhookUrl)}"></label>
  <label>历史保留天数<input name="retention_days" value="${escapeHtml(values.retentionDays)}" inputmode="numeric" required></label>
  <label>告警冷却分钟<input name="alert_cooldown_minutes" value="${escapeHtml(values.alertCooldownMinutes)}" inputmode="numeric" required></label>
  <label class="checkbox"><input type="checkbox" name="webhook_enabled"${checked(values.webhookEnabled)}>启用 Webhook</label>
  <label class="checkbox"><input type="checkbox" name="secret_key_backup_confirmed"${checked(values.secretKeyBackupConfirmed)}>已确认密钥备份</label>
  <button type="submit">保存通知设置</button>
</form>`)

const renderConfigurationPage = ({ configuration, errors = [], notices = [], smtpOperations = [], smtpHistoryFilters = {}, values = {} }) => renderPage({
  title: '天气早报配置中心',
  activePath: '/configuration',
  body: `<section class="hero config-hero">
    <p class="eyebrow">Configuration Workbench</p>
    <h1>配置中心</h1>
    <p>把天气早报配置成一张清晰工作台。当前有 ${configuration.recipients.length} 位收件人与 ${configuration.schedules.length} 条计划。</p>
  </section>
  ${renderNotices(notices, 'success')}
  ${renderErrors(errors)}
  ${renderDefaultsForm(values.defaults || configuration.newUserDefaults)}
  ${renderRecipientForm(values.recipient)}
  ${renderRecipients(configuration.recipients)}
  ${renderSchedules(configuration, values.schedule)}
  ${renderSmtpForm(values.smtp || configuration.smtp, configuration.recipients)}
  <section class="card workbench-card">
    <div class="section-head"><div><h2>SMTP operational history</h2><p class="muted">最近的连接测试和测试邮件结果。</p></div></div>
    ${renderSmtpOperationFilters(smtpHistoryFilters, configuration.recipients)}
    ${renderSmtpOperations(smtpOperations)}
  </section>
  ${renderProviders(configuration.providers)}
  ${renderBrandingForm(values.branding || configuration.branding)}
  ${renderSecretHealth(configuration.secretHealth)}
  ${renderNotificationsForm(values.notifications || configuration.notifications)}`
})

module.exports = { renderConfigurationPage }
