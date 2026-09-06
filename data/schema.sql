-- ============================================================
-- Hotel Bookings NL2SQL - Schema
-- ============================================================

-- Regions of India
CREATE TABLE IF NOT EXISTS regions (
    region_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    region_name TEXT NOT NULL UNIQUE,       -- North, South, East, West, Central
    description TEXT
);

-- Hotels across India
CREATE TABLE IF NOT EXISTS hotels (
    hotel_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_name   TEXT NOT NULL,
    city         TEXT NOT NULL,
    region_id    INTEGER NOT NULL REFERENCES regions(region_id),
    star_rating  INTEGER CHECK (star_rating BETWEEN 1 AND 5),
    total_rooms  INTEGER NOT NULL,
    category     TEXT CHECK (category IN ('Budget', 'Business', 'Luxury', 'Resort'))
);

-- Customers who make bookings
CREATE TABLE IF NOT EXISTS customers (
    customer_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name      TEXT NOT NULL,
    email          TEXT UNIQUE NOT NULL,
    region_id      INTEGER NOT NULL REFERENCES regions(region_id), -- customer's home region
    loyalty_tier   TEXT CHECK (loyalty_tier IN ('Bronze', 'Silver', 'Gold', 'Platinum'))
);

-- Bookings (the main fact table)
CREATE TABLE IF NOT EXISTS bookings (
    booking_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    hotel_id        INTEGER NOT NULL REFERENCES hotels(hotel_id),
    customer_id     INTEGER NOT NULL REFERENCES customers(customer_id),
    check_in_date   DATE NOT NULL,
    check_out_date  DATE NOT NULL,
    room_type       TEXT CHECK (room_type IN ('Standard', 'Deluxe', 'Suite', 'Presidential')),
    channel         TEXT CHECK (channel IN ('Direct', 'OTA', 'Corporate', 'Travel Agent')),
    status          TEXT CHECK (status IN ('Confirmed', 'Cancelled', 'Completed', 'No-show')),
    num_guests      INTEGER DEFAULT 1,
    total_amount    REAL NOT NULL,          -- in INR
    created_at      DATE NOT NULL           -- booking creation date
);

-- Indexes for common query patterns
CREATE INDEX IF NOT EXISTS idx_bookings_hotel     ON bookings(hotel_id);
CREATE INDEX IF NOT EXISTS idx_bookings_customer  ON bookings(customer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_checkin   ON bookings(check_in_date);
CREATE INDEX IF NOT EXISTS idx_bookings_created   ON bookings(created_at);
CREATE INDEX IF NOT EXISTS idx_bookings_status    ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_hotels_region      ON hotels(region_id);
CREATE INDEX IF NOT EXISTS idx_customers_region   ON customers(region_id);
