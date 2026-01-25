// import { datasets } from './data.js';

// const selectedDataset = datasets.matt2_2a;
// const { sentences, wordMap } = selectedDataset;

const tokenY = 150;
const arcHeight = 40;
const spacing = 20;

function arcHeightForDistance(distance, minHeight = 30, maxHeight = 80) {
  const raw = maxHeight - (maxHeight - minHeight) * Math.exp(-(distance - 1)/5);
  return Math.max(minHeight, Math.min(maxHeight, raw));
}

function arcPath(x1, x2, height, y = tokenY - 30) {
  const radius = Math.abs(x2 - x1) / 2;
  return `M${x1},${y} A${radius},${height} 0 0,${x1 < x2 ? 1 : 0} ${x2},${y}`;
}

function computePositions(tokens, rtl, noSpaceAfter, svgWidth) {
  const ctx = document.createElement("canvas").getContext("2d");
  ctx.font = "24px Gentium Plus";
  tokens.forEach(t => t.width = ctx.measureText(t.form).width);
  const noSpaceAfterSet = new Set(noSpaceAfter || []);
  const totalWidth = tokens.reduce((sum, t, i) => {
    const gap = i < tokens.length - 1 && !noSpaceAfterSet.has(t.id) ? spacing : 0;
    return sum + t.width + gap;
  }, 0);
  const startX = Math.max(50, (svgWidth - totalWidth) / 2);
  if (rtl) {
    let rightEdge = startX + totalWidth;
    return tokens.map((t, i) => {
      const x = rightEdge - t.width / 2;
      const gap = i < tokens.length - 1 && !noSpaceAfterSet.has(t.id) ? spacing : 0;
      rightEdge -= t.width + gap;
      return x;
    });
  }
  let currentX = startX;
  return tokens.map((t, i) => {
    const x = currentX + t.width / 2;
    const gap = i < tokens.length - 1 && !noSpaceAfterSet.has(t.id) ? spacing : 0;
    currentX += t.width + gap;
    return x;
  });
}

function renderSentence(sentence) {
  const svg = d3.select(`#${sentence.svgId}`);
  if (sentence.rtl) {
    svg.attr("direction", "rtl")
      .attr("style", "direction: rtl; unicode-bidi: bidi-override;");
  }
  const tokens = sentence.data.split("\n").map(line => {
    const [id, form, , upos, , feats, head, deprel] = line.split("\t");
    return { id: +id, form, upos, feats, head: +head, deprel };
  });

  const idToIndex = Object.fromEntries(tokens.map((t, i) => [t.id, i]));
  const svgWidth = svg.node()?.getBoundingClientRect().width || 1800;
  const positions = computePositions(tokens, sentence.rtl, sentence.noSpaceAfter, svgWidth);

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
      .attr("marker-end", "url(#arrowhead)")
      .attr("d", d => {
        const distance = Math.abs(idToIndex[d.id] - idToIndex[d.head]);
        const height = arcHeightForDistance(distance);
        return arcPath(positions[idToIndex[d.id]], positions[idToIndex[d.head]], height);
      });

  const groups = svg.selectAll(".token")
    .data(tokens).enter()
    .append("g")
      .attr("transform", (d, i) => `translate(${positions[i]},${tokenY})`)
      .attr("data-id", d => `${sentence.svgId}-${d.id}`)
      .on("mouseover", (event, d) => highlight(event, d, sentence, positions, idToIndex))
      .on("mouseout", clearHighlight);

  groups.append("text")
    .attr("text-anchor", "middle")
    .attr("direction", sentence.rtl ? "rtl" : "ltr")
    .attr("unicode-bidi", sentence.rtl ? "bidi-override" : null)
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
    const pairSvg = d3.select(`#${pairSvgId}`);
    const pairSvgWidth = pairSvg.node()?.getBoundingClientRect().width || 1800;
    const pairPositions = computePositions(pairTokens, pairSentence.rtl, pairSentence.noSpaceAfter, pairSvgWidth);
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
    const distance = Math.abs(idToIndex[d.id] - idToIndex[d.head]);
    const height = arcHeightForDistance(distance);
    svg.append("path")
      .attr("class", "arc arc-highlight-out")
      .attr("marker-end", "url(#arrowhead-blue)")
      .attr("d", arcPath(positions[idx], positions[headIdx], height));
    svg.append("text")
      .attr("class", "arc-label")
      .attr("x", (positions[idx] + positions[headIdx]) / 2)
      .attr("y", y - height - 20)
      .text(d.deprel);
  }

  tokens.forEach((t, i) => {
    if (t.head === d.id) {
      const distance = Math.abs(i - idx);
      const height = arcHeightForDistance(distance);
      svg.append("path")
        .attr("class", "arc arc-highlight-in")
        .attr("marker-end", "url(#arrowhead-red)")
        .attr("d", arcPath(positions[i], positions[idx], height));
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

function clearSVGs() {
  d3.selectAll("svg").selectAll("*").remove();
}

// function loadDataset(name) {
//   const { sentences, wordMap } = datasets[name];
//   window.currentWordMap = wordMap;
//   clearSVGs();
//   sentences.forEach(renderSentence);
// }

// document.getElementById("datasetSelector").addEventListener("change", (e) => {
//   loadDataset(e.target.value);
// });

// // Load default
// loadDataset("matt2_2a");
