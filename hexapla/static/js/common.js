// Bilingual Navigator: helpers shared by every page.
(function () {
  const NAV = window.NAV || {};

  // ----- Formatting -----
  NAV.pct = (x, digits = 0) => (x === null || x === undefined ? "–" : `${(x * 100).toFixed(digits)}%`);
  NAV.num = x => (x === null || x === undefined ? "–" : Number(x).toLocaleString());
  NAV.dec = (x, digits = 2) => (x === null || x === undefined ? "–" : Number(x).toFixed(digits));
  NAV.esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  // ----- URLs -----
  NAV.verseUrl = verseId => `${NAV.msUrl}${verseId}/`;
  NAV.lemmaUrl = (langId, lemma) => `${NAV.msUrl}${langId}/${encodeURIComponent(lemma)}/`;
  NAV.linkableLemma = lemma => lemma && !["_", ".", ".."].includes(lemma) && !/[\/\\]/.test(lemma);

  // ----- Sequential colour (one hue, light -> dark), for heatmaps -----
  // The theme's sequential ramp, light to dark (--ramp-0 ... --ramp-6 in hexapla.css).
  const rootStyle = getComputedStyle(document.documentElement);
  NAV.cssColor = name => rootStyle.getPropertyValue(name).trim();
  const RAMP = [0, 1, 2, 3, 4, 5, 6].map(i => NAV.cssColor(`--ramp-${i}`));
  NAV.rampColor = t => {
    const x = Math.max(0, Math.min(1, t)) * (RAMP.length - 1);
    const i = Math.min(RAMP.length - 2, Math.floor(x));
    return d3.interpolateLab(RAMP[i], RAMP[i + 1])(x - i);
  };
  NAV.inkOn = t => (t > 0.45 ? "#ffffff" : "#1b1b1f");

  // ----- Tooltip -----
  const tip = () => document.getElementById("tooltip");
  NAV.showTip = (event, html) => {
    const el = tip();
    if (!el) return;
    el.innerHTML = html;
    el.style.opacity = 1;
    const pad = 14;
    const { innerWidth: w, innerHeight: h } = window;
    const rect = el.getBoundingClientRect();
    let x = event.clientX + pad;
    let y = event.clientY + pad;
    if (x + rect.width > w - 8) x = event.clientX - rect.width - pad;
    if (y + rect.height > h - 8) y = event.clientY - rect.height - pad;
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
  };
  NAV.hideTip = () => { const el = tip(); if (el) el.style.opacity = 0; };

  // ----- Verse text with highlighted words -----
  // side = {ids:[], forms:[], ns:[]} from corpus.js
  NAV.renderText = (side, highlightIds = [], cls = "hl") => {
    const hl = new Set((highlightIds || []).map(Number));
    const ns = new Set(side.ns || []);
    return side.ids.map((id, i) => {
      const form = NAV.esc(side.forms[i]);
      const word = hl.has(id) ? `<span class="${cls}">${form}</span>` : form;
      return word + (i < side.ids.length - 1 && !ns.has(id) ? " " : "");
    }).join("");
  };

  NAV.exampleHtml = (verse, aIds, bIds) => {
    const L = NAV.langs;
    const dirA = L.a.rtl ? ' dir="rtl"' : "";
    const dirB = L.b.rtl ? ' dir="rtl"' : "";
    return `<div class="example">
      <div class="ref"><a href="${NAV.verseUrl(verse.id)}">${NAV.esc(verse.label)}</a></div>
      <div class="txt"${dirA}><span class="lang">${NAV.esc(L.a.label)}</span>${NAV.renderText(verse.a, aIds)}</div>
      <div class="txt"${dirB}><span class="lang">${NAV.esc(L.b.label)}</span>${NAV.renderText(verse.b, bIds)}</div>
    </div>`;
  };

  // ----- Sortable tables: <th data-sort="key" data-type="num|text"> -----
  NAV.sortable = (table, rows, renderRows, initial) => {
    let state = initial || null;
    const ths = table.querySelectorAll("th[data-sort]");
    const apply = () => {
      if (state) {
        const { key, dir, type } = state;
        rows.sort((x, y) => {
          let a = x[key], b = y[key];
          if (a === null || a === undefined) return 1;
          if (b === null || b === undefined) return -1;
          if (type === "text") return dir * String(a).localeCompare(String(b));
          return dir * (a - b);
        });
      }
      ths.forEach(th => {
        th.classList.remove("sorted-asc", "sorted-desc");
        if (state && th.dataset.sort === state.key) th.classList.add(state.dir > 0 ? "sorted-asc" : "sorted-desc");
      });
      renderRows(rows);
    };
    ths.forEach(th => th.addEventListener("click", () => {
      const key = th.dataset.sort;
      const type = th.dataset.type || "num";
      const dir = state && state.key === key ? -state.dir : (type === "text" ? 1 : -1);
      state = { key, dir, type };
      apply();
    }));
    apply();
    return { refresh: apply };
  };

  // "/" focuses the page's search box
  document.addEventListener("keydown", e => {
    if (e.key === "/" && !/input|textarea|select/i.test(document.activeElement.tagName)) {
      const search = document.querySelector("[data-search]");
      if (search) { e.preventDefault(); search.focus(); }
    }
  });

  // Fill a page-jump <select> from window.SELECT_ITEMS ([[id, label], ...]); choosing navigates to ../<id>/.
  NAV.fillSelector = select => {
    if (!select) return;
    const current = select.dataset.current;
    const fragment = document.createDocumentFragment();
    for (const [id, label] of window.SELECT_ITEMS || []) fragment.appendChild(new Option(label, id, false, id === current));
    select.appendChild(fragment);
    // Keep the hash so the verse page stays on the same view (#view=matrix...).
    select.addEventListener("change", () => { window.location.href = `../${select.value}/${window.location.hash}`; });
  };

  window.NAV = NAV;
})();
