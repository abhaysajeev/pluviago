/**
 * Stock Lineage page — client controller.
 *
 * Responsibilities:
 *   - Debounced search → autocomplete via xcall
 *   - Selection / card click → fetch lineage, render lanes, draw SVG edges
 *   - URL state (?focus=<DocType>:<name>) for shareable views
 *   - Consumption log table
 *   - Hover edge highlighting
 */
(function () {
    "use strict";

    const API = {
        search:  "pluviago.pluviago_biotech.api.stock_lineage.search_batches",
        lineage: "pluviago.pluviago_biotech.api.stock_lineage.get_lineage",
    };

    const LANES = ["RMB", "SSB", "MED", "FMB", "PB", "HB", "EB"];

    const STATUS_TONE = {
        // green
        "Approved": "good", "Released": "good", "Passed": "good",
        "Harvested": "good", "Packed": "good", "Dispatched": "good",
        "Completed": "good",
        // amber
        "Pending": "warn", "Draft": "warn", "QC Pending": "warn",
        "Partially Used": "warn", "Used": "warn", "Processing": "warn",
        // red
        "Rejected": "bad", "Wasted": "bad", "Failed": "bad",
        "Disposed": "bad", "Exhausted": "bad", "Written Off (Loss)": "bad",
    };
    const toneFor = s => STATUS_TONE[s] || "info";

    // ---------- DOM refs ----------
    const root = document.querySelector(".sl-page");
    const searchInput = document.getElementById("sl-search");
    const searchResults = document.getElementById("sl-search-results");
    const clearBtn = document.getElementById("sl-clear");
    const laneGrid = document.getElementById("sl-lanes");
    const edgeSvg = document.getElementById("sl-edges");
    const emptyState = document.getElementById("sl-empty");
    const logSection = document.getElementById("sl-log-section");
    const logRows = document.getElementById("sl-log-rows");
    const logTarget = document.getElementById("sl-log-target");

    let currentLineage = null;          // last payload
    let activeResultIdx = -1;

    // ---------- utility ----------
    function escapeHtml(s) {
        if (s === null || s === undefined) return "";
        return String(s).replace(/[&<>"']/g, c => (
            { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
        ));
    }

    function formatQty(qty, uom) {
        if (qty === null || qty === undefined || qty === "") return "";
        const n = Number(qty);
        if (Number.isNaN(n)) return escapeHtml(String(qty));
        const formatted = Number.isInteger(n) ? n.toLocaleString()
                        : n.toLocaleString(undefined, { maximumFractionDigits: 3 });
        return `${formatted}${uom ? `<span class="sl-card-uom">${escapeHtml(uom)}</span>` : ""}`;
    }

    function debounce(fn, ms) {
        let t = null;
        return (...args) => {
            clearTimeout(t);
            t = setTimeout(() => fn(...args), ms);
        };
    }

    function call(method, args) {
        return new Promise((resolve, reject) => {
            frappe.call({
                method, args,
                callback: r => resolve(r.message),
                error: e => reject(e),
            });
        });
    }

    // ---------- search ----------
    const doSearch = debounce(async function (query) {
        if (!query || query.length < 2) {
            searchResults.hidden = true;
            return;
        }
        const rows = await call(API.search, { query });
        renderSearchResults(rows || []);
    }, 250);

    function renderSearchResults(rows) {
        activeResultIdx = -1;
        if (!rows.length) {
            searchResults.innerHTML = `<div class="sl-search-result"><span class="sl-search-label-cell">No matches.</span></div>`;
            searchResults.hidden = false;
            return;
        }
        searchResults.innerHTML = rows.map((r, i) => `
            <div class="sl-search-result" data-doctype="${escapeHtml(r.doctype)}"
                 data-name="${escapeHtml(r.name)}" data-idx="${i}">
                <span class="sl-search-lane">${escapeHtml(r.lane)}</span>
                <span>
                    <span class="sl-search-name">${escapeHtml(r.name)}</span>
                    ${r.label ? `<div class="sl-search-label-cell">${escapeHtml(r.label)}</div>` : ""}
                </span>
                <span class="sl-search-label-cell">${escapeHtml(r.status)}</span>
            </div>
        `).join("");
        searchResults.hidden = false;
    }

    searchInput.addEventListener("input", e => doSearch(e.target.value.trim()));
    searchInput.addEventListener("focus", e => {
        if (e.target.value.trim().length >= 2) searchResults.hidden = false;
    });

    searchInput.addEventListener("keydown", e => {
        const items = searchResults.querySelectorAll(".sl-search-result[data-doctype]");
        if (!items.length) return;
        if (e.key === "ArrowDown") {
            e.preventDefault();
            activeResultIdx = (activeResultIdx + 1) % items.length;
            updateActiveResult(items);
        } else if (e.key === "ArrowUp") {
            e.preventDefault();
            activeResultIdx = (activeResultIdx - 1 + items.length) % items.length;
            updateActiveResult(items);
        } else if (e.key === "Enter" && activeResultIdx >= 0) {
            e.preventDefault();
            items[activeResultIdx].click();
        } else if (e.key === "Escape") {
            searchResults.hidden = true;
        }
    });

    function updateActiveResult(items) {
        items.forEach((el, i) => el.classList.toggle("is-active", i === activeResultIdx));
        items[activeResultIdx].scrollIntoView({ block: "nearest" });
    }

    searchResults.addEventListener("click", e => {
        const row = e.target.closest(".sl-search-result[data-doctype]");
        if (!row) return;
        const dt = row.dataset.doctype;
        const name = row.dataset.name;
        loadLineage(dt, name, /*pushUrl=*/true);
        searchResults.hidden = true;
        searchInput.value = name;
    });

    document.addEventListener("click", e => {
        if (!e.target.closest(".sl-search-row")) searchResults.hidden = true;
    });

    clearBtn.addEventListener("click", () => {
        currentLineage = null;
        searchInput.value = "";
        clearBtn.hidden = true;
        renderLanes(null);
        history.pushState({}, "", window.location.pathname);
    });

    // ---------- lineage ----------
    async function loadLineage(doctype, name, pushUrl) {
        try {
            const payload = await call(API.lineage, { doctype, name });
            if (!payload) return;
            currentLineage = payload;
            renderLanes(payload);
            renderLog(payload);
            clearBtn.hidden = false;
            if (pushUrl) {
                const focus = `${doctype}:${name}`;
                const url = `${window.location.pathname}?focus=${encodeURIComponent(focus)}`;
                history.pushState({ focus }, "", url);
            }
        } catch (err) {
            frappe.msgprint({
                title: "Lineage error",
                message: (err && err.message) || "Failed to load lineage.",
                indicator: "red",
            });
        }
    }

    function renderLanes(payload) {
        // Clear existing lanes
        laneGrid.querySelectorAll(".sl-lane").forEach(l => { l.innerHTML = ""; });
        edgeSvg.innerHTML = "";

        if (!payload) {
            emptyState.hidden = false;
            logSection.hidden = true;
            return;
        }
        emptyState.hidden = true;

        for (const lane of LANES) {
            const laneEl = laneGrid.querySelector(`.sl-lane[data-lane="${lane}"]`);
            const cards = payload.lanes[lane] || [];
            laneEl.innerHTML = cards.map(card => renderCard(card)).join("");
        }

        // Draw edges on next frame so layout has settled
        requestAnimationFrame(() => drawEdges(payload.edges || []));
    }

    function renderCard(card) {
        const tone = toneFor(card.status);
        const isExpiring = (() => {
            if (!card.expiry_date) return false;
            const d = new Date(card.expiry_date);
            const today = new Date();
            const inDays = (d - today) / (1000 * 60 * 60 * 24);
            return inDays >= 0 && inDays <= 30;
        })();

        return `
            <div class="sl-card ${card.is_focal ? "is-focal" : ""}"
                 data-doctype="${escapeHtml(card.doctype)}"
                 data-name="${escapeHtml(card.name)}"
                 data-lane="${escapeHtml(card.lane)}"
                 title="${escapeHtml(card.doctype)}: ${escapeHtml(card.name)}">
                <div class="sl-card-name">${escapeHtml(card.name)}</div>
                ${card.label ? `<div class="sl-card-label">${escapeHtml(card.label)}</div>` : ""}
                <div class="sl-card-meta">
                    <span class="sl-card-qty">${formatQty(card.qty, card.uom)}</span>
                    ${card.status ? `<span class="sl-pill status-${tone}">${escapeHtml(card.status)}</span>` : ""}
                </div>
                ${isExpiring ? `<span class="sl-expiry-flag">Expires ${escapeHtml(card.expiry_date)}</span>` : ""}
            </div>
        `;
    }

    // Click any card → recentre
    laneGrid.addEventListener("click", e => {
        const cardEl = e.target.closest(".sl-card");
        if (!cardEl) return;
        const dt = cardEl.dataset.doctype;
        const name = cardEl.dataset.name;
        if (currentLineage && currentLineage.focal.doctype === dt && currentLineage.focal.name === name) {
            return;     // already focused
        }
        loadLineage(dt, name, true);
        searchInput.value = name;
    });

    // Hover card → highlight its edges
    laneGrid.addEventListener("mouseover", e => {
        const cardEl = e.target.closest(".sl-card");
        if (!cardEl) return;
        const key = `${cardEl.dataset.doctype}:${cardEl.dataset.name}`;
        edgeSvg.querySelectorAll(".sl-edge").forEach(p => {
            const f = p.dataset.from;
            const t = p.dataset.to;
            p.classList.toggle("is-highlight", f === key || t === key);
        });
    });
    laneGrid.addEventListener("mouseout", e => {
        if (e.target.closest(".sl-card")) {
            edgeSvg.querySelectorAll(".sl-edge.is-highlight").forEach(p => p.classList.remove("is-highlight"));
        }
    });

    // ---------- SVG edges ----------
    function drawEdges(edges) {
        const body = document.querySelector(".sl-flow-body");
        const bodyRect = body.getBoundingClientRect();
        edgeSvg.setAttribute("viewBox", `0 0 ${bodyRect.width} ${bodyRect.height}`);
        edgeSvg.setAttribute("width", bodyRect.width);
        edgeSvg.setAttribute("height", bodyRect.height);

        const ns = "http://www.w3.org/2000/svg";
        edgeSvg.innerHTML = "";

        // Pre-cache card right/left midpoints (relative to body)
        const cardCoords = new Map();
        body.querySelectorAll(".sl-card").forEach(card => {
            const r = card.getBoundingClientRect();
            const key = `${card.dataset.doctype}:${card.dataset.name}`;
            cardCoords.set(key, {
                left:   { x: r.left  - bodyRect.left, y: r.top - bodyRect.top + r.height / 2 },
                right:  { x: r.right - bodyRect.left, y: r.top - bodyRect.top + r.height / 2 },
            });
        });

        for (const edge of edges) {
            const fromKey = `${edge.from_dt}:${edge.from_name}`;
            const toKey   = `${edge.to_dt}:${edge.to_name}`;
            const from = cardCoords.get(fromKey);
            const to   = cardCoords.get(toKey);
            if (!from || !to) continue;

            const x1 = from.right.x;
            const y1 = from.right.y;
            const x2 = to.left.x;
            const y2 = to.left.y;
            const cx = (x1 + x2) / 2;
            const d = `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`;

            const path = document.createElementNS(ns, "path");
            path.setAttribute("d", d);
            path.setAttribute("class", "sl-edge");
            path.dataset.from = fromKey;
            path.dataset.to = toKey;
            edgeSvg.appendChild(path);
        }
    }

    window.addEventListener("resize", () => {
        if (currentLineage) drawEdges(currentLineage.edges || []);
    });

    // ---------- log ----------
    function renderLog(payload) {
        const target = `${payload.focal.doctype} · ${payload.focal.name}`;
        logTarget.textContent = target;

        const rows = payload.log || [];
        if (!rows.length) {
            logRows.innerHTML = `<tr><td colspan="7" class="sl-log-empty">No consumption events recorded for this batch.</td></tr>`;
        } else {
            logRows.innerHTML = rows.map(row => {
                const qty = Number(row.qty_change || 0);
                const qtyClass = qty < 0 ? "is-neg" : qty > 0 ? "is-pos" : "";
                const qtySign = qty > 0 ? "+" : "";
                const dt = row.source_doctype || "";
                const src = row.source_document || "";
                const srcCell = src
                    ? `<a href="/app/${encodeURIComponent(dt.toLowerCase().replace(/\s+/g, "-"))}/${encodeURIComponent(src)}" target="_blank">${escapeHtml(src)}</a><span class="sl-log-source-dt">${escapeHtml(dt)}</span>`
                    : "";
                const actionTone = (row.action === "Consumed") ? "info"
                                 : (row.action === "Reversed") ? "good"
                                 : "bad";
                const userShort = (row.performed_by || "").split("@")[0];
                const when = row.creation || "";
                const [whenDate, whenTime] = when ? [when.slice(0, 10), when.slice(11, 16)] : ["", ""];
                return `
                    <tr>
                        <td class="sl-col-when">
                            <span class="sl-log-date">${escapeHtml(whenDate)}</span>
                            <span class="sl-log-time">${escapeHtml(whenTime)}</span>
                        </td>
                        <td class="sl-col-material">
                            ${row.material_name ? `<span class="sl-log-material">${escapeHtml(row.material_name)}</span>` : ""}
                            ${row.raw_material_batch ? `<span class="sl-log-rmb">${escapeHtml(row.raw_material_batch)}</span>` : ""}
                        </td>
                        <td class="sl-num sl-log-qty ${qtyClass}">
                            ${qtySign}${qty.toLocaleString(undefined, { maximumFractionDigits: 3 })}<span class="sl-card-uom">&nbsp;${escapeHtml(row.uom || "")}</span>
                        </td>
                        <td class="sl-num sl-log-balance">${row.balance_after !== null && row.balance_after !== undefined
                            ? `${Number(row.balance_after).toLocaleString(undefined, { maximumFractionDigits: 3 })}<span class="sl-card-uom">&nbsp;${escapeHtml(row.uom || "")}</span>`
                            : ""}</td>
                        <td><span class="sl-pill status-${actionTone}">${escapeHtml(row.action || "")}</span></td>
                        <td class="sl-col-source">${srcCell}</td>
                        <td class="sl-log-by">${escapeHtml(userShort)}</td>
                    </tr>
                `;
            }).join("");
        }
        logSection.hidden = false;
    }

    // ---------- back / forward ----------
    window.addEventListener("popstate", () => {
        const params = new URLSearchParams(window.location.search);
        const focus = params.get("focus");
        if (focus) {
            const [dt, ...rest] = focus.split(":");
            const name = rest.join(":");
            loadLineage(dt, name, false);
            searchInput.value = name;
        } else {
            currentLineage = null;
            searchInput.value = "";
            clearBtn.hidden = true;
            renderLanes(null);
        }
    });

    // ---------- initial focus ----------
    function initialFocus() {
        const params = new URLSearchParams(window.location.search);
        const fromUrl = params.get("focus");
        const fromAttr = root && root.dataset.initialFocus;
        const focus = fromUrl || fromAttr;
        if (!focus) return;
        const [dt, ...rest] = focus.split(":");
        const name = rest.join(":");
        if (dt && name) {
            loadLineage(dt, name, !fromUrl);
            searchInput.value = name;
        }
    }
    initialFocus();
})();
