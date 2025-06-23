import { sentences, wordMap } from './data.js';

const tokenY = 150;
const arcHeight = 40;

function arcPath(x1, x2, y = tokenY - 30) {
  const radius = Math.abs(x2 - x1) / 2;
  return `M${x1},${y} A${radius},${arcHeight} 0 0,${x1 < x2 ? 1 : 0} ${x2},${y}`;
}

function renderSentence(sentence) {
  const svg = d3.select(`#${sentence.svgId}`);
  const tokens = sentence.data.split("\n").map(line => {
    const [id, form, , upos, , feats, head, deprel] = line.split("\t");
    return { id: +id, form, upos, feats, head: +head, deprel };
  });

  const idToIndex = Object.fromEntries(tokens.map((t, i) => [t.id, i]));
  const ctx = document.createElement("canvas").getContext("2d");
  ctx.font = "24px Gentium Plus";
  tokens.forEach(t => t.width = ctx.measureText(t.form).width);
  const spacing = 20;
  let currentX = 50;
  const positions = tokens.map(t => {
    const x = currentX + t.width / 2;
    currentX += t.width + spacing;
    return x;
  });

  const defs = svg.append("defs");
  defs.selectAll("marker")
    .data([
      { id: "arrowhead", color: "#ddd" },
      { id: "arrowhead-red", color: "red" },
      { id: "arrowhead-blue", color: "blue" }
    ])
    .enter().append("marker")
      .attr("id", d => d.id)
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 8)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
    .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", d => d.color);

  svg.selectAll(".arc")
    .data(tokens.filter(t => t.head !== 0))
    .enter().append("path")
      .attr("class", "arc")
      .attr("d", d => arcPath(positions[idToIndex[d.id]], positions[idToIndex[d.head]]));

  const groups = svg.selectAll(".token")
    .data(tokens).enter()
    .append("g")
      .attr("transform", (d, i) => `translate(${positions[i]},${tokenY})`)
      .attr("data-id", d => `${sentence.svgId}-${d.id}`)
      .on("mouseover", (event, d) => highlight(event, d, sentence, positions, idToIndex))
      .on("mouseout", clearHighlight);

  groups.append("text")
    .attr("text-anchor", "middle")
    .attr("class", d => `token${d.head === 0 ? " root" : ""}`)
    .text(d => d.form);
}

function highlight(event, d, sentence, positions, idToIndex) {
  clearHighlight();
  const svg = d3.select(`#${sentence.svgId}`);
  highlightWord(svg, sentence.data, d, positions, idToIndex, sentence.svgId);

  const pairId = wordMap[`${sentence.svgId}-${d.id}`];
  if (pairId) {
    const [pairSvgId, pairTokenId] = pairId.split("-");
    const pairSentence = sentences.find(s => s.svgId === pairSvgId);
    const pairTokens = pairSentence.data.split("\n").map(line => {
      const [id, form, , upos, , feats, head, deprel] = line.split("\t");
      return { id: +id, form, upos, feats, head: +head, deprel };
    });
    const pairIdToIndex = Object.fromEntries(pairTokens.map((t, i) => [t.id, i]));
    const ctx = document.createElement("canvas").getContext("2d");
    ctx.font = "24px Gentium Plus";
    pairTokens.forEach(t => t.width = ctx.measureText(t.form).width);
    let cx = 50;
    const pairPositions = pairTokens.map(t => {
      const x = cx + t.width / 2;
      cx += t.width + 20;
      return x;
    });
    const pairSvg = d3.select(`#${pairSvgId}`);
    const pairD = pairTokens.find(t => t.id === +pairTokenId);
    highlightWord(pairSvg, pairSentence.data, pairD, pairPositions, pairIdToIndex, pairSvgId);
  }
}

function highlightWord(svg, dataStr, d, positions, idToIndex, svgId) {
  const tokens = dataStr.split("\n").map(line => {
    const [id, form, , upos, , feats, head, deprel] = line.split("\t");
    return { id: +id, form, upos, feats, head: +head, deprel };
  });
  const idx = idToIndex[d.id];
  const x = positions[idx];
  const y = tokenY - 18;
  const group = d3.select(`[data-id="${svgId}-${d.id}"]`);
  const text = group.select("text");
  const bbox = text.node().getBBox();
  group.insert("rect", "text")
    .attr("class", "token-bg")
    .attr("x", bbox.x - 4)
    .attr("y", bbox.y - 2)
    .attr("width", bbox.width + 8)
    .attr("height", bbox.height + 4);

  if (d.head !== 0) {
    const headIdx = idToIndex[d.head];
    svg.append("path")
      .attr("class", "arc arc-highlight-out")
      .attr("d", arcPath(positions[idx], positions[headIdx]))
    svg.append("text")
      .attr("class", "arc-label")
      .attr("x", (positions[idx] + positions[headIdx]) / 2)
      .attr("y", y - arcHeight - 5)
      .text(d.deprel);
  }

  tokens.forEach((t, i) => {
    if (t.head === d.id) {
      svg.append("path")
        .attr("class", "arc arc-highlight-in")
        .attr("d", arcPath(positions[i], positions[idx]));
    }
  });

  const featLines = (d.feats && d.feats !== "_") ? d.feats.split("|") : [];
  const lines = [d.upos, ...featLines];
  lines.forEach((line, i) => {
    svg.append("text")
      .attr("class", "features")
      .attr("x", x)
      .attr("y", tokenY + 20 + i * 14)
      .text(line);
  });
}

function clearHighlight() {
  d3.selectAll(".token-bg").remove();
  d3.selectAll(".arc-highlight-in").remove();
  d3.selectAll(".arc-highlight-out").remove();
  d3.selectAll(".arc-label").remove();
  d3.selectAll(".features").remove();
}

sentences.forEach(renderSentence);
