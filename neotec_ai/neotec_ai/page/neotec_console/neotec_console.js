frappe.pages['neotec-console'].on_page_load = function (wrapper) {
  const page = frappe.ui.make_app_page({
    parent: wrapper,
    title: 'Neotec Console',
    single_column: true,
  });

  const $body = $(page.body);
  $body.html(`
    <div class="neotec-console" style="max-width:980px;margin:0 auto;">
      <div class="frappe-card" style="padding:16px;margin-bottom:16px;">
        <div style="display:flex;gap:8px;align-items:flex-start;">
          <textarea id="ntc-query" class="form-control" rows="2"
            placeholder="Ask anything — e.g. 'Top 5 customers by sales this quarter', 'Sales report for last month', 'Dashboard of revenue by month'"></textarea>
          <div style="display:flex;flex-direction:column;gap:6px;min-width:150px;">
            <select id="ntc-mode" class="form-control">
              <option value="">Auto-detect</option>
              <option value="solution">Solution</option>
              <option value="report">Report</option>
              <option value="dashboard">Dashboard</option>
            </select>
            <button id="ntc-ask" class="btn btn-primary btn-sm">Ask</button>
          </div>
        </div>
      </div>
      <div id="ntc-actions" style="display:none;margin-bottom:12px;gap:8px;">
        <button id="ntc-save" class="btn btn-default btn-sm">Save permanently</button>
        <button id="ntc-print" class="btn btn-default btn-sm">Print</button>
        <button id="ntc-excel" class="btn btn-default btn-sm">Export Excel</button>
        <button id="ntc-pdf" class="btn btn-default btn-sm">Export PDF</button>
      </div>
      <div id="ntc-result"></div>
    </div>
  `);

  let last = null; // last result payload, used by the action buttons

  const renderTable = (rows) => {
    if (!rows || !rows.length) return '<p class="text-muted">No data.</p>';
    const headers = Object.keys(rows[0]);
    const th = headers.map(h => `<th>${frappe.utils.escape_html(h)}</th>`).join('');
    const trs = rows.map(r =>
      `<tr>${headers.map(h =>
        `<td>${frappe.utils.escape_html(String(r[h] ?? ''))}</td>`).join('')}</tr>`
    ).join('');
    return `<div class="table-responsive"><table class="table table-bordered">
      <thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table></div>`;
  };

  const renderResult = (data) => {
    last = data;
    const $r = $('#ntc-result').empty();
    $('#ntc-actions').css('display', 'flex');

    if (data.intent === 'solution') {
      $r.html(`<div class="frappe-card" style="padding:16px;">
        ${frappe.markdown(data.answer || '')}
        ${data.data && data.data.length ? '<hr>' + renderTable(data.data) : ''}
      </div>`);
    } else if (data.intent === 'report') {
      $r.html(`<div class="frappe-card" id="ntc-printable" style="padding:16px;">
        ${frappe.markdown(data.report || '')}
        <hr>${renderTable(data.data)}
      </div>`);
    } else if (data.intent === 'dashboard') {
      const dash = data.dashboard || {};
      $r.append(`<h4 style="margin-bottom:12px;">${frappe.utils.escape_html(dash.title || 'Dashboard')}</h4>`);
      (dash.widgets || []).forEach((w, i) => {
        if (w.error) {
          $r.append(`<div class="frappe-card" style="padding:12px;margin-bottom:12px;">
            <b>${frappe.utils.escape_html(w.title)}</b>
            <div class="text-muted">Could not build: ${frappe.utils.escape_html(w.error)}</div></div>`);
          return;
        }
        const id = `ntc-chart-${i}`;
        $r.append(`<div class="frappe-card" style="padding:12px;margin-bottom:12px;">
          <b>${frappe.utils.escape_html(w.title)}</b><div id="${id}"></div></div>`);
        try {
          new frappe.Chart(`#${id}`, {
            title: w.title,
            data: { labels: w.labels, datasets: [{ name: w.title, values: w.values }] },
            type: ['bar', 'line', 'pie', 'percentage'].includes(w.chart_type) ? w.chart_type : 'bar',
            height: 240,
          });
        } catch (e) { /* chart lib edge cases */ }
      });
    }
  };

  $body.on('click', '#ntc-ask', () => {
    const query = $('#ntc-query').val().trim();
    if (!query) return;
    const mode = $('#ntc-mode').val();
    page.set_indicator('Thinking…', 'orange');
    frappe.call({
      method: 'neotec_ai.api.ask',
      args: { query, mode },
      freeze: true, freeze_message: 'Neotec is working…',
      callback: (r) => {
        page.clear_indicator();
        if (r.message && r.message.ok) renderResult(r.message);
      },
      error: () => page.clear_indicator(),
    });
  });

  $body.on('click', '#ntc-save', () => {
    if (!last) return;
    frappe.prompt({ fieldname: 'title', label: 'Title', fieldtype: 'Data',
      default: (last.question || 'Untitled').slice(0, 80) },
      (v) => {
        const payload = Object.assign({}, last, { title: v.title });
        frappe.call({ method: 'neotec_ai.api.save_result',
          args: { payload: JSON.stringify(payload) },
          callback: (r) => { if (r.message && r.message.ok)
            frappe.show_alert({ message: `Saved as ${r.message.name}`, indicator: 'green' }); } });
      }, 'Save permanently', 'Save');
  });

  $body.on('click', '#ntc-print', () => {
    const html = $('#ntc-result').html();
    const w = window.open('', '_blank');
    w.document.write(`<html><head><title>Neotec Report</title></head><body>${html}</body></html>`);
    w.document.close(); w.focus(); w.print();
  });

  $body.on('click', '#ntc-excel', () => {
    const rows = (last && (last.data || (last.dashboard && last.dashboard.widgets &&
      last.dashboard.widgets[0] && last.dashboard.widgets[0].data))) || [];
    frappe.call({ method: 'neotec_ai.api.export_excel',
      args: { data_json: JSON.stringify(rows), title: (last.question || 'neotec').slice(0, 40) },
      callback: (r) => { if (r.message && r.message.ok) window.open(r.message.file_url); } });
  });

  $body.on('click', '#ntc-pdf', () => {
    const html = `<div style="font-family:sans-serif;">${$('#ntc-result').html()}</div>`;
    frappe.call({ method: 'neotec_ai.api.export_pdf',
      args: { html, title: (last.question || 'neotec').slice(0, 40) },
      callback: (r) => { if (r.message && r.message.ok) window.open(r.message.file_url); } });
  });
};
