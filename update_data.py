import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ipo_data import get_dashboard_data


BASE_DIR = Path(__file__).resolve().parent

LATEST_DATA_FILE = BASE_DIR / "latest_data.json"
GMP_HISTORY_FILE = BASE_DIR / "gmp_history.json"
GMP_LATEST_FILE = BASE_DIR / "gmp_latest.json"


def get_ist_time():
    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%Y-%m-%d %H:%M")


def load_json(file_path):
    if not file_path.exists():
        return {}

    try:
        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)

    except (json.JSONDecodeError, OSError):
        return {}


def save_json(file_path, data):
    with open(
        file_path,
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


MISSING = [None, "", "—", "-", "TBA", "₹-", "-%"]

# Everything that comes from the GMP source for one IPO.
GMP_FIELDS = [
    "gmp",
    "gmp_percentage",
    "estimated_listing",
    "gmp_last_updated",
    "gmp_source",
    "investorgain_name",
    "investorgain_confidence",
    # Not "investorgain_url": page links are rebuilt fresh every run
    # (from the GMP table or InvestorGain's page index).
]


def carry_forward_gmp(data, previous_data):
    """For IPOs the GMP source could not look up this run (InvestorGain
    unreachable, or no row for that IPO), keep the last known GMP from
    the previous update instead of blanking it.
    Missing allotment dates are kept the same way. Carried values are
    flagged so they are not recorded as new GMP observations."""

    previous = {
        ipo.get("company"): ipo
        for section in ("open", "recent_closed")
        for ipo in previous_data.get(section, [])
    }

    carried = 0

    for section in ("open", "recent_closed"):
        for ipo in data.get(section, []):

            # Internal flag from ipo_data.py; not saved.
            checked = ipo.pop("gmp_checked", True)

            before = previous.get(ipo.get("company"))

            if not before:
                continue

            if (
                not checked
                and ipo.get("gmp") in MISSING
                and before.get("gmp") not in MISSING
            ):
                for field in GMP_FIELDS:
                    if field in before:
                        ipo[field] = before[field]

                ipo["gmp_carried_forward"] = True
                carried += 1

            if (
                ipo.get("allotment_date") in MISSING
                and before.get("allotment_date") not in MISSING
            ):
                ipo["allotment_date"] = before["allotment_date"]

    return carried


def update_gmp_history(data, timestamp):
    history = load_json(GMP_HISTORY_FILE)
    latest = load_json(GMP_LATEST_FILE)

    all_ipos = (
        data.get("open", [])
        + data.get("recent_closed", [])
    )

    for ipo in all_ipos:

        company = ipo.get("company")
        gmp = ipo.get("gmp")

        if not company:
            continue

        if gmp in [None, "—", ""]:
            continue

        # A carried-forward value was not observed this run.
        if ipo.get("gmp_carried_forward"):
            continue

        try:
            gmp_value = float(
                str(gmp)
                .replace("₹", "")
                .replace(",", "")
                .strip()
            )
        except ValueError:
            continue

        # -------------------------------------------------
        # LATEST OBSERVATION
        # -------------------------------------------------
        #
        # ALWAYS update this.
        #
        # This tells us the most recent time our system
        # actually checked and observed this GMP value.
        # -------------------------------------------------

        latest[company] = {
            "timestamp": timestamp,
            "gmp": gmp_value
        }

        # -------------------------------------------------
        # HISTORICAL GRAPH DATA
        # -------------------------------------------------
        #
        # Only create a new historical point when the
        # GMP value actually changes.
        # -------------------------------------------------

        if company not in history:
            history[company] = []

        company_history = history[company]

        if not company_history:

            company_history.append({
                "timestamp": timestamp,
                "gmp": gmp_value
            })

        else:

            last_gmp = company_history[-1].get("gmp")

            if last_gmp != gmp_value:

                company_history.append({
                    "timestamp": timestamp,
                    "gmp": gmp_value
                })

        # Keep history sorted
        company_history.sort(
            key=lambda entry: entry.get(
                "timestamp",
                ""
            )
        )

    save_json(
        GMP_HISTORY_FILE,
        history
    )

    save_json(
        GMP_LATEST_FILE,
        latest
    )


def update_data():

    print("Fetching latest IPO data...")

    data = get_dashboard_data()

    # Decided per IPO: only IPOs InvestorGain could not look up keep
    # their last known GMP. Always run, so the internal
    # "gmp_checked" flag is stripped before saving.
    previous = load_json(LATEST_DATA_FILE).get("data", {})
    carried = carry_forward_gmp(data, previous)

    if carried:
        print(f"Kept the last known GMP for {carried} IPO(s) InvestorGain could not check.")

    timestamp = get_ist_time()

    latest_data = {
        "fetched_at": timestamp,
        "data": data
    }

    save_json(
        LATEST_DATA_FILE,
        latest_data
    )

    update_gmp_history(
        data,
        timestamp
    )

    print(
        f"Data successfully updated at {timestamp} IST"
    )


if __name__ == "__main__":
    update_data()
