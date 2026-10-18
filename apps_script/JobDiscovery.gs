/* Independent job writer. No Gmail calls, triggers, external libraries or Cloud APIs.
 * Deploy in a NEW standalone Apps Script project to avoid existing doPost conflicts.
 * All persistent properties use JD_ prefix; unrelated properties are never changed.
 */
var JobDiscoveryWebApp = (function () {
  'use strict';
  const SHEET_ID = '1z-zzj5IWsQXTjDL7QV8OYF2_Do_NSJdslh39G2RVHds';
  const TAB = '岗位数据库';
  const HEADERS = ['岗位ID', '公司', '岗位名称', '城市', '企业类型', '岗位方向', '固定年薪(万元)', '薪资公开状态', '匹配度', '招聘状态', '申请状态', '岗位链接', '来源', '发现日期', '最后核实', '匹配理由', '待确认问题'];
  const NOTE_PREFIX = 'JOB_DISCOVERY_V1\n';
  const KEY_RE = /^(greenhouse|lever|ashby):[A-Za-z0-9_-]+:[A-Za-z0-9_-]+$/;
  const SOURCE_RE = /^(greenhouse|lever|ashby):[A-Za-z0-9_-]+$/;
  const fail = code => { throw new Error(code); };
  const hex = bytes => bytes.map(b => ('0' + ((b + 256) % 256).toString(16)).slice(-2)).join('');
  const hash = text => hex(Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, text, Utilities.Charset.UTF_8));
  const stable = value => {
    if (Array.isArray(value)) return '[' + value.map(stable).join(',') + ']';
    if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + stable(value[k])).join(',') + '}';
    return JSON.stringify(value);
  };
  const equal = (a, b) => {
    if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false;
    let diff = 0;
    for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
    return diff === 0;
  };
  const text = value => value instanceof Date ? value.toISOString() : String(value === null || value === undefined ? '' : value);
  const normalize = value => text(value).toLowerCase().replace(/[^\p{L}\p{N}_]/gu, '');
  const fingerprint = v => [v['公司'], v['岗位名称'], v['城市']].map(normalize).join('|');

  function canonicalUrl(value) {
    // Apps Script has no browser URL global. Accept HTTPS only, keep all
    // identity query parameters, remove only known tracking parameters.
    const m = /^https:\/\/([A-Za-z0-9.-]+)(?::443)?(\/[^?#]*)?(?:\?([^#]*))?(?:#.*)?$/.exec(value);
    if (!m) fail('invalid_batch');
    const query = (m[3] || '').split('&').filter(Boolean).filter(pair => {
      let key;
      try { key = decodeURIComponent(pair.split('=')[0]).toLowerCase(); }
      catch (_) { fail('invalid_batch'); }
      return !key.startsWith('utm_') && !['source', 'ref', 'gh_src', 'lever-source'].includes(key);
    }).sort().join('&');
    return 'https://' + m[1].toLowerCase() + (m[2] || '').replace(/\/+$/, '') + (query ? '?' + query : '');
  }

  function authenticate(event, secret) {
    if (!secret || secret.length < 32 || !/^[\x20-\x7E]+$/.test(secret)) fail('auth_failed');
    if (!event || !event.postData || typeof event.postData.contents !== 'string' || event.postData.contents.length > 1500000) fail('bad_request');
    const type = (event.postData.type || '').split(';')[0].trim();
    if (!['text/plain', 'application/json'].includes(type)) fail('bad_request');
    let envelope;
    try { envelope = JSON.parse(event.postData.contents); } catch (_) { fail('bad_request'); }
    if (!envelope || envelope.version !== 1 || !Number.isSafeInteger(envelope.timestamp) ||
        !/^[a-f0-9-]{36}$/.test(envelope.request_id || '') ||
        !/^[a-f0-9]{64}$/.test(envelope.signature || '') ||
        typeof envelope.payload_b64 !== 'string' || !/^[A-Za-z0-9+/]*={0,2}$/.test(envelope.payload_b64)) fail('auth_failed');
    if (Math.abs(Date.now() / 1000 - envelope.timestamp) > 300) fail('auth_failed');
    const message = 'v1\n' + envelope.timestamp + '\n' + envelope.request_id + '\n' + envelope.payload_b64;
    const expected = hex(Utilities.computeHmacSha256Signature(message, secret, Utilities.Charset.UTF_8));
    if (!equal(expected, envelope.signature)) fail('auth_failed');
    return envelope;
  }

  function validateBatch(batch) {
    if (!batch || !Array.isArray(batch.jobs) || batch.jobs.length > 200 ||
        !Array.isArray(batch.observed_keys) || batch.observed_keys.length > 50000 ||
        !Array.isArray(batch.successful_sources) || batch.successful_sources.length > 100 ||
        !Array.isArray(batch.source_failures) || batch.source_failures.length) fail('invalid_batch');
    if (batch.observed_keys.some(x => typeof x !== 'string' || !KEY_RE.test(x)) ||
        batch.successful_sources.some(x => typeof x !== 'string' || !SOURCE_RE.test(x))) fail('invalid_batch');
    batch.jobs.forEach(job => {
      if (!job || typeof job.source_key !== 'string' || !KEY_RE.test(job.source_key) || !job.values || typeof job.values !== 'object' || Array.isArray(job.values)) fail('invalid_batch');
      const fields = Object.keys(job.values);
      if (fields.length !== HEADERS.length - 1 || fields.some(k => !HEADERS.includes(k) || k === '申请状态' || typeof job.values[k] !== 'string' || job.values[k].length > 8000)) fail('invalid_batch');
      if (['岗位ID', '公司', '岗位名称', '城市', '岗位链接'].some(k => !job.values[k])) fail('invalid_batch');
      canonicalUrl(job.values['岗位链接']);
      if (!batch.successful_sources.includes(job.source_key.split(':').slice(0, 2).join(':')) || !batch.observed_keys.includes(job.source_key)) fail('invalid_batch');
    });
  }

  function readTable(sheet) {
    if (!sheet || sheet.getLastRow() < 1 || sheet.getLastRow() > 20000 || sheet.getLastColumn() < 17 || sheet.getLastColumn() > 100) fail('invalid_headers');
    const range = sheet.getRange(1, 1, sheet.getLastRow(), sheet.getLastColumn());
    const values = range.getValues();
    const formulas = range.getFormulas();
    const notes = range.getNotes();
    const rows = values.map((row, r) => row.map((v, c) => formulas[r][c] || text(v)));
    const headers = rows[0];
    if (new Set(headers).size !== headers.length || headers.some(x => !x) || HEADERS.some(x => !headers.includes(x))) fail('invalid_headers');
    return {rows: rows, notes: notes, digest: hash(stable({rows: rows, notes: notes}))};
  }

  function metadata(row, note, headers) {
    const valid = m => m && typeof m.source_key === 'string' && KEY_RE.test(m.source_key) &&
      m.snapshot && typeof m.snapshot === 'object' && !Array.isArray(m.snapshot) &&
      Object.keys(m.snapshot).every(k => HEADERS.includes(k) && k !== '申请状态' && typeof m.snapshot[k] === 'string');
    try {
      if (note.startsWith(NOTE_PREFIX)) {
        const m = JSON.parse(note.slice(NOTE_PREFIX.length));
        return valid(m) ? m : null;
      }
      // Preserve arbitrary human notes. Only migrate legacy metadata if there
      // is no existing note; never write or remove the old extra columns.
      if (note) return null;
      const source = headers.indexOf('自动化来源ID');
      const snapshot = headers.indexOf('自动化快照');
      if (source < 0 || snapshot < 0 || !row[source] || !row[snapshot]) return null;
      const m = {source_key: row[source], snapshot: JSON.parse(row[snapshot])};
      return valid(m) ? m : null;
    } catch (_) { return null; }
  }

  function plan(table, batch) {
    const headers = table.rows[0];
    const observed = new Set(batch.observed_keys);
    const successful = new Set(batch.successful_sources);
    const idColumn = headers.indexOf('岗位ID');
    const read = row => Object.fromEntries(HEADERS.map(k => [k, row[headers.indexOf(k)] || '']));
    const index = new Map();
    const records = new Map();
    const addIndex = (key, r) => { if (!index.has(key)) index.set(key, new Set()); index.get(key).add(r); };
    table.rows.slice(1).forEach((row, offset) => {
      const r = offset + 2;
      const v = read(row);
      let meta = metadata(row, table.notes[r - 1][idColumn] || '', headers);
      // If a value-only sort or a human edit changes row identity, never trust
      // the note left behind on that cell as ownership of the new row.
      if (meta && ['岗位ID', '公司', '岗位名称', '城市', '岗位链接'].some(k => meta.snapshot[k] !== v[k])) meta = null;
      records.set(r, {values: v, meta: meta});
      if (meta) addIndex('source:' + meta.source_key, r);
      if (v['岗位链接']) {
        try { addIndex('url:' + canonicalUrl(v['岗位链接']), r); } catch (_) { /* manual unsupported URL */ }
      }
      if (v['公司'] && v['岗位名称'] && v['城市']) addIndex('fp:' + fingerprint(v), r);
    });
    const result = {updates: [], notes: [], appends: [], skipped: 0};
    const seen = new Set();
    const handled = new Set();
    function update(r, proposed) {
      const record = records.get(r);
      if (!record.meta) { result.skipped++; return; }
      const snapshot = {};
      Object.keys(record.meta.snapshot).forEach(k => {
        const before = record.meta.snapshot[k];
        if (record.values[k] !== before) return; // permanently release manual edits
        let value = Object.prototype.hasOwnProperty.call(proposed, k) ? proposed[k] : before;
        if (['岗位ID', '发现日期'].includes(k)) value = before;
        if (k === '最后核实' && !value) value = before;
        snapshot[k] = value;
        if (value !== before) result.updates.push({row: r, column: headers.indexOf(k) + 1, before: before, value: value});
      });
      const note = NOTE_PREFIX + stable({source_key: record.meta.source_key, snapshot: snapshot});
      if (note.length > 45000) fail('invalid_batch');
      if (note !== (table.notes[r - 1][idColumn] || '')) result.notes.push({row: r, column: idColumn + 1, before: table.notes[r - 1][idColumn] || '', value: note});
    }
    batch.jobs.forEach(job => {
      const v = job.values;
      const keys = ['source:' + job.source_key, 'url:' + canonicalUrl(v['岗位链接']), 'fp:' + fingerprint(v)];
      if (keys.some(k => seen.has(k))) { result.skipped++; return; }
      keys.forEach(k => seen.add(k));
      const matches = new Set();
      keys.forEach(k => (index.get(k) || []).forEach(r => matches.add(r)));
      if (matches.size) {
        matches.forEach(r => handled.add(r));
        if (matches.size !== 1) { result.skipped++; return; }
        const r = [...matches][0];
        if (!records.get(r).meta || records.get(r).meta.source_key !== job.source_key) { result.skipped++; return; }
        update(r, v);
      } else {
        const note = NOTE_PREFIX + stable({source_key: job.source_key, snapshot: v});
        if (note.length > 45000) fail('invalid_batch');
        result.appends.push({values: headers.map(k => v[k] || ''), note: note});
      }
    });
    records.forEach((record, r) => {
      if (handled.has(r) || !record.meta) return;
      const key = record.meta.source_key;
      if (successful.has(key.split(':').slice(0, 2).join(':')) && !observed.has(key)) {
        update(r, {'招聘状态': '待核实（本次官方列表未出现；未确认关闭）'});
      }
    });
    return result;
  }

  function apply(sheet, table, changes) {
    if (readTable(sheet).digest !== table.digest) fail('sheet_changed');
    // RichTextValue is explicit literal text, including strings beginning '='.
    // No formula interpretation, no clear(), no whole-row overwrite of old rows.
    changes.updates.forEach(c => {
      const cell = sheet.getRange(c.row, c.column);
      const current = cell.getFormula() || text(cell.getValue());
      if (current !== c.before) fail('sheet_changed');
      cell.setRichTextValue(SpreadsheetApp.newRichTextValue().setText(c.value).build());
    });
    changes.notes.forEach(n => {
      const cell = sheet.getRange(n.row, n.column);
      if (cell.getNote() !== n.before) fail('sheet_changed');
      cell.setNote(n.value);
    });
    changes.appends.forEach(record => {
      const row = sheet.getLastRow() + 1;
      if (row > sheet.getMaxRows()) sheet.insertRowsAfter(sheet.getMaxRows(), row - sheet.getMaxRows());
      sheet.getRange(row, 1, 1, record.values.length).setRichTextValues([
        record.values.map(v => SpreadsheetApp.newRichTextValue().setText(v).build())
      ]);
      sheet.getRange(row, table.rows[0].indexOf('岗位ID') + 1).setNote(record.note);
    });
    SpreadsheetApp.flush();
  }

  function process(payload, properties) {
    if (!payload || !['preview', 'write'].includes(payload.operation)) fail('bad_request');
    validateBatch(payload.batch);
    const sheet = SpreadsheetApp.openById(SHEET_ID).getSheetByName(TAB);
    const table = readTable(sheet);
    const changes = plan(table, payload.batch);
    const summary = {new_rows: changes.appends.length, cell_updates: changes.updates.length, metadata_updates: changes.notes.length, skipped: changes.skipped, written: false};
    const digest = hash(stable(payload.batch));
    if (payload.operation === 'preview') {
      const token = Utilities.getUuid();
      properties.setProperty('JD_PREVIEW_' + token, JSON.stringify({expires: Date.now() + 900000, digest: digest, sheet: table.digest}));
      return Object.assign(summary, {preview_token: token});
    }
    if (properties.getProperty('JD_ALLOW_WRITES') !== 'true') fail('writes_disabled');
    if (!/^[a-f0-9-]{36}$/.test(payload.preview_token || '')) fail('preview_required');
    const property = 'JD_PREVIEW_' + payload.preview_token;
    const receipt = properties.getProperty(property);
    if (!receipt) fail('preview_required');
    const preview = JSON.parse(receipt);
    if (preview.expires < Date.now()) fail('preview_expired');
    if (preview.digest !== digest) fail('preview_required');
    if (preview.sheet !== table.digest) fail('sheet_changed');
    // Consume before writing. A failed/partial request cannot reuse this approval.
    properties.deleteProperty(property);
    apply(sheet, table, changes);
    summary.written = true;
    return summary;
  }

  function handle(event) {
    let lock = null;
    let envelope = null;
    let nonceKey = null;
    let properties = null;
    let ownsNonce = false;
    let result;
    const safe = ['auth_failed', 'bad_request', 'writes_disabled', 'preview_required', 'preview_expired', 'sheet_changed', 'invalid_batch', 'invalid_headers', 'busy', 'replay_conflict', 'request_in_progress', 'capacity'];
    try {
      properties = PropertiesService.getScriptProperties();
      envelope = authenticate(event, properties.getProperty('JD_SHARED_SECRET'));
      lock = LockService.getScriptLock();
      if (!lock.tryLock(10000)) fail('busy');
      // ScriptProperties is durable; CacheService alone can evict nonce records.
      const all = properties.getProperties();
      let active = 0;
      Object.keys(all).filter(k => k.startsWith('JD_NONCE_') || k.startsWith('JD_PREVIEW_')).forEach(k => {
        let record;
        try { record = JSON.parse(all[k]); } catch (_) { fail('internal_error'); }
        if (record.expires < Date.now()) properties.deleteProperty(k); else active++;
      });
      nonceKey = 'JD_NONCE_' + envelope.request_id;
      const cached = properties.getProperty(nonceKey);
      if (cached) {
        const record = JSON.parse(cached);
        if (!equal(record.signature, envelope.signature)) fail('replay_conflict');
        if (!record.result) fail('request_in_progress');
        return output(record.result);
      }
      if (active >= 400) fail('capacity');
      properties.setProperty(nonceKey, JSON.stringify({expires: Date.now() + 660000, signature: envelope.signature}));
      ownsNonce = true;
      const bytes = Utilities.base64Decode(envelope.payload_b64);
      if (Utilities.base64Encode(bytes) !== envelope.payload_b64) fail('bad_request');
      let payload;
      try { payload = JSON.parse(Utilities.newBlob(bytes).getDataAsString('UTF-8')); } catch (_) { fail('bad_request'); }
      result = Object.assign({ok: true, request_id: envelope.request_id}, process(payload, properties));
    } catch (error) {
      result = {ok: false, code: safe.includes(error.message) ? error.message : 'internal_error'};
      // Never log the body, key, signature, spreadsheet contents or exception.
    } finally {
      if (lock && lock.hasLock()) {
        try {
          if (ownsNonce) properties.setProperty(nonceKey, JSON.stringify({expires: Date.now() + 660000, signature: envelope.signature, result: result}));
        } finally { lock.releaseLock(); }
      }
    }
    return output(result);
  }

  function output(result) {
    // ContentService cannot set arbitrary HTTP status. Clients MUST check ok.
    return ContentService.createTextOutput(JSON.stringify(result)).setMimeType(ContentService.MimeType.JSON);
  }
  return {handle: handle, plan: plan, headers: HEADERS, canonicalUrl: canonicalUrl};
}());

function jobDiscoveryHandlePost(e) {
  return JobDiscoveryWebApp.handle(e);
}
