# 🏨 Hotel Bookings NL2SQL Agent

An AI-powered Natural Language to SQL solution that lets business users ask plain-English questions about hotel bookings and get meaningful answers from the underlying database.

Built with **LangGraph**, **LangChain**, and **Claude Haiku 4.5**, backed by a **SQLite** database of Indian hotel bookings (2025–2026).

---

## Schema

```
regions   → 5 Indian regions (North, South, East, West, Central)
hotels    → 28 hotels across India (2–5 star, Budget to Luxury)
customers → 200 customers with loyalty tiers
bookings  → 800 bookings with room type, channel, status, revenue
```

---

## Sample Questions

| # | Question |
|---|----------|
| 1 | How many bookings did we receive from each region during August 2026? |
| 2 | What is the average booking value by hotel star rating? |
| 3 | Which room type had the highest occupancy in 2026? |
| 4 | Show the top 5 hotels by revenue in 2026 |
| 5 | How does Direct booking compare to OTA channel bookings? |
| 6 | What percentage of bookings were cancelled in 2026? |

---

## Setup

```bash
# 1. Clone
git clone https://github.com/<your-username>/hotel_nl2sql.git
cd hotel_nl2sql

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create the database
python data/seed.py

# 4. Verify data
python data/verify.py

# 5. Add your API key
cp .env.example .env
# Edit .env → add ANTHROPIC_API_KEY

# 6. Run the agent
python src/app.py
```

---

## Architecture

> _To be documented — agent flow diagram goes here_

---

## Tech Stack

- **LLM**: Claude Haiku 4.5 (Anthropic)
- **Agent framework**: LangGraph + LangChain
- **Database**: SQLite
- **UI**: Gradio / Chainlit _(TBD)_
- **SQL validation**: sqlglot

---

## License

MIT
