// app.js — Interactive germination analyzer frontend

// ── State ────────────────────────────────────────────────────────
const state = {
    images      : [],
    active      : null,
    corrections : {},
    baseImages  : {},
    zoom        : 1.0,
};

// ── DOM refs ─────────────────────────────────────────────────────
const uploadArea    = document.getElementById("upload-area");
const fileInput     = document.getElementById("file-input");
const imageList     = document.getElementById("image-list");
const canvas        = document.getElementById("annotation-canvas");
const ctx           = canvas.getContext("2d");
const canvasWrapper = document.getElementById("canvas-wrapper");
const canvasScaler  = document.getElementById("canvas-scaler");
const emptyState    = document.getElementById("empty-state");
const canvasToolbar = document.getElementById("canvas-toolbar");
const resultsPanel  = document.getElementById("results-panel");
const resultsBody   = document.getElementById("results-body");
const loading       = document.getElementById("loading");
const loadingText   = document.getElementById("loading-text");
const undoBtn       = document.getElementById("undo-btn");
const exportBtn     = document.getElementById("export-btn");
const zoomResetBtn  = document.getElementById("zoom-reset-btn");
const zoomLabel     = document.getElementById("zoom-label");

const statTotal      = document.getElementById("stat-total");
const statTotalModel = document.getElementById("stat-total-model");
const statGerm       = document.getElementById("stat-germ");
const statGermModel  = document.getElementById("stat-germ-model");
const statRate       = document.getElementById("stat-rate");
const statRateModel  = document.getElementById("stat-rate-model");
const statAggregate  = document.getElementById("stat-aggregate");

const TOOL_EMOJI = {
    missed_seed : "🎯",
    missed_germ : "💚",
    false_seed  : "🚫",
    false_germ  : "💔",
};

// ── Upload ────────────────────────────────────────────────────────
uploadArea.addEventListener("click", () => fileInput.click());
uploadArea.addEventListener("dragover", e => { e.preventDefault(); uploadArea.classList.add("drag-over"); });
uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("drag-over"));
uploadArea.addEventListener("drop", e => { e.preventDefault(); uploadArea.classList.remove("drag-over"); handleFiles(e.dataTransfer.files); });
fileInput.addEventListener("change", e => handleFiles(e.target.files));

async function handleFiles(files) {
    if (!files.length) return;
    showLoading("Analyzing images...");
    const formData = new FormData();
    for (const f of files) formData.append("images", f);

    try {
        const resp    = await fetch("/upload", { method: "POST", body: formData });
        const results = await resp.json();

        for (const r of results) {
            if (r.error) { console.warn(r.name, r.error); continue; }
            const img = new Image();
            img.src = "data:image/png;base64," + r.annotated_b64;
            state.baseImages[r.name] = img;
            if (!state.corrections[r.name]) state.corrections[r.name] = [];
            const idx = state.images.findIndex(i => i.name === r.name);
            if (idx >= 0) state.images[idx] = r;
            else state.images.push(r);
        }

        renderImageList();
        renderResultsTable();
        updateAggregateRate();
        if (results.length > 0 && !results[0].error) selectImage(results[0].name);

    } catch(e) {
        alert("Upload failed: " + e.message);
    } finally {
        hideLoading();
    }
}

// ── Image list ────────────────────────────────────────────────────
function renderImageList() {
    imageList.innerHTML = "";
    for (const r of state.images) {
        const div = document.createElement("div");
        div.className = "image-item" + (r.name === state.active ? " active" : "");
        div.dataset.name = r.name;
        const nCorr = (state.corrections[r.name] || []).length;
        div.innerHTML = `
            <div class="img-name">${r.name}</div>
            <div class="img-stats">Model: ${r.model_total} / ${r.model_germinated} / ${r.model_rate}%</div>
            <div class="img-stats">
                <span class="corrected">Corrected: ${r.corrected_total} / ${r.corrected_germinated} / ${r.corrected_rate}%</span>
                ${nCorr > 0 ? ` <span>(${nCorr} correction${nCorr > 1 ? "s" : ""})</span>` : ""}
            </div>
        `;
        div.addEventListener("click", () => selectImage(r.name));
        imageList.appendChild(div);
    }
}

// ── Select image ──────────────────────────────────────────────────
function selectImage(name) {
    state.active = name;
    resetZoom();
    renderImageList();

    const r = state.images.find(i => i.name === name);
    if (!r) return;

    emptyState.style.display    = "none";
    canvasScaler.style.display  = "inline-block";
    canvasToolbar.style.display = "flex";
    resultsPanel.style.display  = "block";

    const img = state.baseImages[name];
    if (img.complete) drawCanvas(name);
    else img.onload = () => drawCanvas(name);

    updateStats(r);
    renderResultsTable();
}

// ── Canvas drawing ────────────────────────────────────────────────
function drawCanvas(name) {
    const img = state.baseImages[name];
    canvas.width  = img.naturalWidth;
    canvas.height = img.naturalHeight;

    // Size the scaler to match canvas natural size
    canvasScaler.style.width  = `${canvas.width}px`;
    canvasScaler.style.height = `${canvas.height}px`;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);

    const corrections = state.corrections[name] || [];
    ctx.font         = `${Math.max(10, canvas.width * 0.008)}px serif`;
    ctx.textAlign    = "center";
    ctx.textBaseline = "middle";
    for (const c of corrections) {
        ctx.fillText(TOOL_EMOJI[c.type], c.x, c.y);
    }
}

// ── Zoom ──────────────────────────────────────────────────────────
// We scale the canvasScaler div using transform: scale()
// transform-origin is top left so scroll math is predictable
function applyZoom() {
    canvasScaler.style.transform = `scale(${state.zoom})`;
    // Expand the scaler's footprint so the wrapper scrolls correctly
    canvasScaler.style.marginRight  = `${canvas.width  * (state.zoom - 1)}px`;
    canvasScaler.style.marginBottom = `${canvas.height * (state.zoom - 1)}px`;
    zoomLabel.textContent = `${Math.round(state.zoom * 100)}%`;
}

function resetZoom() {
    state.zoom = 1.0;
    canvasScaler.style.transform    = "";
    canvasScaler.style.marginRight  = "";
    canvasScaler.style.marginBottom = "";
    canvasWrapper.scrollLeft = 0;
    canvasWrapper.scrollTop  = 0;
    zoomLabel.textContent = "100%";
}

zoomResetBtn.addEventListener("click", resetZoom);

// Ctrl+Scroll — zoom toward cursor
canvasWrapper.addEventListener("wheel", e => {
    if (!e.ctrlKey) return;
    e.preventDefault();

    const wrapperRect = canvasWrapper.getBoundingClientRect();
    const mouseX = e.clientX - wrapperRect.left;
    const mouseY = e.clientY - wrapperRect.top;

    // Point in content space before zoom
    const contentX = (canvasWrapper.scrollLeft + mouseX) / state.zoom;
    const contentY = (canvasWrapper.scrollTop  + mouseY) / state.zoom;

    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    state.zoom  = Math.min(8, Math.max(0.5, state.zoom * delta));

    applyZoom();

    // After zoom, scroll so same content point stays under cursor
    canvasWrapper.scrollLeft = contentX * state.zoom - mouseX;
    canvasWrapper.scrollTop  = contentY * state.zoom - mouseY;

}, { passive: false });

// ── Canvas coordinate helper (zoom-aware) ─────────────────────────
function getCanvasCoords(e) {
    // Canvas is scaled via transform — get position relative to unscaled canvas
    const scalerRect = canvasScaler.getBoundingClientRect();
    const x = (e.clientX - scalerRect.left) / state.zoom;
    const y = (e.clientY - scalerRect.top)  / state.zoom;
    return { x, y };
}

// ── Left click — add ──────────────────────────────────────────────
canvas.addEventListener("click", async e => {
    if (!state.active) return;
    const {x, y} = getCanvasCoords(e);
    const tool   = e.shiftKey ? "missed_germ" : "missed_seed";
    await sendCorrection(state.active, tool, x, y);
});

// ── Right click — remove ──────────────────────────────────────────
canvas.addEventListener("contextmenu", async e => {
    e.preventDefault();
    if (!state.active) return;
    const {x, y} = getCanvasCoords(e);
    const tool   = e.shiftKey ? "false_germ" : "false_seed";
    await sendCorrection(state.active, tool, x, y);
});

// ── Keyboard ──────────────────────────────────────────────────────
document.addEventListener("keydown", async e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "z") {
        e.preventDefault();
        await sendUndo(state.active);
    }
});

undoBtn.addEventListener("click", async () => await sendUndo(state.active));

// ── Server communication ──────────────────────────────────────────
async function sendCorrection(name, action, x, y) {
    if (!name) return;
    const correction = { type: action, x, y };
    state.corrections[name].push(correction);
    drawCanvas(name);

    try {
        const resp = await fetch("/correct", {
            method  : "POST",
            headers : { "Content-Type": "application/json" },
            body    : JSON.stringify({ name, action, x, y }),
        });
        const data = await resp.json();
        updateFromServer(name, data);
    } catch(e) {
        state.corrections[name].pop();
        drawCanvas(name);
        console.error("Correction failed:", e);
    }
}

async function sendUndo(name) {
    if (!name || !(state.corrections[name] || []).length) return;
    state.corrections[name].pop();
    drawCanvas(name);

    try {
        const resp = await fetch("/correct", {
            method  : "POST",
            headers : { "Content-Type": "application/json" },
            body    : JSON.stringify({ name, action: "undo" }),
        });
        const data = await resp.json();
        updateFromServer(name, data);
    } catch(e) {
        console.error("Undo failed:", e);
    }
}

function updateFromServer(name, data) {
    const r = state.images.find(i => i.name === name);
    if (!r) return;
    r.corrected_total      = data.corrected_total;
    r.corrected_germinated = data.corrected_germinated;
    r.corrected_rate       = data.corrected_rate;
    if (name === state.active) updateStats(r);
    renderImageList();
    renderResultsTable();
    updateAggregateRate();
}

// ── Stats ─────────────────────────────────────────────────────────
function updateStats(r) {
    statTotal.textContent      = r.corrected_total;
    statTotalModel.textContent = `model: ${r.model_total}`;
    statGerm.textContent       = r.corrected_germinated;
    statGermModel.textContent  = `model: ${r.model_germinated}`;
    statRate.textContent       = r.corrected_rate + "%";
    statRateModel.textContent  = `model: ${r.model_rate}%`;
}

function updateAggregateRate() {
    if (state.images.length < 2) { statAggregate.textContent = "—"; return; }
    const totalGerm  = state.images.reduce((s, r) => s + r.corrected_germinated, 0);
    const totalSeeds = state.images.reduce((s, r) => s + r.corrected_total, 0);
    statAggregate.textContent = totalSeeds > 0
        ? `${(totalGerm / totalSeeds * 100).toFixed(1)}%`
        : "0%";
}

// ── Results table ─────────────────────────────────────────────────
function renderResultsTable() {
    resultsBody.innerHTML = "";
    for (const r of state.images) {
        const tr = document.createElement("tr");
        if (r.name === state.active) tr.classList.add("active-row");
        tr.innerHTML = `
            <td>${r.name}</td>
            <td class="model-val">${r.model_total}</td>
            <td class="model-val">${r.model_germinated}</td>
            <td class="model-val">${r.model_rate}%</td>
            <td class="corrected-val">${r.corrected_total}</td>
            <td class="corrected-val">${r.corrected_germinated}</td>
            <td class="corrected-val">${r.corrected_rate}%</td>
        `;
        tr.addEventListener("click", () => selectImage(r.name));
        resultsBody.appendChild(tr);
    }
}

// ── CSV Export ────────────────────────────────────────────────────
exportBtn.addEventListener("click", async () => {
    try {
        const resp    = await fetch("/export");
        const rows    = await resp.json();
        const headers = Object.keys(rows[0]);
        const csv     = [
            headers.join(","),
            ...rows.map(r => headers.map(h => `"${r[h]}"`).join(","))
        ].join("\n");
        const url  = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
        const a    = document.createElement("a");
        const ts   = new Date().toISOString().slice(0,19).replace(/[:T]/g, "-");
        a.href = url; a.download = `germination_results_${ts}.csv`;
        a.click(); URL.revokeObjectURL(url);
    } catch(e) { alert("Export failed: " + e.message); }
});

// ── Loading ───────────────────────────────────────────────────────
function showLoading(text) { loadingText.textContent = text; loading.classList.add("visible"); }
function hideLoading()      { loading.classList.remove("visible"); }
