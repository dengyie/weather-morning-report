const { readFileSync } = require('node:fs')
const { test } = require('node:test')
const assert = require('node:assert/strict')

const coreModules = [
  '../core/config',
  '../core/period-schedule',
  '../core/recommendation-engine',
  '../core/weather-provider',
  '../core/wttr-parser'
]

test('framework-neutral weather modules are available from core and rendering boundaries', () => {
  for (const modulePath of coreModules) {
    assert.equal(typeof require(modulePath), 'object', `${modulePath} should be importable`)
  }

  assert.equal(typeof require('../rendering/text-renderer').renderWeatherText, 'function')
})

test('OpenPet command adapter depends on core and rendering boundaries instead of local business modules', () => {
  const source = readFileSync('src/commands.js', 'utf8')

  assert.match(source, /require\('\.\.\/core\/weather-provider'\)/)
  assert.match(source, /require\('\.\.\/core\/config'\)/)
  assert.match(source, /require\('\.\.\/core\/recommendation-engine'\)/)
  assert.match(source, /require\('\.\.\/rendering\/text-renderer'\)/)

  assert.doesNotMatch(source, /require\('\.\/weather-provider'\)/)
  assert.doesNotMatch(source, /require\('\.\/config'\)/)
  assert.doesNotMatch(source, /require\('\.\/recommendation-engine'\)/)
  assert.doesNotMatch(source, /require\('\.\/text-renderer'\)/)
})
