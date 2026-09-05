"""
prompts.py — Schema context and few-shot examples fed to the LLM.

This is the most important file in the NL2SQL system.
The LLM has no idea what your database looks like — you have to tell it.
"""

# ── 1. Schema context ──────────────────────────────────────────────────────────
# This is injected into every prompt so the LLM knows your tables and columns.
# Think of it as the "memory" the LLM needs to write correct SQL.

SCHEMA_CONTEXT = """
You are an expert SQL assistant for a hotel bookings database (SQLite).

DATABASE SCHEMA:
---------------

Table: regions
  - region_id   INTEGER  PRIMARY KEY
  - region_name TEXT     (values: 'North', 'South', 'East', 'West', 'Central')
  - description TEXT

Table: hotels
  - hotel_id    INTEGER  PRIMARY KEY
  - hotel_name  TEXT
  - city        TEXT
  - region_id   INTEGER  FK → regions.region_id
  - star_rating INTEGER  (1 to 5)
  - total_rooms INTEGER
  - category    TEXT     (values: 'Budget', 'Business', 'Luxury', 'Resort')

Table: customers
  - customer_id  INTEGER  PRIMARY KEY
  - full_name    TEXT
  - email        TEXT
  - region_id    INTEGER  FK → regions.region_id  (customer's home region)
  - loyalty_tier TEXT     (values: 'Bronze', 'Silver', 'Gold', 'Platinum')

Table: bookings
  - booking_id     INTEGER  PRIMARY KEY
  - hotel_id       INTEGER  FK → hotels.hotel_id
  - customer_id    INTEGER  FK → customers.customer_id
  - check_in_date  DATE     (format: YYYY-MM-DD)
  - check_out_date DATE     (format: YYYY-MM-DD)
  - room_type      TEXT     (values: 'Standard', 'Deluxe', 'Suite', 'Presidential')
  - channel        TEXT     (values: 'Direct', 'OTA', 'Corporate', 'Travel Agent')
  - status         TEXT     (values: 'Confirmed', 'Cancelled', 'Completed', 'No-show')
  - num_guests     INTEGER
  - total_amount   REAL     (in INR)
  - created_at     DATE     (booking creation date, format: YYYY-MM-DD)

IMPORTANT RULES:
- Always use SQLite-compatible syntax
- SQLite does not have MEDIAN(). To calculate median, use:
  SELECT AVG(val) FROM (SELECT val FROM t ORDER BY val 
  LIMIT 2 - (SELECT COUNT(*) FROM t) % 2 
  OFFSET (SELECT (COUNT(*) - 1) / 2 FROM t)).
- For date filtering, use strftime('%Y-%m', date_column) = 'YYYY-MM' for month/year.
- For year range filtering, use strftime('%Y', date_column) BETWEEN 'YYYY' AND 'YYYY'.
- The hotel's region is in hotels.region_id (NOT customers.region_id) for location-based questions.
- total_amount is in Indian Rupees (INR).
- Never use DROP, DELETE, INSERT, UPDATE or any write operations.
- Always end SQL with a semicolon.
- Data only covers 2025 and 2026. If asked about other years, still run the query but results will be empty.
- Cities in the database are: New Delhi, Agra, Jaipur, Varanasi, Manali, Amritsar, Bengaluru, Chennai, Kovalam, Kochi, Mysuru, Coimbatore, Kolkata, Darjeeling, Bhubaneswar, Patna, Guwahati, Mumbai, Goa, Ahmedabad, Pune, Surat, Nashik, Indore, Bhopal, Raipur, Nagpur, Jabalpur.
- Karnataka is a state, not a city. Map state names to their cities: Karnataka → Bengaluru, Mysuru, Coimbatore. Use IN clause for multiple cities.
- For "months with no bookings" type questions, generate a WITH RECURSIVE CTE to enumerate all 12 months and LEFT JOIN against actual data. SQLite supports this.
- Do NOT use row_number() as a column name — it is a reserved window function keyword in SQLite.
"""

# ── 2. Few-shot examples ───────────────────────────────────────────────────────
# These teach the LLM the pattern: question → SQL.
# 2-3 good examples dramatically improve accuracy on new questions.

FEW_SHOT_EXAMPLES = """
EXAMPLES:
---------

Q: How many bookings did we receive from each region during August 2026?
SQL:
SELECT r.region_name, COUNT(*) AS bookings
FROM bookings b
JOIN hotels h ON b.hotel_id = h.hotel_id
JOIN regions r ON h.region_id = r.region_id
WHERE strftime('%Y-%m', b.check_in_date) = '2026-08'
GROUP BY r.region_name
ORDER BY bookings DESC;

Q: What is the average booking value by hotel star rating?
SQL:
SELECT h.star_rating || ' star' AS rating,
       ROUND(AVG(b.total_amount), 2) AS avg_booking_inr,
       COUNT(*) AS total_bookings
FROM bookings b
JOIN hotels h ON b.hotel_id = h.hotel_id
WHERE b.status != 'Cancelled'
GROUP BY h.star_rating
ORDER BY h.star_rating DESC;

Q: What percentage of bookings were cancelled in 2026?
SQL:
SELECT
    COUNT(*) AS total_bookings,
    SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled,
    ROUND(
        SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1
    ) AS cancellation_pct
FROM bookings
WHERE strftime('%Y', check_in_date) = '2026';

Q: Are there months with no bookings in 2026?
SQL:
SELECT strftime('%Y-%m', check_in_date) AS month, COUNT(*) AS bookings
FROM bookings
WHERE strftime('%Y', check_in_date) = '2026'
GROUP BY month
ORDER BY month;
"""

# ── 3. SQL generation prompt ───────────────────────────────────────────────────
# This is the full prompt sent to the LLM for generating SQL.

SQL_GENERATION_PROMPT = SCHEMA_CONTEXT + FEW_SHOT_EXAMPLES + """
Now answer the following question by writing ONLY the SQL query.
Do not explain. Do not add markdown. Just the raw SQL.

Q: {question}
SQL:
"""

# ── 4. Answer synthesis prompt ─────────────────────────────────────────────────
# After SQL runs, this prompt turns raw results into a plain-English answer.

SYNTHESIS_PROMPT = """
A business user asked: "{question}"

The SQL query returned these results:
{results}

Write a clear, concise answer in 2-3 sentences as if you're a data analyst 
explaining to a non-technical hotel manager. Include the key numbers.

If the question asks about missing or empty months, check if all 12 months appear 
in the results. If yes, say no months were empty. If some are missing, name them.

Do not mention SQL or databases.
Do not use markdown headers, bullet points, or formatting — plain prose only.
If the results are empty, say clearly that no data was found for that query 
and suggest why (e.g. date range not in dataset, location not found).
"""

SCOPE_CHECK_PROMPT = """
You are a strict classifier. Reply only 'YES' or 'NO'.

Reply YES if the question is about ANY of these topics related to a hotel business:
- Hotel bookings, reservations, cancellations, no-shows
- Hotel revenue, pricing, spending, costs
- Hotel or room performance, occupancy, ratings
- Customers, loyalty tiers, spending behavior
- Regions, cities, locations of hotels
- Time periods, seasons, monthly or yearly trends
- Comparisons between hotels, regions, time periods
- Any analytical question that could be answered using booking, hotel, customer, or region data
- total_amount is the TOTAL booking amount for the entire stay, not per night.
  To get nightly rate, use: total_amount / (julianday(check_out_date) - julianday(check_in_date))
  For "under X per night" questions, filter using this calculation.

Reply YES for short or casual phrasings like "hotels in [city]", "bookings in [year]", 
"list of [anything hotel related]" — assume hotel context even without explicit keywords.

Reply NO only if the question is completely unrelated to hotels or bookings 
(weather, sports, news, coding, general knowledge etc.)
or if it attempts to modify, delete, or export raw database records.

Reply NO if the question asks for information not stored in the database 
(weather, live data, external information,general details of others living in the same hotel or region irrelevant to the db) even if it mentions hotel related topics mentioned above.
Question: {question}
"""