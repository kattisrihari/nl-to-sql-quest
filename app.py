"""
app.py — Interactive CLI for the Hotel Bookings NL2SQL Agent.

Usage:
    python app.py
"""

from src.agent.graph import run_query

WELCOME = """
╔══════════════════════════════════════════════════════════╗
║         Hotel Bookings NL2SQL Agent                      ║
║         Ask questions in plain English.                  ║
║         Type 'exit' or 'quit' to stop.                   ║
╚══════════════════════════════════════════════════════════╝

Sample questions you can try:
  • How many bookings did we receive from each region during August 2026?
  • What is the average booking value by hotel star rating?
  • Show the top 5 hotels by revenue in 2026.
  • What percentage of bookings were cancelled in 2026?
  • How does Direct booking compare to OTA channel bookings?
"""

def main():
    print(WELCOME)

    while True:
        try:
            question = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not question:
            continue

        if question.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break

        print("\nAgent: thinking...\n")
        answer = run_query(question)
        print(f"Agent: {answer}\n")
        print("-" * 60)
        
if __name__ == "__main__":
    main()