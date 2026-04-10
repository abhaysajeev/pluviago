/* ======================================================
   Pluviago Biotech — Vendor-to-Inventory Workspace JS
   Uses frappe.call + Chart.js for live analytics
====================================================== */

frappe.require([
  'https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js'
], function () {
  'use strict';

  // ── colour palette ──
  const C = {
    blue:   '#4361ee', green:  '#10b981', orange: '#f59e0b',
    red:    '#ef4444', purple: '#8b5cf6', grey:   '#94a3b8',
    blueBg: 'rgba(67,97,238,.12)', greenBg:'rgba(16,185,129,.12)',
    orangeBg:'rgba(245,158,11,.12)', redBg:'rgba(239,68,68,.12)',
    purpleBg:'rgba(139,92,246,.12)',
  };

  // ── helpers ──
  const fmt = (n) => (n || 0).toLocaleString();
  const today = frappe.datetime.nowdate();
  const navTo = (dt, f) => frappe.set_route('List', dt, f || {});

  // ────────────────────────────────────────────────────
  //  Data fetcher — all KPIs + chart data in one call
  // ────────────────────────────────────────────────────
  function fetchDashboardData() {
    return Promise.all([
      // KPI counts
      frappe.xcall('frappe.client.get_count', { doctype: 'Approved Vendor', filters: { docstatus: 1 } }),
      frappe.xcall('frappe.client.get_count', { doctype: 'Purchase Order',  filters: { docstatus: 1, company: 'Pluviago Biotech Pvt. Ltd.' } }),
      frappe.xcall('frappe.client.get_count', { doctype: 'Purchase Receipt', filters: { docstatus: 1, company: 'Pluviago Biotech Pvt. Ltd.' } }),
      frappe.xcall('frappe.client.get_count', { doctype: 'Chemical COA',    filters: { docstatus: 1 } }),
      frappe.xcall('frappe.client.get_count', { doctype: 'Raw Material Batch', filters: { docstatus: 1 } }),
      // RMB status breakdown
      frappe.xcall('frappe.client.get_count', { doctype: 'Raw Material Batch', filters: { docstatus: 1, qc_status: 'Approved' } }),
      frappe.xcall('frappe.client.get_count', { doctype: 'Raw Material Batch', filters: { docstatus: 1, qc_status: 'Pending' } }),
      frappe.xcall('frappe.client.get_count', { doctype: 'Raw Material Batch', filters: { docstatus: 1, qc_status: 'Rejected' } }),
      // Recent RMBs
      frappe.xcall('frappe.client.get_list', {
        doctype: 'Raw Material Batch', fields: ['name','material_name','supplier','received_qty','received_qty_uom','remaining_qty','qc_status','expiry_date','status'],
        filters: { docstatus: 1 }, order_by: 'creation desc', limit_page_length: 8
      }),
      // Recent COAs
      frappe.xcall('frappe.client.get_list', {
        doctype: 'Chemical COA', fields: ['name','supplier','item_code','overall_result','verification_date','verified_by'],
        filters: { docstatus: 1 }, order_by: 'creation desc', limit_page_length: 5
      }),
      // Recent POs
      frappe.xcall('frappe.client.get_list', {
        doctype: 'Purchase Order', fields: ['name','supplier','grand_total','status','transaction_date'],
        filters: { docstatus: 1, company: 'Pluviago Biotech Pvt. Ltd.' }, order_by: 'creation desc', limit_page_length: 5
      }),
      // AVL status counts
      frappe.xcall('frappe.client.get_count', { doctype: 'Approved Vendor', filters: { docstatus: 1, approval_status: 'Approved' } }),
      frappe.xcall('frappe.client.get_count', { doctype: 'Approved Vendor', filters: { docstatus: 1, approval_status: 'Pending' } }),
      frappe.xcall('frappe.client.get_count', { doctype: 'Approved Vendor', filters: { docstatus: 1, approval_status: 'Suspended' } }),
      // COA pass/fail
      frappe.xcall('frappe.client.get_count', { doctype: 'Chemical COA', filters: { docstatus: 1, overall_result: 'Pass' } }),
      frappe.xcall('frappe.client.get_count', { doctype: 'Chemical COA', filters: { docstatus: 1, overall_result: 'Fail' } }),
      // Stock consumption logs
      frappe.xcall('frappe.client.get_count', { doctype: 'Stock Consumption Log', filters: {} }),
    ]).catch(err => {
      console.warn('Pluviago Workspace: some API calls failed, using defaults', err);
      return Array(17).fill(0);
    });
  }

  // ────────────────────────────────────────────────────
  //  Render functions
  // ────────────────────────────────────────────────────
  function renderKPIs(data) {
    const [avlCount, poCount, prCount, coaCount, rmbCount] = data;
    const kpis = [
      { label:'Approved Vendors', value:fmt(avlCount), icon:'✅', cls:'green', dt:'Approved Vendor' },
      { label:'Purchase Orders',  value:fmt(poCount),  icon:'📋', cls:'blue',  dt:'Purchase Order' },
      { label:'Purchase Receipts',value:fmt(prCount),  icon:'📦', cls:'purple',dt:'Purchase Receipt' },
      { label:'Chemical COAs',    value:fmt(coaCount), icon:'🔬', cls:'orange',dt:'Chemical COA' },
      { label:'Raw Material Batches', value:fmt(rmbCount), icon:'🧪', cls:'blue', dt:'Raw Material Batch' },
    ];
    const container = document.getElementById('pv-kpis');
    container.innerHTML = kpis.map(k => `
      <div class="pv-kpi ${k.cls}" onclick="frappe.set_route('List','${k.dt}')">
        <div class="pv-kpi-icon">${k.icon}</div>
        <div class="pv-kpi-value">${k.value}</div>
        <div class="pv-kpi-label">${k.label}</div>
      </div>`).join('');
  }

  function renderPipelineCounts(data) {
    const ids = ['flow-avl','flow-po','flow-pr','flow-coa','flow-rmb'];
    data.slice(0,5).forEach((v,i) => {
      const el = document.getElementById(ids[i]);
      if (el) el.textContent = fmt(v) + ' records';
    });
  }

  // ── Chart: QC Status (Doughnut) ──
  function renderQCChart(approved, pending, rejected) {
    const ctx = document.getElementById('chart-qc-status');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Approved','Pending','Rejected'],
        datasets: [{ data:[approved,pending,rejected], backgroundColor:[C.green,C.orange,C.red], borderWidth:0, hoverOffset:6 }]
      },
      options: {
        cutout: '68%', responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position:'bottom', labels:{ padding:14, usePointStyle:true, pointStyleWidth:8, font:{size:11,weight:600} } }
        }
      }
    });
  }

  // ── Chart: AVL Breakdown (Doughnut) ──
  function renderAVLChart(approved, pending, suspended) {
    const ctx = document.getElementById('chart-avl-status');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Approved','Pending','Suspended'],
        datasets: [{ data:[approved,pending,suspended], backgroundColor:[C.green,C.orange,C.grey], borderWidth:0, hoverOffset:6 }]
      },
      options: {
        cutout: '68%', responsive: true, maintainAspectRatio: false,
        plugins: {
          legend: { position:'bottom', labels:{ padding:14, usePointStyle:true, pointStyleWidth:8, font:{size:11,weight:600} } }
        }
      }
    });
  }

  // ── Chart: COA Results (Bar) ──
  function renderCOAChart(pass, fail) {
    const ctx = document.getElementById('chart-coa-results');
    if (!ctx) return;
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ['Pass','Fail'],
        datasets: [{ data:[pass,fail], backgroundColor:[C.green, C.red], borderRadius:8, barPercentage:.5 }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: { y:{ beginAtZero:true, ticks:{stepSize:1, font:{size:11}}, grid:{color:'#f1f5f9'} }, x:{ grid:{display:false}, ticks:{font:{size:11,weight:600}} } },
        plugins: { legend:{display:false} }
      }
    });
  }

  // ── Chart: Inventory Overview (Horizontal Bar) ──
  function renderInventoryChart(rmbList) {
    const ctx = document.getElementById('chart-inventory');
    if (!ctx) return;
    const top6 = (rmbList||[]).slice(0,6);
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: top6.map(r => (r.material_name||r.name).substring(0,18)),
        datasets: [
          { label:'Remaining', data:top6.map(r=>r.remaining_qty||0), backgroundColor:C.blue, borderRadius:6, barPercentage:.6 },
          { label:'Received',  data:top6.map(r=>r.received_qty||0),  backgroundColor:C.blueBg, borderRadius:6, barPercentage:.6 },
        ]
      },
      options: {
        indexAxis:'y', responsive:true, maintainAspectRatio:false,
        scales: { x:{ beginAtZero:true, grid:{color:'#f1f5f9'}, ticks:{font:{size:10}} }, y:{ grid:{display:false}, ticks:{font:{size:10,weight:600}} } },
        plugins: { legend:{ position:'top', align:'end', labels:{usePointStyle:true, pointStyleWidth:8, font:{size:10}} } }
      }
    });
  }

  // ── Recent RMB Table ──
  function renderRMBTable(list) {
    const tbody = document.getElementById('pv-rmb-tbody');
    if (!tbody) return;
    if (!list || !list.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--pv-muted);padding:24px">No Raw Material Batches yet</td></tr>'; return; }
    tbody.innerHTML = list.map(r => {
      const stCls = (r.qc_status||'').toLowerCase().replace(/\s/g,'');
      const isExpired = r.expiry_date && r.expiry_date < today;
      return `<tr>
        <td><a href="/app/raw-material-batch/${r.name}">${r.name}</a></td>
        <td>${r.material_name||'-'}</td>
        <td>${r.supplier||'-'}</td>
        <td>${fmt(r.received_qty)} ${r.received_qty_uom||''}</td>
        <td>${fmt(r.remaining_qty)} ${r.received_qty_uom||''}</td>
        <td><span class="pv-status ${stCls}">${r.qc_status||'-'}</span></td>
        <td>${isExpired ? '<span class="pv-status expired">Expired</span>' : (r.expiry_date||'-')}</td>
      </tr>`;
    }).join('');
  }

  // ── Recent COA Table ──
  function renderCOATable(list) {
    const tbody = document.getElementById('pv-coa-tbody');
    if (!tbody) return;
    if (!list || !list.length) { tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--pv-muted);padding:24px">No COAs yet</td></tr>'; return; }
    tbody.innerHTML = list.map(r => {
      const resCls = (r.overall_result||'').toLowerCase();
      return `<tr>
        <td><a href="/app/chemical-coa/${r.name}">${r.name}</a></td>
        <td>${r.supplier||'-'}</td>
        <td>${r.item_code||'-'}</td>
        <td><span class="pv-status ${resCls}">${r.overall_result||'-'}</span></td>
        <td>${r.verification_date||'-'}</td>
      </tr>`;
    }).join('');
  }

  // ── Alerts ──
  function renderAlerts(rmbList) {
    const container = document.getElementById('pv-alerts');
    if (!container) return;
    const alerts = [];
    (rmbList||[]).forEach(r => {
      if (r.expiry_date && r.expiry_date < today) {
        alerts.push({ type:'danger', icon:'⛔', title:`${r.name} Expired`, detail:`${r.material_name} expired on ${r.expiry_date}` });
      } else if (r.expiry_date) {
        const diff = frappe.datetime.get_diff(r.expiry_date, today);
        if (diff <= 30 && diff > 0) {
          alerts.push({ type:'warn', icon:'⚠️', title:`${r.name} Expiring Soon`, detail:`${r.material_name} expires in ${diff} days` });
        }
      }
      if (r.remaining_qty !== undefined && r.remaining_qty <= 0 && r.qc_status === 'Approved') {
        alerts.push({ type:'info', icon:'📭', title:`${r.name} Exhausted`, detail:`${r.material_name} stock depleted` });
      }
    });
    if (!alerts.length) { container.innerHTML = '<div class="pv-alert info"><div class="pv-alert-icon">✅</div><div><div class="pv-alert-title">All Clear</div>No alerts at this time.</div></div>'; return; }
    container.innerHTML = alerts.slice(0,6).map(a => `
      <div class="pv-alert ${a.type}">
        <div class="pv-alert-icon">${a.icon}</div>
        <div>
          <div class="pv-alert-title">${a.title}</div>
          <div class="pv-alert-meta">${a.detail}</div>
        </div>
      </div>`).join('');
  }

  // ────────────────────────────────────────────────────
  //  INIT — bootstrap everything
  // ────────────────────────────────────────────────────
  function init() {
    fetchDashboardData().then(data => {
      const [avl,po,pr,coa,rmb, qcApp,qcPend,qcRej, rmbList,coaList,poList, avlApp,avlPend,avlSusp, coaPass,coaFail, sclCount] = data;

      renderKPIs(data);
      renderPipelineCounts(data);
      renderQCChart(qcApp||0, qcPend||0, qcRej||0);
      renderAVLChart(avlApp||0, avlPend||0, avlSusp||0);
      renderCOAChart(coaPass||0, coaFail||0);
      renderInventoryChart(rmbList);
      renderRMBTable(rmbList);
      renderCOATable(coaList);
      renderAlerts(rmbList);

      // SCL count
      const sclEl = document.getElementById('pv-scl-count');
      if (sclEl) sclEl.textContent = fmt(sclCount);
    });
  }

  // Wait for DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    // small delay to let the HTML block render
    setTimeout(init, 300);
  }
});
