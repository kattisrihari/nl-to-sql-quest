"""
seed.py — Generates realistic dummy data for the hotel bookings NL2SQL demo.

Usage:
    python data/seed.py

Output:
    data/hotel_bookings.db  (SQLite database, ~500-1000 bookings)
"""

import sqlite3
import random
import os
from datetime import date, timedelta
from pathlib import Path

# ── Reproducibility ────────────────────────────────────────────────────────────
random.seed(42)

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
SCHEMA_FILE = BASE_DIR / "schema.sql"
DB_FILE = BASE_DIR / "hotel_bookings.db"


# ── Master data ────────────────────────────────────────────────────────────────

REGIONS = [
    ("North", "Delhi, Rajasthan, UP, Himachal Pradesh"),
    ("South", "Tamil Nadu, Karnataka, Kerala, Andhra Pradesh"),
    ("East",  "West Bengal, Odisha, Bihar, Jharkhand"),
    ("West",  "Maharashtra, Goa, Gujarat, Rajasthan West"),
    ("Central", "Madhya Pradesh, Chhattisgarh, Telangana"),
]

# (name, city, region_name, star, total_rooms, category)
HOTELS = [
    # North
    ("The Imperial New Delhi",   "New Delhi",   "North", 5, 235, "Luxury"),
    ("Taj Hotel & Convention",   "Agra",        "North", 5, 180, "Luxury"),
    ("Rambagh Palace",           "Jaipur",      "North", 5, 78,  "Resort"),
    ("Hotel Clarks Varanasi",    "Varanasi",    "North", 4, 130, "Business"),
    ("Snow Valley Resorts",      "Manali",      "North", 3, 60,  "Resort"),
    ("Budget Inn Amritsar",      "Amritsar",    "North", 2, 50,  "Budget"),

    # South
    ("Leela Palace Bengaluru",   "Bengaluru",   "South", 5, 357, "Luxury"),
    ("ITC Grand Chola",          "Chennai",     "South", 5, 600, "Luxury"),
    ("Taj Kovalam Resort",       "Kovalam",     "South", 5, 60,  "Resort"),
    ("Radisson Blu Kochi",       "Kochi",       "South", 4, 280, "Business"),
    ("Hotel Sandesh",            "Mysuru",      "South", 3, 80,  "Business"),
    ("Budget Stay Coimbatore",   "Coimbatore",  "South", 2, 45,  "Budget"),

    # East
    ("Oberoi Grand Kolkata",     "Kolkata",     "East",  5, 209, "Luxury"),
    ("Mayfair Darjeeling",       "Darjeeling",  "East",  4, 75,  "Resort"),
    ("Vivanta Bhubaneswar",      "Bhubaneswar", "East",  4, 168, "Business"),
    ("Hotel Patliputra Cont.",   "Patna",       "East",  3, 100, "Business"),
    ("Budget Lodge Guwahati",    "Guwahati",    "East",  2, 40,  "Budget"),

    # West
    ("Taj Mahal Palace Mumbai",  "Mumbai",      "West",  5, 285, "Luxury"),
    ("Leela Goa",                "Goa",         "West",  5, 206, "Resort"),
    ("Taj Ummed Ahmedabad",      "Ahmedabad",   "West",  5, 168, "Business"),
    ("Radisson Blu Pune",        "Pune",        "West",  4, 287, "Business"),
    ("Hotel Surat Regency",      "Surat",       "West",  3, 90,  "Business"),
    ("Budget Rooms Nashik",      "Nashik",      "West",  2, 35,  "Budget"),

    # Central
    ("Marriott Indore",          "Indore",      "Central", 5, 218, "Luxury"),
    ("Jehan Numa Palace",        "Bhopal",      "Central", 4, 100, "Business"),
    ("Hyatt Raipur",             "Raipur",      "Central", 4, 180, "Business"),
    ("Hotel Aditya Nagpur",      "Nagpur",      "Central", 3, 75,  "Business"),
    ("Budget Inn Jabalpur",      "Jabalpur",    "Central", 2, 40,  "Budget"),
]

# First names and last names for realistic Indian customer names
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Sai", "Arjun", "Reyansh", "Ayaan", "Krishna",
    "Ishaan", "Shaurya", "Atharv", "Advik", "Pranav", "Advaith", "Dhruv",
    "Priya", "Ananya", "Aadhya", "Diya", "Saanvi", "Anya", "Kiara", "Myra",
    "Kavya", "Anika", "Riya", "Shreya", "Nisha", "Pooja", "Meera",
    "Rohan", "Vikram", "Rahul", "Amit", "Nikhil", "Karan", "Siddharth",
    "Anjali", "Deepa", "Sunita", "Radha", "Geeta", "Lalita", "Rekha",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Mehta", "Joshi", "Nair", "Pillai", "Reddy",
    "Rao", "Iyer", "Gupta", "Singh", "Kumar", "Das", "Chatterjee", "Mukherjee",
    "Agarwal", "Shah", "Desai", "Mishra", "Tiwari", "Pandey", "Chaudhary",
    "Bose", "Sen", "Ghosh", "Sinha", "Roy", "Kapoor", "Malhotra",
]

LOYALTY_TIERS  = ["Bronze", "Silver", "Gold", "Platinum"]
LOYALTY_WEIGHTS = [0.40,    0.30,    0.20,   0.10]

ROOM_TYPES      = ["Standard", "Deluxe", "Suite", "Presidential"]
CHANNELS        = ["Direct", "OTA", "Corporate", "Travel Agent"]
CHANNEL_WEIGHTS = [0.30,    0.40,  0.20,      0.10]

# Room pricing bands in INR per night (min, max) by room type
ROOM_PRICES = {
    "Standard":     (2_000,  6_000),
    "Deluxe":       (5_000, 12_000),
    "Suite":       (12_000, 35_000),
    "Presidential":(40_000, 1_50_000),
}

# Room type availability by hotel star rating
ROOM_TYPE_BY_STARS = {
    5: ["Standard", "Deluxe", "Suite", "Presidential"],
    4: ["Standard", "Deluxe", "Suite"],
    3: ["Standard", "Deluxe"],
    2: ["Standard"],
}

# Booking status distribution
STATUSES        = ["Completed", "Confirmed", "Cancelled", "No-show"]
STATUS_WEIGHTS  = [0.60,        0.20,        0.15,        0.05]

# ── Seasonality: monthly booking volume multipliers ────────────────────────────
# Peak: Oct-Nov (festive), Dec-Jan (winter tourism), Aug (end of year travel)
# Low: June-July (monsoon)
MONTHLY_WEIGHTS = {
    1:  1.3,   # Jan — winter tourism
    2:  1.1,   # Feb
    3:  1.0,   # Mar
    4:  0.9,   # Apr
    5:  0.8,   # May — heat
    6:  0.5,   # Jun — monsoon low
    7:  0.5,   # Jul — monsoon low
    8:  1.4,   # Aug — intentionally high (matches sample question)
    9:  1.0,   # Sep
    10: 1.5,   # Oct — festive season peak
    11: 1.4,   # Nov — festive/winter
    12: 1.3,   # Dec — holiday season
}


# ── Helpers ────────────────────────────────────────────────────────────────────

def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def weighted_choice(choices, weights):
    return random.choices(choices, weights=weights, k=1)[0]


def generate_email(name: str, idx: int) -> str:
    providers = ["gmail.com", "yahoo.in", "outlook.com", "rediffmail.com", "hotmail.com"]
    slug = name.lower().replace(" ", ".") + str(idx)
    return f"{slug}@{random.choice(providers)}"


def booking_amount(room_type: str, nights: int, star: int) -> float:
    lo, hi = ROOM_PRICES[room_type]
    # 5-star hotels skew toward higher end
    skew = 0.5 + (star - 1) * 0.12
    nightly = lo + (hi - lo) * random.betavariate(2, max(1, 4 - star))
    return round(nightly * nights, 2)


# ── Build date pool with seasonality ──────────────────────────────────────────

def build_date_pool(n_bookings: int) -> list[date]:
    """Return n_bookings check-in dates distributed across 2025-2026 with seasonal weights."""
    start = date(2025, 1, 1)
    end   = date(2026, 12, 31)
    total_days = (end - start).days + 1

    # Build day-level weights
    days, weights = [], []
    for i in range(total_days):
        d = start + timedelta(days=i)
        days.append(d)
        weights.append(MONTHLY_WEIGHTS[d.month])

    return random.choices(days, weights=weights, k=n_bookings)


# ── Main seeding function ──────────────────────────────────────────────────────

def seed(n_customers: int = 200, n_bookings: int = 800):
    # Remove existing DB
    if DB_FILE.exists():
        DB_FILE.unlink()
        print(f"  Removed existing {DB_FILE.name}")

    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()

    # Apply schema
    with open(SCHEMA_FILE) as f:
        cur.executescript(f.read())
    print("  Schema applied.")

    # ── 1. Regions ─────────────────────────────────────────────────────────────
    cur.executemany(
        "INSERT INTO regions (region_name, description) VALUES (?, ?)",
        REGIONS
    )
    region_rows = cur.execute("SELECT region_id, region_name FROM regions").fetchall()
    region_map  = {name: rid for rid, name in region_rows}
    print(f"  Inserted {len(region_map)} regions.")

    # ── 2. Hotels ──────────────────────────────────────────────────────────────
    hotel_inserts = [
        (name, city, region_map[region], stars, rooms, cat)
        for name, city, region, stars, rooms, cat in HOTELS
    ]
    cur.executemany(
        "INSERT INTO hotels (hotel_name, city, region_id, star_rating, total_rooms, category) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        hotel_inserts
    )
    hotel_rows = cur.execute(
        "SELECT hotel_id, region_id, star_rating FROM hotels"
    ).fetchall()
    print(f"  Inserted {len(hotel_rows)} hotels.")

    # ── 3. Customers ───────────────────────────────────────────────────────────
    used_emails = set()
    customer_data = []
    for i in range(n_customers):
        fname   = random.choice(FIRST_NAMES)
        lname   = random.choice(LAST_NAMES)
        name    = f"{fname} {lname}"
        email   = generate_email(name, i)
        while email in used_emails:
            email = generate_email(name, i + random.randint(100, 999))
        used_emails.add(email)
        region_id = random.choice(list(region_map.values()))
        tier      = weighted_choice(LOYALTY_TIERS, LOYALTY_WEIGHTS)
        customer_data.append((name, email, region_id, tier))

    cur.executemany(
        "INSERT INTO customers (full_name, email, region_id, loyalty_tier) VALUES (?, ?, ?, ?)",
        customer_data
    )
    customer_ids = [
        r[0] for r in cur.execute("SELECT customer_id FROM customers").fetchall()
    ]
    print(f"  Inserted {len(customer_ids)} customers.")

    # ── 4. Bookings ────────────────────────────────────────────────────────────
    check_in_dates = build_date_pool(n_bookings)
    booking_data   = []

    for check_in in check_in_dates:
        hotel_id, hotel_region_id, stars = random.choice(hotel_rows)
        customer_id = random.choice(customer_ids)

        # Stay duration: 1–7 nights, weighted toward shorter stays
        nights       = random.choices([1,2,3,4,5,6,7], weights=[30,28,20,10,6,4,2])[0]
        check_out    = check_in + timedelta(days=nights)

        room_type    = random.choice(ROOM_TYPE_BY_STARS[stars])
        channel      = weighted_choice(CHANNELS, CHANNEL_WEIGHTS)
        status       = weighted_choice(STATUSES, STATUS_WEIGHTS)
        num_guests   = random.choices([1,2,3,4], weights=[35,40,15,10])[0]
        amount       = booking_amount(room_type, nights, stars)

        # Booking created 1–90 days before check-in
        lead_days    = random.randint(1, 90)
        created_at   = check_in - timedelta(days=lead_days)
        # Keep created_at within our data range
        created_at   = max(created_at, date(2025, 1, 1))

        booking_data.append((
            hotel_id, customer_id,
            check_in.isoformat(), check_out.isoformat(),
            room_type, channel, status,
            num_guests, amount, created_at.isoformat()
        ))

    cur.executemany(
        """INSERT INTO bookings
           (hotel_id, customer_id, check_in_date, check_out_date,
            room_type, channel, status, num_guests, total_amount, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        booking_data
    )
    print(f"  Inserted {len(booking_data)} bookings.")

    conn.commit()
    conn.close()
    print(f"\n  ✅  Database created: {DB_FILE}")
    print(f"      Size: {DB_FILE.stat().st_size / 1024:.1f} KB")


# ── Quick sanity preview ───────────────────────────────────────────────────────

def preview():
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()

    print("\n── Bookings by region (all time) ──────────────────────────────")
    rows = cur.execute("""
        SELECT r.region_name, COUNT(*) AS total_bookings
        FROM bookings b
        JOIN hotels h ON b.hotel_id = h.hotel_id
        JOIN regions r ON h.region_id = r.region_id
        GROUP BY r.region_name
        ORDER BY total_bookings DESC
    """).fetchall()
    for row in rows:
        print(f"  {row[0]:<10} {row[1]} bookings")

    print("\n── Bookings per region — August 2026 (sample question) ────────")
    rows = cur.execute("""
        SELECT r.region_name, COUNT(*) AS bookings
        FROM bookings b
        JOIN hotels h ON b.hotel_id = h.hotel_id
        JOIN regions r ON h.region_id = r.region_id
        WHERE strftime('%Y-%m', b.check_in_date) = '2026-08'
        GROUP BY r.region_name
        ORDER BY bookings DESC
    """).fetchall()
    for row in rows:
        print(f"  {row[0]:<10} {row[1]} bookings")

    print("\n── Booking status breakdown ────────────────────────────────────")
    rows = cur.execute("""
        SELECT status, COUNT(*) FROM bookings GROUP BY status ORDER BY 2 DESC
    """).fetchall()
    for row in rows:
        print(f"  {row[0]:<12} {row[1]}")

    print("\n── Revenue by hotel category ───────────────────────────────────")
    rows = cur.execute("""
        SELECT h.category,
               COUNT(*) AS bookings,
               ROUND(SUM(b.total_amount)/1e6, 2) AS revenue_mn_inr
        FROM bookings b
        JOIN hotels h ON b.hotel_id = h.hotel_id
        WHERE b.status != 'Cancelled'
        GROUP BY h.category
        ORDER BY revenue_mn_inr DESC
    """).fetchall()
    for row in rows:
        print(f"  {row[0]:<10}  {row[1]} bookings  ₹{row[2]}M revenue")

    conn.close()


if __name__ == "__main__":
    print("\n🌱  Seeding hotel_bookings.db...\n")
    seed(n_customers=200, n_bookings=800)
    preview()
    print("\nDone. Run verify.py for full checks.\n")
