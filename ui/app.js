(function () {
    "use strict";

    /* =============================================================
       BOOT / RE-ENTRY
       Streamlit can re-render the page (data refresh, reconnect).
       Tear down the previous instance's listeners and portals first.
       ============================================================= */

    if (window.__IPOT && typeof window.__IPOT.destroy === "function") {
        try { window.__IPOT.destroy(); } catch (error) { /* ignore */ }
    }

    const root = document.getElementById("ipot");
    const dataNode = document.getElementById("ipot-data");

    if (!root || !dataNode) {
        return;
    }

    let DATA;

    try {
        DATA = JSON.parse(dataNode.textContent);
    } catch (error) {
        console.error("IPO Tracker: could not read data", error);
        return;
    }

    // Decorative orbit (echoes the logo's ring). It arrives from the
    // loader because Streamlit's sanitizer strips inline SVG.
    const orbitSlot = root.querySelector(".orbit-slot");
    const assets = typeof ASSETS !== "undefined" && ASSETS ? ASSETS : {};

    if (orbitSlot && assets.orbit) {
        orbitSlot.outerHTML = assets.orbit;
    }

    const ac = new AbortController();
    const timers = new Set();
    const portals = [];
    const observers = [];

    const on = (target, type, fn, options) =>
        target.addEventListener(type, fn, Object.assign({ signal: ac.signal }, options || {}));

    const later = (fn, ms) => {
        const id = setTimeout(() => { timers.delete(id); fn(); }, ms);
        timers.add(id);
        return id;
    };

    const every = (fn, ms) => {
        const id = setInterval(fn, ms);
        timers.add(id);
        return id;
    };

    window.__IPOT = {
        destroy() {
            ac.abort();
            timers.forEach((id) => { clearTimeout(id); clearInterval(id); });
            observers.forEach((observer) => observer.disconnect());
            portals.forEach((node) => node.remove());
            document.documentElement.classList.remove("ipot-locked");
        },
    };

    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const reduced = () => motionQuery.matches;
    const EASE = "cubic-bezier(.2,.8,.2,1)";

    // Streamlit may mount the page more than once while loading, so the
    // intro is keyed to "not yet completed on this page", not "first run".
    window.__IPOT_BOOTS = (window.__IPOT_BOOTS || 0) + 1;
    window.__IPOT_BOOTED = true;

    const firstBoot = !window.__IPOT_INTRO_DONE;
    const INTRO = firstBoot && !reduced();
    const bootAt = performance.now();
    const INTRO_SETTLE = 1150;

    if (INTRO) {
        later(() => {
            root.classList.remove("intro");
            window.__IPOT_INTRO_DONE = true;
        }, 3500);
    } else {
        root.classList.remove("intro");
        window.__IPOT_INTRO_DONE = true;
    }

    const introRemaining = () =>
        INTRO ? Math.max(0, INTRO_SETTLE - (performance.now() - bootAt)) : 0;

    const $ = (selector, scope) => (scope || root).querySelector(selector);
    const $$ = (selector, scope) => Array.from((scope || root).querySelectorAll(selector));

    /* =============================================================
       DOM + ICON HELPERS
       Text is always set as text (never HTML), so scraped company
       names can't inject markup. Icon SVGs are static constants.
       ============================================================= */

    function h(tag, props) {
        const el = document.createElement(tag);
        const kids = Array.prototype.slice.call(arguments, 2);

        if (props) {
            Object.keys(props).forEach((key) => {
                const value = props[key];

                if (value === null || value === undefined || value === false) {
                    return;
                }

                if (key === "class") {
                    el.className = value;
                } else if (key === "style") {
                    el.style.cssText = value;
                } else if (key.slice(0, 2) === "on" && typeof value === "function") {
                    on(el, key.slice(2), value);
                } else if (value === true) {
                    el.setAttribute(key, "");
                } else {
                    el.setAttribute(key, String(value));
                }
            });
        }

        (function append(list) {
            list.forEach((kid) => {
                if (kid === null || kid === undefined || kid === false) {
                    return;
                }

                if (Array.isArray(kid)) {
                    append(kid);
                } else {
                    el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
                }
            });
        })(kids);

        return el;
    }

    const PATHS = {
        search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6"/>',
        x: '<path d="M6 6l12 12M18 6 6 18"/>',
        chev: '<path d="m6 9 6 6 6-6"/>',
        sort: '<path d="M7 4v16M3.5 16.5 7 20l3.5-3.5M17 20V4M13.5 7.5 17 4l3.5 3.5"/>',
        check: '<path d="M5 12.5 10 17.5 19.5 7"/>',
        arrow: '<path d="M7 17 17 7M8.5 7H17v8.5"/>',
        right: '<path d="M5 12h14M13 6l6 6-6 6"/>',
        info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5.5M12 7.6h.01"/>',
        grid: '<rect x="4" y="4" width="6.5" height="6.5" rx="1.6"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="1.6"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="1.6"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1.6"/>',
        star: '<path d="M12 3.6l2.5 5.2 5.7.8-4.1 4 1 5.7L12 16.6l-5.1 2.7 1-5.7-4.1-4 5.7-.8z"/>',
        layers: '<path d="m12 3.5 8.5 4.75L12 13 3.5 8.25z"/><path d="m3.5 12.25 8.5 4.75 8.5-4.75"/><path d="m3.5 16.25 8.5 4.75 8.5-4.75"/>',
        calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
        rupee: '<path d="M7 4.5h10M7 9h10M9.5 4.5c3.2 0 4.6 1.9 4.6 4.5s-1.9 4.5-5.1 4.5H7l7.5 6"/>',
        trend: '<path d="m3.5 16.5 5.5-5.5 4 4 7.5-7.5"/><path d="M15 7.5h5.5V13"/>',
        searchx: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.6-3.6M8.8 8.8l4.4 4.4M13.2 8.8l-4.4 4.4"/>',
        inbox: '<path d="M4 13.5h4.2l1.8 2.7h4l1.8-2.7H20"/><path d="M6.2 5.5h11.6l2.2 8v4.7a1.8 1.8 0 0 1-1.8 1.8H5.8A1.8 1.8 0 0 1 4 18.2v-4.7z"/>',
        reset: '<path d="M4 12a8 8 0 1 0 2.4-5.7L4 8.6"/><path d="M4 4v4.6h4.6"/>',
    };

    const FILLED = {
        up: '<path d="M12 6.5 18.5 16h-13z"/>',
        down: '<path d="M12 17.5 5.5 8h13z"/>',
    };

    function svgMarkup(name) {
        if (FILLED[name]) {
            return '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">' + FILLED[name] + "</svg>";
        }

        return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (PATHS[name] || "") + "</svg>";
    }

    function icon(name, extraClass) {
        const span = document.createElement("span");
        span.className = "ico" + (extraClass ? " " + extraClass : "");
        span.setAttribute("aria-hidden", "true");
        span.innerHTML = svgMarkup(name);
        return span;
    }

    $$("[data-icon]").forEach((el) => { el.innerHTML = svgMarkup(el.dataset.icon); });

    /* =============================================================
       FORMATTING
       ============================================================= */

    const nf0 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 0 });
    const nf2 = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });

    const money = (value) => {
        if (value === null || value === undefined || Number.isNaN(value)) {
            return "—";
        }

        const abs = Math.abs(value);
        return (value < 0 ? "−₹" : "₹") + (Number.isInteger(abs) ? nf0 : nf2).format(abs);
    };

    const signedPct = (value, digits) => {
        if (value === null || value === undefined || Number.isNaN(value)) {
            return "—";
        }

        const d = digits === undefined ? 2 : digits;
        const rounded = Number(Math.abs(value).toFixed(d));
        const sign = rounded === 0 ? "" : value > 0 ? "+" : "−";
        return sign + rounded.toFixed(d) + "%";
    };

    const times = (value) =>
        value === null || value === undefined ? "—" : value.toFixed(2) + "×";

    const integer = (value) => String(Math.round(value));

    const band = (ipo) => {
        if (ipo.priceLow === null || ipo.priceLow === undefined) {
            return ipo.priceText || "—";
        }

        return ipo.priceLow === ipo.priceHigh
            ? money(ipo.priceHigh)
            : money(ipo.priceLow) + " – " + money(ipo.priceHigh);
    };

    const plural = (n, one, many) => (n === 1 ? one : many);

    /* ---------- dates (all in IST) ---------- */

    const DAY_MS = 864e5;

    const dayNum = (iso) => (iso
        ? Math.round(Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) / DAY_MS)
        : null);

    const istToday = () => new Intl.DateTimeFormat("en-CA", {
        timeZone: "Asia/Kolkata",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
    }).format(new Date());

    const TODAY = dayNum(istToday());

    const fmtDay = (iso) => (iso
        ? new Date(dayNum(iso) * DAY_MS).toLocaleDateString("en-GB", {
            day: "2-digit",
            month: "short",
            timeZone: "UTC",
        })
        : null);

    function statusOf(ipo) {
        if (ipo.section === "closed") {
            return { cls: "closed", text: "Closed" };
        }

        if (ipo.section === "preapply") {
            const d = ipo.open ? dayNum(ipo.open) - TODAY : null;

            if (d === null) {
                return { cls: "pre", text: "Pre-apply" };
            }

            return {
                cls: "pre",
                text: d <= 0
                    ? "Pre-apply · opens today"
                    : d === 1
                        ? "Pre-apply · opens tomorrow"
                        : "Pre-apply · opens in " + d + " days",
            };
        }

        if (!ipo.close) {
            return { cls: "open", text: "Open" };
        }

        const d = dayNum(ipo.close) - TODAY;

        if (d < 0) {
            return { cls: "closed", text: "Closed" };
        }

        if (d === 0) {
            return { cls: "last", text: "Last day · closes today", last: true };
        }

        if (d === 1) {
            return { cls: "soon", text: "Closes tomorrow" };
        }

        return { cls: "open", text: "Closes in " + d + " days" };
    }

    function timelineProgress(ipo) {
        const o = dayNum(ipo.open);
        const c = dayNum(ipo.close);
        const a = dayNum(ipo.allot);
        const t = TODAY;

        if (o === null || c === null || t <= o) {
            return 0;
        }

        if (t < c) {
            return 0.5 * (t - o) / Math.max(1, c - o);
        }

        if (t === c || a === null) {
            return 0.5;
        }

        if (t < a) {
            return 0.5 + 0.5 * (t - c) / Math.max(1, a - c);
        }

        return 1;
    }

    /* =============================================================
       NUMBER COUNT-UP  (700ms, ease-out cubic, rAF, in place)
       ============================================================= */

    const easeOut = (p) => 1 - Math.pow(1 - p, 3);

    function tween(el, to, fmt, options) {
        const opts = options || {};

        if (el._raf) {
            cancelAnimationFrame(el._raf);
            el._raf = 0;
        }

        if (to === null || to === undefined || Number.isNaN(to)) {
            el._val = null;
            el.textContent = fmt(null);
            return;
        }

        const from = opts.from !== undefined ? opts.from : el._val;
        const token = (el._tweenToken || 0) + 1;
        el._tweenToken = token;

        if (from === null || from === undefined || reduced() || from === to || document.hidden) {
            el._val = to;
            el.textContent = fmt(to);
            return;
        }

        const duration = opts.duration || 700;
        const delay = opts.delay || 0;
        const start = performance.now() + delay;

        el._val = from;
        el.textContent = fmt(from);

        const settle = () => {
            if (el._tweenToken !== token) return;
            if (el._raf) cancelAnimationFrame(el._raf);
            el._raf = 0;
            el._val = to;
            el.textContent = fmt(to);
        };

        const step = (now) => {
            if (el._tweenToken !== token) return;

            const p = Math.min(1, Math.max(0, (now - start) / duration));
            const value = from + (to - from) * easeOut(p);

            el._val = value;
            el.textContent = fmt(value);

            if (p < 1) {
                el._raf = requestAnimationFrame(step);
            } else {
                settle();
            }
        };

        el._raf = requestAnimationFrame(step);

        // Safety net: if frames stall (background tab), still land on the value.
        later(settle, delay + duration + 250);
    }

    /* =============================================================
       DATA MODEL
       ============================================================= */

    const IPOS = DATA.ipos || [];
    const byId = new Map(IPOS.map((ipo, index) => {
        ipo._i = index;
        return [ipo.id, ipo];
    }));
    const LIVE = IPOS.filter((ipo) => ipo.section !== "closed");

    const SECTIONS = ["apply", "preapply", "closed"].map((key) => {
        const el = root.querySelector('[data-section="' + key + '"]');

        return {
            key,
            el,
            list: $("[data-list]", el),
            empty: $("[data-empty]", el),
            count: $("[data-count]", el),
            countWord: $("[data-count-word]", el),
            items: IPOS.filter((ipo) => ipo.section === key),
        };
    });

    const state = { q: "", type: "all", sort: "closing" };

    const TYPE_LABEL = { all: "All", mainboard: "Mainboard", sme: "SME" };

    function matches(ipo, ignoreType) {
        const q = state.q.trim().toLowerCase();

        if (q && ipo.name.toLowerCase().indexOf(q) === -1) {
            return false;
        }

        if (!ignoreType && state.type !== "all" && String(ipo.type).toLowerCase() !== state.type) {
            return false;
        }

        return true;
    }

    const nullsLast = (a, b, dir) => {
        const an = a === null || a === undefined;
        const bn = b === null || b === undefined;

        if (an && bn) return 0;
        if (an) return 1;
        if (bn) return -1;
        return dir * (a - b);
    };

    const SORTS = {
        closing: (a, b, section) => nullsLast(dayNum(a.close), dayNum(b.close), section === "closed" ? -1 : 1),
        gmp: (a, b) => nullsLast(a.gmpPct, b.gmpPct, -1),
        subs: (a, b) => nullsLast(a.subs, b.subs, -1),
        name: (a, b) => a.name.localeCompare(b.name, "en", { sensitivity: "base" }),
    };

    const SORT_OPTIONS = [
        { value: "closing", label: "Closing soonest" },
        { value: "gmp", label: "Highest GMP %" },
        { value: "subs", label: "Most subscribed" },
        { value: "name", label: "Name A–Z" },
    ];

    function visibleFor(section) {
        const sorter = SORTS[state.sort];

        return section.items
            .filter((ipo) => matches(ipo))
            .sort((a, b) => sorter(a, b, section.key) || a._i - b._i);
    }

    /* =============================================================
       BUILDERS
       ============================================================= */

    const typeTag = (type) => {
        const key = String(type).toLowerCase();
        return h("span", { class: "tag tag--" + (key === "sme" ? "sme" : "mainboard") }, type);
    };

    const statusBadge = (ipo) => {
        const status = statusOf(ipo);
        return h("span", { class: "status status--" + status.cls }, h("i"), status.text);
    };

    function deltaNode(ipo) {
        if (ipo.gmpChange === null || ipo.gmpChange === undefined || ipo.gmpChange === 0) {
            return null;
        }

        const up = ipo.gmpChange > 0;
        const when = ipo.gmpChangeAt ? fmtDay(ipo.gmpChangeAt.slice(0, 10)) : null;

        return h(
            "div",
            { class: "card-gmp-delta" },
            h(
                "span",
                { class: "delta " + (up ? "up" : "down") },
                icon(up ? "up" : "down"),
                money(Math.abs(ipo.gmpChange)),
                when ? h("span", { class: "delta-when" }, "since " + when) : null
            )
        );
    }

    function meterNode(subs) {
        const value = Math.max(0.04, Math.min(1, (Math.log10(Math.max(subs, 0.1)) + 1) / (Math.log10(300) + 1)));
        const level = subs < 1 ? " is-low" : subs >= 10 ? " is-high" : "";

        return h(
            "div",
            { class: "meter" + level, "aria-hidden": "true" },
            h("span", { class: "meter-fill", style: "--v:" + value.toFixed(3) })
        );
    }

    function fact(label, value, note, extra, isNone) {
        return h(
            "div",
            null,
            h("dt", null, label),
            h("dd", { class: isNone ? "is-none" : null }, value, note ? h("span", { class: "fact-note" }, note) : null),
            extra || null
        );
    }

    const INVESTORGAIN_HOME = "https://www.investorgain.com/report/ipo-gmp-live/331/";

    // GMP button: this IPO's InvestorGain page, else the live GMP table.
    function gmpSourceLink(ipo) {
        return { label: "InvestorGain", href: ipo.investorgain || INVESTORGAIN_HOME };
    }

    function buildCard(ipo) {
        const hasGmp = ipo.gmp !== null && ipo.gmp !== undefined;
        const hasPct = ipo.gmpPct !== null && ipo.gmpPct !== undefined;
        const dir = !hasPct ? "flat" : ipo.gmpPct > 0 ? "up" : ipo.gmpPct < 0 ? "down" : "flat";

        const gmpSub = h(
            "div",
            { class: "card-gmp-sub" },
            hasPct
                ? h("span", { class: "pill pill--" + dir }, signedPct(ipo.gmpPct))
                : h("span", { class: "card-gmp-note" }, hasGmp ? "% not quoted" : "Not quoted yet")
        );

        const top = h(
            "div",
            { class: "card-top" },
            h(
                "div",
                { class: "card-id" },
                h("div", { class: "card-tags" }, typeTag(ipo.type), statusBadge(ipo)),
                h("h3", { class: "card-name" }, ipo.name)
            ),
            h(
                "div",
                { class: "card-gmp" },
                h("div", { class: "card-gmp-label" }, "GMP"),
                h("div", { class: "card-gmp-value num" + (hasGmp ? "" : " is-none") }, hasGmp ? money(ipo.gmp) : "—"),
                gmpSub,
                deltaNode(ipo)
            )
        );

        const isPre = ipo.section === "preapply";
        const hasSubs = ipo.subs !== null && ipo.subs !== undefined;

        const facts = h(
            "dl",
            { class: "facts" },
            fact("Price band", band(ipo)),
            fact(
                "Est. listing",
                money(ipo.estListing),
                ipo.estListing !== null && ipo.estListing !== undefined ? "on current GMP" : "awaiting GMP",
                null,
                ipo.estListing === null || ipo.estListing === undefined
            ),
            hasSubs
                ? fact("Subscribed", times(ipo.subs), null, meterNode(ipo.subs))
                : fact("Subscribed", isPre ? "Not open" : "—", isPre ? "bidding opens soon" : "not reported yet", null, true)
        );

        const progress = timelineProgress(ipo);
        const steps = [
            ["Opens", ipo.open, ipo.openText],
            ["Closes", ipo.close, ipo.closeText],
            ["Allotment", ipo.allot, ipo.allotText],
        ];

        const timeline = h(
            "div",
            { class: "tl" },
            h("div", { class: "tl-track", "aria-hidden": "true" },
                h("span", { class: "tl-fill", style: "--p:" + progress.toFixed(3) })),
            h(
                "ol",
                { class: "tl-steps" },
                steps.map((step) => {
                    const d = dayNum(step[1]);
                    const cls = d === null ? "" : d < TODAY ? " is-done" : d === TODAY ? " is-now" : "";

                    return h(
                        "li",
                        { class: "tl-step" + cls },
                        h("span", { class: "tl-dot", "aria-hidden": "true" }),
                        h("span", { class: "tl-k" }, step[0]),
                        h("span", { class: "tl-v" }, d === TODAY ? "Today" : (fmtDay(step[1]) || step[2] || "TBA"))
                    );
                })
            )
        );

        const actions = h(
            "div",
            { class: "card-actions" },
            h("a", {
                class: "card-link",
                href: gmpSourceLink(ipo).href,
                target: "_blank",
                rel: "noopener",
            }, gmpSourceLink(ipo).label, icon("arrow")),
            h("a", {
                class: "card-link",
                href: ipo.groww || "https://groww.in/ipo",
                target: "_blank",
                rel: "noopener",
            }, "Groww", icon("arrow"))
        );

        return h("article", {
            class: "card",
            id: "card-" + ipo.id,
            "data-id": ipo.id,
            "aria-label": ipo.name,
        }, top, facts, timeline, actions);
    }

    function rowCell(label, value, extraClass, small) {
        return h(
            "div",
            { class: "row-cell" },
            h("span", { class: "row-k" }, label),
            h("span", { class: "row-v" + (extraClass ? " " + extraClass : "") }, value, small ? h("small", null, small) : null)
        );
    }

    function buildRow(ipo) {
        const perf = ipo.perf;
        const hasPerf = perf !== null && perf !== undefined;
        const hasGmp = ipo.gmp !== null && ipo.gmp !== undefined;

        return h(
            "article",
            { class: "row", id: "card-" + ipo.id, "data-id": ipo.id, "aria-label": ipo.name },
            h("div", { class: "row-name" }, h("strong", null, ipo.name), typeTag(ipo.type)),
            rowCell("Closed", fmtDay(ipo.close) || ipo.closeText),
            rowCell("Allotment", fmtDay(ipo.allot) || ipo.allotText || "TBA"),
            rowCell("Issue price", band(ipo)),
            rowCell("Subscribed", times(ipo.subs), ipo.subs === null || ipo.subs === undefined ? "is-none" : ""),
            rowCell(
                "GMP",
                hasGmp ? money(ipo.gmp) : "—",
                hasGmp ? "" : "is-none",
                hasGmp && ipo.gmpPct !== null && ipo.gmpPct !== undefined ? signedPct(ipo.gmpPct) : null
            ),
            h(
                "div",
                { class: "row-cell" },
                h("span", { class: "row-k" }, "Listing"),
                hasPerf
                    ? h("span", { class: "pill pill--" + (perf > 0 ? "up" : perf < 0 ? "down" : "flat") }, signedPct(perf))
                    : h("span", { class: "row-v is-none" }, "Not listed yet")
            ),
            h("a", {
                class: "row-link",
                href: gmpSourceLink(ipo).href,
                target: "_blank",
                rel: "noopener",
                "aria-label": "Open " + ipo.name + " on " + gmpSourceLink(ipo).label,
            }, icon("arrow"))
        );
    }

    const elById = new Map();

    SECTIONS.forEach((section) => {
        section.items.forEach((ipo) => {
            const el = section.key === "closed" ? buildRow(ipo) : buildCard(ipo);
            elById.set(ipo.id, el);
            section.list.appendChild(el);
        });
    });

    /* =============================================================
       FLIP LAYOUT — filter / sort without anything jumping.
       Staying items glide to their new spot, leaving items fade out
       where they stood, arriving items rise in.
       ============================================================= */

    let pendingLeaves = [];
    const PIN_PROPS = ["position", "left", "top", "width", "height", "margin", "pointerEvents", "zIndex"];

    function finishLeaves() {
        const list = pendingLeaves;
        pendingLeaves = [];
        list.forEach((fn) => fn());
    }

    function layout(plan, animate) {
        finishLeaves();

        const all = Array.from(elById.values());
        const shown = all.filter((el) => !el.hidden);
        const first = new Map();
        const parentFirst = new Map();

        if (animate) {
            shown.forEach((el) => first.set(el, el.getBoundingClientRect()));
            SECTIONS.forEach((section) => parentFirst.set(section.list, section.list.getBoundingClientRect()));
        }

        all.forEach((el) => {
            el.getAnimations().forEach((anim) => {
                const isTransition = typeof CSSTransition !== "undefined" && anim instanceof CSSTransition;

                if (!isTransition) {
                    anim.cancel();
                }
            });
        });

        const next = new Set();
        plan.forEach((entry) => entry.els.forEach((el) => next.add(el)));

        const leaving = shown.filter((el) => !next.has(el));
        const entering = [];

        leaving.forEach((el) => {
            if (!animate) {
                el.hidden = true;
                return;
            }

            const rect = first.get(el);
            const parentRect = parentFirst.get(el.parentElement);

            Object.assign(el.style, {
                position: "absolute",
                left: rect.left - parentRect.left + "px",
                top: rect.top - parentRect.top + "px",
                width: rect.width + "px",
                height: rect.height + "px",
                margin: "0",
                pointerEvents: "none",
                zIndex: "0",
            });
        });

        plan.forEach((entry) => {
            entry.els.forEach((el) => {
                if (el.hidden) {
                    el.hidden = false;
                    entering.push(el);
                }

                entry.section.list.appendChild(el);
            });

            leaving
                .filter((el) => el.parentElement === entry.section.list)
                .forEach((el) => entry.section.list.appendChild(el));
        });

        if (!animate) {
            return;
        }

        next.forEach((el) => {
            if (entering.indexOf(el) !== -1) {
                return;
            }

            const before = first.get(el);

            if (!before) {
                return;
            }

            const after = el.getBoundingClientRect();
            const dx = before.left - after.left;
            const dy = before.top - after.top;

            if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) {
                return;
            }

            el.animate(
                [{ transform: "translate(" + dx + "px," + dy + "px)" }, { transform: "translate(0,0)" }],
                { duration: 640, easing: EASE }
            );
        });

        entering.forEach((el, index) => {
            el.animate(
                [
                    { opacity: 0, transform: "translateY(18px) scale(.985)" },
                    { opacity: 1, transform: "translateY(0) scale(1)" },
                ],
                { duration: 600, delay: 140 + Math.min(index, 6) * 45, easing: EASE, fill: "backwards" }
            );
        });

        leaving.forEach((el) => {
            const anim = el.animate(
                [
                    { opacity: 1, transform: "scale(1)" },
                    { opacity: 0, transform: "scale(.96)" },
                ],
                { duration: 360, easing: EASE, fill: "forwards" }
            );

            let done = false;

            const finish = () => {
                if (done) return;
                done = true;
                anim.cancel();
                el.hidden = true;
                PIN_PROPS.forEach((prop) => { el.style[prop] = ""; });
            };

            anim.onfinish = finish;
            pendingLeaves.push(finish);
        });
    }

    /* =============================================================
       EMPTY STATES
       ============================================================= */

    const EMPTY_COPY = {
        apply: ["No IPOs are open for bidding right now.", "New issues show up here the moment applications open."],
        preapply: ["Nothing in pre-apply right now.", "Upcoming issues appear here once pre-application opens."],
        closed: ["No recently closed IPOs.", "Closed issues appear here for reference."],
    };

    const SECTION_NOUN = {
        apply: "open IPOs",
        preapply: "pre-apply IPOs",
        closed: "recently closed IPOs",
    };

    function setEmpty(section, isEmpty) {
        const filtered = state.q.trim() !== "" || state.type !== "all";
        const box = $(".empty", section.empty);

        if (isEmpty) {
            let title;
            let text;

            if (filtered) {
                const q = state.q.trim();
                title = "No " + SECTION_NOUN[section.key]
                    + (q ? " match “" + q + "”" : "")
                    + (state.type !== "all" ? (q ? " in " : " in ") + TYPE_LABEL[state.type] : "")
                    + ".";
                text = "Try a different name, or widen the type filter.";
            } else {
                title = EMPTY_COPY[section.key][0];
                text = EMPTY_COPY[section.key][1];
            }

            box.replaceChildren(
                h("span", { class: "empty-ico" }, icon(filtered ? "searchx" : "inbox")),
                h("div", null, h("p", { class: "empty-title" }, title), h("p", { class: "empty-text" }, text)),
                filtered
                    ? h("button", { class: "btn btn-ghost", type: "button", onclick: () => resetFilters(true) },
                        icon("reset"), "Clear filters")
                    : null
            );
        }

        section.empty.classList.toggle("is-open", isEmpty);
        section.empty.inert = !isEmpty;
        section.el.classList.toggle("is-empty", isEmpty);
    }

    /* =============================================================
       KPIs / COUNTS
       ============================================================= */

    const kpi = (key) => $('[data-kpi="' + key + '"]');
    const kpiValue = (key) => $("[data-value]", kpi(key));

    function kpiNumbers(visible) {
        const apply = visible.apply;
        const live = visible.apply.concat(visible.preapply);
        const quoted = live.filter((ipo) => ipo.gmpPct !== null && ipo.gmpPct !== undefined);

        return {
            apply: apply.length,
            preapply: visible.preapply.length,
            today: apply.filter((ipo) => dayNum(ipo.close) === TODAY).length,
            avg: quoted.length ? quoted.reduce((sum, ipo) => sum + ipo.gmpPct, 0) / quoted.length : null,
            quoted: quoted.length,
        };
    }

    const fmtAvg = (value) => signedPct(value, 1);

    function renderKpis(numbers, intro) {
        const set = (key, value, fmt, i) => {
            if (intro) {
                tween(kpiValue(key), value, fmt, { from: 0, delay: 900 + i * 70 });
            } else {
                tween(kpiValue(key), value, fmt);
            }
        };

        set("apply", numbers.apply, integer, 0);
        set("preapply", numbers.preapply, integer, 1);
        set("today", numbers.today, integer, 2);
        set("avg", numbers.avg, fmtAvg, 3);

        kpi("today").classList.toggle("has-alert", numbers.today > 0);
        $("[data-sub]", kpi("avg")).textContent = numbers.quoted
            ? "across " + numbers.quoted + " quoted " + plural(numbers.quoted, "IPO", "IPOs")
            : "no GMP quotes in view";
    }

    const segButtons = $$("#seg button");

    function renderSegCounts() {
        const pool = IPOS.filter((ipo) => matches(ipo, true));
        const counts = {
            all: pool.length,
            mainboard: pool.filter((ipo) => String(ipo.type).toLowerCase() === "mainboard").length,
            sme: pool.filter((ipo) => String(ipo.type).toLowerCase() === "sme").length,
        };

        segButtons.forEach((button) => {
            tween($(".seg-count", button), counts[button.dataset.value], integer);
        });
    }

    /* =============================================================
       UPDATE
       ============================================================= */

    function update(options) {
        const opts = options || {};
        const animate = opts.animate !== false && !reduced();
        const visible = {};

        const plan = SECTIONS.map((section) => {
            const list = visibleFor(section);
            visible[section.key] = list;
            return { section, list, els: list.map((ipo) => elById.get(ipo.id)) };
        });

        layout(plan, animate);

        plan.forEach((entry) => {
            tween(entry.section.count, entry.list.length, integer);
            entry.section.countWord.textContent = plural(entry.list.length, "IPO", "IPOs");
            setEmpty(entry.section, entry.list.length === 0);
        });

        renderKpis(kpiNumbers(visible), false);
        renderSegCounts();
        placeThumb(true);

        return visible;
    }

    let updateTimer = 0;

    function scheduleUpdate() {
        clearTimeout(updateTimer);
        timers.delete(updateTimer);
        updateTimer = later(() => update(), 140);
    }

    /* =============================================================
       SPOTLIGHT + EYEBROW
       ============================================================= */

    function buildSpotlight() {
        const box = $("#spotlight");
        const quoted = LIVE.filter((ipo) => ipo.gmpPct !== null && ipo.gmpPct !== undefined);
        const top = quoted.slice().sort((a, b) => b.gmpPct - a.gmpPct)[0]
            || LIVE.slice().sort((a, b) => nullsLast(dayNum(a.close), dayNum(b.close), 1))[0];

        if (!top) {
            box.hidden = true;
            return null;
        }

        const isTopGmp = top.gmpPct !== null && top.gmpPct !== undefined;
        const pct = h("span", { class: "spot-pct num" + (isTopGmp && top.gmpPct < 0 ? " is-down" : "") },
            isTopGmp ? signedPct(top.gmpPct) : money(top.gmp));

        box.replaceChildren(
            h("p", { class: "spot-kicker" }, icon("star"), isTopGmp ? "Highest GMP right now" : "Closing next"),
            h("h3", { class: "spot-name" }, top.name),
            h("div", { class: "spot-meta" }, typeTag(top.type), statusBadge(top)),
            h("div", { class: "spot-figure" }, pct, h("span", { class: "spot-cap" }, isTopGmp ? "grey-market premium" : "GMP")),
            h(
                "dl",
                { class: "spot-facts" },
                h("div", null, h("dt", null, "GMP"), h("dd", { class: "num" }, money(top.gmp))),
                h("div", null, h("dt", null, "Price band"), h("dd", { class: "num" }, band(top))),
                h("div", null, h("dt", null, "Est. listing"), h("dd", { class: "num" }, money(top.estListing)))
            ),
            h("button", { class: "spot-cta", type: "button", onclick: () => focusIpo(top.id) },
                "View this IPO", icon("right"))
        );

        if (isTopGmp && INTRO) {
            tween(pct, top.gmpPct, (v) => signedPct(v), { from: 0, delay: 1050 });
        }

        return top;
    }

    function renderEyebrow() {
        const count = $("#eyebrow-count");
        $("#eyebrow-word").textContent = plural(LIVE.length, "IPO", "IPOs");

        if (INTRO) {
            tween(count, LIVE.length, integer, { from: 0, delay: 250 });
        } else {
            tween(count, LIVE.length, integer);
        }
    }

    /* =============================================================
       TICKER
       ============================================================= */

    const tickerTrack = $("#ticker-track");

    function buildTicker() {
        const items = LIVE.slice().sort((a, b) => nullsLast(a.gmpPct, b.gmpPct, -1) || a._i - b._i);

        if (!items.length) {
            $("#ticker").hidden = true;
            return;
        }

        const makeTick = (ipo, clone) => {
            const hasPct = ipo.gmpPct !== null && ipo.gmpPct !== undefined;
            const dir = !hasPct ? "none" : ipo.gmpPct < 0 ? "down" : "up";

            return h(
                "button",
                {
                    class: "tick",
                    type: "button",
                    tabindex: clone ? "-1" : null,
                    "aria-hidden": clone ? "true" : null,
                    onclick: () => focusIpo(ipo.id),
                },
                h("span", { class: "tick-name" }, ipo.name),
                h("span", { class: "tick-type" }, String(ipo.type).toLowerCase() === "sme" ? "SME" : "MB"),
                h("span", { class: "tick-gmp" }, ipo.gmp !== null && ipo.gmp !== undefined ? money(ipo.gmp) : "GMP —"),
                h("span", { class: "tick-pct " + dir }, hasPct ? signedPct(ipo.gmpPct) : "")
            );
        };

        // One "run" must be wider than the screen; then the run is
        // duplicated so translating by -50% loops seamlessly.
        const sequence = items.slice();
        tickerTrack.replaceChildren.apply(tickerTrack, items.map((ipo) => makeTick(ipo, false)));

        while (tickerTrack.scrollWidth < window.innerWidth * 1.15 && sequence.length < 96) {
            items.forEach((ipo) => {
                sequence.push(ipo);
                tickerTrack.append(makeTick(ipo, true));
            });
        }

        sequence.forEach((ipo) => tickerTrack.append(makeTick(ipo, true)));

        sizeTicker();
    }

    function sizeTicker() {
        const half = tickerTrack.scrollWidth / 2;
        tickerTrack.style.setProperty("--ticker-dur", Math.max(20, half / 46).toFixed(1) + "s");
    }

    /* =============================================================
       STATUS CHIP (data freshness)
       ============================================================= */

    const chip = $("#status-chip");

    function renderStatus() {
        const fetched = Date.parse(DATA.fetchedAt);
        const mins = Math.max(0, Math.round((Date.now() - fetched) / 60000));
        let text;

        if (!Number.isFinite(mins)) {
            text = "Updated";
        } else if (mins < 1) {
            text = "Updated just now";
        } else if (mins < 60) {
            text = "Updated " + mins + " min ago";
        } else if (mins < 48 * 60) {
            const hours = Math.round(mins / 60);
            text = "Updated " + hours + " " + plural(hours, "hr", "hrs") + " ago";
        } else {
            const days = Math.round(mins / 1440);
            text = "Updated " + days + " days ago";
        }

        $("#status-text").textContent = text;
        // The updater runs on GitHub's (best-effort) schedule, so a few
        // hours is normal: green under 3h, amber under a day, red beyond.
        chip.classList.toggle("is-stale", mins >= 180 && mins < 1440);
        chip.classList.toggle("is-old", mins >= 1440);

        $("#status-pop").replaceChildren(
            "Last updated ", h("b", null, DATA.fetchedText || "—"),
            ". Updated automatically as new data becomes available."
        );
    }

    $("#footer-updated").textContent = DATA.fetchedText || "—";

    /* =============================================================
       SCROLL HELPERS
       ============================================================= */

    const toolbar = $("#toolbar");

    function scrollToNode(node) {
        const rootRect = root.getBoundingClientRect();
        const rect = node.getBoundingClientRect();
        const offset = toolbar.offsetHeight + 22;
        const top = root.scrollTop + rect.top - rootRect.top - offset;

        root.scrollTo({ top: Math.max(0, top), behavior: reduced() ? "auto" : "smooth" });
    }

    function flash(node) {
        node.classList.remove("is-flash");
        void node.offsetWidth;
        node.classList.add("is-flash");
        later(() => node.classList.remove("is-flash"), 1700);
    }

    function revealNow(node) {
        if (node.classList.contains("is-reveal")) {
            node.classList.remove("is-reveal");
            if (revealObserver) revealObserver.unobserve(node);
        }
    }

    function focusIpo(id) {
        const node = elById.get(id);

        if (!node) {
            return;
        }

        if (node.hidden || !matches(byId.get(id))) {
            resetFilters(false);
        }

        revealNow(node);

        later(() => {
            scrollToNode(node);
            later(() => flash(node), reduced() ? 0 : 520);
        }, 30);
    }

    /* =============================================================
       SEARCH
       ============================================================= */

    const searchInput = $("#search");
    const searchWrap = $("#search-wrap");

    function setQuery(value, immediate) {
        searchInput.value = value;
        searchWrap.classList.toggle("has-value", value !== "");
        state.q = value;

        if (immediate) {
            update();
        } else {
            scheduleUpdate();
        }
    }

    on(searchInput, "input", () => setQuery(searchInput.value, false));

    on(searchInput, "keydown", (event) => {
        if (event.key === "Escape" && searchInput.value) {
            event.preventDefault();
            event.stopPropagation();
            setQuery("", true);
        }
    });

    on($("#search-clear"), "click", (event) => {
        event.preventDefault();
        setQuery("", true);
        searchInput.focus();
    });

    const isTypingTarget = (target) =>
        target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);

    on(document, "keydown", (event) => {
        if (event.key === "/" && !isTypingTarget(event.target) && !openModal && !event.metaKey && !event.ctrlKey) {
            event.preventDefault();
            searchInput.focus();
        }
    });

    /* =============================================================
       SEGMENTED TYPE FILTER
       ============================================================= */

    const seg = $("#seg");
    const thumb = $(".seg-thumb", seg);

    function placeThumb(animate) {
        const active = segButtons.find((button) => button.dataset.value === state.type);

        if (!active) return;

        if (!animate) seg.classList.add("no-anim");

        thumb.style.width = active.offsetWidth + "px";
        thumb.style.transform = "translateX(" + active.offsetLeft + "px)";

        if (!animate) {
            void thumb.offsetWidth;
            seg.classList.remove("no-anim");
        }
    }

    function setType(value, focus) {
        if (state.type === value) return;

        state.type = value;

        segButtons.forEach((button) => {
            const checked = button.dataset.value === value;
            button.setAttribute("aria-checked", String(checked));
            button.tabIndex = checked ? 0 : -1;

            if (checked && focus) button.focus();
        });

        update();
    }

    segButtons.forEach((button) => {
        button.tabIndex = button.dataset.value === state.type ? 0 : -1;
        on(button, "click", () => setType(button.dataset.value, false));
    });

    on(seg, "keydown", (event) => {
        const keys = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 };

        if (!(event.key in keys)) return;

        event.preventDefault();
        const index = segButtons.findIndex((button) => button.dataset.value === state.type);
        const next = segButtons[(index + keys[event.key] + segButtons.length) % segButtons.length];
        setType(next.dataset.value, true);
    });

    function resetFilters(animate) {
        searchInput.value = "";
        searchWrap.classList.remove("has-value");
        state.q = "";
        state.type = "all";

        segButtons.forEach((button) => {
            const checked = button.dataset.value === "all";
            button.setAttribute("aria-checked", String(checked));
            button.tabIndex = checked ? 0 : -1;
        });

        update({ animate: animate });
    }

    /* =============================================================
       CUSTOM DROPDOWN (sort) — portalled, flips upward when short
       on space, same open/close animation both ways.
       ============================================================= */

    const sortButton = $("#sort-btn");
    const sortValue = $("#sort-value");

    const menu = h("div", {
        class: "ipot-portal ipot-menu",
        id: "ipot-sort-menu",
        role: "listbox",
        tabindex: "-1",
        "aria-label": "Sort IPOs",
        inert: true,
    });

    menu.append(h("p", { class: "ipot-menu-label" }, "Sort by"));

    const optionNodes = SORT_OPTIONS.map((option) => h(
        "div",
        {
            class: "ipot-option",
            role: "option",
            id: "ipot-sort-" + option.value,
            "data-value": option.value,
            "aria-selected": String(option.value === state.sort),
        },
        icon("check"),
        h("span", null, option.label)
    ));

    optionNodes.forEach((node) => menu.append(node));
    document.body.appendChild(menu);
    portals.push(menu);

    let menuOpen = false;
    let activeIndex = 0;
    let menuToken = 0;

    function setActive(index) {
        activeIndex = (index + optionNodes.length) % optionNodes.length;
        optionNodes.forEach((node, i) => node.classList.toggle("is-active", i === activeIndex));
        menu.setAttribute("aria-activedescendant", optionNodes[activeIndex].id);
    }

    function placeMenu() {
        const rect = sortButton.getBoundingClientRect();
        const width = Math.max(rect.width, 220);
        menu.style.minWidth = width + "px";

        const height = menu.offsetHeight;
        const below = window.innerHeight - rect.bottom - 12;
        const above = rect.top - 12;
        const up = below < height + 8 && above > below;

        menu.classList.toggle("is-up", up);

        const left = Math.min(Math.max(12, rect.right - width), window.innerWidth - width - 12);
        menu.style.left = left + "px";
        menu.style.top = (up ? rect.top - height - 8 : rect.bottom + 8) + "px";
    }

    function openMenu() {
        if (menuOpen) return;

        menuOpen = true;
        menuToken += 1;
        placeMenu();
        menu.inert = false;
        menu.classList.add("is-open");
        sortButton.setAttribute("aria-expanded", "true");
        setActive(SORT_OPTIONS.findIndex((option) => option.value === state.sort));
        menu.focus({ preventScroll: true });
    }

    function closeMenu(refocus) {
        if (!menuOpen) return;

        menuOpen = false;
        menu.classList.remove("is-open");
        sortButton.setAttribute("aria-expanded", "false");

        const token = ++menuToken;
        later(() => { if (token === menuToken) menu.inert = true; }, 320);

        if (refocus) sortButton.focus({ preventScroll: true });
    }

    function chooseSort(value) {
        closeMenu(true);

        if (value === state.sort) return;

        state.sort = value;
        const label = SORT_OPTIONS.find((option) => option.value === value).label;
        sortValue.textContent = label;
        sortButton.setAttribute("aria-label", "Sort: " + label);
        optionNodes.forEach((node) => node.setAttribute("aria-selected", String(node.dataset.value === value)));

        later(() => update(), 60);
    }

    sortButton.setAttribute("aria-label", "Sort: " + sortValue.textContent);

    on(sortButton, "click", () => (menuOpen ? closeMenu(true) : openMenu()));

    on(sortButton, "keydown", (event) => {
        if (event.key === "ArrowDown" || event.key === "ArrowUp") {
            event.preventDefault();
            openMenu();
        }
    });

    optionNodes.forEach((node, index) => {
        on(node, "pointermove", () => setActive(index));
        on(node, "click", () => chooseSort(node.dataset.value));
    });

    on(menu, "keydown", (event) => {
        if (event.key === "ArrowDown") { event.preventDefault(); setActive(activeIndex + 1); }
        else if (event.key === "ArrowUp") { event.preventDefault(); setActive(activeIndex - 1); }
        else if (event.key === "Home") { event.preventDefault(); setActive(0); }
        else if (event.key === "End") { event.preventDefault(); setActive(optionNodes.length - 1); }
        else if (event.key === "Enter" || event.key === " ") { event.preventDefault(); chooseSort(optionNodes[activeIndex].dataset.value); }
        else if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); closeMenu(true); }
        else if (event.key === "Tab") { closeMenu(false); }
    });

    on(document, "pointerdown", (event) => {
        if (menuOpen && !menu.contains(event.target) && !sortButton.contains(event.target)) {
            closeMenu(false);
        }
    }, { capture: true });

    on(root, "scroll", () => { if (menuOpen) placeMenu(); }, { passive: true });

    /* =============================================================
       MODALS — portalled; panel rises in from translateY(28px)
       scale(.96) and closes as the exact reverse.
       ============================================================= */

    let openModal = null;

    function createModal(config) {
        const wrap = h("div", {
            class: "ipot-portal ipot-modal" + (config.wide ? " is-wide" : ""),
            id: config.id,
            inert: true,
        });

        const backdrop = h("div", { class: "ipot-modal-backdrop" });
        const closeButton = h("button", { class: "ipot-modal-close", type: "button", "aria-label": "Close" }, icon("x"));

        const head = h(
            "div",
            { class: "ipot-modal-head" },
            config.withMark ? h("img", { src: root.dataset.mark, alt: "", width: "113", height: "128" }) : null,
            h(
                "div",
                { class: "ipot-modal-titles" },
                h("p", { class: "ipot-modal-kicker" }, config.kicker),
                h("h2", { class: "ipot-modal-title", id: config.id + "-title" }, config.title)
            ),
            closeButton
        );

        const body = h("div", { class: "ipot-modal-body" });
        const panel = h("div", {
            class: "ipot-modal-panel",
            role: "dialog",
            "aria-modal": "true",
            "aria-labelledby": config.id + "-title",
            tabindex: "-1",
        }, head, body);

        let foot = null;

        if (config.footButton) {
            foot = h(
                "div",
                { class: "ipot-modal-foot" },
                h("button", { class: "btn btn-gold", type: "button", onclick: () => api.close() }, config.footButton)
            );
            panel.append(foot);
        }

        wrap.append(backdrop, panel);
        document.body.appendChild(wrap);
        portals.push(wrap);

        let lastFocus = null;
        let token = 0;

        const api = {
            body,
            open() {
                if (openModal === api) return;
                if (openModal) openModal.close(true);
                if (menuOpen) closeMenu(false);

                if (config.onOpen) config.onOpen(body);

                lastFocus = document.activeElement;
                token += 1;
                wrap.inert = false;
                body.scrollTop = 0;
                void wrap.offsetWidth;
                wrap.classList.add("is-open");
                root.classList.add("is-locked");
                openModal = api;
                later(() => panel.focus({ preventScroll: true }), 40);
            },
            close(silent) {
                if (openModal !== api) return;

                openModal = null;
                wrap.classList.remove("is-open");
                root.classList.remove("is-locked");

                const mine = ++token;
                later(() => { if (mine === token) wrap.inert = true; }, 400);

                if (!silent && lastFocus && lastFocus.focus && document.contains(lastFocus)) {
                    lastFocus.focus({ preventScroll: true });
                }

                if (config.onClose) config.onClose();
            },
        };

        on(closeButton, "click", () => api.close());
        on(backdrop, "click", () => api.close());
        on(wrap, "click", (event) => { if (event.target === wrap) api.close(); });

        on(wrap, "keydown", (event) => {
            if (event.key === "Escape") {
                event.preventDefault();
                api.close();
                return;
            }

            if (event.key !== "Tab") return;

            const focusables = $$('a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])', panel)
                .filter((node) => node.offsetParent !== null);

            if (!focusables.length) return;

            const firstNode = focusables[0];
            const lastNode = focusables[focusables.length - 1];

            if (event.shiftKey && (document.activeElement === firstNode || document.activeElement === panel)) {
                event.preventDefault();
                lastNode.focus();
            } else if (!event.shiftKey && document.activeElement === lastNode) {
                event.preventDefault();
                firstNode.focus();
            }
        });

        config.build(body);
        return api;
    }

    /* ---------- Welcome ---------- */

    const welcome = createModal({
        id: "ipot-welcome",
        kicker: "Welcome",
        title: ["Welcome to ", h("em", null, "IPO Tracker")],
        withMark: true,
        footButton: "Understood",
        build(body) {
            const item = (name, text) => h("div", { class: "w-item" }, icon(name), h("span", null, text));

            body.append(
                h(
                    "section",
                    { class: "w-block" },
                    h("p", { class: "w-label" }, "What you can track"),
                    h(
                        "div",
                        { class: "w-grid" },
                        item("trend", "Current & upcoming IPOs"),
                        item("layers", "Mainboard & SME IPOs"),
                        item("calendar", "Application & allotment dates"),
                        item("rupee", "Issue price & GMP prices")
                    )
                ),
                h(
                    "section",
                    { class: "w-block" },
                    h("p", { class: "w-label" }, "About the data"),
                    h(
                        "p",
                        { class: "w-text" },
                        "IPO data is sourced from ",
                        h("a", { href: "https://groww.in/ipo", target: "_blank", rel: "noopener" }, "Groww"),
                        ", while GMP data is sourced from ",
                        h("a", { href: INVESTORGAIN_HOME, target: "_blank", rel: "noopener" }, "InvestorGain"),
                        " (Chittorgarh's GMP site)."
                    ),
                    h("p", { class: "w-text" }, "Please note that GMP and other IPO information can change throughout the day."),
                    h("p", { class: "w-text" }, "Information displayed on this website is provided for informational purposes.")
                ),
                h(
                    "section",
                    { class: "w-block" },
                    h("p", { class: "w-label" }, "Disclaimer"),
                    h(
                        "div",
                        { class: "w-callout" },
                        "IPO Tracker is an independent informational project and ",
                        h("strong", null, "is not investment advice or a recommendation to apply for or avoid any IPO"),
                        ". Please verify important information with official sources before making any investment decision."
                    )
                )
            );
        },
        onClose() {
            try { sessionStorage.setItem("ipot-welcome-seen", "1"); } catch (error) { /* storage blocked */ }
        },
    });

    /* ---------- Quick overview (always the full, unfiltered list) ---------- */

    const overview = createModal({
        id: "ipot-overview",
        kicker: "At a glance",
        title: ["Quick ", h("em", null, "overview")],
        wide: true,
        build() { /* filled on open so it is always current */ },
        onOpen(body) {
            const groups = [
                ["Apply now", "apply", "Closes"],
                ["Pre-apply", "preapply", "Closes"],
                ["Recently closed", "closed", "Closed"],
            ];

            body.replaceChildren.apply(body, groups.map((group) => {
                const items = IPOS.filter((ipo) => ipo.section === group[1]);

                const table = items.length
                    ? h(
                        "table",
                        { class: "qo-table" },
                        h("thead", null, h("tr", null,
                            h("th", null, "Company"),
                            h("th", null, "Type"),
                            h("th", null, "GMP"),
                            h("th", null, "GMP %"),
                            h("th", null, group[2]))),
                        h("tbody", null, items.map((ipo) => {
                            const hasPct = ipo.gmpPct !== null && ipo.gmpPct !== undefined;
                            const go = () => {
                                overview.close(true);
                                later(() => focusIpo(ipo.id), reduced() ? 0 : 380);
                            };

                            return h(
                                "tr",
                                {
                                    tabindex: "0",
                                    onclick: go,
                                    onkeydown: (event) => {
                                        if (event.key === "Enter" || event.key === " ") {
                                            event.preventDefault();
                                            go();
                                        }
                                    },
                                },
                                h("td", null, ipo.name),
                                h("td", null, ipo.type),
                                h("td", { class: ipo.gmp === null || ipo.gmp === undefined ? "none" : "" }, money(ipo.gmp)),
                                h("td", { class: !hasPct ? "none" : ipo.gmpPct < 0 ? "down" : ipo.gmpPct > 0 ? "up" : "" }, signedPct(ipo.gmpPct)),
                                h("td", null, fmtDay(ipo.close) || ipo.closeText)
                            );
                        }))
                    )
                    : h("p", { class: "qo-empty" }, "No IPOs here right now.");

                return h(
                    "section",
                    { class: "qo-group" },
                    h("div", { class: "qo-head" },
                        h("h3", null, group[0]),
                        h("span", { class: "section-count" }, items.length + " " + plural(items.length, "IPO", "IPOs"))),
                    table
                );
            }));
        },
    });

    on($("#btn-overview"), "click", () => overview.open());
    on($("#btn-about"), "click", () => welcome.open());

    on($("#brand"), "click", (event) => {
        event.preventDefault();
        root.scrollTo({ top: 0, behavior: reduced() ? "auto" : "smooth" });
    });

    $$(".kpi[data-jump]").forEach((tile) => {
        on(tile, "click", () => {
            const target = document.getElementById(tile.dataset.jump);
            if (target) scrollToNode(target);
        });
    });

    /* =============================================================
       STICKY TOOLBAR STATE
       ============================================================= */

    const stuckObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            const rootTop = root.getBoundingClientRect().top;
            toolbar.classList.toggle("is-stuck", !entry.isIntersecting && entry.boundingClientRect.top < rootTop + 1);
        });
    }, { root, threshold: 0 });

    stuckObserver.observe($("#toolbar-sentinel"));
    observers.push(stuckObserver);

    /* =============================================================
       SCROLL REVEAL (first visit only, brand-new elements only)
       ============================================================= */

    let revealObserver = null;

    if (firstBoot && !reduced() && "IntersectionObserver" in window) {
        elById.forEach((node) => node.classList.add("is-reveal"));

        revealObserver = new IntersectionObserver((entries) => {
            const incoming = entries
                .filter((entry) => entry.isIntersecting)
                .map((entry) => entry.target)
                .sort((a, b) => a.getBoundingClientRect().top - b.getBoundingClientRect().top
                    || a.getBoundingClientRect().left - b.getBoundingClientRect().left);

            const base = introRemaining();

            incoming.forEach((node, index) => {
                const delay = Math.round(base + Math.min(index, 7) * 80);

                revealObserver.unobserve(node);
                node.style.transitionDelay = delay + "ms";
                node.style.setProperty("--rd", delay + "ms");
                node.classList.remove("is-reveal");

                later(() => {
                    node.style.transitionDelay = "";
                    node.style.removeProperty("--rd");
                }, delay + 1000);
            });
        }, { root, rootMargin: "0px 0px -6% 0px", threshold: 0.06 });

        elById.forEach((node) => revealObserver.observe(node));
        observers.push(revealObserver);
    }

    /* =============================================================
       CARD SPOTLIGHT (follows the pointer)
       ============================================================= */

    let pointerFrame = 0;
    let lastPointer = null;

    on(root, "pointermove", (event) => {
        if (event.pointerType !== "mouse") return;

        lastPointer = event;

        if (pointerFrame) return;

        pointerFrame = requestAnimationFrame(() => {
            pointerFrame = 0;
            const card = lastPointer.target.closest && lastPointer.target.closest(".card");

            if (!card) return;

            const rect = card.getBoundingClientRect();
            card.style.setProperty("--mx", (lastPointer.clientX - rect.left) + "px");
            card.style.setProperty("--my", (lastPointer.clientY - rect.top) + "px");
        });
    }, { passive: true });

    /* =============================================================
       HERO DEPTH (aurora + orbit drift a little with the pointer)
       ============================================================= */

    const hero = $(".hero");
    const heroBg = $(".hero-bg");
    let heroFrame = 0;
    let heroPoint = null;

    on(hero, "pointermove", (event) => {
        if (event.pointerType !== "mouse" || reduced()) return;

        heroPoint = event;

        if (heroFrame) return;

        heroFrame = requestAnimationFrame(() => {
            heroFrame = 0;
            const rect = hero.getBoundingClientRect();
            const px = ((heroPoint.clientX - rect.left) / rect.width) * 2 - 1;
            const py = ((heroPoint.clientY - rect.top) / rect.height) * 2 - 1;
            heroBg.style.setProperty("--px", px.toFixed(3));
            heroBg.style.setProperty("--py", py.toFixed(3));
        });
    }, { passive: true });

    on(hero, "pointerleave", () => {
        heroBg.style.setProperty("--px", "0");
        heroBg.style.setProperty("--py", "0");
    });

    /* =============================================================
       GLOBAL KEYS + RESIZE
       ============================================================= */

    on(document, "keydown", (event) => {
        if (event.key === "Escape" && openModal) {
            openModal.close();
        }
    });

    let resizeTimer = 0;

    on(window, "resize", () => {
        placeThumb(false);
        if (menuOpen) placeMenu();

        clearTimeout(resizeTimer);
        timers.delete(resizeTimer);
        resizeTimer = later(sizeTicker, 200);
    }, { passive: true });

    /* =============================================================
       FIRST RENDER
       ============================================================= */

    buildSpotlight();
    renderEyebrow();
    buildTicker();
    renderStatus();
    every(renderStatus, 60000);

    const visible = update({ animate: false });

    if (INTRO) {
        renderKpis(kpiNumbers(visible), true);
    }

    placeThumb(false);

    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(() => {
            if (ac.signal.aborted) return;
            placeThumb(false);
            sizeTicker();
        });
    }

    let welcomeSeen = false;

    try { welcomeSeen = sessionStorage.getItem("ipot-welcome-seen") === "1"; } catch (error) { /* storage blocked */ }

    if (firstBoot && !welcomeSeen) {
        later(() => welcome.open(), INTRO ? 2000 : 350);
    }
})();
