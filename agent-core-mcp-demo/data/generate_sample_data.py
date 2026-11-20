"""Generate sample CSV data files for the AgentCore MCP demo.

Produces three CSVs with realistic UK financial data patterns:
- customers.csv (~1000 records)
- transactions.csv (~5000 records)
- risk_scores.csv (~1000 records)

Usage:
    python data/generate_sample_data.py
"""

import csv
import os
import random
from datetime import date, timedelta

# Seed for reproducibility
random.seed(42)

# Output directory (relative to project root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "sample")

# --- Reference data ---

UK_FIRST_NAMES = [
    "Oliver", "George", "Harry", "Jack", "Jacob", "Noah", "Charlie", "Thomas",
    "Oscar", "William", "James", "Leo", "Alfie", "Henry", "Archie", "Joshua",
    "Edward", "Alexander", "Samuel", "Daniel", "Freddie", "Benjamin", "Joseph",
    "Arthur", "Ethan", "Sebastian", "Adam", "Ryan", "Lucas", "Dylan",
    "Olivia", "Amelia", "Isla", "Ava", "Emily", "Sophia", "Grace", "Mia",
    "Poppy", "Ella", "Lily", "Jessica", "Charlotte", "Sophie", "Daisy",
    "Alice", "Freya", "Isabella", "Evie", "Ruby", "Hannah", "Florence",
    "Lucy", "Eleanor", "Phoebe", "Matilda", "Rosie", "Millie", "Sienna",
    "Elizabeth", "Martha", "Sarah", "Harriet", "Imogen", "Scarlett", "Ivy",
]

UK_SURNAMES = [
    "Smith", "Jones", "Williams", "Taylor", "Brown", "Davies", "Evans",
    "Wilson", "Thomas", "Roberts", "Johnson", "Lewis", "Walker", "Robinson",
    "Wood", "Thompson", "White", "Watson", "Jackson", "Wright", "Green",
    "Harris", "Cooper", "King", "Lee", "Martin", "Clarke", "James", "Morgan",
    "Hughes", "Edwards", "Hill", "Moore", "Clark", "Harrison", "Scott",
    "Young", "Morris", "Hall", "Ward", "Turner", "Carter", "Phillips",
    "Mitchell", "Patel", "Adams", "Campbell", "Anderson", "Allen", "Cook",
    "Bailey", "Palmer", "Stevens", "Bell", "Richardson", "Collins", "Gray",
    "Shaw", "Murphy", "O'Brien", "Sullivan", "Khan", "Ali", "Singh",
    "Bennett", "Griffiths", "Price", "Parker", "Fox", "Spencer", "Butler",
]

SEGMENTS = ["Retail", "Premier", "Private Banking", "Business"]
SEGMENT_WEIGHTS = [0.55, 0.25, 0.10, 0.10]

UK_REGIONS = [
    "London", "South East", "South West", "East Midlands", "West Midlands",
    "North West", "North East", "Yorkshire", "East Anglia", "Scotland",
    "Wales", "Northern Ireland",
]

TRANSACTION_CATEGORIES = [
    "Groceries", "Utilities", "Transport", "Entertainment", "Dining",
    "Healthcare", "Insurance", "Investments", "Savings", "Mortgage",
    "Rent", "Shopping", "Travel", "Education", "Charity",
]

CHANNELS = [
    "Online Banking", "Mobile App", "Branch", "ATM", "Contactless",
    "Direct Debit", "Standing Order",
]
CHANNEL_WEIGHTS = [0.20, 0.30, 0.05, 0.08, 0.20, 0.12, 0.05]

RISK_BANDS = ["Very Low", "Low", "Medium", "High", "Very High"]
MODEL_VERSIONS = ["v2.1", "v2.2", "v3.0"]

NUM_CUSTOMERS = 1000
NUM_TRANSACTIONS = 5000


def random_date(start: date, end: date) -> date:
    """Return a random date between start and end (inclusive)."""
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def generate_customers() -> list[dict]:
    """Generate 1000 customer records."""
    customers = []
    onboard_start = date(2015, 1, 1)
    onboard_end = date(2024, 12, 31)

    for i in range(1, NUM_CUSTOMERS + 1):
        customer_id = f"CUST-{i:04d}"
        first_name = random.choice(UK_FIRST_NAMES)
        surname = random.choice(UK_SURNAMES)
        name = f"{first_name} {surname}"
        segment = random.choices(SEGMENTS, weights=SEGMENT_WEIGHTS, k=1)[0]
        region = random.choice(UK_REGIONS)
        onboarded_date = random_date(onboard_start, onboard_end).isoformat()

        # Lifetime value varies by segment (GBP)
        if segment == "Private Banking":
            lifetime_value = round(random.uniform(50000, 500000), 2)
        elif segment == "Premier":
            lifetime_value = round(random.uniform(10000, 80000), 2)
        elif segment == "Business":
            lifetime_value = round(random.uniform(5000, 150000), 2)
        else:  # Retail
            lifetime_value = round(random.uniform(500, 25000), 2)

        customers.append({
            "customer_id": customer_id,
            "name": name,
            "segment": segment,
            "region": region,
            "onboarded_date": onboarded_date,
            "lifetime_value": lifetime_value,
        })

    return customers


def generate_transactions(customers: list[dict]) -> list[dict]:
    """Generate 5000 transaction records linked to existing customers."""
    transactions = []
    txn_start = date(2024, 1, 1)
    txn_end = date(2024, 12, 31)

    customer_ids = [c["customer_id"] for c in customers]

    for i in range(1, NUM_TRANSACTIONS + 1):
        txn_id = f"TXN-{i:06d}"
        customer_id = random.choice(customer_ids)
        category = random.choice(TRANSACTION_CATEGORIES)

        # Amount ranges depend on category (GBP)
        if category == "Mortgage":
            amount = round(random.uniform(500, 2500), 2)
        elif category == "Rent":
            amount = round(random.uniform(400, 2000), 2)
        elif category in ("Investments", "Savings"):
            amount = round(random.uniform(100, 5000), 2)
        elif category == "Insurance":
            amount = round(random.uniform(30, 300), 2)
        elif category in ("Travel", "Shopping"):
            amount = round(random.uniform(20, 800), 2)
        elif category in ("Utilities", "Transport"):
            amount = round(random.uniform(15, 250), 2)
        elif category in ("Groceries", "Dining"):
            amount = round(random.uniform(5, 150), 2)
        elif category == "Education":
            amount = round(random.uniform(50, 1500), 2)
        elif category == "Charity":
            amount = round(random.uniform(5, 200), 2)
        else:  # Entertainment, Healthcare
            amount = round(random.uniform(10, 300), 2)

        txn_date = random_date(txn_start, txn_end).isoformat()
        channel = random.choices(CHANNELS, weights=CHANNEL_WEIGHTS, k=1)[0]

        transactions.append({
            "txn_id": txn_id,
            "customer_id": customer_id,
            "amount": amount,
            "category": category,
            "txn_date": txn_date,
            "channel": channel,
        })

    return transactions


def generate_risk_scores(customers: list[dict]) -> list[dict]:
    """Generate 1000 risk score records (one per customer)."""
    risk_scores = []
    calc_start = date(2024, 10, 1)
    calc_end = date(2024, 12, 31)

    for customer in customers:
        score = random.randint(100, 999)

        # Determine risk band based on score ranges
        if score <= 300:
            risk_band = "Very High"
        elif score <= 450:
            risk_band = "High"
        elif score <= 600:
            risk_band = "Medium"
        elif score <= 800:
            risk_band = "Low"
        else:
            risk_band = "Very Low"

        model_version = random.choice(MODEL_VERSIONS)
        calculated_date = random_date(calc_start, calc_end).isoformat()

        risk_scores.append({
            "customer_id": customer["customer_id"],
            "score": score,
            "model_version": model_version,
            "calculated_date": calculated_date,
            "risk_band": risk_band,
        })

    return risk_scores


def write_csv(filepath: str, data: list[dict]) -> None:
    """Write a list of dicts to a CSV file."""
    if not data:
        return
    fieldnames = list(data[0].keys())
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def main():
    """Generate all sample data files."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Generating customer data...")
    customers = generate_customers()
    customers_path = os.path.join(OUTPUT_DIR, "customers.csv")
    write_csv(customers_path, customers)
    print(f"  -> {customers_path} ({len(customers)} records)")

    print("Generating transaction data...")
    transactions = generate_transactions(customers)
    transactions_path = os.path.join(OUTPUT_DIR, "transactions.csv")
    write_csv(transactions_path, transactions)
    print(f"  -> {transactions_path} ({len(transactions)} records)")

    print("Generating risk score data...")
    risk_scores = generate_risk_scores(customers)
    risk_scores_path = os.path.join(OUTPUT_DIR, "risk_scores.csv")
    write_csv(risk_scores_path, risk_scores)
    print(f"  -> {risk_scores_path} ({len(risk_scores)} records)")

    print("\nDone! All sample data files generated.")


if __name__ == "__main__":
    main()
