// Bilingual Navigator: verse page (dependency trees, interlinear view, alignment matrix).
// Expects the globals defined by <dataset>-<verse>.js: wordMap, siglum, sentences.

const TOKEN_FONT = '24px "Gentium Plus"';
const TOP = 130;           // baseline of the first row (room for arcs above it)
const ROW_GAP = 175;       // distance between row baselines
const SPACING = 22;        // horizontal gap between words
const MARGIN = 30;

const measureCtx = document.createElement("canvas").getContext("2d");
function textWidth(text) {
  measureCtx.font = TOKEN_FONT;
  return measureCtx.measureText(text).width;
}

// Words in CoNLL-U order; head is null when the parser left it as "_".
function parseTokens(data) {
  return data.split("\n").filter(line => line.trim()).map(line => {
    const [id, form, lemma, upos, , feats, head, deprel] = line.split("\t");
    const headNum = Number.parseInt(head, 10);
    return { id: +id, form, lemma, upos, feats, head: Number.isFinite(headNum) ? headNum : null, deprel };
  });
}

function arcHeightForDistance(distance, minHeight = 30, maxHeight = 85) {
  const raw = maxHeight - (maxHeight - minHeight) * Math.exp(-(distance - 1) / 5);
  return Math.max(minHeight, Math.min(maxHeight, raw));
}

function arcPath(x1, x2, height, y) {
  const radius = Math.abs(x2 - x1) / 2;
  const sweep = x1 < x2 ? 1 : 0;
  return `M${x1},${y} A${radius},${height} 0 0,${sweep} ${x2},${y}`;
}

function adjustArabicTaMarbuta(str) {
  return str.length > 1 && str.endsWith("ة") ? str.slice(0, -1) + "ت" : str;
}

// ---------------------------------------------------------------- layout
// Words joined without a space (multiword tokens) form one group; groups wrap onto as many rows as needed.
function computeLayout(sentence, svgWidth) {
  const tokens = parseTokens(sentence.data);
  const noSpace = new Set(sentence.noSpaceAfter || []);
  const groups = [];
  for (let i = 0; i < tokens.length;) {
    let end = i;
    let text = tokens[i].form;
    while (end < tokens.length - 1 && noSpace.has(tokens[end].id)) {
      end += 1;
      text = adjustArabicTaMarbuta(text) + tokens[end].form;
    }
    groups.push({ start: i, end, text, width: textWidth(text) });
    i = end + 1;
  }

  const available = Math.max(300, svgWidth - 2 * MARGIN);
  const rowsOfGroups = [[]];
  let used = 0;
  groups.forEach(g => {
    const row = rowsOfGroups[rowsOfGroups.length - 1];
    const needed = (row.length ? SPACING : 0) + g.width;
    if (row.length && used + needed > available) {
      rowsOfGroups.push([g]);
      used = g.width;
    } else {
      row.push(g);
      used += needed;
    }
  });

  const n = tokens.length;
  const rows = new Array(n).fill(0);
  const positions = new Array(n).fill(0);
  const bounds = new Array(n).fill(null);
  const display = new Array(n).fill(null);
  const rowYs = rowsOfGroups.map((_, r) => TOP + r * ROW_GAP);

  rowsOfGroups.forEach((rowGroups, r) => {
    const total = rowGroups.reduce((sum, g, i) => sum + g.width + (i ? SPACING : 0), 0);
    const start = Math.max(MARGIN, (svgWidth - total) / 2);
    let cursor = sentence.rtl ? start + total : start;
    rowGroups.forEach(g => {
      const left = sentence.rtl ? cursor - g.width : cursor;
      const right = left + g.width;
      cursor = sentence.rtl ? left - SPACING : right + SPACING;
      // Split the group's width between its words in proportion to their own widths.
      const idx = [];
      for (let k = g.start; k <= g.end; k += 1) idx.push(k);
      const weights = idx.map(k => textWidth(tokens[k].form) || 1);
      const sum = weights.reduce((a, b) => a + b, 0);
      let segCursor = sentence.rtl ? right : left;
      idx.forEach((k, j) => {
        const w = g.width * (weights[j] / sum);
        const segLeft = sentence.rtl ? segCursor - w : segCursor;
        const segRight = segLeft + w;
        segCursor = sentence.rtl ? segLeft : segRight;
        rows[k] = r;
        positions[k] = (segLeft + segRight) / 2;
        bounds[k] = { left: segLeft, right: segRight };
        display[k] = { x: (left + right) / 2, text: j === 0 ? g.text : "", visible: j === 0 };
      });
    });
  });

  const idToIndex = Object.fromEntries(tokens.map((t, i) => [t.id, i]));
  const height = rowYs[rowYs.length - 1] + 150;
  return { tokens, idToIndex, rows, rowYs, positions, bounds, display, height };
}

// A dependency edge from token index i to its head index h.
function edgePath(L, i, h) {
  const ri = L.rows[i], rh = L.rows[h];
  if (ri === rh) {
    const height = arcHeightForDistance(Math.abs(i - h));
    return { d: arcPath(L.positions[i], L.positions[h], height, L.rowYs[ri] - 30), height, sameRow: true };
  }
  // Across rows: a straight line from the lower word's top to the upper word's bottom.
  const yi = ri > rh ? L.rowYs[ri] - 24 : L.rowYs[ri] + 8;
  const yh = rh > ri ? L.rowYs[rh] - 24 : L.rowYs[rh] + 8;
  return { d: `M${L.positions[i]},${yi} L${L.positions[h]},${yh}`, sameRow: false };
}

const layouts = {};

// ---------------------------------------------------------------- trees
function renderSentence(sentence) {
  const svg = d3.select(`#${sentence.svgId}`);
  svg.selectAll("*").remove();
  const svgWidth = svg.node()?.getBoundingClientRect().width || 1200;
  const L = computeLayout(sentence, svgWidth);
  layouts[sentence.svgId] = L;
  svg.attr("height", L.height);
  if (sentence.rtl) svg.attr("direction", "rtl");

  const defs = svg.append("defs");
  [["arrowhead", "#d8dbe3"], ["arrowhead-red", "#d03b3b"], ["arrowhead-blue", "#1c3fae"]].forEach(([id, color]) => {
    defs.append("marker").attr("id", `${sentence.svgId}-${id}`).attr("viewBox", "0 -5 10 10")
      .attr("refX", 8).attr("refY", 0).attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto")
      .append("path").attr("d", "M0,-5L10,0L0,5").attr("fill", color);
  });

  L.tokens.forEach((t, i) => {
    if (!t.head || L.idToIndex[t.head] === undefined) return;
    const e = edgePath(L, i, L.idToIndex[t.head]);
    svg.append("path").attr("class", e.sameRow ? "arc" : "arc cross").attr("d", e.d)
      .attr("marker-end", e.sameRow ? `url(#${sentence.svgId}-arrowhead)` : null);
  });

  const lowConf = new Set(sentence.lowConf || []);
  const groups = svg.selectAll(".token-g").data(L.tokens).enter().append("g")
    .attr("class", "token-g")
    .attr("transform", (d, i) => `translate(${L.display[i].x},${L.rowYs[L.rows[i]]})`)
    .attr("data-id", d => `${sentence.svgId}-${d.id}`);
  groups.append("text")
    .attr("text-anchor", "middle")
    .attr("class", d => `token${d.head === 0 ? " root" : ""}${lowConf.has(d.id) ? " low-conf" : ""}`)
    .attr("direction", sentence.rtl ? "rtl" : "ltr")
    .style("opacity", (d, i) => (L.display[i].visible ? 1 : 0))
    .style("pointer-events", "none")
    .text((d, i) => L.display[i].text);

  svg.selectAll(".token-hit").data(L.tokens).enter().append("rect")
    .attr("class", "token-hit")
    .attr("x", (d, i) => L.bounds[i].left - 2)
    .attr("y", (d, i) => L.rowYs[L.rows[i]] - 22)
    .attr("width", (d, i) => L.bounds[i].right - L.bounds[i].left + 4)
    .attr("height", 28)
    .attr("fill", "transparent")
    .style("cursor", "pointer")
    .on("mouseover", (event, d) => highlight(sentence, d))
    .on("mouseout", clearHighlight)
    .on("click", (event, d) => navigateToLemma(sentence, d));
}

function highlight(sentence, d) {
  clearHighlight();
  highlightWord(sentence, d, "token-bg", null, true);
  (wordMap[`${sentence.svgId}-${d.id}`] || []).forEach(partner => {
    const other = sentences.find(s => s.svgId === partner.svgId);
    const L = layouts[partner.svgId];
    if (!other || !L) return;
    const pd = L.tokens.find(t => t.id === +partner.id);
    if (pd) highlightWord(other, pd, partner.sure === false ? "token-bg-probable" : "token-bg", partner.confidence, true);
  });
}

function highlightWord(sentence, d, bgClass, confidence, details) {
  const L = layouts[sentence.svgId];
  const svg = d3.select(`#${sentence.svgId}`);
  const idx = L.idToIndex[d.id];
  const row = L.rows[idx];
  const rowY = L.rowYs[row];
  const b = L.bounds[idx];
  const group = svg.select(`[data-id="${sentence.svgId}-${d.id}"]`);
  const bg = group.insert("rect", "text").attr("class", bgClass)
    .attr("x", b.left - L.display[idx].x - 4).attr("y", -22)
    .attr("width", b.right - b.left + 8).attr("height", 28).attr("rx", 4);
  if (confidence !== null && confidence !== undefined) {
    bg.append("title").text(`alignment confidence ${Number(confidence).toFixed(2)}`);
  }
  if (!details) return;

  const sid = sentence.svgId;
  if (d.head && L.idToIndex[d.head] !== undefined) {
    const h = L.idToIndex[d.head];
    const e = edgePath(L, idx, h);
    svg.append("path").attr("class", "arc arc-highlight-out").attr("d", e.d).attr("marker-end", `url(#${sid}-arrowhead-blue)`);
    const labelY = e.sameRow ? rowY - 30 - e.height - 8 : (rowY + L.rowYs[L.rows[h]]) / 2;
    svg.append("text").attr("class", "arc-label").attr("x", (L.positions[idx] + L.positions[h]) / 2).attr("y", labelY).text(d.deprel);
  }
  L.tokens.forEach((t, i) => {
    if (t.head === d.id) {
      svg.append("path").attr("class", "arc arc-highlight-in").attr("d", edgePath(L, i, idx).d)
        .attr("marker-end", `url(#${sid}-arrowhead-red)`);
    }
  });

  const featLines = d.feats && d.feats !== "_" ? d.feats.split("|") : [];
  const lines = [[d.lemma && d.lemma !== "_" ? d.lemma : null, "lemma-line"], [d.upos, ""], ...featLines.map(f => [f, ""])]
    .filter(([text]) => text);
  lines.forEach(([text, cls], i) => {
    svg.append("text").attr("class", `features ${cls}`).attr("x", L.positions[idx]).attr("y", rowY + 22 + i * 14).text(text);
  });
}

function clearHighlight() {
  d3.selectAll(".token-bg, .token-bg-probable, .arc-highlight-in, .arc-highlight-out, .arc-label, .features").remove();
}

function lemmaUrl(languageSlug, lemma) {
  return `../${languageSlug}/${encodeURIComponent(lemma)}/`;
}

function navigateToLemma(sentence, d) {
  const lemma = sentence.lemmaMap && sentence.lemmaMap[d.id];
  if (lemma) window.location.href = lemmaUrl(sentence.languageSlug, lemma);
}

function renderTrees() {
  sentences.forEach(renderSentence);
}

// ---------------------------------------------------------------- interlinear
function renderInterlinear(sideIndex) {
  const main = sentences[sideIndex];
  const other = sentences[1 - sideIndex];
  const otherTokens = Object.fromEntries(parseTokens(other.data).map(t => [t.id, t]));
  const container = document.getElementById("interlinear");
  container.setAttribute("dir", main.rtl ? "rtl" : "ltr");
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const linkedOther = new Set();
  container.innerHTML = parseTokens(main.data).map(t => {
    const partners = (wordMap[`${main.svgId}-${t.id}`] || []).slice().sort((a, b) => a.id - b.id);
    partners.forEach(p => linkedOther.add(p.id));
    const partnerHtml = partners.length
      ? partners.map(p => {
          const pt = otherTokens[p.id];
          const conf = p.confidence !== null && p.confidence !== undefined ? ` · confidence ${Number(p.confidence).toFixed(2)}` : "";
          return `<span class="${p.sure === false ? "probable" : ""}" title="${esc(pt?.lemma)} (${esc(pt?.upos)})${p.sure === false ? " · probable" : ""}${conf}">${esc(pt?.form)}</span>`;
        }).join(" ")
      : '<span class="none">—</span>';
    const lemma = main.lemmaMap[t.id];
    return `<div class="il-word${partners.length ? "" : " unaligned"}" data-lemma="${esc(lemma || "")}" title="${esc(t.feats !== "_" ? t.feats : "")}">
      <div class="form">${esc(t.form)}</div>
      <div class="lemma">${esc(t.lemma !== "_" ? t.lemma : "")}</div>
      <div class="upos">${esc(t.upos)}</div>
      <div class="partners" ${other.rtl ? 'dir="rtl"' : ""}>${partnerHtml}</div>
    </div>`;
  }).join("");
  container.querySelectorAll(".il-word").forEach(el => el.addEventListener("click", () => {
    if (el.dataset.lemma) window.location.href = lemmaUrl(main.languageSlug, el.dataset.lemma);
  }));

  const leftover = Object.values(otherTokens).filter(t => !linkedOther.has(t.id) && t.upos !== "PUNCT");
  document.getElementById("interlinear-extra").innerHTML = leftover.length
    ? `Not aligned to any word above: <span class="text-serif" style="font-size:1.05rem">${leftover.map(t => esc(t.form)).join(" · ")}</span>`
    : "";
}

// ---------------------------------------------------------------- matrix
function renderMatrix() {
  const [A, B] = sentences;
  const ta = parseTokens(A.data), tb = parseTokens(B.data);
  const cell = 24;
  measureCtx.font = '15px "Gentium Plus"';
  const left = Math.min(220, 16 + Math.max(...ta.map(t => measureCtx.measureText(t.form).width)));
  const top = Math.min(220, 16 + Math.max(...tb.map(t => measureCtx.measureText(t.form).width)) * 0.75);
  const width = left + tb.length * cell + 20;
  const height = top + ta.length * cell + 20;
  const svg = d3.select("#matrix").attr("width", width).attr("height", height);
  svg.selectAll("*").remove();
  const ai = Object.fromEntries(ta.map((t, i) => [t.id, i]));
  const bi = Object.fromEntries(tb.map((t, i) => [t.id, i]));

  const grid = svg.append("g");
  ta.forEach((_, r) => tb.forEach((__, c) => {
    grid.append("rect").attr("class", "gridcell").attr("data-r", r).attr("data-c", c)
      .attr("x", left + c * cell).attr("y", top + r * cell).attr("width", cell).attr("height", cell);
  }));
  svg.append("line").attr("class", "diag").attr("x1", left).attr("y1", top)
    .attr("x2", left + tb.length * cell).attr("y2", top + ta.length * cell);

  svg.selectAll(".row-lbl").data(ta).enter().append("text").attr("class", "lbl row-lbl")
    .attr("x", left - 8).attr("y", (d, i) => top + i * cell + cell / 2 + 5).attr("text-anchor", "end").text(d => d.form);
  svg.selectAll(".col-lbl").data(tb).enter().append("text").attr("class", "lbl col-lbl")
    .attr("transform", (d, i) => `translate(${left + i * cell + cell / 2 + 4},${top - 8}) rotate(-50)`).text(d => d.form);

  const links = [];
  ta.forEach(t => (wordMap[`${A.svgId}-${t.id}`] || []).forEach(p => links.push({ a: t, b: tb[bi[p.id]], p })));
  svg.selectAll(".dot").data(links.filter(l => l.b)).enter().append("circle")
    .attr("class", l => `dot ${l.p.sure === false ? "probable" : "sure"}`)
    .attr("cx", l => left + bi[l.b.id] * cell + cell / 2)
    .attr("cy", l => top + ai[l.a.id] * cell + cell / 2)
    .attr("r", 7)
    .on("mouseover", (event, l) => {
      const r = ai[l.a.id], c = bi[l.b.id];
      svg.selectAll(".gridcell").classed("hover", function () { return +this.dataset.r === r || +this.dataset.c === c; });
      svg.selectAll(".row-lbl").classed("active", (d, i) => i === r);
      svg.selectAll(".col-lbl").classed("active", (d, i) => i === c);
      const conf = l.p.confidence !== null && l.p.confidence !== undefined ? `<br>confidence ${Number(l.p.confidence).toFixed(2)}` : "";
      NAV.showTip(event, `<b>${NAV.esc(l.a.form)}</b> → <b>${NAV.esc(l.b.form)}</b><br>${NAV.esc(l.a.lemma)} → ${NAV.esc(l.b.lemma)}<br>${l.p.sure === false ? "probable" : "sure"}${conf}`);
    })
    .on("mouseout", () => {
      svg.selectAll(".gridcell").classed("hover", false);
      svg.selectAll(".lbl").classed("active", false);
      NAV.hideTip();
    });
}

// ---------------------------------------------------------------- wiring
renderTrees();
renderInterlinear(0);
renderMatrix();

let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(renderTrees, 150);
});
// Trees measure their width, so re-render when their tab is shown again.
document.querySelector('[data-bs-target="#tab-trees"]')?.addEventListener("shown.bs.tab", renderTrees);

document.querySelectorAll("#il-direction button").forEach(btn => btn.addEventListener("click", () => {
  document.querySelectorAll("#il-direction button").forEach(b => b.classList.toggle("active", b === btn));
  renderInterlinear(+btn.dataset.side);
}));

document.addEventListener("keydown", e => {
  if (/input|textarea|select/i.test(document.activeElement.tagName) || e.metaKey || e.ctrlKey || e.altKey) return;
  const go = id => { const a = document.getElementById(id); if (a && !a.classList.contains("disabled")) window.location.href = a.href; };
  if (e.key === "ArrowLeft") go("prev-verse");
  if (e.key === "ArrowRight") go("next-verse");
  const tabs = ["#tab-trees", "#tab-interlinear", "#tab-matrix"];
  if (["1", "2", "3"].includes(e.key)) {
    const btn = document.querySelector(`[data-bs-target="${tabs[+e.key - 1]}"]`);
    if (btn) bootstrap.Tab.getOrCreateInstance(btn).show();
  }
});
