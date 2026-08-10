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
