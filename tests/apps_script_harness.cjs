const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const fixture = require('./fixtures/signed_preview.json');
const SECRET = fixture.secret;
const clone = value => JSON.parse(JSON.stringify(value));

function harness() {
  const props = new Map([['JD_SHARED_SECRET', SECRET], ['GMAIL_SYNC_CURSOR', 'leave-me-alone']]);
  const mutations = [];
  const state = {rows: [], notes: [], formulas: [], maxRows: 1000, opened: [], tabs: [], now: fixture.timestamp * 1000};
  const propertyStore = {
    getProperty: k => props.has(k) ? props.get(k) : null,
    setProperty: (k, v) => props.set(k, v),
    deleteProperty: k => props.delete(k),
    getProperties: () => Object.fromEntries(props),
  };
  let held = false;
  const at = (matrix, r, c) => (matrix[r] || [])[c] || '';
  const put = (matrix, r, c, value) => { while (matrix.length <= r) matrix.push([]); matrix[r][c] = value; };
  function range(row, column, height = 1, width = 1) {
    const read = matrix => Array.from({length: height}, (_, r) => Array.from({length: width}, (_, c) => at(matrix, row - 1 + r, column - 1 + c)));
    return {
      getValues: () => read(state.rows), getFormulas: () => read(state.formulas), getNotes: () => read(state.notes),
      getFormula: () => at(state.formulas, row - 1, column - 1), getValue: () => at(state.rows, row - 1, column - 1),
      getNote: () => at(state.notes, row - 1, column - 1),
      setRichTextValue: value => {
        mutations.push(['text', row, column, value.text]);
        put(state.rows, row - 1, column - 1, value.text);
        put(state.formulas, row - 1, column - 1, '');
      },
      setRichTextValues: values => values.forEach((items, r) => items.forEach((v, c) => range(row+r, column+c).setRichTextValue(v))),
      setNote: value => { mutations.push(['note', row, column]); put(state.notes, row-1, column-1, value); },
    };
  }
  const sheet = {
    getLastRow: () => state.rows.length,
    getLastColumn: () => Math.max(0, ...state.rows.map(r => r.length)),
    getMaxRows: () => state.maxRows,
    insertRowsAfter: (_, n) => { state.maxRows += n; mutations.push(['insertRows', n]); },
    getRange: range,
  };
  class Clock extends Date { static now() { return state.now; } }
  const context = vm.createContext({
    Date: Clock,
    Utilities: {
      Charset: {UTF_8: 'UTF-8'}, DigestAlgorithm: {SHA_256: 'sha256'},
      computeDigest: (_, text) => Array.from(crypto.createHash('sha256').update(text).digest()),
      computeHmacSha256Signature: (text, secret) => Array.from(crypto.createHmac('sha256', secret).update(text).digest()),
      base64Decode: value => Array.from(Buffer.from(value, 'base64')),
      base64Encode: bytes => Buffer.from(bytes).toString('base64'),
      newBlob: bytes => ({getDataAsString: () => Buffer.from(bytes).toString('utf8')}),
      getUuid: () => crypto.randomUUID(),
    },
    PropertiesService: {getScriptProperties: () => propertyStore},
    LockService: {getScriptLock: () => ({tryLock: () => { if (held) return false; held = true; return true; }, hasLock: () => held, releaseLock: () => {held = false;}})},
    SpreadsheetApp: {
      openById: id => {state.opened.push(id); return {getSheetByName: name => {state.tabs.push(name); return sheet;}};},
      newRichTextValue: () => {const value = {text: ''}; return {setText: t => {value.text = t; return {build: () => value};}};},
      flush: () => {},
    },
    ContentService: {MimeType: {JSON: 'json'}, createTextOutput: text => ({setMimeType: () => text})},
  });
  vm.runInContext(fs.readFileSync('apps_script/JobDiscovery.gs', 'utf8'), context);
  vm.runInContext(fs.readFileSync('apps_script/WebAppEntry.gs', 'utf8'), context);
  state.rows = [Array.from(context.JobDiscoveryWebApp.headers)];
  function sign(payload, options = {}) {
    const env = {version: 1, timestamp: Math.floor(state.now/1000), request_id: crypto.randomUUID(),
      payload_b64: Buffer.from(JSON.stringify(payload)).toString('base64'), ...options};
    env.signature = crypto.createHmac('sha256', SECRET).update(`v1\n${env.timestamp}\n${env.request_id}\n${env.payload_b64}`).digest('hex');
    return env;
  }
  function send(env, type = 'text/plain; charset=utf-8') {
    return JSON.parse(context.doPost({postData: {type, contents: JSON.stringify(env)}}));
  }
  function request(payload) { return send(sign(payload)); }
  function batch() { return clone(JSON.parse(Buffer.from(fixture.envelope.payload_b64, 'base64').toString()).batch); }
  function write(data = batch()) {
    const preview = request({operation: 'preview', batch: data});
    if (!preview.ok) throw new Error(preview.code);
    return request({operation: 'write', batch: data, preview_token: preview.preview_token});
  }
  return {state, props, mutations, context, sheet, sign, send, request, batch, write};
}
module.exports = {harness, fixture, clone};
