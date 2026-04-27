/* ═══════════════════════════════════════════════════════════
   PLUVIAGO BIOTECH — OPERATING HUB · Workspace Controller
   For Frappe Custom HTML Block — uses `root_element` scope
═══════════════════════════════════════════════════════════ */

const root = root_element.querySelector('#plv-hub') || root_element;

if (root.dataset.plvBound !== '1') {
  root.dataset.plvBound = '1';

  const $  = (s) => root.querySelector(s);
  const $$ = (s) => Array.from(root.querySelectorAll(s));

  // ───────── header chips ─────────
  const dateEl = $('#plv-date');
  const userEl = $('#plv-user');
  if (dateEl) {
    dateEl.textContent = new Date().toLocaleDateString(undefined, {
      weekday: 'short', day: '2-digit', month: 'short', year: 'numeric',
    });
  }
  if (userEl && window.frappe && frappe.session) {
    userEl.textContent = frappe.session.user_fullname || frappe.session.user || 'User';
  } else if (userEl) {
    userEl.style.display = 'none';
  }

  // ───────── routing helpers ─────────
  const go = function () {
    try { frappe.set_route.apply(frappe, arguments); }
    catch (e) { console.warn('[plv-hub] route failed', e); }
  };
  const openList   = (dt, f) => go('List', dt, f && Object.keys(f).length ? f : undefined);
  const openDoc    = (dt, n) => go('Form', dt, n);
  const openReport = (n)     => go('query-report', n);
  const openNew    = (dt)    => { try { frappe.new_doc(dt); } catch (e) { go('Form', dt, 'new'); } };

  const parseFilter = (el) => {
    const raw = el && el.getAttribute('data-filter');
    if (!raw) return null;
    try { return JSON.parse(raw); } catch (e) { return null; }
  };

  // ───────── click bindings ─────────
  $$('.plv-kpi').forEach((el) => {
    el.addEventListener('click', () => {
      const dt = el.getAttribute('data-route');
      if (dt) openList(dt, parseFilter(el) || {});
    });
  });

  $$('.plv-stage').forEach((el) => {
    el.addEventListener('click', () => {
      openList('Production Batch', { current_stage: el.getAttribute('data-stage') });
    });
  });

  $$('[data-action="new"]').forEach((el) => {
    el.addEventListener('click', () => {
      const dt = el.getAttribute('data-doctype');
      if (dt) openNew(dt);
    });
  });

  $$('.plv-link').forEach((el) => {
    el.addEventListener('click', () => {
      const report = el.getAttribute('data-report');
      if (report) return openReport(report);
      const dt = el.getAttribute('data-route');
      if (dt) openList(dt, parseFilter(el) || {});
    });
  });

  // ───────── smart batch search ─────────
  const PREFIX_MAP = [
    { rx: /^RMB[-_]/i,                dt: 'Raw Material Batch' },
    { rx: /^COA[-_]/i,                dt: 'Chemical COA' },
    { rx: /^SSB[-_]/i,                dt: 'Stock Solution Batch' },
    { rx: /^MED[-_]GRN/i,             dt: 'Medium Batch', extra: { medium_type: 'Green' } },
    { rx: /^MED[-_]RED/i,             dt: 'Medium Batch', extra: { medium_type: 'Red' } },
    { rx: /^FMB[-_]/i,                dt: 'Final Medium Batch' },
    { rx: /^PROD[-_]/i,               dt: 'Production Batch' },
    { rx: /^HVB[-_]|^HRV[-_]|^HARV/i, dt: 'Harvest Batch' },
    { rx: /^EXT[-_]/i,                dt: 'Extraction Batch' },
    { rx: /^AVL[-_]/i,                dt: 'Approved Vendor' },
    { rx: /^QPS[-_]/i,                dt: 'QC Parameter Spec' },
    { rx: /^SCL[-_]/i,                dt: 'Stock Consumption Log' },
    { rx: /^CON[-_]|^CINC/i,          dt: 'Contamination Incident' },
  ];

  const runSearch = () => {
    const input = $('#plv-batch-search');
    const q = (input && input.value || '').trim();
    if (!q) { input && input.focus(); return; }

    const m = PREFIX_MAP.find((p) => p.rx.test(q));
    if (!m) {
      openList('Raw Material Batch', { name: ['like', '%' + q + '%'] });
      return;
    }
    callApi('frappe.client.get_value', { doctype: m.dt, filters: { name: q }, fieldname: 'name' })
      .then((r) => {
        if (r && r.message && r.message.name) openDoc(m.dt, r.message.name);
        else openList(m.dt, Object.assign({ name: ['like', '%' + q + '%'] }, m.extra || {}));
      })
      .catch(() => openList(m.dt, Object.assign({ name: ['like', '%' + q + '%'] }, m.extra || {})));
  };

  const sBtn = $('#plv-search-btn'), sIn = $('#plv-batch-search');
  sBtn && sBtn.addEventListener('click', runSearch);
  sIn  && sIn.addEventListener('keydown', (e) => { if (e.key === 'Enter') runSearch(); });

  // ───────── Frappe API wrappers ─────────
  const callApi = (method, args) => {
    if (!(window.frappe && frappe.call)) return Promise.reject('frappe.call missing');
    return new Promise((resolve, reject) => {
      frappe.call({
        method: method, args: args || {}, type: 'GET',
        callback: (r) => resolve(r),
        error: (e) => reject(e),
      });
    });
  };

  const getCount = (doctype, filters) =>
    callApi('frappe.client.get_count', { doctype: doctype, filters: filters || {} })
      .then((r) => (r && typeof r.message === 'number') ? r.message : 0)
      .catch(() => null);

  const getList = (doctype, opts) =>
    callApi('frappe.client.get_list', Object.assign({ doctype: doctype }, opts || {}))
      .then((r) => (r && Array.isArray(r.message)) ? r.message : [])
      .catch(() => []);

  // ───────── DOM setters ─────────
  const setNum = (key, val) => {
    const el = root.querySelector('[data-kpi="' + key + '"]');
    if (el) el.textContent = (val == null ? '—' : Number(val).toLocaleString());
  };
  const setCnt = (doctype, val) => {
    $$('[data-cnt-doctype]').forEach((el) => {
      if (el.getAttribute('data-cnt-doctype') === doctype) {
        el.textContent = (val == null ? '—' : val);
      }
    });
  };
  const setStageCnt = (stage, val) => {
    $$('[data-stage-cnt]').forEach((el) => {
      if (el.getAttribute('data-stage-cnt') === stage) {
        el.textContent = (val == null ? '—' : val);
      }
    });
  };

  const addDaysISO = (n) => {
    const d = new Date(); d.setDate(d.getDate() + n);
    return d.toISOString().slice(0, 10);
  };

  // ───────── KPIs ─────────
  const loadKPIs = () => {
    const in30 = addDaysISO(30);
    getCount('Chemical COA',           { docstatus: 0 }).then((n) => setNum('coa_pending', n));
    getCount('Raw Material Batch',     { qc_status: 'Pending', docstatus: 0 }).then((n) => setNum('rmb_pending', n));
    getCount('Production Batch',       { status: 'Active' }).then((n) => setNum('prod_active', n));
    getCount('Contamination Incident', {}).then((n) => setNum('contam_open', n));
    getCount('Stock Solution Batch',   { docstatus: 1 }).then((n) => setNum('ssb_available', n));
    getCount('Raw Material Batch', { docstatus: 1, expiry_date: ['<=', in30], remaining_qty: ['>', 0] })
      .then((n) => setNum('expiring', n));
  };

  // ───────── Module link counts ─────────
  const loadModuleCounts = () => {
    ['Chemical COA','Raw Material Batch','Stock Solution Batch','Final Medium Batch',
     'Production Batch','Contamination Incident','Harvest Batch','Extraction Batch']
    .forEach((dt) => getCount(dt, {}).then((n) => setCnt(dt, n)));
  };

  // ───────── Pipeline stage counts ─────────
  const loadStageCounts = () => {
    ['Flask','25L PBR','275L PBR','925L PBR','6600L PBR','Harvested'].forEach((s) => {
      getCount('Production Batch', { current_stage: s, status: 'Active' })
        .then((n) => setStageCnt(s, n));
    });
  };

  // ───────── Action Center ─────────
  const rowEl = (opts) => {
    const div = document.createElement('div');
    div.className = 'plv-row sev-' + (opts.sev || 'low');
    const dot = document.createElement('span'); dot.className = 'plv-dot';
    const body = document.createElement('div'); body.className = 'plv-row-body';
    const title = document.createElement('div'); title.className = 'plv-row-title'; title.textContent = opts.title || '';
    const meta = document.createElement('div'); meta.className = 'plv-row-meta'; meta.textContent = opts.meta || '';
    body.appendChild(title); body.appendChild(meta);
    div.appendChild(dot); div.appendChild(body);
    if (opts.onClick) div.addEventListener('click', opts.onClick);
    return div;
  };

  const loadAlerts = () => {
    const box = $('#plv-alerts'); if (!box) return;
    box.innerHTML = '';
    const in30 = addDaysISO(30);

    const tasks = [
      getList('Raw Material Batch', {
        filters: { docstatus: 1, expiry_date: ['<=', in30], remaining_qty: ['>', 0] },
        fields: ['name','material_name','expiry_date','remaining_qty','received_qty_uom'],
        order_by: 'expiry_date asc', limit: 5,
      }).then((rows) => rows.map((r) => ({
        title: 'Expiring: ' + (r.material_name || r.name),
        meta: r.name + ' · ' + (r.expiry_date || '') + ' · ' + (r.remaining_qty || 0) + ' ' + (r.received_qty_uom || ''),
        sev: 'high', onClick: () => openDoc('Raw Material Batch', r.name),
      }))),

      getList('Chemical COA', {
        filters: { docstatus: 0 },
        fields: ['name','material_name','supplier','coa_date'],
        order_by: 'modified desc', limit: 4,
      }).then((rows) => rows.map((r) => ({
        title: 'COA pending: ' + (r.material_name || r.name),
        meta: r.name + ' · ' + (r.supplier || '—') + ' · ' + (r.coa_date || ''),
        sev: 'med', onClick: () => openDoc('Chemical COA', r.name),
      }))),

      getList('Raw Material Batch', {
        filters: { qc_status: 'Pending', docstatus: 0 },
        fields: ['name','material_name','supplier','received_date'],
        order_by: 'received_date desc', limit: 4,
      }).then((rows) => rows.map((r) => ({
        title: 'QC pending: ' + (r.material_name || r.name),
        meta: r.name + ' · ' + (r.supplier || '—'),
        sev: 'med', onClick: () => openDoc('Raw Material Batch', r.name),
      }))),

      getList('Production Batch', {
        filters: { contamination_status: 'Contaminated' },
        fields: ['name','current_stage','strain'],
        order_by: 'modified desc', limit: 3,
      }).then((rows) => rows.map((r) => ({
        title: 'Contamination: ' + r.name,
        meta: 'Stage ' + (r.current_stage || '—') + ' · strain ' + (r.strain || '—'),
        sev: 'high', onClick: () => openDoc('Production Batch', r.name),
      }))),
    ];

    Promise.all(tasks).then((groups) => {
      const flat = [].concat.apply([], groups);
      if (!flat.length) {
        box.innerHTML = '<div class="plv-empty">All clear — no pending QC, expiry or contamination alerts.</div>';
        return;
      }
      flat.slice(0, 12).forEach((a) => box.appendChild(rowEl(a)));
    });
  };

  // ───────── Recent activity ─────────
  const RECENT_TAGS = {
    'Raw Material Batch':   'RMB',
    'Chemical COA':         'COA',
    'Stock Solution Batch': 'SSB',
    'Medium Batch':         'MED',
    'Final Medium Batch':   'FMB',
    'Production Batch':     'PROD',
    'Harvest Batch':        'HVB',
  };
  const timeAgo = (iso) => {
    if (!iso) return '';
    const d = new Date(String(iso).replace(' ', 'T'));
    if (isNaN(d.getTime())) return '';
    const s = Math.max(1, Math.floor((Date.now() - d.getTime()) / 1000));
    if (s < 60) return s + 's';
    const m = Math.floor(s / 60); if (m < 60) return m + 'm';
    const h = Math.floor(m / 60); if (h < 24) return h + 'h';
    const dd = Math.floor(h / 24); if (dd < 30) return dd + 'd';
    return d.toLocaleDateString();
  };

  const loadRecent = () => {
    const box = $('#plv-recent'); if (!box) return;
    const dts = Object.keys(RECENT_TAGS);
    const ps = dts.map((dt) =>
      getList(dt, { fields: ['name','modified'], order_by: 'modified desc', limit: 3 })
        .then((rows) => rows.map((r) => ({ dt: dt, name: r.name, modified: r.modified })))
    );

    Promise.all(ps).then((groups) => {
      const all = [].concat.apply([], groups)
        .sort((a, b) => String(b.modified || '').localeCompare(String(a.modified || '')))
        .slice(0, 7);

      box.innerHTML = '';
      if (!all.length) {
        box.innerHTML = '<div class="plv-empty">No recent activity.</div>';
        return;
      }
      all.forEach((r) => {
        const row = document.createElement('div');
        row.className = 'plv-row';
        const tag = document.createElement('span'); tag.className = 'plv-rec-tag'; tag.textContent = RECENT_TAGS[r.dt];
        const body = document.createElement('div'); body.className = 'plv-row-body';
        const title = document.createElement('div'); title.className = 'plv-row-title'; title.textContent = r.name;
        const meta = document.createElement('div'); meta.className = 'plv-row-meta'; meta.textContent = r.dt;
        body.appendChild(title); body.appendChild(meta);
        const time = document.createElement('span'); time.className = 'plv-row-time'; time.textContent = timeAgo(r.modified);
        row.appendChild(tag); row.appendChild(body); row.appendChild(time);
        row.addEventListener('click', () => openDoc(r.dt, r.name));
        box.appendChild(row);
      });
    });
  };

  // ───────── refresh + auto-refresh ─────────
  const refreshAll = () => {
    loadKPIs();
    loadStageCounts();
    loadModuleCounts();
    loadAlerts();
    loadRecent();
  };
  const rBtn = $('#plv-refresh');
  rBtn && rBtn.addEventListener('click', refreshAll);

  refreshAll();

  if (root._plvTimer) clearInterval(root._plvTimer);
  root._plvTimer = setInterval(() => {
    if (!document.body.contains(root)) { clearInterval(root._plvTimer); return; }
    if (document.visibilityState === 'visible') refreshAll();
  }, 60000);
}
