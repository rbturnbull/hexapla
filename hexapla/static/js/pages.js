// Bilingual Navigator: overview, lexicon, insights and review pages.
(function () {
  const NAV = window.NAV;
  const page = document.body.dataset.page;
  const L = NAV.langs;

  // ================================================================ overview
  function initOverview() {
    const data = OVERVIEW;
    const verses = data.verses;

    // ---- strip chart: one bar per verse ----
    const METRICS = {
      coverage: { label: "Words aligned", fmt: v => NAV.pct(v), sub: "Share of the verse's words (both languages) that have at least one link." },
      reordering: { label: "Word-order change", fmt: v => NAV.pct(v), sub: "Share of link pairs that cross: 0% = same word order in both languages." },
      link_confidence: { label: "Link confidence", fmt: v => NAV.dec(v), sub: "Mean confidence of the verse's alignment links (mcaligner)." },
      parse_confidence: { label: "Parse confidence", fmt: v => NAV.dec(v), sub: "Mean of each word's lowest annotation confidence (mcparser)." },
    };
    let metric = "coverage";
    const strip = d3.select("#strip");

    function drawStrip() {
      strip.selectAll("*").remove();
      const width = strip.node().getBoundingClientRect().width || 900;
      const height = 190, m = { t: 22, r: 8, b: 8, l: 40 };
      const svg = strip.append("svg").attr("width", width).attr("height", height);
      const x = d3.scaleBand().domain(verses.map(v => v.i)).range([m.l, width - m.r]).paddingInner(verses.length > 150 ? 0 : 0.15);
      const y = d3.scaleLinear().domain([0, 1]).range([height - m.b, m.t]);
      const fmt = METRICS[metric].fmt;

      [0, 0.5, 1].forEach(t => {
        svg.append("line").attr("class", "gridline").attr("x1", m.l).attr("x2", width - m.r).attr("y1", y(t)).attr("y2", y(t));
        svg.append("text").attr("x", m.l - 6).attr("y", y(t) + 4).attr("text-anchor", "end").attr("font-size", 11).attr("fill", "#52514e")
          .text(metric.includes("confidence") ? t.toFixed(1) : `${t * 100}%`);
      });

      // Book boundaries; a book is labelled only if its label fits before the next one
      const runs = [];
      verses.forEach(v => {
        const book = v.label.includes(":") ? v.label.replace(/\s+\d+:\d+.*$/, "") : null;
        if (book && (!runs.length || runs[runs.length - 1].book !== book)) runs.push({ book, x: x(v.i) });
      });
      runs.forEach((run, k) => {
        const next = k + 1 < runs.length ? runs[k + 1].x : width - m.r;
        if (k > 0) svg.append("line").attr("x1", run.x).attr("x2", run.x).attr("y1", m.t - 14).attr("y2", height - m.b).attr("stroke", "#c5c7d0").attr("stroke-dasharray", "2 3");
        if (next - run.x > run.book.length * 6.5 + 6) {
          svg.append("text").attr("x", run.x + 3).attr("y", m.t - 6).attr("font-size", 11).attr("fill", "#52514e").text(run.book);
        }
      });

      const bw = x.bandwidth();
      svg.append("g").selectAll("rect").data(verses).enter().append("rect")
        .attr("x", v => x(v.i)).attr("width", Math.max(1, bw))
        .attr("y", v => (v[metric] === null ? y(0) - 2 : y(v[metric])))
        .attr("height", v => (v[metric] === null ? 2 : Math.max(1, y(0) - y(v[metric]))))
        .attr("rx", bw >= 8 ? 3 : 0)
        .attr("fill", v => (v[metric] === null ? "#d8dbe3" : "var(--series-1)"));

      // Hit areas: the full column, wider than the bar
      svg.append("g").selectAll("rect").data(verses).enter().append("rect")
        .attr("x", v => x(v.i)).attr("width", Math.max(2, x.step())).attr("y", m.t).attr("height", height - m.t - m.b)
        .attr("fill", "transparent").style("cursor", "pointer")
        .on("mousemove", (event, v) => NAV.showTip(event, `<b>${NAV.esc(v.label)}</b><br>${METRICS[metric].label}: ${fmt(v[metric])}<br>${v.links} links · ${v.words_a}/${v.words_b} words`))
        .on("mouseleave", NAV.hideTip)
        .on("click", (event, v) => { window.location.href = `${v.id}/`; });
      document.getElementById("strip-sub").textContent = `${METRICS[metric].sub} Each bar is a verse, in manuscript order. Click one to read it.`;
    }
    document.querySelectorAll("#strip-metric button").forEach(btn => btn.addEventListener("click", () => {
      metric = btn.dataset.metric;
      document.querySelectorAll("#strip-metric button").forEach(b => b.classList.toggle("active", b === btn));
      drawStrip();
    }));
    drawStrip();
    let t;
    window.addEventListener("resize", () => { clearTimeout(t); t = setTimeout(drawStrip, 150); });

    // ---- shapes ----
    const shapes = data.summary.shapes;
    const totalGroups = Object.values(shapes).reduce((a, b) => a + b, 0) || 1;
    const names = { "1:1": "one to one", "1:n": `one ${L.a.label} to several ${L.b.label}`, "n:1": `several ${L.a.label} to one ${L.b.label}`, "n:m": "several to several" };
    document.getElementById("shapes").innerHTML = Object.entries(shapes).map(([shape, n]) => `
      <div class="hbar-row" style="cursor:default" title="${names[shape]}">
        <span><b>${shape}</b></span>
        <span class="hbar-track"><span class="hbar-fill" style="display:block; width:${(100 * n / totalGroups).toFixed(1)}%"></span></span>
        <span class="val">${NAV.num(n)} · ${NAV.pct(n / totalGroups)}</span>
      </div>`).join("") + `<div class="muted small mt-2">${Object.entries(names).map(([k, v]) => `<b>${k}</b> ${v}`).join(" · ")}</div>`;

    // ---- verse table ----
    const tbody = document.querySelector("#verse-table tbody");
    const filter = document.getElementById("verse-filter");
    const fmtNull = (v, f) => (v === null || v === undefined ? '<span class="muted">–</span>' : f(v));
    const render = rows => {
      const q = filter.value.trim().toLowerCase();
      const shown = q ? rows.filter(v => v.label.toLowerCase().includes(q) || v.id.toLowerCase().includes(q)) : rows;
      document.getElementById("verse-count").textContent = `${shown.length} of ${rows.length} verses`;
      tbody.innerHTML = shown.map(v => `<tr style="cursor:pointer" data-href="${v.id}/">
        <td class="muted">${v.i + 1}</td>
        <td><a href="${v.id}/">${NAV.esc(v.label)}</a></td>
        <td class="num">${v.words_a}</td><td class="num">${v.words_b}</td>
        <td class="num">${v.links}${v.probable ? ` <span class="muted">(${v.probable}P)</span>` : ""}</td>
        <td><span class="meter"><span style="width:${(v.coverage * 100).toFixed(0)}%"></span></span>${NAV.pct(v.coverage)}</td>
        <td class="num">${fmtNull(v.reordering, x => NAV.pct(x))}</td>
        <td class="num">${fmtNull(v.link_confidence, x => NAV.dec(x))}</td>
        <td class="num">${fmtNull(v.parse_confidence, x => NAV.dec(x))}</td>
        <td class="num">${v.low_confidence_words || '<span class="muted">0</span>'}</td>
      </tr>`).join("");
    };
    const rows = verses.slice();
    const table = NAV.sortable(document.getElementById("verse-table"), rows, render, { key: "i", dir: 1, type: "num" });
    filter.addEventListener("input", () => render(rows));
    tbody.addEventListener("click", e => {
      const tr = e.target.closest("tr[data-href]");
      if (tr && e.target.tagName !== "A") window.location.href = tr.dataset.href;
    });
  }

  // ================================================================ lexicon
  function initLexicon() {
    let side = new URLSearchParams(location.search).get("side") === "b" ? "b" : "a";
    const search = document.getElementById("lex-search");
    const uposSel = document.getElementById("lex-upos");
    const tbody = document.querySelector("#lex-table tbody");
    const LIMIT = 800;
    let rows = [];
    let sorter;

    const fillUpos = () => {
      const counts = {};
      LEXICON[side].forEach(e => { counts[e.upos] = (counts[e.upos] || 0) + 1; });
      const current = uposSel.value;
      uposSel.innerHTML = '<option value="">All parts of speech</option>' +
        Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([u, n]) => `<option value="${u}">${u} (${n})</option>`).join("");
      if (counts[current]) uposSel.value = current;
    };

    const render = sorted => {
      const q = search.value.trim().toLowerCase();
      const upos = uposSel.value;
      const other = side === "a" ? L.b : L.a;
      const me = side === "a" ? L.a : L.b;
      const shown = sorted.filter(e => (!upos || e.upos === upos) &&
        (!q || e.lemma.toLowerCase().includes(q) || e.eq.some(([lemma]) => lemma.toLowerCase().includes(q))));
      document.getElementById("lex-count").textContent = `${NAV.num(shown.length)} lemmas`;
      document.getElementById("lex-more").textContent = shown.length > LIMIT ? `Showing the first ${LIMIT}. Search or filter to narrow down.` : "";
      tbody.innerHTML = shown.slice(0, LIMIT).map(e => {
        const lemmaCell = NAV.linkableLemma(e.lemma) ? `<a class="text-serif" style="font-size:1.1rem" href="${NAV.lemmaUrl(me.id, e.lemma)}">${NAV.esc(e.lemma)}</a>` : `<span class="text-serif">${NAV.esc(e.lemma)}</span>`;
        const eq = e.eq.map(([lemma, n, parts]) => parts
          // Several linked words: one chip, each lemma linked on its own ("…" marks a gap between them)
          ? `<span class="chip chip-multi">${parts.map(p => p !== "…" && NAV.linkableLemma(p)
              ? `<a href="${NAV.lemmaUrl(other.id, p)}">${NAV.esc(p)}</a>` : `<span class="muted">${NAV.esc(p)}</span>`).join(" ")}<span class="n">${n}</span></span>`
          : NAV.linkableLemma(lemma)
          ? `<a class="chip" href="${NAV.lemmaUrl(other.id, lemma)}">${NAV.esc(lemma)}<span class="n">${n}</span></a>`
          : `<span class="chip">${NAV.esc(lemma)}<span class="n">${n}</span></span>`).join("");
        return `<tr><td ${me.rtl ? 'dir="rtl"' : ""}>${lemmaCell}</td><td class="upos">${e.upos}</td>
          <td class="num">${NAV.num(e.count)}</td><td class="num">${NAV.num(e.verses)}</td>
          <td>${e.in_aligned ? `<span class="meter"><span style="width:${(e.share * 100).toFixed(0)}%"></span></span>${NAV.pct(e.share)}` : '<span class="muted">–</span>'}</td>
          <td class="num">${e.eq_total}</td><td ${other.rtl ? 'dir="rtl"' : ""}>${eq || '<span class="muted">none</span>'}</td></tr>`;
      }).join("");
    };

    const load = () => {
      rows = LEXICON[side].map(e => ({ ...e, share: e.in_aligned ? e.aligned / e.in_aligned : null }));
      fillUpos();
      document.querySelectorAll("#lex-side button").forEach(b => b.classList.toggle("active", b.dataset.side === side));
      sorter = NAV.sortable(document.getElementById("lex-table"), rows, render, { key: "count", dir: -1, type: "num" });
    };
    document.querySelectorAll("#lex-side button").forEach(btn => btn.addEventListener("click", () => {
      side = btn.dataset.side;
      history.replaceState(null, "", side === "b" ? "?side=b" : "?");
      load();
    }));
    search.addEventListener("input", () => render(rows));
    uposSel.addEventListener("change", () => render(rows));
    load();
  }

  // ================================================================ insights
  function initInsights() {
    const matrices = INSIGHTS.matrices;
    let current = matrices[0];
    let norm = "row";
    const examplesEl = document.getElementById("examples");
    const tabs = document.getElementById("matrix-tabs");
    tabs.innerHTML = matrices.map((m, i) => `<button data-i="${i}" class="${i === 0 ? "active" : ""}">${NAV.esc(m.title)}</button>`).join("");

    function showExamples(title, sub, examples) {
      document.getElementById("examples-title").textContent = title;
      document.getElementById("examples-sub").textContent = sub;
      examplesEl.innerHTML = examples.length
        ? examples.map(([v, a, b]) => NAV.exampleHtml(CORPUS[v], a === null ? [] : [a], b === null || b === undefined ? [] : [b])).join("")
        : '<div class="muted">No examples.</div>';
    }

    function drawMatrix() {
      const m = current;
      document.getElementById("matrix-title").textContent = `${m.title}: ${L.a.label} → ${L.b.label}`;
      document.getElementById("matrix-desc").textContent = `${m.description} · ${NAV.num(m.total)} aligned word pairs`;
      const counts = {};
      const rowTot = {}, colTot = {};
      m.cells.forEach(c => {
        counts[`${c.a}\u0000${c.b}`] = c;
        rowTot[c.a] = (rowTot[c.a] || 0) + c.n;
        colTot[c.b] = (colTot[c.b] || 0) + c.n;
      });
      const head = `<tr><th></th><th colspan="${m.cols.length}" class="col-head axis-label">${NAV.esc(L.b.label)}</th></tr>
        <tr><th class="row-head axis-label">${NAV.esc(L.a.label)}</th>${m.cols.map(c => `<th class="col-head">${NAV.esc(c)}<br><span class="total">${NAV.num(colTot[c])}</span></th>`).join("")}</tr>`;
      const body = m.rows.map(r => `<tr><th class="row-head">${NAV.esc(r)} <span class="total">${NAV.num(rowTot[r])}</span></th>${m.cols.map(c => {
        const cell = counts[`${r}\u0000${c}`];
        if (!cell) return '<td class="cell empty">0</td>';
        const share = norm === "row" ? cell.n / rowTot[r] : cell.n / colTot[c];
        return `<td class="cell" data-a="${NAV.esc(r)}" data-b="${NAV.esc(c)}" style="background:${NAV.rampColor(share)}; color:${NAV.inkOn(share)}">${NAV.num(cell.n)}</td>`;
      }).join("")}</tr>`).join("");
      const table = document.getElementById("heatmap");
      table.innerHTML = `<thead>${head}</thead><tbody>${body}</tbody>`;
      document.querySelector(".legend-ramp span:last-child").textContent = norm === "row" ? `100% of ${L.a.label} row` : `100% of ${L.b.label} column`;

      table.querySelectorAll("td.cell:not(.empty)").forEach(td => {
        const cell = counts[`${td.dataset.a}\u0000${td.dataset.b}`];
        td.addEventListener("mousemove", e => NAV.showTip(e,
          `<b>${NAV.esc(L.a.label)} ${NAV.esc(cell.a)} → ${NAV.esc(L.b.label)} ${NAV.esc(cell.b)}</b><br>${NAV.num(cell.n)} pair${cell.n === 1 ? "" : "s"}<br>` +
          `${NAV.pct(cell.n / rowTot[cell.a], 1)} of ${NAV.esc(L.a.label)} ${NAV.esc(cell.a)}<br>${NAV.pct(cell.n / colTot[cell.b], 1)} of ${NAV.esc(L.b.label)} ${NAV.esc(cell.b)}`));
        td.addEventListener("mouseleave", NAV.hideTip);
        td.addEventListener("click", () => {
          table.querySelectorAll(".selected").forEach(x => x.classList.remove("selected"));
          td.classList.add("selected");
          showExamples(`${cell.a} → ${cell.b}`, `${m.title}: ${NAV.num(cell.n)} pair${cell.n === 1 ? "" : "s"}, showing ${cell.ex.length < cell.n ? `${cell.ex.length} examples` : "all"}`, cell.ex);
        });
      });
    }

    tabs.querySelectorAll("button").forEach(btn => btn.addEventListener("click", () => {
      current = matrices[+btn.dataset.i];
      tabs.querySelectorAll("button").forEach(b => b.classList.toggle("active", b === btn));
      drawMatrix();
    }));
    document.querySelectorAll("#matrix-norm button").forEach(btn => btn.addEventListener("click", () => {
      norm = btn.dataset.norm;
      document.querySelectorAll("#matrix-norm button").forEach(b => b.classList.toggle("active", b === btn));
      drawMatrix();
    }));
    drawMatrix();

    // ---- unaligned words by part of speech ----
    ["a", "b"].forEach(side => {
      const rows = INSIGHTS.unaligned[side].filter(r => r.total >= 3);
      const el = document.getElementById(`unaligned-${side}`);
      if (!rows.length) { el.innerHTML = '<div class="muted">No aligned verses yet.</div>'; return; }
      el.innerHTML = rows.map((r, i) => `<div class="hbar-row" data-i="${i}">
          <span class="upos" style="font-size:.82rem">${r.upos}</span>
          <span class="hbar-track"><span class="hbar-fill" style="display:block; width:${(r.share * 100).toFixed(1)}%"></span></span>
          <span class="val">${NAV.pct(r.share)} <span class="muted">${r.unaligned}/${r.total}</span></span>
        </div>`).join("");
      el.querySelectorAll(".hbar-row").forEach(row => {
        const r = rows[+row.dataset.i];
        row.addEventListener("click", () => {
          const lang = side === "a" ? L.a.label : L.b.label;
          showExamples(`Unaligned ${lang} ${r.upos}`, `${r.unaligned} of ${r.total} words, showing up to ${r.ex.length}`,
            r.ex.map(([v, id]) => (side === "a" ? [v, id, null] : [v, null, id])));
          document.getElementById("examples-title").scrollIntoView({ behavior: "smooth", block: "nearest" });
        });
      });
    });
  }

  // ================================================================ review
  function initReview() {
    const label = v => CORPUS[v].label;
    const links = REVIEW.links.map(l => ({ ...l, label: label(l.v), verse_id: CORPUS[l.v].id }));
    const words = REVIEW.words.map(w => ({ ...w, label: label(w.v), verse_id: CORPUS[w.v].id }));
    document.getElementById("review-links-sub").textContent =
      `${NAV.num(REVIEW.links_total)} links with a confidence or marked probable${REVIEW.links_total > links.length ? `, the ${links.length} least confident shown` : ""}. Probable links first, then by confidence.`;
    document.getElementById("review-words-sub").textContent =
      `${NAV.num(REVIEW.words_total)} words below 0.8${REVIEW.words_total > words.length ? `, the ${words.length} least confident shown` : ""}.`;

    let linkFilter = "all";
    const linkBody = document.querySelector("#review-links tbody");
    const renderLinks = rows => {
      linkBody.innerHTML = rows.filter(l => linkFilter === "all" || !l.sure).map(l => `<tr>
        <td><a href="${NAV.verseUrl(l.verse_id)}">${NAV.esc(l.label)}</a></td>
        <td class="text-serif" style="font-size:1.05rem">${NAV.esc(l.a_form)}</td>
        <td class="text-serif" style="font-size:1.05rem">${NAV.esc(l.b_form)}</td>
        <td>${l.sure ? "sure" : '<span style="color:var(--link-probable-edge)">probable</span>'}</td>
        <td class="num">${NAV.dec(l.confidence)}</td><td class="muted">${NAV.esc(l.agent || "")}</td></tr>`).join("");
    };
    const linkSorter = NAV.sortable(document.getElementById("review-links"), links, renderLinks);
    document.querySelectorAll("#review-link-filter button").forEach(btn => btn.addEventListener("click", () => {
      linkFilter = btn.dataset.filter;
      document.querySelectorAll("#review-link-filter button").forEach(b => b.classList.toggle("active", b === btn));
      renderLinks(links);
    }));

    let wordSide = "";
    const wordBody = document.querySelector("#review-words tbody");
    const renderWords = rows => {
      wordBody.innerHTML = rows.filter(w => !wordSide || w.side === wordSide).map(w => `<tr>
        <td><a href="${NAV.verseUrl(w.verse_id)}">${NAV.esc(w.label)}</a></td>
        <td class="text-serif" style="font-size:1.05rem">${NAV.esc(w.form)} <span class="muted small">${w.side === "a" ? L.a.label : L.b.label}</span></td>
        <td class="text-serif">${NAV.esc(w.lemma)}</td><td class="upos">${NAV.esc(w.upos)}</td>
        <td class="muted">${NAV.esc(w.deprel)}</td><td class="num">${NAV.dec(w.confidence)}</td></tr>`).join("");
    };
    NAV.sortable(document.getElementById("review-words"), words, renderWords);
    document.querySelectorAll("#review-word-side button").forEach(btn => btn.addEventListener("click", () => {
      wordSide = btn.dataset.side;
      document.querySelectorAll("#review-word-side button").forEach(b => b.classList.toggle("active", b === btn));
      renderWords(words);
    }));
  }

  const init = { overview: initOverview, lexicon: initLexicon, insights: initInsights, review: initReview }[page];
  if (init) init();
})();
