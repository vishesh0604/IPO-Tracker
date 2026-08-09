import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ipo_data import get_dashboard_data


BASE_DIR = Path(__file__).resolve().parent

LATEST_DATA_FILE = BASE_DIR / "latest_data.json"
GMP_HISTORY_FILE = BASE_DIR / "gmp_history.json"


def get_ist_time():
    return datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%Y-%m-%d %H:%M")


def load_gmp_history():
    if not GMP_HISTORY_FILE.exists():
        return {}

    try:
        with open(
            GMP_HISTORY_FILE,
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
    history = load_gmp_history()

    all_ipos = (
        data.get("open", [])
        + data.get("recent_closed", [])
    )

    current_date = timestamp[:10]

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

        if company not in history:
            history[company] = []

        # -------------------------------------------------
        # REMOVE DUPLICATES FOR THE SAME DAY
        # -------------------------------------------------

        daily_entries = []
        other_entries = []

        for entry in history[company]:
            entry_date = str(
                entry.get("timestamp", "")
            )[:10]

            if entry_date == current_date:
                daily_entries.append(entry)
            else:
                other_entries.append(entry)

        # -------------------------------------------------
        # KEEP ONLY THE LATEST ENTRY FOR TODAY
        # -------------------------------------------------

        latest_today = {
            "timestamp": timestamp,
            "gmp": gmp_value
        }

        history[company] = (
            other_entries
            + [latest_today]
        )

        # Keep history sorted by date/time
        history[company].sort(
            key=lambda entry: entry.get(
                "timestamp",
                ""
            )
        )

    save_json(
        GMP_HISTORY_FILE,
        history
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
