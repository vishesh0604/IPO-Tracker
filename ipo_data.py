import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
from difflib import SequenceMatcher
from urllib.parse import quote, urljoin
from concurrent.futures import ThreadPoolExecutor


# =========================================================
# SETTINGS
# =========================================================

GROWW_URL = "https://groww.in/ipo"

# The /ipo landing page only shows the latest 10 rows per table.
# The full lists live behind its "View All" links.
GROWW_OPEN_URL = "https://groww.in/ipo/open"
GROWW_CLOSED_URL = "https://groww.in/ipo/closed"

IPOWATCH_URL = "https://ipowatch.in/ipo-grey-market-premium-latest-ipo/"

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

    # Known naming differences between Groww and IPOWatch
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

def get_groww_ipos():

    # Read the full open + closed lists, not the truncated
    # 10-row tables on the /ipo landing page.
    rows = []

    for url in (GROWW_OPEN_URL, GROWW_CLOSED_URL):

        soup = BeautifulSoup(
            get_page(url),
            "html.parser"
        )

        rows.extend(
            soup.select("tr.cur-po")
        )

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
# IPOWATCH — CURRENT GMP TABLE
# =========================================================

def _ipowatch_column(headers, *names):
    """Index of the first header that starts with one of `names`."""

    for index, header in enumerate(headers):
        if any(header.startswith(name) for name in names):
            return index

    return None


def get_ipowatch_ipos():

    html = get_page(IPOWATCH_URL)

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    # IPOWatch has changed this page's layout before (Oct 2026: one
    # 8+ column table became separate Mainboard and SME tables with
    # 6 columns), so columns are located by header name, and every
    # table whose header has "Company" + "GMP" is read.
    ipos = []

    for table in soup.find_all("table"):

        rows = table.find_all("tr")

        if not rows:
            continue

        headers = [
            cell.get_text(" ", strip=True).lower()
            for cell in rows[0].find_all(["th", "td"])
        ]

        col_company = _ipowatch_column(headers, "company", "ipo")
        col_gmp = _ipowatch_column(headers, "gmp")

        if col_company is None or col_gmp is None:
            continue

        col_trend = _ipowatch_column(headers, "trend")
        col_price = _ipowatch_column(headers, "price")
        col_listing = _ipowatch_column(headers, "est")
        col_date = _ipowatch_column(headers, "date")
        col_type = _ipowatch_column(headers, "type")
        col_status = _ipowatch_column(headers, "status")
        col_updated = _ipowatch_column(headers, "last", "updated")

        # The new layout states the board in the heading above the table.
        heading = table.find_previous(["h2", "h3", "h4"])
        heading_text = heading.get_text(" ", strip=True).lower() if heading else ""
        table_type = (
            "SME" if "sme" in heading_text
            else "Mainboard" if "mainboard" in heading_text
            else ""
        )

        for row in rows[1:]:

            cells = row.find_all(["th", "td"])

            if len(cells) <= max(col_company, col_gmp):
                continue

            values = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            def value(index):
                return values[index] if index is not None and index < len(values) else ""

            # Company name is the link text; the cell also carries a
            # status badge ("Open", "Upcoming") after a <br>.
            name_cell = cells[col_company]
            link = name_cell.find("a", href=True)
            badge = name_cell.find("span")

            company = (
                link.get_text(" ", strip=True)
                if link
                else values[col_company]
            )

            if not company:
                continue

            ipo = {
                "company": company,
                "gmp": value(col_gmp),
                "trend": value(col_trend),
                "price_band": value(col_price),
                "estimated_listing": value(col_listing),
                "date": value(col_date),
                "type": value(col_type) or table_type,
                "status": (
                    value(col_status)
                    or (badge.get_text(" ", strip=True) if badge else "")
                ),
                "last_updated": value(col_updated),
                # Links are sometimes relative on the new page.
                "ipowatch_url": (
                    urljoin(IPOWATCH_URL, link["href"])
                    if link
                    else None
                ),
            }

            ipos.append(ipo)

    if not ipos:
        raise Exception(
            "Could not find any rows in the IPOWatch GMP tables."
        )

    return ipos

# =========================================================
# MATCH COMPANY TO IPOWATCH
# =========================================================

def find_ipowatch_match(
    groww_company,
    ipowatch_ipos
):

    best_match = None
    best_score = 0

    groww_words = clean_name(groww_company).split()

    for ipo in ipowatch_ipos:

        score = similarity(
            groww_company,
            ipo["company"]
        )

        # IPOWatch often shortens names ("Sahajanand Medical" for
        # "Sahajanand Medical Technologies"); a multi-word prefix match
        # is a confident match.
        watch_words = clean_name(ipo["company"]).split()
        shorter, longer = sorted([groww_words, watch_words], key=len)

        if len(shorter) >= 2 and longer[:len(shorter)] == shorter:
            score = max(score, 0.95)

        if score > best_score:

            best_score = score
            best_match = ipo

    # 0.55 used to pair unrelated names that share a common word
    # (e.g. "Acme India" with "Shellz India").
    if best_score >= 0.75:

        return best_match, best_score

    return None, best_score


# =========================================================
# IPOWATCH — INDIVIDUAL IPO PAGE
# GET ALLOTMENT DATE
# =========================================================

def get_ipowatch_allotment_date(company):

    slug = clean_name(company).replace(
        " ",
        "-"
    )

    url = (
        f"https://ipowatch.in/"
        f"{slug}-ipo/"
    )

    try:

        html = get_page(url)

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        text = soup.get_text(
            " ",
            strip=True
        )

        marker = "Basis of Allotment:"

        position = text.find(marker)

        if position == -1:

            return "TBA"

        section = text[
            position:
            position + 150
        ]

        section = section.replace(
            marker,
            ""
        ).strip()

        # The date ends before "Refunds:"
        if "Refunds:" in section:

            allotment = section.split(
                "Refunds:"
            )[0].strip()

            return allotment

        return section.split(
            " "
        )[0]

    except Exception:

        return "TBA"


# =========================================================
# ADD IPOWATCH DATA
# =========================================================

def find_ipowatch_page(company):

    search_url = (
        "https://ipowatch.in/"
        "?s="
        + quote(company + " IPO GMP")
    )

    try:

        html = get_page(search_url)

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        company_words = [
            word.lower()
            for word in company.split()
            if len(word) > 2
        ]

        candidates = []

        for link in soup.find_all(
            "a",
            href=True
        ):

            title = link.get_text(
                " ",
                strip=True
            )

            href = link["href"]

            combined = (
                title + " " + href
            ).lower()

            matches = sum(
                word in combined
                for word in company_words
            )

            if matches >= min(
                2,
                len(company_words)
            ):

                if (
                    "ipowatch.in" in href
                    and "ipo" in combined
                ):

                    candidates.append(href)

        # Prefer a GMP-specific page
        for href in candidates:

            if (
                "gmp" in href.lower()
                or "grey-market" in href.lower()
            ):

                return href

        # Otherwise return the normal IPO page
        if candidates:

            return candidates[0]

    except Exception:

        pass

    return None



def get_ipowatch_gmp_details(company):

    slug = clean_name(company).replace(" ", "-")

    # Try direct IPOWatch pages first. This avoids the search
    # request in the normal case and reduces total requests.
    direct_urls = [
        f"https://ipowatch.in/{slug}-ipo-gmp-grey-market-premium/",
        f"https://ipowatch.in/{slug}-ipo/",
    ]

    direct_urls = list(dict.fromkeys(direct_urls))

    for url in direct_urls:

        try:

            html = get_page(url)

            soup = BeautifulSoup(
                html,
                "html.parser"
            )

            tables = soup.find_all("table")

            for table in tables:

                rows = table.find_all("tr")

                if not rows:
                    continue

                header_cells = rows[0].find_all(
                    ["th", "td"]
                )

                headers = [
                    cell.get_text(
                        " ",
                        strip=True
                    ).lower()
                    for cell in header_cells
                ]

                if (
                    "ipo gmp" not in headers
                    or "gain" not in headers
                ):
                    continue

                for row in rows[1:]:

                    cells = row.find_all(
                        ["th", "td"]
                    )

                    values = [
                        cell.get_text(
                            " ",
                            strip=True
                        )
                        for cell in cells
                    ]

                    if len(values) < 4:
                        continue

                    return {
                        "gmp": values[1],
                        "gmp_trend": values[2],
                        "gmp_percentage": values[3],
                        "gmp_last_updated": (
                            values[4]
                            if len(values) > 4
                            else "—"
                        )
                    }

        except Exception:
            continue

    # Fallback: use IPOWatch search only if direct URLs fail.
    first_url = find_ipowatch_page(company)

    if first_url:

        try:

            html = get_page(first_url)

            soup = BeautifulSoup(
                html,
                "html.parser"
            )

            tables = soup.find_all("table")

            for table in tables:

                rows = table.find_all("tr")

                if not rows:
                    continue

                header_cells = rows[0].find_all(
                    ["th", "td"]
                )

                headers = [
                    cell.get_text(
                        " ",
                        strip=True
                    ).lower()
                    for cell in header_cells
                ]

                if (
                    "ipo gmp" not in headers
                    or "gain" not in headers
                ):
                    continue

                for row in rows[1:]:

                    cells = row.find_all(
                        ["th", "td"]
                    )

                    values = [
                        cell.get_text(
                            " ",
                            strip=True
                        )
                        for cell in cells
                    ]

                    if len(values) < 4:
                        continue

                    return {
                        "gmp": values[1],
                        "gmp_trend": values[2],
                        "gmp_percentage": values[3],
                        "gmp_last_updated": (
                            values[4]
                            if len(values) > 4
                            else "—"
                        )
                    }

        except Exception:
            pass

    return {
        "gmp": "—",
        "gmp_trend": "—",
        "gmp_percentage": "—",
        "gmp_last_updated": "—"
    }



def enrich_ipo(
    ipo,
    ipowatch_ipos,
    use_ipowatch_pages=True
):

    match, score = find_ipowatch_match(
        ipo["company"],
        ipowatch_ipos
    )

    result = ipo.copy()

    if "groww_status" not in result:
        result["groww_status"] = "Open"

    # -------------------------------------------------
    # First: use the IPOWatch main table
    # for the current GMP/status.
    # -------------------------------------------------

    if match:

        result["ipowatch_name"] = (
            match["company"]
        )
        result["ipowatch_url"] = (
        match.get("ipowatch_url")
        )

        result["gmp"] = match["gmp"]

        result["gmp_status"] = (
            match["status"]
        )

        result["gmp_trend"] = (
            match["trend"]
        )

        result["gmp_price_band"] = (
            match["price_band"]
        )

        result["estimated_listing"] = (
            match["estimated_listing"]
        )

        result["gmp_last_updated"] = (
            match["last_updated"]
        )

        result["match_confidence"] = round(
            score * 100,
            1
        )

    else:

        result["ipowatch_name"] = "Not found"
        result["ipowatch_url"] = None
        result["gmp"] = "—"
        result["gmp_status"] = "—"
        result["gmp_trend"] = "—"
        result["gmp_price_band"] = "—"
        result["estimated_listing"] = "—"
        result["gmp_last_updated"] = "—"
        result["match_confidence"] = 0

    # -------------------------------------------------
    # Second: get GMP percentage from individual
    # IPOWatch page.
    # -------------------------------------------------

    # When IPOWatch is refusing us (e.g. HTTP 403), every per-IPO page
    # would fail too, so don't request them at all.
    gmp_details = (
        get_ipowatch_gmp_details(result["company"])
        if use_ipowatch_pages
        else {
            "gmp": "—",
            "gmp_trend": "—",
            "gmp_percentage": "—",
            "gmp_last_updated": "—",
        }
    )

    if result["gmp"] == "—":
        result["gmp"] = gmp_details["gmp"]

    result["gmp_percentage"] = (
        gmp_details["gmp_percentage"]
    )

    # Fallback: the main table's "Est. Gain" reads "₹1349 (20.55%)".
    if result["gmp_percentage"] in ["—", "", "-%", None]:

        gain = str(result.get("estimated_listing") or "")

        if "(" in gain and "%" in gain:
            result["gmp_percentage"] = (
                gain.split("(")[-1].split(")")[0].strip()
            )

    if gmp_details["gmp_last_updated"] != "—":
        result["gmp_last_updated"] = (
            gmp_details["gmp_last_updated"]
        )

    # -------------------------------------------------
    # Third: allotment date
    # -------------------------------------------------

    if result["allotment_date"] == "—" and use_ipowatch_pages:

        result["allotment_date"] = (
            get_ipowatch_allotment_date(
                result["company"]
            )
        )

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
    # 3. IPOWatch GMP
    # -----------------------------------------------

    # A problem with IPOWatch must not stop the whole update.
    #  - Site unreachable / refusing us (e.g. Cloudflare HTTP 403 on
    #    GitHub's servers): skip all IPOWatch requests this run and
    #    report it, so update_data.py can keep the last known GMP.
    #  - Main table unreadable (layout change): each IPO still falls
    #    back to its own IPOWatch page below.
    ipowatch_available = True

    try:
        ipowatch_ipos = get_ipowatch_ipos()

    except requests.RequestException as error:
        ipowatch_available = False
        ipowatch_ipos = []
        print(f"WARNING: IPOWatch unreachable ({error}). Skipping GMP lookups this run.")

    except Exception as error:
        ipowatch_ipos = []
        print(f"WARNING: IPOWatch GMP table unreadable ({error}); using per-IPO pages.")

    if progress_callback:
        progress_callback(
            40,
            "IPOWatch GMP data fetched"
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

    with ThreadPoolExecutor(
        max_workers=5
    ) as executor:

        enriched_ipos = list(
            executor.map(
                lambda ipo: enrich_ipo(
                    ipo,
                    ipowatch_ipos,
                    use_ipowatch_pages=ipowatch_available
                ),
                all_ipos
            )
        )

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
        # Read (and removed) by update_data.py before saving.
        "ipowatch_available": ipowatch_available,
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
            "IPOWatch status:",
            ipo["gmp_status"]
        )

        print(
            "GMP updated:",
            ipo["gmp_last_updated"]
        )

        print(
            "Match:",
            ipo["match_confidence"],
            "%"
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

