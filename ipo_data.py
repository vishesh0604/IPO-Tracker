import json
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from difflib import SequenceMatcher
from urllib.parse import urljoin


# =========================================================
# SETTINGS
# =========================================================

GROWW_URL = "https://groww.in/ipo"

# The /ipo landing page only shows the latest 10 rows per table.
# The full lists live behind its "View All" links.
GROWW_OPEN_URL = "https://groww.in/ipo/open"
GROWW_CLOSED_URL = "https://groww.in/ipo/closed"

# GMP source. Chittorgarh's "Grey Market Premium" links lead here; this is
# the final page itself — the /live-ipo-gmp/331/ipo/ link Chittorgarh uses
# is only a JavaScript redirect to it. (IPOWatch was the GMP source until
# Oct 2026, when its Cloudflare started blocking GitHub's servers.)
INVESTORGAIN_URL = "https://www.investorgain.com/report/ipo-gmp-live/331/"

# InvestorGain's own index of every IPO page (id + URL slug + dates).
# Used to link an IPO's exact page when it isn't in the live GMP table.
INVESTORGAIN_INDEX_URL = "https://webnodejs.investorgain.com/cloud/v2/ipo/ipo-url-lists"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    # A bare User-Agent looks like a bot to Cloudflare; send what a
    # real browser sends for a page load.
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}


# =========================================================
# WEBSITE REQUEST
# =========================================================

def get_page(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    return response.text


# =========================================================
# COMPANY NAME CLEANING
# =========================================================

def clean_name(name):

    name = name.lower().strip()

    # Known naming differences between Groww and the GMP site
    aliases = {
        "milky mist dairy food": "milky mist",
        "milky mist dairy foods": "milky mist",
    }

    if name in aliases:
        name = aliases[name]

    replacements = [
        " limited",
        " ltd",
        " private limited",
        " pvt ltd",
        " ipo",
        " industries",
        " industry",
        " corporation",
        " corp",
    ]

    for word in replacements:
        name = name.replace(word, "")

    name = "".join(
        character
        for character in name
        if character.isalnum() or character == " "
    )

    return " ".join(name.split())



def similarity(name1, name2):

    return SequenceMatcher(
        None,
        clean_name(name1),
        clean_name(name2)
    ).ratio()


# =========================================================
# GROWW — GET ALL IPOs
# =========================================================

def _groww_page_links(soup):
    """{company name: its Groww IPO page} from the page's __NEXT_DATA__."""

    links = {}
    script = soup.find("script", id="__NEXT_DATA__")

    try:
        data = json.loads(script.string)
        listing = data["props"]["pageProps"].get("dataList") or []
    except (AttributeError, TypeError, KeyError, ValueError):
        return links

    for item in listing:
        name = item.get("companyName")
        slug = item.get("searchId")

        if name and slug:
            links[name] = f"https://groww.in/ipo/{slug}"

    return links


def get_groww_ipos():

    # Read the full open + closed lists, not the truncated
    # 10-row tables on the /ipo landing page.
    rows = []

    # Groww's rows have no links (clicks are handled by JavaScript), but
    # the page embeds its data: each IPO's "searchId" is the slug of its
    # own page, groww.in/ipo/<searchId>.
    groww_urls = {}

    for url in (GROWW_OPEN_URL, GROWW_CLOSED_URL):

        soup = BeautifulSoup(
            get_page(url),
            "html.parser"
        )

        rows.extend(
            soup.select("tr.cur-po")
        )

        groww_urls.update(_groww_page_links(soup))

    ipos = []

    for row in rows:

        cells = row.find_all("td")

        if len(cells) < 6:
            continue

        company_element = row.select_one(
            '[aria-label="Company name"]'
        )

        if not company_element:
            continue

        company = company_element.get_text(
            strip=True
        )

        values = [
            cell.get_text(
                " ",
                strip=True
            )
            for cell in cells
        ]

        # -------------------------------------------------
        # DETERMINE OPEN VS CLOSED FROM THE DATA ITSELF
        # -------------------------------------------------

        # Open / Pre-apply rows have the action in the final
        # column. Closed rows have a listing date in values[4].
        is_open = (
            len(values) >= 7
            and values[-1] in ["Apply", "Pre-apply"]
        )

        is_closed = False

        if len(values) >= 6:
            try:
                parse_date(values[2])   # Open date
                parse_date(values[3])   # Close date
                parse_date(values[4])   # Listing date
                is_closed = True
            except ValueError:
                pass

        # -------------------------------------------------
        # OPEN / PRE-APPLY IPO
        # -------------------------------------------------

        if is_open:

            ipo = {
                "company": company,
                "type": values[1],
                "open_date": values[2],
                "close_date": values[3],
                "allotment_date": "—",
                "issue_price": values[4],
                "subscription": values[5],
                "action": values[6],
                "groww_status": (
                    "Pre-apply"
                    if values[-1] == "Pre-apply"
                    else "Open"
                ),
                "status_source": "current",
                "groww_url": groww_urls.get(company),
            }

        # -------------------------------------------------
        # CLOSED IPO
        # -------------------------------------------------

        elif is_closed:

            # Groww /ipo/closed columns:
            # 0 Company | 1 Type | 2 Open | 3 Close | 4 Listing |
            # 5 Allotment | 6 Issue Price | 7 Listing Price |
            # 8 Subscription | 9 Performance
            ipo = {
                "company": company,
                "type": values[1],
                "open_date": values[2],
                "close_date": values[3],
                "allotment_date": values[5],
                "issue_price": values[6],
                "subscription": (
                    values[8]
                    if len(values) > 8
                    else "—"
                ),
                "action": (
                    values[9]
                    if len(values) > 9
                    else "Closed"
                ),
                "groww_status": "Closed",
                "status_source": "closed",
                "groww_url": groww_urls.get(company),
            }

        else:
            continue

        ipos.append(ipo)

    return ipos


# =========================================================
# DATE HELPERS
# =========================================================

def parse_date(date_text):

    return datetime.strptime(
        date_text,
        "%d %b %Y"
    ).date()


# =========================================================
# FIND OPEN IPOs
# =========================================================

def get_open_ipos(ipos):

    open_ipos = []

    for ipo in ipos:

        # Groww's Open tab contains both:
        # "Apply" and "Pre-apply"
        if ipo.get("action") in [
            "Apply",
            "Pre-apply"
        ]:

            open_ipos.append(ipo)

    # Always display open IPOs chronologically
    # by their closing/application deadline.
    open_ipos.sort(
        key=lambda ipo: parse_date(ipo["close_date"])
    )

    return open_ipos



# =========================================================
# FIND 3 MOST RECENT CLOSED IPOs
# =========================================================

def get_recent_closed_ipos(ipos):

    today = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).date()
    
    closed_ipos = []

    for ipo in ipos:

        try:

            close_date = parse_date(
                ipo["close_date"]
            )

        except ValueError:

            continue

        if close_date < today:

            ipo_copy = ipo.copy()

            ipo_copy["_close_date_object"] = close_date

            closed_ipos.append(
                ipo_copy
            )

    closed_ipos.sort(
        key=lambda x: x["_close_date_object"],
        reverse=True
    )

    closed_ipos = closed_ipos[:5]

    for ipo in closed_ipos:

        ipo.pop(
            "_close_date_object",
            None
        )

    return closed_ipos


# =========================================================
# INVESTORGAIN — LIVE GMP TABLE
# =========================================================

def _first_day_month(text):
    """'15-OctGMP: 500' -> '15-Oct' (the cell also holds a GMP note)."""

    found = re.match(r"\s*(\d{1,2}-[A-Za-z]{3})", text or "")
    return found.group(1) if found else ""


def get_investorgain_ipos():

    html = get_page(INVESTORGAIN_URL)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    ipos = []

    for row in soup.select("#tableBody tr"):

        # Every cell is labelled, so read by label, not position.
        cells = {
            cell.get("data-label"): cell
            for cell in row.find_all("td")
            if cell.get("data-label")
        }

        # The table repeats its header row every few entries.
        name_cell = cells.get("Name")

        if name_cell is None:
            continue

        link = name_cell.find("a", href=True)
        company = (
            link.get_text(" ", strip=True)
            if link
            else name_cell.get_text(" ", strip=True)
        )

        if not company:
            continue

        badges = [
            badge.get_text(" ", strip=True)
            for badge in name_cell.select("span.badge")
        ]

        # GMP cell: "₹<b>115</b> (16.59%)<br><small>83 ↓ / 115 ↑</small>"
        # "₹ --" means no grey-market quote.
        gmp_cell = cells.get("GMP")
        gmp_bold = gmp_cell.find("b") if gmp_cell else None
        gmp_value = gmp_bold.get_text(strip=True) if gmp_bold else ""

        try:
            gmp_number = float(gmp_value.replace(",", ""))
        except ValueError:
            gmp_number = None

        pct_match = re.search(
            r"\((-?[\d.]+)%\)",
            gmp_cell.get_text(" ", strip=True) if gmp_cell else ""
        )

        def text(label):
            cell = cells.get(label)
            return cell.get_text(" ", strip=True) if cell else ""

        gmp = "—"
        gmp_percentage = "—"

        if gmp_number is not None:
            gmp = f"₹{gmp_number:g}"
            gmp_percentage = (
                f"{float(pct_match.group(1)):.2f}%"
                if pct_match
                else "—"
            )

        ipos.append({
            "company": company,
            "gmp": gmp,
            "gmp_percentage": gmp_percentage,
            "price": text("Price (₹)").replace(",", ""),
            "type": "SME" if any("SME" in badge for badge in badges) else "Mainboard",
            "open": _first_day_month(text("Open")),
            "close": _first_day_month(text("Close")),
            "allotment": _first_day_month(text("BoA Dt")),
            "last_updated": text("Updated-On"),
            "url": urljoin(INVESTORGAIN_URL, link["href"]) if link else None,
        })

    if not ipos:
        raise Exception(
            "Could not find any rows in the InvestorGain GMP table."
        )

    return ipos


def get_investorgain_page_index():
    """[{company, url, close}] for every IPO page InvestorGain has."""

    response = requests.get(
        INVESTORGAIN_INDEX_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    pages = []

    for entry in response.json().get("lists", []):

        page_id = entry.get("id")
        slug = entry.get("urlrewrite_folder_name")

        if not page_id or not slug:
            continue

        pages.append({
            "company": entry.get("company_short_name") or "",
            "url": f"https://www.investorgain.com/gmp/{slug}/{page_id}/",
            "close": (entry.get("issue_end_dt") or "")[:10],
        })

    return pages


def link_missing_investorgain_pages(ipos):
    """Give every IPO its own InvestorGain page link, even if it isn't
    in the live GMP table: look it up in InvestorGain's IPO index by
    name, and only accept a candidate whose closing date matches."""

    missing = [ipo for ipo in ipos if not ipo.get("investorgain_url")]

    if not missing:
        return

    try:
        index = get_investorgain_page_index()
    except Exception as error:
        print(f"WARNING: InvestorGain page index unavailable ({error}).")
        return

    for ipo in missing:

        try:
            close = parse_date(ipo.get("close_date"))
        except (ValueError, TypeError):
            close = None

        # Same company name on another date = a different IPO.
        candidates = []

        for page in index:
            try:
                page_close = datetime.strptime(page["close"], "%Y-%m-%d").date()
            except ValueError:
                continue

            if close and abs((page_close - close).days) <= 7:
                candidates.append(page)

        match, score = find_name_match(ipo["company"], candidates)

        if match:
            ipo["investorgain_url"] = match["url"]


def _allotment_from_day_month(day_month, reference_date_text):
    """'26-Oct' + Groww close date '23 Oct 2026' -> '26 Oct 2026'."""

    if not day_month:
        return None

    try:
        reference = parse_date(reference_date_text)
        day_month_date = datetime.strptime(
            f"{day_month}-{reference.year}",
            "%d-%b-%Y"
        ).date()
    except (ValueError, TypeError):
        return None

    # Allotment after a December close falls in the next year.
    if day_month_date < reference:
        day_month_date = day_month_date.replace(year=reference.year + 1)

    return day_month_date.strftime("%d %b %Y")


# =========================================================
# MATCH COMPANY NAMES (Groww <-> InvestorGain)
# =========================================================

def find_name_match(
    groww_company,
    source_ipos
):

    best_match = None
    best_score = 0

    groww_words = clean_name(groww_company).split()

    for ipo in source_ipos:

        score = similarity(
            groww_company,
            ipo["company"]
        )

        # GMP sites often shorten or extend names ("Sahajanand Medical" for
        # "Sahajanand Medical Technologies"); a multi-word prefix match
        # is a confident match.
        source_words = clean_name(ipo["company"]).split()
        shorter, longer = sorted([groww_words, source_words], key=len)

        if len(shorter) >= 2 and longer[:len(shorter)] == shorter:
            score = max(score, 0.95)

        # Same idea ignoring spaces/dots: "R K Fashion" vs
        # "R.K.Fashion Accessories" -> "rkfashion" / "rkfashionaccessories".
        compact_groww = "".join(groww_words)
        compact_source = "".join(source_words)
        short_c, long_c = sorted([compact_groww, compact_source], key=len)

        if len(short_c) >= 6 and long_c.startswith(short_c):
            score = max(score, 0.9)

        if score > best_score:

            best_score = score
            best_match = ipo

    # 0.55 used to pair unrelated names that share a common word
    # (e.g. "Acme India" with "Shellz India").
    if best_score >= 0.75:

        return best_match, best_score

    return None, best_score


def enrich_ipo(
    ipo,
    investorgain_ipos
):

    result = ipo.copy()

    if "groww_status" not in result:
        result["groww_status"] = "Open"

    # Defaults: no grey-market quote found.
    result.update({
        "gmp": "—",
        "gmp_percentage": "—",
        "gmp_last_updated": "—",
        "estimated_listing": "—",
        "gmp_source": "—",
        "investorgain_name": "Not found",
        "investorgain_url": None,
        "investorgain_confidence": 0,
    })

    match, score = find_name_match(
        result["company"],
        investorgain_ipos
    )

    # Did InvestorGain actually look this IPO up? If not (no row for it,
    # or the site was unreachable), update_data.py keeps the last known
    # GMP instead of blanking it.
    result["gmp_checked"] = bool(match)

    if match:

        result["investorgain_name"] = match["company"]
        result["investorgain_url"] = match["url"]
        result["investorgain_confidence"] = round(score * 100, 1)

        # "₹ --" on InvestorGain means no grey-market quote right now.
        if match["gmp"] != "—":

            result["gmp"] = match["gmp"]
            result["gmp_percentage"] = match["gmp_percentage"]
            result["gmp_last_updated"] = match["last_updated"] or "—"
            result["gmp_source"] = "InvestorGain"

            try:
                upper_price = float(match["price"])
                gmp_value = float(match["gmp"].replace("₹", ""))
                result["estimated_listing"] = (
                    f"₹{upper_price + gmp_value:g} ({match['gmp_percentage']})"
                )
            except ValueError:
                pass

        # Allotment date from InvestorGain's "BoA Dt" when Groww has none.
        if result["allotment_date"] == "—":
            result["allotment_date"] = (
                _allotment_from_day_month(
                    match["allotment"],
                    result.get("close_date")
                )
                or "—"
            )

    if result["allotment_date"] == "—":
        result["allotment_date"] = "TBA"

    return result

# =========================================================
# MAIN DATA FUNCTION
# =========================================================

def get_dashboard_data(progress_callback=None):

    # -----------------------------------------------
    # 1. Groww
    # -----------------------------------------------

    groww_ipos = get_groww_ipos()

    if progress_callback:
        progress_callback(
            20,
            "Groww data fetched"
        )

    # -----------------------------------------------
    # 2. Determine status
    # -----------------------------------------------

    open_ipos = get_open_ipos(
        groww_ipos
    )

    recent_closed = get_recent_closed_ipos(
        groww_ipos
    )

    if progress_callback:
        progress_callback(
            30,
            "IPO status processed"
        )

    # -----------------------------------------------
    # 3. InvestorGain GMP
    # -----------------------------------------------

    # A failure here must not stop the update: Groww data is still saved
    # and update_data.py keeps each IPO's last known GMP.
    try:
        investorgain_ipos = get_investorgain_ipos()
        print(f"InvestorGain GMP table: {len(investorgain_ipos)} rows.")
    except Exception as error:
        investorgain_ipos = []
        print(f"WARNING: InvestorGain GMP unavailable ({error}). Keeping last known GMP.")

    if progress_callback:
        progress_callback(
            40,
            "GMP data fetched"
        )

    # -----------------------------------------------
    # 4. Match GMP
    # -----------------------------------------------

    all_ipos = (
        open_ipos +
        recent_closed
    )

    if progress_callback:
        progress_callback(
            45,
            "Enriching IPO data..."
        )

    # Pure matching against the one table — no further requests.
    enriched_ipos = [
        enrich_ipo(ipo, investorgain_ipos)
        for ipo in all_ipos
    ]

    # Exact InvestorGain page for IPOs the GMP table didn't list.
    link_missing_investorgain_pages(enriched_ipos)

    if progress_callback:
        progress_callback(
            85,
            "IPO enrichment complete"
        )

    # -----------------------------------------------
    # 5. Restore original sections
    # -----------------------------------------------

    open_count = len(
        open_ipos
    )

    open_ipos = enriched_ipos[
        :open_count
    ]

    recent_closed = enriched_ipos[
        open_count:
    ]

    if progress_callback:
        progress_callback(
            100,
            "Data ready"
        )

    return {
        "open": open_ipos,
        "recent_closed": recent_closed,
    }
    


# =========================================================
# TERMINAL TEST
# =========================================================

def main():

    print()
    print("=" * 70)
    print("IPO TRACKER")
    print("=" * 70)

    print()
    print("Getting data...")

    data = get_dashboard_data()

    open_ipos = data["open"]
    recent_closed = data["recent_closed"]

    print()
    print(
        f"OPEN IPOs: {len(open_ipos)}"
    )

    print(
        f"RECENT CLOSED IPOs: {len(recent_closed)}"
    )

    print()
    print("=" * 70)
    print("OPEN IPOs")
    print("=" * 70)

    for ipo in open_ipos:

        print()
        print(
            "Company:",
            ipo["company"]
        )

        print(
            "Type:",
            ipo["type"]
        )

        print(
            "Open:",
            ipo["open_date"]
        )

        print(
            "Last application:",
            ipo["close_date"]
        )

        print(
            "Allotment:",
            ipo["allotment_date"]
        )

        print(
            "Price:",
            ipo["issue_price"]
        )

        print(
            "GMP:",
            ipo["gmp"]
        )

        print(
            "GMP %:",
            ipo["gmp_percentage"]
        )

        print(
            "Groww status:",
            ipo["groww_status"]
        )

        print(
            "GMP source:",
            ipo["gmp_source"]
        )

        print(
            "GMP updated:",
            ipo["gmp_last_updated"]
        )

        print(
            "InvestorGain match:",
            ipo["investorgain_name"],
            f"({ipo['investorgain_confidence']}%)"
        )

        print("-" * 70)

    print()
    print("=" * 70)
    print("3 MOST RECENT CLOSED IPOs")
    print("=" * 70)

    for ipo in recent_closed:

        print()

        print(
            "Company:",
            ipo["company"]
        )

        print(
            "Type:",
            ipo["type"]
        )

        print(
            "Last application:",
            ipo["close_date"]
        )

        print(
            "Allotment:",
            ipo["allotment_date"]
        )

        print(
            "Price:",
            ipo["issue_price"]
        )

        print(
            "GMP:",
            ipo["gmp"]
        )

        print(
            "GMP %:",
            ipo["gmp_percentage"]
        )

        print("-" * 70)


if __name__ == "__main__":

    main()

