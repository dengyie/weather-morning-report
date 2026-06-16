const EMAIL_TEMPLATE_OPTIONS = [
  ['1', '暖调风格'],
  ['2', '行动风格'],
  ['3', '玻璃渐变'],
  ['4', '极简风格'],
  ['5', '仪表风格']
]

const DEFAULT_EMAIL_TEMPLATE = '1'
const EMAIL_TEMPLATES = new Set(EMAIL_TEMPLATE_OPTIONS.map(([value]) => value))

const emailTemplateLabel = (value) => {
  const normalized = normalizeEmailTemplate(value)
  return EMAIL_TEMPLATE_OPTIONS.find(([option]) => option === normalized)[1]
}

const normalizeEmailTemplate = (value) => EMAIL_TEMPLATES.has(String(value || ''))
  ? String(value)
  : DEFAULT_EMAIL_TEMPLATE

module.exports = {
  DEFAULT_EMAIL_TEMPLATE,
  EMAIL_TEMPLATE_OPTIONS,
  EMAIL_TEMPLATES,
  emailTemplateLabel,
  normalizeEmailTemplate
}
