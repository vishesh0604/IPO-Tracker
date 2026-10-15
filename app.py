import base64
import json
import re
from datetime import datetime
from pathlib import Path

import streamlit as st


# =========================================================
# IPO TRACKER — REDESIGN HOST
#
# Streamlit only loads the data and hands it to a single
# client-side app (ui/index.html + ui/styles.css + ui/app.js).
# Search, filters, sorting, popups and animations all run in
# the browser, so nothing triggers a Streamlit rerun.
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
UI_DIR = BASE_DIR / "ui"

st.set_page_config(
    page_title="IPO Tracker",
    page_icon=str(BASE_DIR / "ipo_tracker_favicon.png"),
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# PARSING HELPERS
# =========================================================

MISSING = {"", "-", "—", "–", "--", "na", "n/a", "tba"}


def to_number(value):
    """'₹1,200' / '35.4%' / '61.38x' / '+12.76%' -> float, else None."""

    if value is None:
        return None

    text = (
        str(value)
        .replace("₹", "")
        .replace(",", "")
        .replace("%", "")
        .replace("×", "")
        .strip()
        .rstrip("xX")
        .strip()
    )

    if text.lower() in MISSING:
        return None

    try:
        return float(text)
    except ValueError:
        return None


def to_iso_date(value):
    """Groww and InvestorGain use several date styles; normalise to ISO."""

    if not value:
        return None

    text = str(value).strip()

    for fmt in (
        "%d %b %Y",
        "%d %B %Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %b, %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass

    return None


def price_band(value):
    """'₹258 - ₹271' -> (258, 271); '₹93.00' -> (93, 93)."""

    text = str(value or "").replace("₹", "").replace(",", "")
    parts = [
        to_number(part)
        for part in re.split(r"\s*[-–]\s*", text)
        if part.strip()
    ]
    parts = [part for part in parts if part is not None]

    if not parts:
        return None, None

    return min(parts), max(parts)


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")


def safe_url(value):
    if isinstance(value, str) and value.startswith(("https://", "http://")):
        return value

    return None


# =========================================================
# DATA
# =========================================================

def read_json(name):
    with open(BASE_DIR / name, "r", encoding="utf-8") as file:
        return json.load(file)


def build_ipo(ipo, section, history):
    low, high = price_band(ipo.get("issue_price"))
    gmp = to_number(ipo.get("gmp"))
    gmp_pct = to_number(ipo.get("gmp_percentage"))

    # Same estimate as before: upper end of the band + current GMP.
    est_listing = (
        high + gmp
        if high is not None and gmp is not None
        else None
    )

    # GMP move since the previous recorded change (history only
    # stores actual changes, so this is the last real move).
    company_history = history.get(ipo.get("company"), [])
    gmp_change = None
    gmp_change_at = None

    if section != "closed" and len(company_history) >= 2:
        gmp_change = (
            company_history[-1]["gmp"] - company_history[-2]["gmp"]
        )
        gmp_change_at = company_history[-1].get("timestamp")

    return {
        "id": f"{section}-{slug(ipo.get('company', ''))}",
        "name": ipo.get("company", "—"),
        "type": ipo.get("type", "—"),
        "section": section,
        "open": to_iso_date(ipo.get("open_date")),
        "close": to_iso_date(ipo.get("close_date")),
        "allot": to_iso_date(ipo.get("allotment_date")),
        "openText": ipo.get("open_date") or "—",
        "closeText": ipo.get("close_date") or "—",
        "allotText": ipo.get("allotment_date") or "TBA",
        "priceText": ipo.get("issue_price") or "—",
        "priceLow": low,
        "priceHigh": high,
        "gmp": gmp,
        "gmpPct": gmp_pct,
        "gmpChange": gmp_change,
        "gmpChangeAt": gmp_change_at,
        "estListing": est_listing,
        "subs": to_number(ipo.get("subscription")),
        # For closed IPOs the parser stores Groww's listing
        # performance column in "action".
        "perf": (
            to_number(ipo.get("action"))
            if section == "closed"
            else None
        ),
        "investorgain": safe_url(ipo.get("investorgain_url")),
        "groww": safe_url(ipo.get("groww_url")),
    }


@st.cache_data(ttl=1800)
def load_payload():
    saved = read_json("latest_data.json")
    history = read_json("gmp_history.json")

    data = saved.get("data", {})
    open_ipos = data.get("open", [])

    def close_key(ipo):
        return to_iso_date(ipo.get("close_date")) or "9999-12-31"

    apply_ipos = sorted(
        [ipo for ipo in open_ipos if ipo.get("groww_status") == "Open"],
        key=close_key,
    )
    preapply_ipos = sorted(
        [ipo for ipo in open_ipos if ipo.get("groww_status") == "Pre-apply"],
        key=close_key,
    )

    ipos = (
        [build_ipo(ipo, "apply", history) for ipo in apply_ipos]
        + [build_ipo(ipo, "preapply", history) for ipo in preapply_ipos]
        + [
            build_ipo(ipo, "closed", history)
            for ipo in data.get("recent_closed", [])
        ]
    )

    fetched = datetime.strptime(saved["fetched_at"], "%Y-%m-%d %H:%M")

    return {
        "fetchedAt": fetched.strftime("%Y-%m-%dT%H:%M:00+05:30"),
        "fetchedText": fetched.strftime("%d %b %Y, %I:%M %p IST"),
        "ipos": ipos,
    }


def data_uri(path, mime):
    encoded = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{encoded}"


def b64(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


FONTS_URL = (
    "https://fonts.googleapis.com/css2"
    "?family=Geist:wght@400;500;600;700"
    "&family=Geist+Mono:wght@400;500;600"
    "&family=Instrument+Serif:ital@0;1"
    "&display=swap"
)

# st.html runs everything through DOMPurify, which drops <link>, SVG and
# any <style>/<script> whose text contains "<" + letter. So the page only
# carries plain markup plus this tiny loader (deliberately free of such
# sequences); CSS, JS and the orbit SVG travel base64-encoded and are
# injected by the loader in the same task, so nothing flashes unstyled.
BOOT_TEMPLATE = """
(function () {
    var dec = function (data) {
        var bin = atob(data);
        var bytes = new Uint8Array(bin.length);
        for (var i = 0; i !== bin.length; i += 1) { bytes[i] = bin.charCodeAt(i); }
        return new TextDecoder("utf-8").decode(bytes);
    };
    var head = document.head;
    ["https://fonts.googleapis.com", "https://fonts.gstatic.com"].forEach(function (origin, index) {
        var id = "ipot-pc-" + index;
        if (document.getElementById(id)) { return; }
        var hint = document.createElement("link");
        hint.id = id;
        hint.rel = "preconnect";
        hint.href = origin;
        if (index === 1) { hint.crossOrigin = "anonymous"; }
        head.appendChild(hint);
    });
    if (!document.getElementById("ipot-fonts")) {
        var link = document.createElement("link");
        link.id = "ipot-fonts";
        link.rel = "stylesheet";
        link.href = "__FONTS__";
        head.appendChild(link);
    }
    var style = document.getElementById("ipot-style");
    if (!style) {
        style = document.createElement("style");
        style.id = "ipot-style";
        head.appendChild(style);
    }
    var css = dec("__CSS64__");
    if (style.textContent !== css) { style.textContent = css; }
    try {
        new Function("ASSETS", dec("__JS64__"))({ orbit: dec("__SVG64__") });
    } catch (error) {
        console.error("IPO Tracker failed to start", error);
    }
})();
"""


def render():
    try:
        payload = load_payload()
    except Exception as error:  # pragma: no cover - shown in the UI
        st.error("Could not load IPO data.")
        st.exception(error)
        st.stop()

    # Inside <script> the JSON must not contain "<" at all (closing tag /
    # sanitizer); < is the same character to JSON.parse.
    data_json = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")

    boot = (
        BOOT_TEMPLATE
        .replace("__FONTS__", FONTS_URL)
        .replace("__CSS64__", b64((UI_DIR / "styles.css").read_text(encoding="utf-8")))
        .replace("__JS64__", b64((UI_DIR / "app.js").read_text(encoding="utf-8")))
        .replace("__SVG64__", b64((UI_DIR / "orbit.svg").read_text(encoding="utf-8")))
    )

    html = (
        (UI_DIR / "index.html").read_text(encoding="utf-8")
        .replace("/*__BOOT__*/", boot)
        .replace("__LOGO__", data_uri(UI_DIR / "logo.png", "image/png"))
        .replace("__MARK__", data_uri(UI_DIR / "mark.png", "image/png"))
        # Data last, so nothing inside it is ever treated as a placeholder.
        .replace("__DATA__", data_json)
    )

    st.html(html, unsafe_allow_javascript=True)


render()
