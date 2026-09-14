// PVsyst .PAN File Generator - Interactive Core Script
if (window.pdfjsLib) {
  pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
}

let bins = [];
let sel = -1;
let baseModelTemplate = "";

const dz = document.getElementById("dropZone");
const fi = document.getElementById("fileInput");

if (dz && fi) {
  dz.onclick = () => fi.click();
  dz.ondragover = (e) => { e.preventDefault(); dz.style.borderColor = "#0ea5e9"; };
  dz.ondragleave = () => { dz.style.borderColor = ""; };
  dz.ondrop = (e) => {
    e.preventDefault();
    dz.style.borderColor = "";
    if (e.dataTransfer.files.length) handlePDF(e.dataTransfer.files[0]);
  };
  fi.onchange = (e) => {
    if (e.target.files.length) handlePDF(e.target.files[0]);
  };
}

async function handlePDF(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    return alert("Please upload a PDF datasheet.");
  }

  document.getElementById("statusMsg").innerText = "Extracting text and coordinates...";

  let allItems = [];
  let rawLines = [];

  try {
    const ab = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: ab }).promise;

    for (let p = 1; p <= pdf.numPages; p++) {
      const page = await pdf.getPage(p);
      const c = await page.getTextContent();
      let ymap = {};

      c.items.forEach(it => {
        const x = it.transform[4];
        const y = Math.round(it.transform[5]);
        const str = it.str.trim();
        if (!str) return;

        allItems.push({ str, x, y, page: p });

        let k = Object.keys(ymap).find(k => Math.abs(k - y) < 6);
        if (!k) {
          ymap[y] = [];
          k = y;
        }
        ymap[k].push({ s: it.str, x: x });
      });

      Object.keys(ymap).sort((a, b) => b - a).forEach(y => {
        ymap[y].sort((a, b) => a.x - b.x);
        rawLines.push(ymap[y].map(i => i.s).join("   "));
      });
    }
  } catch (e) {
    console.error("PDF read error:", e);
    return alert("Unable to parse text from this PDF.");
  }

  try {
    parseDatasheet(allItems, rawLines, file.name);
    document.getElementById("statusMsg").innerText = "Upload complete. Click any STC Wp below.";
  } catch (err) {
    console.error("Datasheet processing error:", err);
  }
}

function cleanTextNumbers(text) {
  if (!text) return "";
  let t = text.replace(/(\.\d{2})(\d{2}\.\d{2})/g, "$1 $2");
  t = t.replace(/(\.\d{2})(\d{3,4})\b/g, "$1 $2");
  t = t.replace(/(\d+)\s*\.\s*(\d+)/g, "$1.$2");
  t = t.replace(/(\d),(\d)/g, "$1.$2");
  return t;
}

function nums(str) {
  const clean = cleanTextNumbers(str);
  return (clean.match(/[-+]?\b\d+(?:\.\d+)?\b/g) || []).map(Number).filter(n => !isNaN(n) && isFinite(n));
}

// ============================================================
// UNIVERSAL STC TABLE PARSER (Horizontal, Vertical, Vector & Cluster)
// ============================================================
function parseDatasheet(items, lines, filename) {
  const rawFullText = lines.join(" \n ");
  const fullText = cleanTextNumbers(rawFullText);
  const cleanLines = lines.map(l => cleanTextNumbers(l).trim()).filter(l => l.length > 0);

  detectManufacturer(fullText, cleanLines);
  parseMechanicalTable(cleanLines, fullText);
  parseTempCoefficients(fullText, cleanLines);
  detectModelName(fullText, cleanLines, filename);

  bins = [];

  // Filter out bifacial gain / backside gain lines for STC parsing
  const stcLines = cleanLines.filter(l => {
    const low = l.toLowerCase();
    if (/^\s*(?:5%|10%|15%|20%|25%|30%)\s*$/.test(l)) return false;
    if (low.includes("bifacial gain") || low.includes("backside power gain") || low.includes("gain @")) return false;
    return true;
  });
  const stcText = stcLines.join(" \n ");

  // ------------------------------------------------------------
  // STRATEGY 1: Horizontal Rows (Direct or subsequent line matching)
  // (e.g. Goldi, Avaada, Future Solar, Tongwei, Rayzon)
  // ------------------------------------------------------------
  let pmaxRow = getRowNumbersSTC(stcLines, [/(?:pmax|peak\s*power|nominal\s*max|capacity\s*rating|rated\s*power|maximum\s*power)/i], 450, 750);
  let vmpRow = getRowNumbersSTC(stcLines, [/\bvmp\b/i, /voltage\s*at\s*pmax/i, /maximum\s*power\s*voltage/i, /rated\s*voltage/i, /optimum\s*operating\s*voltage/i], 28, 58);
  let impRow = getRowNumbersSTC(stcLines, [/\bimp\b/i, /current\s*at\s*pmax/i, /maximum\s*power\s*current/i, /rated\s*current/i, /optimum\s*operating\s*current/i], 7, 24);
  let vocRow = getRowNumbersSTC(stcLines, [/\bvoc\b/i, /open[\s-]circuit\s*voltage/i], 35, 70);
  let iscRow = getRowNumbersSTC(stcLines, [/\bisc\b/i, /short[\s-]circuit\s*current/i, /short\s*ciruit/i], 8, 25);
  let effRow = getRowNumbersSTC(stcLines, [/module\s*eff/i, /efficiency\s*stc/i, /efficiency\s*\(?%?\)?/i], 18, 26);

  if (pmaxRow.length >= 2 && vmpRow.length >= 2 && impRow.length >= 2) {
    const count = Math.min(pmaxRow.length, vmpRow.length, impRow.length);
    for (let k = 0; k < count; k++) {
      const w = pmaxRow[k];
      const v = vmpRow[k];
      const i = impRow[k];
      const vo = (k < vocRow.length) ? vocRow[k] : +(v * 1.2).toFixed(2);
      const isc = (k < iscRow.length) ? iscRow[k] : +(i * 1.055).toFixed(2);
      const eff = (k < effRow.length) ? effRow[k] : null;

      if (Math.abs(v * i - w) / w < 0.05) {
        bins.push({ wp: w, vmp: v, imp: i, voc: vo, isc: isc, eff: eff, src: "HorizontalRows" });
      }
    }
  }

  // ------------------------------------------------------------
  // STRATEGY 2: Sequential Vector Stream (Waaree BiN-11 style)
  // ------------------------------------------------------------
  if (bins.length === 0) {
    const allNums = nums(stcText);
    const vmpsList = [];
    const impsList = [];
    const vocsList = [];
    const iscsList = [];

    for (let N = 4; N <= 12; N++) {
      for (let i = 0; i <= allNums.length - N; i++) {
        const chunk = allNums.slice(i, i + N);
        if (chunk.every(x => x >= 32 && x <= 58) && chunk.every((x, idx) => idx === 0 || x >= chunk[idx - 1])) {
          vmpsList.push({ idx: i, n: N, chunk });
        }
        if (chunk.every(x => x >= 8 && x <= 22) && chunk.every((x, idx) => idx === 0 || x >= chunk[idx - 1])) {
          impsList.push({ idx: i, n: N, chunk });
        }
        if (chunk.every(x => x >= 42 && x <= 65) && chunk.every((x, idx) => idx === 0 || x >= chunk[idx - 1])) {
          vocsList.push({ idx: i, n: N, chunk });
        }
        if (chunk.every(x => x >= 9 && x <= 24) && chunk.every((x, idx) => idx === 0 || x >= chunk[idx - 1])) {
          iscsList.push({ idx: i, n: N, chunk });
        }
      }
    }

    const bestMatches = [];
    for (const vObj of vmpsList) {
      for (const iObj of impsList) {
        if (vObj.n === iObj.n && Math.abs(vObj.idx - iObj.idx) < 120) {
          const powers = vObj.chunk.map((v, k) => Math.round(v * iObj.chunk[k]));
          const validPowers = powers.every(p => p >= 450 && p <= 750);
          const stepValid = powers.every((p, idx) => idx === 0 || [5, 10].includes(p - powers[idx - 1]));
          if (validPowers && stepValid) {
            bestMatches.push({ n: vObj.n, powers, vmps: vObj.chunk, imps: iObj.chunk, vIdx: vObj.idx, iIdx: iObj.idx });
          }
        }
      }
    }

    if (bestMatches.length > 0) {
      bestMatches.sort((a, b) => b.n - a.n);
      const best = bestMatches[0];
      const N = best.n;

      let bestVoc = best.vmps.map(v => +(v * 1.2).toFixed(2));
      for (const voObj of vocsList) {
        if (voObj.n === N && voObj.chunk.every((vo, k) => vo > best.vmps[k])) {
          bestVoc = voObj.chunk;
          break;
        }
      }

      let bestIsc = best.imps.map(i => +(i * 1.055).toFixed(2));
      for (const iscObj of iscsList) {
        if (iscObj.n === N && iscObj.chunk.every((isc, k) => isc > best.imps[k])) {
          bestIsc = iscObj.chunk;
          break;
        }
      }

      for (let k = 0; k < N; k++) {
        bins.push({
          wp: best.powers[k],
          vmp: best.vmps[k],
          imp: best.imps[k],
          voc: bestVoc[k],
          isc: bestIsc[k],
          eff: null,
          src: "VectorSequence"
        });
      }
    }
  }

  // ------------------------------------------------------------
  // STRATEGY 3: Vertical Single-Line Rows (RenewSys)
  // ------------------------------------------------------------
  if (bins.length === 0) {
    for (const l of stcLines) {
      const ns = nums(l);
      if (ns.length >= 4) {
        const pCands = ns.filter(x => x >= 450 && x <= 750 && (x % 5 === 0 || x % 1 === 0));
        for (const p of pCands) {
          const vCands = ns.filter(x => x >= 30 && x <= 65 && x !== p);
          const iCands = ns.filter(x => x >= 8 && x <= 22 && x !== p);
          for (const v of vCands) {
            for (const i of iCands) {
              if (Math.abs(v * i - p) / p < 0.02) {
                const higherV = vCands.filter(x => x >= v);
                const higherI = iCands.filter(x => x >= i);
                const voc = higherV.length ? Math.max(...higherV) : +(v * 1.2).toFixed(2);
                const isc = higherI.length ? Math.max(...higherI) : +(i * 1.055).toFixed(2);
                bins.push({ wp: p, vmp: v, imp: i, voc: voc, isc: isc, eff: null, src: "SingleLineVertical" });
                break;
              }
            }
          }
        }
      }
    }
  }

  // ------------------------------------------------------------
  // STRATEGY 4: Clustered Columns (Adani)
  // ------------------------------------------------------------
  if (bins.length === 0) {
    const allNums = nums(stcText);
    for (let idx = 0; idx < allNums.length; idx++) {
      const n = allNums[idx];
      if (n >= 450 && n <= 750 && (n % 5 === 0 || n % 1 === 0)) {
        const window = allNums.slice(idx + 1, idx + 7);
        const vmps = window.filter(x => x >= 35 && x <= 58);
        const imps = window.filter(x => x >= 8 && x <= 22);
        const vocs = window.filter(x => x >= 45 && x <= 65);
        const iscs = window.filter(x => x >= 9 && x <= 24);

        let bestV = null, bestI = null;
        for (const v of vmps) {
          for (const i of imps) {
            if (Math.abs(v * i - n) / n < 0.015) {
              bestV = v;
              bestI = i;
              break;
            }
          }
          if (bestV) break;
        }

        if (!bestV && imps.length >= 1) {
          const i = imps[0];
          const v = +(n / i).toFixed(2);
          if (v >= 35 && v <= 58) {
            bestV = v;
            bestI = i;
          }
        }

        if (bestV && bestI) {
          const higherV = vocs.filter(x => x > bestV);
          const higherI = iscs.filter(x => x > bestI);
          const voc = higherV.length ? Math.max(...higherV) : +(bestV * 1.2).toFixed(2);
          const isc = higherI.length ? Math.max(...higherI) : +(bestI * 1.055).toFixed(2);
          bins.push({ wp: n, vmp: bestV, imp: bestI, voc: voc, isc: isc, eff: null, src: "ClusterBlock" });
        }
      }
    }
  }

  // ------------------------------------------------------------
  // STRATEGY 5: Fallback Wp Range Extraction
  // ------------------------------------------------------------
  if (bins.length === 0) {
    const wpList = extractWpListFromText(fullText, cleanLines);
    if (wpList.length > 0) {
      const baseVoc = 50.0;
      const baseVmp = 42.0;
      wpList.forEach(w => {
        const ratio = w / wpList[0];
        const curVmp = +(baseVmp * (1 + (ratio - 1) * 0.25)).toFixed(2);
        const curImp = +(w / curVmp).toFixed(2);
        const curVoc = +(baseVoc * (1 + (ratio - 1) * 0.2)).toFixed(2);
        const curIsc = +(curImp * 1.055).toFixed(2);
        bins.push({ wp: w, vmp: curVmp, imp: curImp, voc: curVoc, isc: curIsc, eff: null, src: "RangeFallback" });
      });
    }
  }

  // Deduplicate by wp and sort
  bins = bins.filter((v, i, a) => a.findIndex(t => t.wp === v.wp) === i);
  bins.sort((a, b) => a.wp - b.wp);

  renderBins();
  if (bins.length) selectBin(bins.length - 1);
}

function extractWpListFromText(fullText, lines) {
  const rangePatterns = [
    /(?:XXX|AAA)?\s*=?\s*(\d{3,4})\s*[-~–]\s*(\d{3,4})\s*(?:W|Wp|Watt)?/i,
    /(\d{3,4})\s*(?:W|Wp|Watt)?\s*[-~–]\s*(\d{3,4})\s*(?:W|Wp|Watt)/i,
    /\b(\d{3})\s*[-~–]\s*(\d{3})\s*Wp\b/i
  ];

  for (const pat of rangePatterns) {
    const match = fullText.match(pat);
    if (match) {
      const minWp = parseInt(match[1]);
      const maxWp = parseInt(match[2]);
      if (minWp >= 450 && maxWp <= 750 && maxWp > minWp && (maxWp - minWp) <= 120) {
        const step = (maxWp - minWp) % 5 === 0 ? 5 : 10;
        const res = [];
        for (let w = minWp; w <= maxWp; w += step) {
          res.push(w);
        }
        if (res.length >= 2) return res;
      }
    }
  }
  return [];
}

function getRowNumbersSTC(lines, patterns, min, max) {
  for (let idx = 0; idx < lines.length; idx++) {
    const l = lines[idx];
    const lower = l.toLowerCase();
    if (lower.includes("bifacial output") || lower.includes("backside") || lower.includes("gain") || lower.includes("tolerance") || lower.includes("noct (wp)") || lower.includes("noct:")) continue;

    for (let pat of patterns) {
      if (pat.test(lower)) {
        let found = nums(l).filter(n => n >= min && n <= max);
        if (found.length >= 2) {
          if (found.length >= 6 && found.length % 2 === 0) {
            let stcOnly = [];
            for (let i = 0; i < found.length; i += 2) {
              stcOnly.push(found[i]);
            }
            if (stcOnly.length >= 2) return stcOnly;
          }
          const maxVal = Math.max(...found);
          let stcOnly = found.filter(n => n >= maxVal * 0.85);
          if (stcOnly.length >= 2) return stcOnly;
          return found;
        }
        // Check subsequent lines if label line is separate
        for (let nextIdx = idx + 1; nextIdx <= Math.min(lines.length - 1, idx + 8); nextIdx++) {
          let nextFound = nums(lines[nextIdx]).filter(n => n >= min && n <= max);
          if (nextFound.length >= 2) {
            return nextFound;
          }
        }
      }
    }
  }
  return [];
}

function detectManufacturer(fullText, lines) {
  const mfgMap = [
    { name: "Waaree Energies", match: /waaree/i },
    { name: "RenewSys", match: /renewsys/i },
    { name: "Navitas Solar", match: /navitas/i },
    { name: "Vikram Solar", match: /vikram/i },
    { name: "Sunbond Energy", match: /sunbond/i },
    { name: "Avaada Electro", match: /avaada/i },
    { name: "Tongwei Co., Ltd.", match: /tongwei|\btw solar\b/i },
    { name: "Rayzon Solar", match: /rayzon/i },
    { name: "Adani Solar", match: /adani/i },
    { name: "Goldi Solar", match: /goldi/i },
    { name: "Insolation Energy", match: /insolation|ina solar/i },
    { name: "Premier Energies", match: /premier energies/i },
    { name: "Saatvik Solar", match: /saatvik/i },
    { name: "Future Solar", match: /future solar|fs green energies/i },
    { name: "JinkoSolar", match: /jinko/i },
    { name: "LONGi Solar", match: /longi/i },
    { name: "Trina Solar", match: /trina/i },
    { name: "JA Solar", match: /ja solar/i },
    { name: "Canadian Solar", match: /canadian solar/i },
    { name: "Astronergy", match: /astronergy|chint/i },
    { name: "Risen Energy", match: /risen/i }
  ];

  const topSlice = lines.slice(0, 30).join(" ");
  for (const m of mfgMap) {
    if (m.match.test(topSlice) || m.match.test(fullText)) {
      document.getElementById("manufacturer").value = m.name;
      return;
    }
  }
  document.getElementById("manufacturer").value = "SolarModule";
}

function parseTempCoefficients(fullText, lines) {
  let parsedPmp = null, parsedVoc = null, parsedIsc = null;

  for (let l of lines) {
    let line = l.replace(/["”]/g, "°")
                .replace(/[\u2212\u2013\u2014]/g, "-")
                .replace(/\s+/g, " ");

    if (parsedPmp === null && /(?:power|pmax|pmp|p\(max\)|\bpm\b|[\u03B3\u03B4]|gamma)/i.test(line)) {
      let m = line.match(/(?:coeff[a-z]*|rating|[\u03B3\u03B4]|gamma)?[:\s\-=]+([−\-]\s*0\.\d{2,4})\s*(?:%|\/|°c|k)?/i);
      if (m) parsedPmp = parseFloat(m[1].replace(/\s+/g, ""));
    }

    if (parsedVoc === null && /(?:voc|open[\s-]circuit|voltage|[\u03B2]|beta)/i.test(line)) {
      let m = line.match(/(?:coeff[a-z]*|rating|[\u03B2]|beta)?[:\s\-=]+([−\-]\s*0\.\d{2,4})\s*(?:%|\/|°c|k)?/i);
      if (m) parsedVoc = parseFloat(m[1].replace(/\s+/g, ""));
    }

    if (parsedIsc === null && /(?:isc|short[\s-]circuit|current|[\u03B1]|alpha)/i.test(line)) {
      let m = line.match(/(?:coeff[a-z]*|rating|[\u03B1]|alpha)?[:\s\-=]+(\+?\s*0\.0\d{1,4})\s*(?:%|\/|°c|k)?/i);
      if (m) parsedIsc = parseFloat(m[1].replace(/\s+/g, "").replace("+", ""));
    }
  }

  const fullDoc = lines.join(" \n ").replace(/["”]/g, "°").replace(/[\u2212\u2013\u2014]/g, "-");

  if (parsedPmp === null) {
    let m = fullDoc.match(/(?:pmax|pmp|\bpm\b)[^\d−\-]{0,45}([−\-]\s*0\.\d{2,4})\s*%/i);
    if (m) parsedPmp = parseFloat(m[1].replace(/\s+/g, ""));
  }
  if (parsedVoc === null) {
    let m = fullDoc.match(/(?:voc|open[\s-]circuit)[^\d−\-]{0,45}([−\-]\s*0\.\d{2,4})\s*%/i);
    if (m) parsedVoc = parseFloat(m[1].replace(/\s+/g, ""));
  }
  if (parsedIsc === null) {
    let m = fullDoc.match(/(?:isc|short[\s-]circuit)[^\d\+]{0,45}(\+?\s*0\.0\d{1,4})\s*%/i);
    if (m) parsedIsc = parseFloat(m[1].replace(/\s+/g, "").replace("+", ""));
  }

  document.getElementById("muPmpPct").value = parsedPmp !== null ? parsedPmp.toFixed(3) : "-0.300";
  document.getElementById("muVocPct").value = parsedVoc !== null ? parsedVoc.toFixed(3) : "-0.250";
  document.getElementById("muIscPct").value = parsedIsc !== null ? parsedIsc.toFixed(3) : "0.045";
}

function detectModelName(fullText, lines, filename) {
  let detected = "";

  for (let l of lines.slice(0, 30)) {
    let m = l.match(/(?:module\s*type|model\s*type|models?|product\s*code)\s*[:：\s]*([A-Z0-9\-_]{5,22})/i);
    if (m && !/electrical|standard|conditions|rating|capacity|characteristics|technical|specification/i.test(m[1])) {
      detected = m[1].trim();
      break;
    }
  }

  if (!detected) {
    let m2 = fullText.match(/\b(BIN-[0-9]{2}-[0-9]{3}|BiN-[0-9]{2}-[0-9]{3}|DESERV[A-Z0-9\s\-]+|GS10-M156-WF|FST-M10\.[0-9A-Z\.\-]+|SEPLT[0-9A-Z\-]+|AVN[0-9]{2}[A-Z0-9]+|TWMNF-[A-Z0-9\-]+|ASB-M10-[0-9A-Z\-]+)\b/i);
    if (m2) detected = m2[1].trim();
  }

  if (!detected) {
    detected = filename.replace(/\.[^/.]+$/, "").replace(/[-_]/g, " ");
  }

  detected = detected.replace(/\b(capacity|rating|pmax|power|stc|table|rev[0-9]+|data)\b.*/i, "").trim();

  baseModelTemplate = detected;
  document.getElementById("model").value = detected;
}

function parseMechanicalTable(lines, fullText) {
  let length_mm = null, width_mm = null, depth_mm = null, weight_kg = null, cellCount = null;

  for (let l of lines) {
    let clean = l.replace(/[\u00d7\u2A2F\u2715\u2716\*]/g, " x ")
                 .replace(/\([A-Z]\)/gi, "")
                 .replace(/(\d),(\d)/g, "$1.$2");

    let m = clean.match(/\b([12]\d{3})\b\s*(?:mm)?\s*x\s*\b([1]\d{3})\b\s*(?:mm)?\s*x\s*\b([2-5]\d(?:\.\d)?)\b/i);
    if (m && !length_mm) {
      length_mm = parseFloat(m[1]);
      width_mm = parseFloat(m[2]);
      depth_mm = parseFloat(m[3]);
    }

    if (!length_mm && /(?:dimension|external\s*dimension|size)/i.test(clean)) {
      let numMatches = (clean.match(/\b\d{2,4}(?:\.\d+)?\b/g) || []).map(Number);
      let cLen = numMatches.find(n => n >= 1600 && n <= 2600);
      let cWid = numMatches.find(n => n >= 980 && n <= 1400);
      let cDep = numMatches.find(n => n >= 25 && n <= 50);

      if (cLen && cWid) {
        length_mm = cLen;
        width_mm = cWid;
        depth_mm = cDep || 35;
      }
    }

    if (!weight_kg && /(?:weight|mass)/i.test(clean)) {
      let wm = clean.match(/(?:weight|mass)[^\d]{0,25}(\d{1,2}(?:\.\d{1,2})?)\s*(?:k?g|kgs)?/i);
      if (wm && parseFloat(wm[1]) >= 18 && parseFloat(wm[1]) <= 55) {
        weight_kg = parseFloat(wm[1]);
      }
    }

    if (!cellCount) {
      let cm = clean.match(/\b(108|120|132|144|156)\s*(?:half[\s-]cells?|cells?|\(.*cells?\)|pcs)/i);
      if (cm) cellCount = parseInt(cm[1]);
    }
  }

  // Direct regex on fullText for weight
  if (!weight_kg) {
    let wm = fullText.match(/(?:weight|mass)[^\d]{0,25}(\d{1,2}(?:\.\d{1,2})?)\s*(?:k?g|kgs)?/i);
    if (wm && parseFloat(wm[1]) >= 18 && parseFloat(wm[1]) <= 55) {
      weight_kg = parseFloat(wm[1]);
    }
  }

  if (!weight_kg) {
    let wm2 = fullText.match(/\b(\d{1,2}(?:\.\d{1,2})?)\s*(?:kg|kgs)\b/i);
    if (wm2 && parseFloat(wm2[1]) >= 18 && parseFloat(wm2[1]) <= 55) {
      weight_kg = parseFloat(wm2[1]);
    }
  }

  // Search inside Physical Parameters / Mechanical tables
  if (!weight_kg || !length_mm) {
    for (let idx = 0; idx < lines.length; idx++) {
      if (/(?:physical\s*parameters|mechanical\s*specifications|mechanical\s*characteristics|mechanical\s*data)/i.test(lines[idx])) {
        for (let subIdx = idx; subIdx <= Math.min(lines.length - 1, idx + 15); subIdx++) {
          const subNums = nums(lines[subIdx]);
          for (const n of subNums) {
            if (!weight_kg && n >= 20.0 && n <= 45.0 && n !== depth_mm) {
              weight_kg = n;
            }
            if (!length_mm && n >= 1800 && n <= 2600) {
              length_mm = n;
            }
          }
        }
      }
    }
  }

  if (!length_mm) length_mm = 2278;
  if (!width_mm) width_mm = 1134;
  if (!depth_mm) depth_mm = 35;
  if (!weight_kg) weight_kg = 33.0;

  if (!cellCount) {
    if (length_mm > 2350 && width_mm > 1250) cellCount = 132;
    else if (length_mm > 2400) cellCount = 156;
    else cellCount = 144;
  }

  document.getElementById("lenMm").value = Math.max(length_mm, width_mm);
  document.getElementById("widMm").value = Math.min(length_mm, width_mm);
  document.getElementById("thkMm").value = depth_mm;
  document.getElementById("weight").value = weight_kg.toFixed(2);
  document.getElementById("ncels").value = Math.round(cellCount / 2);
  document.getElementById("ncelp").value = 2;

  let cellW = (width_mm > 1200) ? 210.0 : 182.0;
  let cellH = (cellCount === 132 || cellCount === 156) ? 105.0 : 91.0;
  document.getElementById("cellW").value = cellW.toFixed(1);
  document.getElementById("cellH").value = cellH.toFixed(1);

  recalcGeometryAndEff();
}

function handleDimensionChange() {
  const widMm = parseFloat(document.getElementById("widMm").value) || 1134;
  let cellW = (widMm > 1200) ? 210.0 : 182.0;
  document.getElementById("cellW").value = cellW.toFixed(1);
  recalcGeometryAndEff();
}

function handleCellCountChange() {
  recalcGeometryAndEff();
  calculateDiodeModel();
}

function recalcGeometryAndEff() {
  const lenMm = parseFloat(document.getElementById("lenMm").value) || 0;
  const widMm = parseFloat(document.getElementById("widMm").value) || 0;

  const modAreaM2 = (lenMm / 1000) * (widMm / 1000);
  document.getElementById("modArea").value = modAreaM2 > 0 ? modAreaM2.toFixed(3) : "";

  const cellW = parseFloat(document.getElementById("cellW").value) || 0;
  const cellH = parseFloat(document.getElementById("cellH").value) || 0;
  const cellAreaCm2 = (cellW * cellH) / 100;
  document.getElementById("cellAreaCm2").value = cellAreaCm2 > 0 ? cellAreaCm2.toFixed(1) : "";

  const ncels = parseInt(document.getElementById("ncels").value) || 72;
  const ncelp = parseInt(document.getElementById("ncelp").value) || 2;
  const totalCells = ncels * ncelp;

  const cellsTotalAreaM2 = (cellAreaCm2 / 10000) * totalCells;
  document.getElementById("cellsTotalArea").value = cellsTotalAreaM2 > 0 ? cellsTotalAreaM2.toFixed(3) : "";

  const pnom = parseFloat(document.getElementById("pnom").value) || 0;
  if (pnom > 0 && modAreaM2 > 0) {
    const modEffVal = (pnom / (modAreaM2 * 1000)) * 100;
    const curEffField = document.getElementById("stcEff");
    if (!curEffField.value || curEffField.dataset.autoCalculated === "true") {
      curEffField.value = modEffVal.toFixed(2);
      curEffField.dataset.autoCalculated = "true";
    }
  }
}

function renderBins() {
  const g = document.getElementById("binGrid");
  document.getElementById("binCount").innerText = bins.length + " STC Bins";

  if (!bins.length) {
    return g.innerHTML = '<span class="text-xs text-slate-500 italic">No STC bins detected. Add manually below.</span>';
  }

  g.innerHTML = "";
  bins.forEach((b, i) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.innerText = b.wp + " Wp";
    btn.className = "px-4 py-2 rounded-xl text-xs font-bold border transition cursor-pointer " + (i === sel ? "active-wp" : "bg-slate-950 border-slate-800 text-slate-200 hover:bg-slate-800");
    btn.onclick = () => selectBin(i);
    g.appendChild(btn);
  });
}

function selectBin(idx) {
  if (idx < 0 || idx >= bins.length) return;
  sel = idx;
  renderBins();

  const b = bins[idx];
  document.getElementById("pnom").value = b.wp.toFixed(1);
  document.getElementById("vmp").value = b.vmp.toFixed(2);
  document.getElementById("imp").value = b.imp.toFixed(2);
  document.getElementById("voc").value = b.voc.toFixed(2);
  document.getElementById("isc").value = b.isc.toFixed(2);

  const effField = document.getElementById("stcEff");
  if (b.eff) {
    effField.value = b.eff.toFixed(2);
    effField.dataset.autoCalculated = "false";
  } else {
    effField.dataset.autoCalculated = "true";
  }

  const mInput = document.getElementById("model");
  if (b.modelCode) {
    mInput.value = b.modelCode;
  } else {
    let currentTemplate = baseModelTemplate || mInput.value;
    currentTemplate = currentTemplate.replace(/[-_ ]?[0-9]{3}[wW]?$/i, "");
    mInput.value = currentTemplate + "-" + b.wp + "W";
  }

  calculateDiodeModel();
  checkAgreement();
  recalcGeometryAndEff();
}

function calculateDiodeModel() {
  const voc = +document.getElementById("voc").value || 49.0;
  const isc = +document.getElementById("isc").value || 18.0;
  const vmp = +document.getElementById("vmp").value || 41.0;
  const imp = +document.getElementById("imp").value || 17.0;
  const ncels = +document.getElementById("ncels").value || 66;
  const gamma = +document.getElementById("gamma").value || 1.055;

  const rshunt = Math.round(Math.min(1500, Math.max(800, (voc / Math.max(0.1, isc)) * 380)));
  const Vt = 0.025693;
  const a = ncels * gamma * Vt;

  const diffCurrent = Math.max(0.04, isc - imp);
  const safeRatio = Math.max(1.001, isc / diffCurrent);
  const rs = Math.max(0.08, Math.min(0.35, ((voc - vmp) - a * Math.log(safeRatio)) / Math.max(0.1, imp)));

  document.getElementById("rshunt").value = rshunt;
  document.getElementById("rserie").value = rs.toFixed(3);
}

function checkAgreement() {
  const p = +document.getElementById("pnom").value || 1;
  const c = (+document.getElementById("vmp").value) * (+document.getElementById("imp").value);
  const diff = Math.abs(c - p) / p * 100;
  const el = document.getElementById("pcalcDiff");
  el.innerText = diff <= 0.25 ? "Pnom Check: Optimal (Δ " + diff.toFixed(2) + "%)" : "Pnom Check: Δ " + diff.toFixed(2) + "%";
  el.className = diff <= 0.25 ? "text-[11px] text-emerald-400 font-semibold" : "text-[11px] text-amber-400 font-semibold";
}

function addManualWp() {
  const v = parseFloat(document.getElementById("manualWp").value);
  if (isNaN(v) || v <= 0) return alert("Enter valid Wp");

  const bv = bins.length ? bins[0].voc : 49.0;
  const bm = bins.length ? bins[0].vmp : 41.0;
  const baseP = bins.length ? bins[0].wp : v;
  const ratio = v / baseP;
  const cv = +(bm * (1 + (ratio - 1) * 0.25)).toFixed(2);
  const ci = +(v / cv).toFixed(2);

  const ex = bins.findIndex(b => b.wp === v);
  if (ex !== -1) {
    selectBin(ex);
  } else {
    bins.push({
      wp: v,
      vmp: cv,
      imp: ci,
      voc: +(bv * (1 + (ratio - 1) * 0.2)).toFixed(2),
      isc: +(ci * 1.055).toFixed(2),
      eff: null
    });
    bins.sort((a, b) => a.wp - b.wp);
    selectBin(bins.findIndex(b => b.wp === v));
  }

  document.getElementById("manualWp").value = "";
}

// PVsyst v7/v8 Clean Native PAN Output (Omitted custom IAM to prevent Fresnel warning)
function downloadPAN() {
  const rawMfg = document.getElementById("manufacturer").value.trim() || "SolarModule";
  const rawMod = document.getElementById("model").value.trim() || "Module";

  const mfg = rawMfg.replace(/[^a-zA-Z0-9 .,_-]/g, "").trim();
  const mod = rawMod.replace(/[^a-zA-Z0-9 ._-]/g, "").trim();

  const pnom = (+document.getElementById("pnom").value || 700).toFixed(1);
  const vmp = (+document.getElementById("vmp").value || 41.0).toFixed(2);
  const imp = (+document.getElementById("imp").value || 17.0).toFixed(3);
  const voc = (+document.getElementById("voc").value || 49.0).toFixed(2);
  const isc = (+document.getElementById("isc").value || 18.0).toFixed(3);

  const lenMm = +document.getElementById("lenMm").value || 2384;
  const widMm = +document.getElementById("widMm").value || 1303;
  const thkMm = +document.getElementById("thkMm").value || 33;
  const wt = (+document.getElementById("weight").value || 35.0).toFixed(3);

  const w = (widMm / 1000).toFixed(3);
  const h = (lenMm / 1000).toFixed(3);
  const depth = (thkMm / 1000).toFixed(3);

  const nCelS = parseInt(document.getElementById("ncels").value) || 66;
  const nCelP = parseInt(document.getElementById("ncelp").value) || 2;
  const cellTech = document.getElementById("cellTech").value;

  const cellW_m = ((+document.getElementById("cellW").value || 210.0) / 1000).toFixed(3);
  const cellH_m = ((+document.getElementById("cellH").value || 105.0) / 1000).toFixed(3);

  const rshunt = +document.getElementById("rshunt").value || 1000;
  const rserie = (+document.getElementById("rserie").value || 0.155).toFixed(3);
  const gamma = (+document.getElementById("gamma").value || 1.055).toFixed(3);

  const muIscPct = +document.getElementById("muIscPct").value || 0.045;
  const muVocPct = +document.getElementById("muVocPct").value || -0.250;
  const muPmpPct = +document.getElementById("muPmpPct").value || -0.300;

  const muIsc_mA = (isc * (muIscPct / 100) * 1000).toFixed(2);
  const muVoc_mV = (voc * (muVocPct / 100) * 1000).toFixed(1);

  const bif = (+document.getElementById("bifacial").value || 0.8).toFixed(3);
  const vmaxIec = document.getElementById("vmaxIec").value || "1500";
  const vmaxUl = document.getElementById("vmaxUl").value || "1500";

  const p1_p = (+pnom).toFixed(2);
  const p2_v = (voc * 0.984).toFixed(2);
  const p2_i = (isc * 0.794).toFixed(3);
  const p2_im = (imp * 0.802).toFixed(3);
  const p2_vm = (vmp * 0.987).toFixed(2);
  const p2_p = (p2_im * p2_vm).toFixed(2);

  const p3_v = (voc * 0.976).toFixed(2);
  const p3_i = (isc * 0.595).toFixed(3);
  const p3_im = (imp * 0.604).toFixed(3);
  const p3_vm = (vmp * 0.984).toFixed(2);
  const p3_p = (p3_im * p3_vm).toFixed(2);

  const p4_v = (voc * 0.959).toFixed(2);
  const p4_i = (isc * 0.397).toFixed(3);
  const p4_im = (imp * 0.406).toFixed(3);
  const p4_vm = (vmp * 0.976).toFixed(2);
  const p4_p = (p4_im * p4_vm).toFixed(2);

  const p5_v = (voc * 0.935).toFixed(2);
  const p5_i = (isc * 0.198).toFixed(3);
  const p5_im = (imp * 0.204).toFixed(3);
  const p5_vm = (vmp * 0.957).toFixed(2);
  const p5_p = (p5_im * p5_vm).toFixed(2);

  const panLines = [
    "PVObject_=pvModule",
    "  Version=7.4.7",
    "  Flags=$00908043",
    "",
    "  PVObject_Commercial=pvCommercial",
    "    Flags=$0041",
    `    Manufacturer=${mfg}`,
    `    Model=${mod}`,
    "    DataSource=Manufacturer Datasheet",
    `    Width=${w}`,
    `    Height=${h}`,
    `    Depth=${depth}`,
    `    Weight=${wt}`,
    "    NPieces=100",
    "  End of PVObject pvCommercial",
    "",
    `  Technol=${cellTech}`,
    `  NCelS=${nCelS}`,
    `  NCelP=${nCelP}`,
    "  NDiode=3",
    "  SubModuleLayout=slTwinHalfCells",
    "  FrontSurface=fsARCoating",
    "  GRef=1000",
    "  TRef=25.0",
    `  PNom=${pnom}`,
    "  PNomTolLow=0.00",
    "  PNomTolUp=3.00",
    `  BifacialityFactor=${bif}`,
    `  Isc=${isc}`,
    `  Voc=${voc}`,
    `  Imp=${imp}`,
    `  Vmp=${vmp}`,
    `  muISC=${muIsc_mA}`,
    `  muVocSpec=${muVoc_mV}`,
    `  muPmpReq=${muPmpPct}`,
    `  RShunt=${rshunt}`,
    `  Rp_0=${rshunt * 326}`,
    "  Rp_Exp=6.00",
    `  RSerie=${rserie}`,
    `  Gamma=${gamma}`,
    "  muGamma=-0.0003",
    `  VMaxIEC=${vmaxIec}`,
    `  VMaxUL=${vmaxUl}`,
    "  Absorb=0.90",
    "  ARev=3.200",
    "  BRev=-11998.800",
    "  RDiode=0.010",
    "  VRevDiode=-0.70",
    "  AirMassRef=1.500",
    `  CellWidth=${cellW_m}`,
    `  CellHeight=${cellH_m}`,
    "  SandiaAMCorr=50.000",
    "  RelEffic800=-1.04",
    "  RelEffic600=0.81",
    "  RelEffic400=0.62",
    "  RelEffic200=-0.82",
    "",
    "  OperPoints, list of=5 tOperPoint",
    `    Point_1=True,1000,25.0,0.00,${voc},${isc},${imp},${vmp},${p1_p}`,
    `    Point_2=True,800,25.0,-1.04,${p2_v},${p2_i},${p2_im},${p2_vm},${p2_p}`,
    `    Point_3=False,600,25.0,0.81,${p3_v},${p3_i},${p3_im},${p3_vm},${p3_p}`,
    `    Point_4=False,400,25.0,0.62,${p4_v},${p4_i},${p4_im},${p4_vm},${p4_p}`,
    `    Point_5=False,200,25.0,-0.82,${p5_v},${p5_i},${p5_im},${p5_vm},${p5_p}`,
    "  End of List OperPoints",
    "End of PVObject pvModule",
    ""
  ];

  const panData = panLines.join("\r\n");

  const buffer = new Uint8Array(panData.length);
  for (let i = 0; i < panData.length; i++) {
    buffer[i] = panData.charCodeAt(i) & 0xFF;
  }

  const fileName = `${mfg}_${mod}.PAN`.replace(/[/\\?%*:|"<> ]/g, "_");
  const blob = new Blob([buffer], { type: "application/octet-stream" });
  const aEl = document.createElement("a");
  aEl.href = URL.createObjectURL(blob);
  aEl.download = fileName;
  document.body.appendChild(aEl);
  aEl.click();
  document.body.removeChild(aEl);
}
