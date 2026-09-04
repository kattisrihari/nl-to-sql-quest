"""
verify.py — Sanity checks on hotel_bookings.db.
Runs the 6 sample NL2SQL demo questions as raw SQL to confirm data quality.

Usage:
    python data/verify.py
"""

import sqlite3
from pathlib import Path

DB_FILE = Path(__file__).parent / "hotel_bookings.db"

CHECKS = [
    {
        "question": "How many bookings did we receive from each region during August 2026?",
        "sql": """
            SELECT r.region_name, COUNT(*) AS bookings
            FROM bookings b
            JOIN hotels h ON b.hotel_id = h.hotel_id
            JOIN regions r ON h.region_id = r.region_id
            WHERE strftime('%Y-%m', b.check_in_date) = '2026-08'
            GROUP BY r.region_name
            ORDER BY bookings DESC
        """,
    },
    {
        "question": "What is the average booking value by hotel star rating?",
        "sql": """
            SELECT h.star_rating || ' star' AS rating,
                   ROUND(AVG(b.total_amount), 2) AS avg_booking_inr,
                   COUNT(*) AS total_bookings
            FROM bookings b
            JOIN hotels h ON b.hotel_id = h.hotel_id
            WHERE b.status != 'Cancelled'
            GROUP BY h.star_rating
            ORDER BY h.star_rating DESC
        """,
    },
    {
        "question": "Which room type had the highest occupancy in 2026?",
        "sql": """
            SELECT room_type,
                   COUNT(*) AS bookings,
                   SUM(julianday(check_out_date) - julianday(check_in_date)) AS total_nights
            FROM bookings
            WHERE strftime('%Y', check_in_date) = '2026'
              AND status IN ('Confirmed', 'Completed')
            GROUP BY room_type
            ORDER BY total_nights DESC
        """,
    },
    {
        "question": "Show the top 5 hotels by revenue in 2026.",
        "sql": """
            SELECT h.hotel_name, h.city,
                   COUNT(*) AS bookings,
                   ROUND(SUM(b.total_amount)/1e6, 3) AS revenue_mn_inr
            FROM bookings b
            JOIN hotels h ON b.hotel_id = h.hotel_id
            WHERE strftime('%Y', b.check_in_date) = '2026'
              AND b.status != 'Cancelled'
            GROUP BY h.hotel_id
            ORDER BY revenue_mn_inr DESC
            LIMIT 5
        """,
    },
    {
        "question": "How does Direct booking compare to OTA channel bookings?",
        "sql": """
            SELECT channel,
                   COUNT(*) AS total_bookings,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) AS pct_share,
                   ROUND(AVG(total_amount), 2) AS avg_booking_value_inr
            FROM bookings
            GROUP BY channel
            ORDER BY total_bookings DESC
        """,
    },
    {
        "question": "What percentage of bookings were cancelled in 2026?",
        "sql": """
            SELECT
                COUNT(*) AS total_bookings,
                SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled,
                ROUND(
                    SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) * 100.0 / COUNT(*),
                    1
                ) AS cancellation_pct
            FROM bookings
            WHERE strftime('%Y', check_in_date) = '2026'
        """,
    },
]


def run_checks():
    if not DB_FILE.exists():
        print(f"❌  Database not found: {DB_FILE}")
        print("    Run `python data/seed.py` first.")
        return

    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    print(f"\n✅  Connected to {DB_FILE.name}\n")
    print("=" * 65)

    for i, check in enumerate(CHECKS, 1):
        print(f"\n[Q{i}] {check['question']}")
        print("-" * 65)
        try:
            rows = cur.execute(check["sql"]).fetchall()
            if not rows:
                print("  ⚠️  No results returned — check date ranges or data.")
            else:
                # Print column headers
                headers = rows[0].keys()
                col_widths = [max(len(h), max(len(str(r[h])) for r in rows)) for h in headers]
                header_line = "  " + "  ".join(h.ljust(w) for h, w in zip(headers, col_widths))
                print(header_line)
                print("  " + "  ".join("-" * w for w in col_widths))
                for row in rows:
                    print("  " + "  ".join(str(row[h]).ljust(w) for h, w in zip(headers, col_widths)))
        except Exception as e:
            print(f"  ❌  SQL ERROR: {e}")

    print("\n" + "=" * 65)

    # Table counts
    print("\n── Row counts ──────────────────────────────────────────────────")
    for table in ["regions", "hotels", "customers", "bookings"]:
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<12} {count:>5} rows")

    conn.close()
    print("\n✅  All checks complete.\n")


if __name__ == "__main__":
    run_checks()
