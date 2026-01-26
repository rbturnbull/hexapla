// import { datasets } from './data.js';

// const selectedDataset = datasets.matt2_2a;
// const { sentences, wordMap } = selectedDataset;

const tokenY = 120;
const spacing = 20;
const rowGap = 100;
const defaultMaxWordsPerRow = 12;

function arcHeightForDistance(distance, minHeight = 30, maxHeight = 80) {
  const raw = maxHeight - (maxHeight - minHeight) * Math.exp(-(distance - 1)/5);
  return Math.max(minHeight, Math.min(maxHeight, raw));
}

function arcPath(x1, x2, height, y, flip = false) {
  const radius = Math.abs(x2 - x1) / 2;
  const sweep = flip ? (x1 < x2 ? 0 : 1) : (x1 < x2 ? 1 : 0);
  return `M${x1},${y} A${radius},${height} 0 0,${sweep} ${x2},${y}`;
}

function connectorY(rowYs, rowIndex, edge) {
  const rowY = rowYs[rowIndex];
  if (edge === "top") {
    return rowY - 18;
  }
  return rowY + 6;
}

function adjustArabicTaMarbuta(str) {
  if (str.length > 1 && str.endsWith("ة")) {
    return str.slice(0, -1) + "ت";
  }
  return str;
}

function buildGroups(tokens, rows, noSpaceAfter, rtl) {
  const noSpaceAfterSet = new Set(noSpaceAfter || []);
  const groups = [];
  const tokenToGroup = new Array(tokens.length).fill(-1);
  let i = 0;
  while (i < tokens.length) {
    const rowIndex = rows[i];
    let end = i;
    let text = tokens[i].form;
    while (
      end < tokens.length - 1 &&
      noSpaceAfterSet.has(tokens[end].id) &&
      rows[end + 1] === rowIndex
    ) {
      end += 1;
      text = adjustArabicTaMarbuta(text) + tokens[end].form;
    }
    const tokenIndexes = [];
    for (let j = i; j <= end; j += 1) {
      tokenToGroup[j] = groups.length;
      tokenIndexes.push(j);
    }
    groups.push({ rowIndex, tokenIndexes, text, rtl });
    i = end + 1;
  }
  return { groups, tokenToGroup };
}

function computeGroupPositions(groups, svgWidth) {
  const ctx = document.createElement("canvas").getContext("2d");
  ctx.font = "24px Gentium Plus";
  const positionsByGroup = new Array(groups.length).fill(null);

  const rows = {};
  groups.forEach((g, idx) => {
    const width = ctx.measureText(g.text).width;
    if (!rows[g.rowIndex]) {
      rows[g.rowIndex] = [];
    }
    rows[g.rowIndex].push({ idx, width, rtl: g.rtl });
  });

  Object.values(rows).forEach((rowGroups) => {
    const totalWidth = rowGroups.reduce((sum, g, i) => {
      const gap = i < rowGroups.length - 1 ? spacing : 0;
      return sum + g.width + gap;
    }, 0);
    const rtl = rowGroups[0]?.rtl;
    const startX = Math.max(50, (svgWidth - totalWidth) / 2);
    if (rtl) {
      let rightEdge = startX + totalWidth;
      rowGroups.forEach((g, i) => {
        const center = rightEdge - g.width / 2;
        positionsByGroup[g.idx] = { center, width: g.width, left: rightEdge - g.width, right: rightEdge };
        const gap = i < rowGroups.length - 1 ? spacing : 0;
        rightEdge -= g.width + gap;
      });
    } else {
      let currentX = startX;
      rowGroups.forEach((g, i) => {
        const center = currentX + g.width / 2;
        positionsByGroup[g.idx] = { center, width: g.width, left: currentX, right: currentX + g.width };
        const gap = i < rowGroups.length - 1 ? spacing : 0;
        currentX += g.width + gap;
      });
    }
  });

  return positionsByGroup;
}

function computeLayout(tokens, rtl, noSpaceAfter, svgWidth, maxWordsPerRow = defaultMaxWordsPerRow) {
  const rows = new Array(tokens.length).fill(0);
  const rowYs = [tokenY];
  let split = tokens.length;
  const noSpaceAfterSet = new Set(noSpaceAfter || []);
  if (tokens.length > maxWordsPerRow) {
    split = Math.ceil(tokens.length / 2);
    while (split < tokens.length && noSpaceAfterSet.has(tokens[split - 1]?.id)) {
      split += 1;
    }
    rowYs.push(tokenY + rowGap);
    for (let i = split; i < tokens.length; i += 1) {
      rows[i] = 1;
    }
  }

  const { groups } = buildGroups(tokens, rows, noSpaceAfter, rtl);
  const groupPositions = computeGroupPositions(groups, svgWidth);
  const ctx = document.createElement("canvas").getContext("2d");
  ctx.font = "24px Gentium Plus";

  const positions = new Array(tokens.length).fill(0);
  const segmentBounds = new Array(tokens.length).fill(null);
  const displayPositions = new Array(tokens.length).fill(0);
  const displayText = tokens.map(t => t.form);
  const displayOpacity = new Array(tokens.length).fill(1);
  const displayAnchors = new Array(tokens.length).fill(rtl ? "end" : "middle");
  const displayDx = new Array(tokens.length).fill(0);

  groups.forEach((group, groupIndex) => {
    const groupPos = groupPositions[groupIndex];
    const tokenIndexes = group.tokenIndexes;
    if (!groupPos) {
      return;
    }
    const totalWeight = tokenIndexes.reduce((sum, idx) => {
      const width = ctx.measureText(tokens[idx].form).width;
      return sum + (width || 1);
    }, 0) || 1;
    let cursor = group.rtl ? groupPos.right : groupPos.left;
    tokenIndexes.forEach((idx, segIndex) => {
      const segWeight = ctx.measureText(tokens[idx].form).width || 1;
      const segWidth = groupPos.width * (segWeight / totalWeight);
      let segLeft;
      let segRight;
      if (group.rtl) {
        segRight = cursor;
        segLeft = cursor - segWidth;
        cursor = segLeft;
      } else {
        segLeft = cursor;
        segRight = cursor + segWidth;
        cursor = segRight;
      }
      positions[idx] = (segLeft + segRight) / 2;
      segmentBounds[idx] = { left: segLeft, right: segRight };
      if (segIndex === 0) {
        displayPositions[idx] = groupPos.center;
        displayText[idx] = group.text;
        displayOpacity[idx] = 1;
        displayAnchors[idx] = "middle";
        displayDx[idx] = 0;
      } else {
        displayPositions[idx] = groupPos.center;
        displayOpacity[idx] = 0;
      }
    });
  });

  return {
    positions,
    segmentBounds,
    rows,
    rowYs,
    split,
    displayPositions,
    displayText,
    displayOpacity,
    displayAnchors,
    displayDx
  };
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
  const {
    positions,
    segmentBounds,
    rows,
    rowYs,
    displayPositions,
    displayText,
    displayOpacity,
    displayAnchors,
    displayDx
  } = computeLayout(
    tokens,
    sentence.rtl,
    sentence.noSpaceAfter,
    svgWidth
  );

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
        const fromIndex = idToIndex[d.id];
        const toIndex = idToIndex[d.head];
        const fromRow = rows[fromIndex];
        const toRow = rows[toIndex];
        const x1 = positions[fromIndex];
        const x2 = positions[toIndex];
        if (fromRow !== toRow) {
          const y1 = fromRow === 0 ? connectorY(rowYs, fromRow, "bottom") : connectorY(rowYs, fromRow, "top");
          const y2 = toRow === 0 ? connectorY(rowYs, toRow, "bottom") : connectorY(rowYs, toRow, "top");
          return `M${x1},${y1} L${x2},${y2}`;
        }
        const distance = Math.abs(fromIndex - toIndex);
        const height = arcHeightForDistance(distance);
        const y = fromRow === 0 ? rowYs[0] - 30 : rowYs[1] + 30;
        return arcPath(x1, x2, height, y, fromRow === 1);
      });

  const groups = svg.selectAll(".token")
    .data(tokens).enter()
    .append("g")
      .attr("transform", (d, i) => `translate(${displayPositions[i]},${rowYs[rows[i]]})`)
      .attr("data-id", d => `${sentence.svgId}-${d.id}`);

  groups.append("text")
    .attr("text-anchor", (d, i) => displayAnchors[i])
    .attr("direction", sentence.rtl ? "rtl" : "ltr")
    .attr("unicode-bidi", sentence.rtl ? "bidi-override" : null)
    .attr("class", d => `token${d.head === 0 ? " root" : ""}`)
    .style("opacity", (d, i) => displayOpacity[i])
    .style("pointer-events", "none")
    .attr("dx", (d, i) => displayDx[i])
    .text((d, i) => displayText[i]);

  const hitHeight = 24;
  svg.selectAll(".token-hit")
    .data(tokens)
    .enter()
    .append("rect")
      .attr("class", "token-hit")
      .attr("x", (d, i) => {
        const bounds = segmentBounds[i];
        return bounds ? (bounds.left - 2) : (positions[i] - 10);
      })
      .attr("y", (d, i) => rowYs[rows[i]] - hitHeight + 4)
      .attr("width", (d, i) => {
        const bounds = segmentBounds[i];
        return bounds ? (bounds.right - bounds.left + 4) : 20;
      })
      .attr("height", hitHeight)
      .attr("fill", "transparent")
      .style("cursor", "pointer")
      .on("mouseover", (event, d) => highlight(event, d, sentence, positions, displayPositions, idToIndex, segmentBounds))
      .on("mouseout", clearHighlight)
      .on("click", (event, d) => navigateToLemma(sentence, d));
}

function highlight(event, d, sentence, positions, displayPositions, idToIndex, segmentBounds) {
  clearHighlight();
  const svg = d3.select(`#${sentence.svgId}`);
  highlightWord(svg, sentence, d, positions, displayPositions, idToIndex, sentence.svgId, null, null, segmentBounds);

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
    const {
      positions: pairPositions,
      rows: pairRows,
      rowYs: pairRowYs,
      segmentBounds: pairSegmentBounds,
      displayPositions: pairDisplayPositions
    } = computeLayout(
      pairTokens,
      pairSentence.rtl,
      pairSentence.noSpaceAfter,
      pairSvgWidth
    );
    const pairD = pairTokens.find(t => t.id === +pairTokenId);
    highlightWord(
      pairSvg,
      pairSentence,
      pairD,
      pairPositions,
      pairDisplayPositions,
      pairIdToIndex,
      pairSvgId,
      pairRows,
      pairRowYs,
      pairSegmentBounds
    );
  }
}

function highlightWord(svg, sentence, d, positions, displayPositions, idToIndex, svgId, rows, rowYs, segmentBounds) {
  const tokens = sentence.data.split("\n").map(line => {
    const [id, form, , upos, , feats, head, deprel] = line.split("\t");
    return { id: +id, form, upos, feats, head: +head, deprel };
  });
  const svgWidth = svg.node()?.getBoundingClientRect().width || 1800;
  if (!rows || !rowYs || !segmentBounds || !displayPositions) {
    ({ rows, rowYs, segmentBounds, displayPositions } = computeLayout(
      tokens,
      sentence.rtl,
      sentence.noSpaceAfter,
      svgWidth
    ));
  }
  const idx = idToIndex[d.id];
  const x = positions[idx];
  const displayX = displayPositions ? displayPositions[idx] : positions[idx];
  const rowIndex = rows[idx];
  const rowY = rowYs[rowIndex];
  const y = rowIndex === 0 ? rowY - 18 : rowY + 18;
  const group = d3.select(`[data-id="${svgId}-${d.id}"]`);
  const bounds = segmentBounds[idx];
  const rectWidth = bounds ? (bounds.right - bounds.left) : 0;
  const rectHeight = 24;
  group.insert("rect", "text")
    .attr("class", "token-bg")
    .attr("x", bounds ? (bounds.left - displayX - 4) : -10)
    .attr("y", -rectHeight + 4)
    .attr("width", bounds ? (rectWidth + 8) : 20)
    .attr("height", rectHeight);

  if (d.head !== 0) {
    const headIdx = idToIndex[d.head];
    const headRow = rows[headIdx];
    if (headRow !== rowIndex) {
      const y1 = rowIndex === 0 ? connectorY(rowYs, rowIndex, "bottom") : connectorY(rowYs, rowIndex, "top");
      const y2 = headRow === 0 ? connectorY(rowYs, headRow, "bottom") : connectorY(rowYs, headRow, "top");
      svg.append("path")
        .attr("class", "arc arc-highlight-out")
        .attr("marker-end", "url(#arrowhead-blue)")
        .attr("d", `M${positions[idx]},${y1} L${positions[headIdx]},${y2}`);
    } else {
      const distance = Math.abs(idToIndex[d.id] - idToIndex[d.head]);
      const height = arcHeightForDistance(distance);
      const arcY = rowIndex === 0 ? rowY - 30 : rowY + 30;
      svg.append("path")
        .attr("class", "arc arc-highlight-out")
        .attr("marker-end", "url(#arrowhead-blue)")
        .attr("d", arcPath(positions[idx], positions[headIdx], height, arcY, rowIndex === 1));
      svg.append("text")
        .attr("class", "arc-label")
        .attr("x", (positions[idx] + positions[headIdx]) / 2)
        .attr("y", rowIndex === 0 ? arcY - height - 20 : arcY + height + 20)
        .text(d.deprel);
    }
  }

  tokens.forEach((t, i) => {
    if (t.head === d.id) {
      const childRow = rows[i];
      if (childRow !== rowIndex) {
        const y1 = rowIndex === 0 ? connectorY(rowYs, rowIndex, "bottom") : connectorY(rowYs, rowIndex, "top");
        const y2 = childRow === 0 ? connectorY(rowYs, childRow, "bottom") : connectorY(rowYs, childRow, "top");
        svg.append("path")
          .attr("class", "arc arc-highlight-in")
          .attr("marker-end", "url(#arrowhead-red)")
          .attr("d", `M${positions[i]},${y2} L${positions[idx]},${y1}`);
      } else {
        const distance = Math.abs(i - idx);
        const height = arcHeightForDistance(distance);
        const arcY = rowIndex === 0 ? rowY - 30 : rowY + 30;
        svg.append("path")
          .attr("class", "arc arc-highlight-in")
          .attr("marker-end", "url(#arrowhead-red)")
          .attr("d", arcPath(positions[i], positions[idx], height, arcY, rowIndex === 1));
      }
    }
  });

  const featLines = (d.feats && d.feats !== "_") ? d.feats.split("|") : [];
  const lines = [d.upos, ...featLines];
  lines.forEach((line, i) => {
    svg.append("text")
      .attr("class", "features")
      .attr("x", x)
      .attr("y", rowIndex === 0 ? (rowY + 20 + i * 14) : (rowY - 20 - i * 14))
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

function navigateToLemma(sentence, d) {
  if (!sentence.lemmaMap || !sentence.languageSlug) {
    return;
  }
  const lemma = sentence.lemmaMap[d.id];
  if (!lemma || lemma === "_") {
    return;
  }
  const encodedLemma = encodeURIComponent(lemma);
  window.location.href = `../../${siglum}/${sentence.languageSlug}/${encodedLemma}/`;
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
