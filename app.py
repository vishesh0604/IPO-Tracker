import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo


# =========================================================
# IMPORT DATA
# =========================================================

import json
from pathlib import Path


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="IPO Tracker",
    page_icon="📈",
    layout="wide",
)
# =========================================================
# WELCOME POPUP
# =========================================================

if "welcome_seen" not in st.session_state:
    st.session_state.welcome_seen = False

if not st.session_state.welcome_seen:

    @st.dialog("Welcome to IPO Tracker")
    def welcome_popup():

        st.markdown(
            """
            **Developed by Vishesh Vasudeva**

            ### WHAT YOU CAN TRACK

            - Current & upcoming IPOs
            - Mainboard & SME IPOs
            - Application & allotment dates
            - Issue price & GMP prices
            

            ### ABOUT THE DATA
            IPO data is sourced from [Groww](https://groww.in/ipo), while GMP data is sourced from [IPOWatch](https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/).

            Please note that GMP and other IPO information can change throughout the day.

            Information displayed on this website is provided for informational purposes.

            ### DISCLAIMER

            IPO Tracker is an independent informational project and
            **is not investment advice or a recommendation to apply for
            or avoid any IPO**.

            Please verify important information with official sources
            before making any investment decision.
            """
        )

        if st.button(
            "Understood!",
            type="primary",
            use_container_width=True
        ):

            st.session_state.welcome_seen = True
            st.rerun()

    welcome_popup()


# =========================================================
# CSS
# =========================================================

st.markdown(
    """
<style>

.block-container {
    max-width: 1200px;
    padding-top: 4rem;
    padding-bottom: 4rem;
}


/* HEADER */

.main-title {
    font-size: 42px;
    font-weight: 800;
    letter-spacing: -1.5px;
    line-height: 1;
}
.developer-credit {
    font-size: 20px;
    font-weight: 800;
    letter-spacing: -0.5px;
    margin-top: 8px;
}

.subtitle {
    color: #888;
    font-size: 14px;
    margin-top: 8px;
}

.refresh-text {
    color: #666;
    font-size: 11px;
    margin-top: 5px;
}


/* SUMMARY */

.summary-box {
    border: 1px solid rgba(128,128,128,0.22);
    border-radius: 12px;
    padding: 15px;
    text-align: center;
}

.summary-number {
    font-size: 28px;
    font-weight: 800;
    line-height: 1;
}

.summary-label {
    color: #888;
    font-size: 10px;
    margin-top: 6px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
}


/* SECTION */

.section-title {
    font-size: 25px;
    font-weight: 800;
    margin-top: 38px;
    margin-bottom: 3px;
}

.section-subtitle {
    color: #777;
    font-size: 12px;
    margin-bottom: 15px;
}

.apply-heading {
    border-left: 4px solid #2ecc71;
    padding-left: 12px;
}

.preapply-heading {
    border-left: 4px solid #f1c40f;
    padding-left: 12px;
}


/* IPO CARD */

.ipo-card-title {
    font-size: 20px;
    font-weight: 750;
    line-height: 1.2;
}

.ipo-card-type {
    color: #888;
    font-size: 12px;
    margin-top: 4px;
}


/* STATUS */

.status-open {
    display: inline-block;
    margin-top: 9px;
    padding: 4px 9px;
    border-radius: 5px;
    background: rgba(46, 204, 113, 0.12);
    color: #2ecc71;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

.status-preapply {
    display: inline-block;
    margin-top: 9px;
    padding: 4px 9px;
    border-radius: 5px;
    background: rgba(241, 196, 15, 0.12);
    color: #f1c40f;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.5px;
}


/* GMP */

.gmp-label {
    color: #777;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.7px;
}

.gmp-value {
    font-size: 32px;
    font-weight: 850;
    line-height: 1;
    margin-top: 3px;
}

.gmp-percent {
    font-size: 18px;
    font-weight: 850;
    margin-top: 5px;
}


/* DETAILS */

.detail-label {
    color: #777;
    font-size: 9px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 4px;
}

.detail-value {
    font-size: 14px;
    font-weight: 700;
}

.listing-price {
    font-size: 16px;
    font-weight: 800;
}

.countdown {
    color: #888;
    font-size: 10px;
    font-weight: 650;
    margin-top: 5px;
}


/* CLOSED */

.closed-name {
    font-size: 17px;
    font-weight: 750;
}

.closed-type {
    color: #888;
    font-size: 11px;
    margin-top: 3px;
}

.closed-details {
    color: #888;
    font-size: 11px;
    margin-top: 7px;
}

.closed-gmp {
    font-size: 22px;
    font-weight: 800;
    text-align: right;
}

.closed-percent {
    font-size: 13px;
    font-weight: 750;
    text-align: right;
    margin-top: 3px;
}
.gmp-trend-mobile {
    display: none;
}
@media screen and (max-width: 600px) {

    .gmp-trend-desktop {
        display: none !important;
    }

    .gmp-trend-mobile {
        display: inline !important;
        white-space: nowrap !important;
        font-size: 11px !important;
        line-height: 18px !important;
    }

    .block-container {
        padding: 2.8rem 0.6rem !important;
        max-width: 100% !important;
    }

    .summary-box {
        padding: 8px 4px !important;
        border-radius: 9px !important;
    }

    .summary-number {
        font-size: 21px !important;
    }

    .summary-label {
        font-size: 8px !important;
        margin-top: 3px !important;
    }

    .section-title {
        font-size: 21px !important;
        margin-top: 20px !important;
        margin-bottom: 2px !important;
    }

    .section-subtitle {
        font-size: 10px !important;
        margin-bottom: 8px !important;
    }

    /* IPO card */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        margin-bottom: 8px !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 10px !important;
    }

    div[data-testid="stHorizontalBlock"] > div {
        min-width: 0 !important;
    }

    .ipo-card-title {
        font-size: 18px !important;
    }

    .ipo-card-type {
        font-size: 10px !important;
        margin-top: 2px !important;
    }

    .status-open,
    .status-preapply {
        margin-top: 5px !important;
        padding: 3px 7px !important;
        font-size: 8px !important;
    }

    .gmp-label {
        font-size: 8px !important;
    }

    .gmp-value {
        font-size: 25px !important;
    }

    .gmp-percent {
        font-size: 14px !important;
        margin-top: 2px !important;
    }

    
    .detail-label {
        font-size: 8px !important;
        margin-bottom: 2px !important;
    }

    .detail-value {
        font-size: 12px !important;
    }

    .listing-price {
        font-size: 13px !important;
    }

    .countdown {
        font-size: 8px !important;
        margin-top: 2px !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] hr {
        margin: 7px 0 !important;
    }
/* Mobile filter layout */
div[data-testid="stHorizontalBlock"]:has(
    input[placeholder="Search by company name..."]
) {
    flex-wrap: wrap !important;
}

/* Keep Search + Type on the first row */
div[data-testid="stHorizontalBlock"]:has(
    input[placeholder="Search by company name..."]
) > div:nth-child(1),
div[data-testid="stHorizontalBlock"]:has(
    input[placeholder="Search by company name..."]
) > div:nth-child(2) {
    flex: 0 0 auto !important;
}

/* Move Refresh Data underneath */
div[data-testid="stHorizontalBlock"]:has(
    input[placeholder="Search by company name..."]
) > div:nth-child(3) {
    flex: 0 0 100% !important;
    width: 100% !important;
}

/* Full-width Refresh button */
div[data-testid="stHorizontalBlock"]:has(
    input[placeholder="Search by company name..."]
) > div:nth-child(3) button {
    width: 100% !important;
    white-space: nowrap !important;
    font-size: 13px !important;
}
    /* Make Search + Type fill the full phone width */
    div[data-testid="stHorizontalBlock"]:has(
        input[placeholder="Search by company name..."]
    ) > div:nth-child(1) {
        flex: 3 1 0% !important;
    }

    div[data-testid="stHorizontalBlock"]:has(
        input[placeholder="Search by company name..."]
    ) > div:nth-child(2) {
        flex: 2 1 0% !important;
    }

</style>
""",
    unsafe_allow_html=True,
)



# =========================================================
# HELPERS
# =========================================================

def parse_date(value):

    if not value or value in ["—", "TBA"]:
        return None

    formats = [
        "%d %b %Y",
        "%d %B %Y",
    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                value,
                fmt
            ).date()

        except ValueError:
            pass

    return None


def get_estimated_listing_price(
    issue_price,
    gmp
):

    try:

        price_text = (
            str(issue_price)
            .replace("₹", "")
            .replace(",", "")
            .strip()
        )

        if "-" in price_text:

            upper_price = (
                price_text
                .split("-")[-1]
                .strip()
            )

        elif "–" in price_text:

            upper_price = (
                price_text
                .split("–")[-1]
                .strip()
            )

        else:

            upper_price = price_text


        gmp_text = (
            str(gmp)
            .replace("₹", "")
            .replace(",", "")
            .strip()
        )

        upper_price = float(
            upper_price
        )

        gmp_value = float(
            gmp_text
        )

        return (
            f"₹{upper_price + gmp_value:,.0f}"
        )

    except Exception:

        return "—"


def countdown(close_date):

    date = parse_date(
        close_date
    )

    if date is None:
        return ""

    today = datetime.now().date()

    days = (
        date - today
    ).days

    if days < 0:
        return "Closed"

    if days == 0:
        return "Closes today"

    if days == 1:
        return "Closes tomorrow"

    return f"Closes in {days} days"


# =========================================================
# IPOWATCH URL
# =========================================================

def get_ipowatch_url(company):

    known_urls = {

        "G V Electricals":
            "https://ipowatch.in/gv-electricals-ipo/",

        "Ardee Industries":
            "https://ipowatch.in/ardee-industries-ipo/",

        "Aegeus Technologies":
            "https://ipowatch.in/aegeus-technologies-ipo/",
    }

    if company in known_urls:

        return known_urls[company]


    slug = company.lower().strip()

    characters = []

    for character in slug:

        if character.isalnum():

            characters.append(
                character
            )

        else:

            characters.append("-")


    slug = "".join(
        characters
    )

    while "--" in slug:

        slug = slug.replace(
            "--",
            "-"
        )

    slug = slug.strip("-")

    return (
        f"https://ipowatch.in/"
        f"{slug}-ipo/"
    )


# =========================================================
# LOAD DATA
# =========================================================

@st.cache_data(ttl=1800)
def load_data():
    data_file = Path(__file__).parent / "latest_data.json"

    with open(
        data_file,
        "r",
        encoding="utf-8"
    ) as file:
        saved_data = json.load(file)

    data = saved_data["data"]

    fetched_at = datetime.strptime(
        saved_data["fetched_at"],
        "%Y-%m-%d %H:%M"
    )

    return data, fetched_at


try:

    with st.spinner(
        "Loading IPO data..."
    ):

        data, fetched_at = load_data()

except Exception as e:

    st.error(
        "Could not fetch IPO data."
    )

    st.exception(e)

    st.stop()


# =========================================================
# DATA
# =========================================================

all_open_ipos = data["open"]

recent_closed = data["recent_closed"]
gmp_history_file = (
    Path(__file__).parent / "gmp_history.json"
)

with open(
    gmp_history_file,
    "r",
    encoding="utf-8"
) as file:
    gmp_history = json.load(file)
    

# =========================================================
# SPLIT APPLY / PRE-APPLY
# =========================================================

apply_ipos = [
    ipo
    for ipo in all_open_ipos
    if ipo.get("groww_status") == "Open"
]


preapply_ipos = [
    ipo
    for ipo in all_open_ipos
    if ipo.get("groww_status") == "Pre-apply"
]
apply_ipos.sort(
    key=lambda ipo: datetime.strptime(
        ipo["open_date"],
        "%d %b %Y"
    )
)

preapply_ipos.sort(
    key=lambda ipo: datetime.strptime(
        ipo["open_date"],
        "%d %b %Y"
    )
)

# =========================================================
# GMP DAILY TREND
# =========================================================

for ipo in apply_ipos + preapply_ipos:

    company = ipo["company"]

    history = gmp_history.get(
        company,
        []
    )

    if len(history) >= 2:

        current_gmp = history[-1]["gmp"]
        previous_gmp = history[-2]["gmp"]

        gmp_change = (
            current_gmp - previous_gmp
        )

    else:

        gmp_change = None

    ipo["gmp_change"] = gmp_change

# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">'
    'IPO Tracker'
    '</div>',
    unsafe_allow_html=True
)
st.markdown(
    '<div class="developer-credit">'
    'Developed by Vishesh Vasudeva'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Open & Upcoming Indian IPOs with live GMP data'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    f'<div class="refresh-text">'
    f'Last updated: '
    f'{fetched_at.strftime("%d %b %Y, %I:%M %p")} IST'
    f' &nbsp; · &nbsp; '
    f'Updated automatically as new data becomes available'
    f'</div>',
    unsafe_allow_html=True
)

st.write("")


# =========================================================
# FILTERS
# =========================================================

filter_col1, filter_col2 = st.columns(
    [3, 2]
)


with filter_col1:

    search_query = st.text_input(
        "Search IPOs",
        placeholder="Search by company name...",
        key="ipo_search"
    )


with filter_col2:

    type_filter = st.selectbox(
        "Type",
        [
            "All",
            "Mainboard",
            "SME"
        ],
        key="ipo_type_filter"
    )

    
# =========================================================
# APPLY FILTERS
# =========================================================

search_query = search_query.strip().lower()


def matches_filters(ipo):

    # Company-name search
    if search_query:

        company = str(
            ipo.get(
                "company",
                ""
            )
        ).lower()

        if search_query not in company:

            return False


    # Mainboard / SME filter
    if type_filter != "All":

        ipo_type = str(
            ipo.get(
                "type",
                ""
            )
        ).lower()

        if ipo_type != type_filter.lower():

            return False


    return True


apply_ipos = [
    ipo
    for ipo in apply_ipos
    if matches_filters(ipo)
]


preapply_ipos = [
    ipo
    for ipo in preapply_ipos
    if matches_filters(ipo)
]

# =========================================================
# SUMMARY
# =========================================================

st.write("")


s1, s2, s3 = st.columns(3)


with s1:

    st.markdown(
        f'''
        <div class="summary-box">
            <div class="summary-number">
                {len(all_open_ipos)}
            </div>
            <div class="summary-label">
                Open IPOs
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )


with s2:

    st.markdown(
        f'''
        <div class="summary-box">
            <div class="summary-number">
                {len(apply_ipos)}
            </div>
            <div class="summary-label">
                Apply
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )


with s3:

    st.markdown(
        f'''
        <div class="summary-box">
            <div class="summary-number">
                {len(preapply_ipos)}
            </div>
            <div class="summary-label">
                Pre-apply
            </div>
        </div>
        ''',
        unsafe_allow_html=True
    )


# =========================================================
# APPLY-NOW
# =========================================================

st.markdown(
    '<div class="section-title apply-heading">'
    'Apply Now'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'IPO is currently open for application'
    '</div>',
    unsafe_allow_html=True
)


for ipo in apply_ipos:

    estimated_listing = (
        get_estimated_listing_price(
            ipo.get("issue_price"),
            ipo.get("gmp")
        )
    )

    ipowatch_url = get_ipowatch_url(
        ipo["company"]
    )


    with st.container(
        border=True
    ):

        left, right = st.columns(
            [3, 1]
        )


        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        with left:

            st.markdown(
                f'''
                <div class="ipo-card-title">
                    {ipo["company"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="ipo-card-type">
                    {ipo["type"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                '<span class="status-open">'
                'OPEN'
                '</span>',
                unsafe_allow_html=True
            )


        # -------------------------------------------------
        # GMP
        # -------------------------------------------------

        with right:

            st.markdown(
                '''
                <div style="text-align:right;">
                    <div class="gmp-label">
                        GMP
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div style="text-align:right;"
                     class="gmp-value">
                    {ipo["gmp"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div style="text-align:right;"
                     class="gmp-percent">
                    {ipo["gmp_percentage"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            # GMP DAILY TREND

            gmp_change = ipo.get(
                "gmp_change"
            )

            if gmp_change is None:

                trend_text = (
                    '<span class="gmp-trend-desktop">'
                    '🟡'
                    '</span>'
                    '<span class="gmp-trend-mobile">'
                    '🟡'
                    '</span>'
                )

                trend_class = (
                    "gmp-trend-neutral"
                )
            elif gmp_change > 0:

                trend_text = (
                    f"🟢+₹{gmp_change:g}"
                )

                trend_class = (
                    "gmp-trend-up"
                )

            elif gmp_change < 0:

                trend_text = (
                    f"🔴−₹{abs(gmp_change):g}"
                )

                trend_class = (
                    "gmp-trend-down"
                )

            else:

                trend_text = (
                    "🟡"
                )

                trend_class = (
                    "gmp-trend-neutral"
                )

            st.markdown(
                f'''
                <div class="{trend_class}"
                     style="
                         text-align:right;
                         height:18px;
                         line-height:18px;
                         margin-top:4px;
                         white-space:nowrap;
                     ">
                    {trend_text}
                </div>
                ''',
                unsafe_allow_html=True
            )


        st.divider()

        # -------------------------------------------------
        # DETAILS
        # -------------------------------------------------

        d1, d2, d3, d4 = st.columns(4)


        with d1:

            st.markdown(
                '''
                <div class="detail-label">
                    PRICE BAND
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="detail-value">
                    {ipo["issue_price"]}
                </div>
                ''',
                unsafe_allow_html=True
            )


        with d2:

            st.markdown(
                '''
                <div class="detail-label">
                    EST. LISTING
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="detail-value listing-price">
                    {estimated_listing}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                '''
                <div class="countdown">
                    Based on current GMP
                </div>
                ''',
                unsafe_allow_html=True
            )


        with d3:

            st.markdown(
                '''
                <div class="detail-label">
                    LAST APPLICATION
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="detail-value">
                    {ipo["close_date"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="countdown">
                    {countdown(ipo["close_date"])}
                </div>
                ''',
                unsafe_allow_html=True
            )


        with d4:

            st.markdown(
                '''
                <div class="detail-label">
                    ALLOTMENT
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="detail-value">
                    {ipo["allotment_date"]}
                </div>
                ''',
                unsafe_allow_html=True
            )


        st.divider()


        # -------------------------------------------------
        # LINKS
        # -------------------------------------------------

        link1, link2 = st.columns(2)


        with link1:

            st.link_button(
                "Open IPOWatch",
                ipowatch_url,
                use_container_width=True
            )


        with link2:

            st.link_button(
                "Open Groww IPOs",
                "https://groww.in/ipo",
                use_container_width=True
            )


# =========================================================
# PRE-APPLY
# =========================================================

st.markdown(
    '<div class="section-title preapply-heading">'
    'Pre-Apply'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'Upcoming IPOs available for pre-application on Groww'
    '</div>',
    unsafe_allow_html=True
)


if not preapply_ipos:

    st.info(
        "No Pre-Apply IPOs match your current filters."
    )


for ipo in preapply_ipos:

    estimated_listing = (
        get_estimated_listing_price(
            ipo.get("issue_price"),
            ipo.get("gmp")
        )
    )

    ipowatch_url = get_ipowatch_url(
        ipo["company"]
    )


    with st.container(
        border=True
    ):

        left, right = st.columns(
            [3, 1]
        )


        with left:

            st.markdown(
                f'''
                <div class="ipo-card-title">
                    {ipo["company"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="ipo-card-type">
                    {ipo["type"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                '<span class="status-preapply">'
                'PRE-APPLY'
                '</span>',
                unsafe_allow_html=True
            )


        with right:

            st.markdown(
                '''
                <div style="text-align:right;">
                    <div class="gmp-label">
                        GMP
                    </div>
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div style="text-align:right;"
                     class="gmp-value">
                    {ipo["gmp"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div style="text-align:right;"
                     class="gmp-percent">
                    {ipo["gmp_percentage"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            # GMP DAILY TREND

            gmp_change = ipo.get(
                "gmp_change"
            )

            if gmp_change is None:

                trend_text = (
                    "🟡"
                )

                trend_class = (
                    "gmp-trend-neutral"
                )

            elif gmp_change > 0:

                trend_text = (
                    f"🟢+₹{gmp_change:g}"
                )

                trend_class = (
                    "gmp-trend-up"
                )

            elif gmp_change < 0:

                trend_text = (
                    f"🔴−₹{abs(gmp_change):g}"
                )

                trend_class = (
                    "gmp-trend-down"
                )

            else:

                trend_text = (
                    "🟡"
                )

                trend_class = (
                    "gmp-trend-neutral"
                )

            st.markdown(
                f'''
                <div class="{trend_class}"
                     style="
                         text-align:right;
                         height:18px;
                         line-height:18px;
                         margin-top:4px;
                         white-space:nowrap;
                     ">
                    {trend_text}
                </div>
                ''',
                unsafe_allow_html=True
            )
            
        st.divider()


        d1, d2, d3, d4 = st.columns(4)


        with d1:

            st.markdown(
                '''
                <div class="detail-label">
                    PRICE BAND
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="detail-value">
                    {ipo["issue_price"]}
                </div>
                ''',
                unsafe_allow_html=True
            )


        with d2:

            st.markdown(
                '''
                <div class="detail-label">
                    EST. LISTING
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="detail-value listing-price">
                    {estimated_listing}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                '''
                <div class="countdown">
                    Based on current GMP
                </div>
                ''',
                unsafe_allow_html=True
            )


        with d3:

            st.markdown(
                '''
                <div class="detail-label">
                    LAST APPLICATION
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="detail-value">
                    {ipo["close_date"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="countdown">
                    {countdown(ipo["close_date"])}
                </div>
                ''',
                unsafe_allow_html=True
            )


        with d4:

            st.markdown(
                '''
                <div class="detail-label">
                    ALLOTMENT
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="detail-value">
                    {ipo["allotment_date"]}
                </div>
                ''',
                unsafe_allow_html=True
            )


        st.divider()


        link1, link2 = st.columns(2)


        with link1:

            st.link_button(
                "Open IPOWatch",
                ipowatch_url,
                use_container_width=True
            )


        with link2:

            st.link_button(
                "Open Groww IPOs",
                "https://groww.in/ipo",
                use_container_width=True
            )


# =========================================================
# CLOSED IPOs
# =========================================================

st.markdown(
    '<div class="section-title">'
    '3 Most Recent Closed IPOs'
    '</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="section-subtitle">'
    'Recent issues for reference'
    '</div>',
    unsafe_allow_html=True
)


for ipo in recent_closed:

    ipowatch_url = get_ipowatch_url(
        ipo["company"]
    )


    with st.container(
        border=True
    ):

        left, right = st.columns(
            [3, 1]
        )


        with left:

            st.markdown(
                f'''
                <div class="closed-name">
                    {ipo["company"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="closed-type">
                    {ipo["type"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="closed-details">
                    Last application:
                    {ipo["close_date"]}
                    &nbsp; · &nbsp;
                    Allotment:
                    {ipo["allotment_date"]}
                    &nbsp; · &nbsp;
                    Issue price:
                    {ipo["issue_price"]}
                </div>
                ''',
                unsafe_allow_html=True
            )


        with right:

            st.markdown(
                f'''
                <div class="closed-gmp">
                    {ipo["gmp"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="closed-percent">
                    {ipo["gmp_percentage"]}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown(
                '''
                <div style="text-align:right;"
                     class="gmp-label">
                    GMP
                </div>
                ''',
                unsafe_allow_html=True
            )


        st.divider()


        st.link_button(
            "Open IPOWatch",
            ipowatch_url,
            use_container_width=True
        )