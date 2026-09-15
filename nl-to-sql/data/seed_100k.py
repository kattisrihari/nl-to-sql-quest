"""
seed_100k.py — Generates scaled dummy data: 1000 customers, 100000 bookings.
Same schema, same hotels, same value distributions as seed.py.
Outputs: data/hotel_bookings_100k.db

Usage:
    python data/seed_100k.py
"""

import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path
import time

random.seed(77)

BASE_DIR    = Path(__file__).parent
SCHEMA_FILE = BASE_DIR / "schema.sql"
DB_FILE     = BASE_DIR / "hotel_bookings_100k.db"

REGIONS = [
    ("North",   "Delhi, Rajasthan, UP, Himachal Pradesh"),
    ("South",   "Tamil Nadu, Karnataka, Kerala, Andhra Pradesh"),
    ("East",    "West Bengal, Odisha, Bihar, Jharkhand"),
    ("West",    "Maharashtra, Goa, Gujarat, Rajasthan West"),
    ("Central", "Madhya Pradesh, Chhattisgarh, Telangana"),
]

HOTELS = [
    ("The Imperial New Delhi",  "New Delhi",   "North",   5, 235, "Luxury"),
    ("Taj Hotel & Convention",  "Agra",        "North",   5, 180, "Luxury"),
    ("Rambagh Palace",          "Jaipur",      "North",   5, 78,  "Resort"),
    ("Hotel Clarks Varanasi",   "Varanasi",    "North",   4, 130, "Business"),
    ("Snow Valley Resorts",     "Manali",      "North",   3, 60,  "Resort"),
    ("Budget Inn Amritsar",     "Amritsar",    "North",   2, 50,  "Budget"),
    ("Leela Palace Bengaluru",  "Bengaluru",   "South",   5, 357, "Luxury"),
    ("ITC Grand Chola",         "Chennai",     "South",   5, 600, "Luxury"),
    ("Taj Kovalam Resort",      "Kovalam",     "South",   5, 60,  "Resort"),
    ("Radisson Blu Kochi",      "Kochi",       "South",   4, 280, "Business"),
    ("Hotel Sandesh",           "Mysuru",      "South",   3, 80,  "Business"),
    ("Budget Stay Coimbatore",  "Coimbatore",  "South",   2, 45,  "Budget"),
    ("Oberoi Grand Kolkata",    "Kolkata",     "East",    5, 209, "Luxury"),
    ("Mayfair Darjeeling",      "Darjeeling",  "East",    4, 75,  "Resort"),
    ("Vivanta Bhubaneswar",     "Bhubaneswar", "East",    4, 168, "Business"),
    ("Hotel Patliputra Cont.",  "Patna",       "East",    3, 100, "Business"),
    ("Budget Lodge Guwahati",   "Guwahati",    "East",    2, 40,  "Budget"),
    ("Taj Mahal Palace Mumbai", "Mumbai",      "West",    5, 285, "Luxury"),
    ("Leela Goa",               "Goa",         "West",    5, 206, "Resort"),
    ("Taj Ummed Ahmedabad",     "Ahmedabad",   "West",    5, 168, "Business"),
    ("Radisson Blu Pune",       "Pune",        "West",    4, 287, "Business"),
    ("Hotel Surat Regency",     "Surat",       "West",    3, 90,  "Business"),
    ("Budget Rooms Nashik",     "Nashik",      "West",    2, 35,  "Budget"),
    ("Marriott Indore",         "Indore",      "Central", 5, 218, "Luxury"),
    ("Jehan Numa Palace",       "Bhopal",      "Central", 4, 100, "Business"),
    ("Hyatt Raipur",            "Raipur",      "Central", 4, 180, "Business"),
    ("Hotel Aditya Nagpur",     "Nagpur",      "Central", 3, 75,  "Business"),
    ("Budget Inn Jabalpur",     "Jabalpur",    "Central", 2, 40,  "Budget"),
]

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Sai", "Arjun", "Reyansh", "Ayaan", "Krishna",
    "Ishaan", "Shaurya", "Atharv", "Advik", "Pranav", "Advaith", "Dhruv",
    "Priya", "Ananya", "Aadhya", "Diya", "Saanvi", "Anya", "Kiara", "Myra",
    "Kavya", "Anika", "Riya", "Shreya", "Nisha", "Pooja", "Meera",
    "Rohan", "Vikram", "Rahul", "Amit", "Nikhil", "Karan", "Siddharth",
    "Anjali", "Deepa", "Sunita", "Radha", "Geeta", "Lalita", "Rekha",
    "Aryan", "Dev", "Kabir", "Vihaan", "Rudra", "Ranbir", "Zara",
    "Navya", "Sia", "Tara", "Mira", "Isha", "Raina", "Aanya",
    "Harsh", "Yash", "Kunal", "Akash", "Varun", "Mohit", "Rajesh",
    "Sneha", "Preeti", "Divya", "Swati", "Neha", "Pallavi", "Shweta",
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Mehta", "Joshi", "Nair", "Pillai", "Reddy",
    "Rao", "Iyer", "Gupta", "Singh", "Kumar", "Das", "Chatterjee", "Mukherjee",
    "Agarwal", "Shah", "Desai", "Mishra", "Tiwari", "Pandey", "Chaudhary",
    "Bose", "Sen", "Ghosh", "Sinha", "Roy", "Kapoor", "Malhotra",
    "Kulkarni", "Naik", "Hegde", "Menon", "Krishnan", "Subramaniam",
    "Banerjee", "Dutta", "Chakraborty", "Mandal", "Biswas", "Sarkar",
    "Tripathi", "Shukla", "Saxena", "Srivastava", "Yadav", "Dubey",
]

LOYALTY_TIERS   = ["Bronze", "Silver", "Gold", "Platinum"]
LOYALTY_WEIGHTS = [0.40,     0.30,     0.20,   0.10]

CHANNELS        = ["Direct", "OTA", "Corporate", "Travel Agent"]
CHANNEL_WEIGHTS = [0.30,     0.40,  0.20,        0.10]

ROOM_PRICES = {
    "Standard":      (2_000,   6_000),
    "Deluxe":        (5_000,  12_000),
    "Suite":        (12_000,  35_000),
    "Presidential": (40_000, 150_000),
}

ROOM_TYPE_BY_STARS = {
    5: ["Standard", "Deluxe", "Suite", "Presidential"],
    4: ["Standard", "Deluxe", "Suite"],
    3: ["Standard", "Deluxe"],
    2: ["Standard"],
}

STATUSES        = ["Completed", "Confirmed", "Cancelled", "No-show"]
STATUS_WEIGHTS  = [0.60,        0.20,        0.15,        0.05]

MONTHLY_WEIGHTS = {
    1: 1.3, 2: 1.1, 3: 1.0, 4: 0.9,  5: 0.8,
    6: 0.5, 7: 0.5, 8: 1.4, 9: 1.0, 10: 1.5,
    11: 1.4, 12: 1.3,
}


def weighted_choice(choices, weights):
    return random.choices(choices, weights=weights, k=1)[0]

def generate_email(name: str, idx: int) -> str:
    providers = ["gmail.com", "yahoo.in", "outlook.com", "rediffmail.com", "hotmail.com"]
    slug = name.lower().replace(" ", ".") + str(idx)
    return f"{slug}@{random.choice(providers)}"

def booking_amount(room_type: str, nights: int, star: int) -> float:
    lo, hi = ROOM_PRICES[room_type]
    nightly = lo + (hi - lo) * random.betavariate(2, max(1, 4 - star))
    return round(nightly * nights, 2)

def build_date_pool(n: int) -> list:
    start = date(2025, 1, 1)
    end   = date(2026, 12, 31)
    days, weights = [], []
    for i in range((end - start).days + 1):
        d = start + timedelta(days=i)
        days.append(d)
        weights.append(MONTHLY_WEIGHTS[d.month])
    return random.choices(days, weights=weights, k=n)


def seed(n_customers: int = 1000, n_bookings: int = 100_000):
    if DB_FILE.exists():
        DB_FILE.unlink()
        print(f"  Removed existing {DB_FILE.name}")

    conn = sqlite3.connect(DB_FILE)
    # Performance pragmas for bulk insert
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=10000")
    cur = conn.cursor()

    with open(SCHEMA_FILE) as f:
        cur.executescript(f.read())
    print("  Schema applied.")

    # Regions
    cur.executemany("INSERT INTO regions (region_name, description) VALUES (?, ?)", REGIONS)
    region_map = {name: rid for rid, name in cur.execute("SELECT region_id, region_name FROM regions").fetchall()}
    print(f"  Inserted {len(region_map)} regions.")

    # Hotels
    cur.executemany(
        "INSERT INTO hotels (hotel_name, city, region_id, star_rating, total_rooms, category) VALUES (?, ?, ?, ?, ?, ?)",
        [(name, city, region_map[region], stars, rooms, cat) for name, city, region, stars, rooms, cat in HOTELS]
    )
    hotel_rows = cur.execute("SELECT hotel_id, region_id, star_rating FROM hotels").fetchall()
    print(f"  Inserted {len(hotel_rows)} hotels.")

    # Customers
    used_emails, customer_data = set(), []
    for i in range(n_customers):
        fname = random.choice(FIRST_NAMES)
        lname = random.choice(LAST_NAMES)
        name  = f"{fname} {lname}"
        email = generate_email(name, i)
        while email in used_emails:
            email = generate_email(name, i + random.randint(100, 999))
        used_emails.add(email)
        customer_data.append((
            name, email,
            random.choice(list(region_map.values())),
            weighted_choice(LOYALTY_TIERS, LOYALTY_WEIGHTS)
        ))

    cur.executemany("INSERT INTO customers (full_name, email, region_id, loyalty_tier) VALUES (?, ?, ?, ?)", customer_data)
    customer_ids = [r[0] for r in cur.execute("SELECT customer_id FROM customers").fetchall()]
    print(f"  Inserted {len(customer_ids)} customers.")

    # Bookings — batch insert in chunks of 10k for memory efficiency
    print(f"  Generating {n_bookings} bookings...")
    check_in_dates = build_date_pool(n_bookings)
    t0 = time.time()

    BATCH_SIZE = 10_000
    for batch_start in range(0, n_bookings, BATCH_SIZE):
        batch = check_in_dates[batch_start:batch_start + BATCH_SIZE]
        booking_data = []
        for check_in in batch:
            hotel_id, _, stars = random.choice(hotel_rows)
            customer_id = random.choice(customer_ids)
            nights      = random.choices([1,2,3,4,5,6,7], weights=[30,28,20,10,6,4,2])[0]
            check_out   = check_in + timedelta(days=nights)
            room_type   = random.choice(ROOM_TYPE_BY_STARS[stars])
            channel     = weighted_choice(CHANNELS, CHANNEL_WEIGHTS)
            status      = weighted_choice(STATUSES, STATUS_WEIGHTS)
            num_guests  = random.choices([1,2,3,4], weights=[35,40,15,10])[0]
            amount      = booking_amount(room_type, nights, stars)
            created_at  = max(check_in - timedelta(days=random.randint(1, 90)), date(2025, 1, 1))
            booking_data.append((
                hotel_id, customer_id,
                check_in.isoformat(), check_out.isoformat(),
                room_type, channel, status,
                num_guests, amount, created_at.isoformat()
            ))

        cur.executemany(
            "INSERT INTO bookings (hotel_id, customer_id, check_in_date, check_out_date, room_type, channel, status, num_guests, total_amount, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            booking_data
        )
        conn.commit()
        done = min(batch_start + BATCH_SIZE, n_bookings)
        print(f"    {done:>7} / {n_bookings} inserted ({done*100//n_bookings}%)")

    t1 = time.time()
    print(f"  Booking insert time: {t1-t0:.2f}s")
    conn.close()
    print(f"\n  DB: {DB_FILE}")
    print(f"  Size: {DB_FILE.stat().st_size / 1024 / 1024:.1f} MB")


def preview():
    conn = sqlite3.connect(DB_FILE)
    cur  = conn.cursor()
    print("\n── Row counts ──")
    for t in ["regions", "hotels", "customers", "bookings"]:
        print(f"  {t:<12} {cur.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>8}")

    print("\n── August 2026 bookings by region ──")
    t0 = time.time()
    rows = cur.execute("""
        SELECT r.region_name, COUNT(*)
        FROM bookings b
        JOIN hotels h ON b.hotel_id = h.hotel_id
        JOIN regions r ON h.region_id = r.region_id
        WHERE strftime('%Y-%m', b.check_in_date) = '2026-08'
        GROUP BY r.region_name
        ORDER BY 2 DESC
    """).fetchall()
    t1 = time.time()
    for row in rows:
        print(f"  {row[0]:<10} {row[1]}")
    print(f"  Query time: {t1-t0:.4f}s")

    print("\n── Status breakdown ──")
    for row in cur.execute("SELECT status, COUNT(*) FROM bookings GROUP BY status ORDER BY 2 DESC").fetchall():
        print(f"  {row[0]:<12} {row[1]:>8}")

    print("\n── Revenue by category (non-cancelled) ──")
    for row in cur.execute("""
        SELECT h.category, COUNT(*) AS bookings, ROUND(SUM(b.total_amount)/1e7, 2) AS revenue_cr
        FROM bookings b JOIN hotels h ON b.hotel_id=h.hotel_id
        WHERE b.status != 'Cancelled'
        GROUP BY h.category ORDER BY revenue_cr DESC
    """).fetchall():
        print(f"  {row[0]:<10} {row[1]:>7} bookings  ₹{row[2]} Cr")

    conn.close()


if __name__ == "__main__":
    print("\n🌱  Seeding hotel_bookings_100k.db (1000 customers, 100000 bookings)...\n")
    seed()
    preview()
    print("\nDone. To use: update DB_PATH in src/agent/tools.py to hotel_bookings_100k.db\n")
