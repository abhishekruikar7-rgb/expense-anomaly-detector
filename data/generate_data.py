import mysql.connector
import random
from faker import Faker
from datetime import date, timedelta, datetime

fake = Faker('en_IN')
random.seed(42)

# ── DB CONFIG ─────────────────────────────────────────────
DB_CONFIG = {
    "host": "localhost",
    "user": "root",         # change if needed
    "password": "abhishek@123",  # ← PUT YOUR PASSWORD HERE
    "database": "expense_anomaly"
}

# ── CONSTANTS ─────────────────────────────────────────────
DEPARTMENTS   = ["Engineering", "Sales", "Marketing", "Operations", "HR"]
DESIGNATIONS  = ["Analyst", "Senior Analyst", "Manager", "Senior Manager", "Lead"]

CATEGORIES = {
    "Travel":        5000.00,
    "Meals":         2000.00,
    "Accommodation": 8000.00,
    "Software":      10000.00,
    "Office Supplies": 3000.00,
    "Miscellaneous": 4000.00,
}

VENDORS = {
    "Travel":        ["MakeMyTrip", "IRCTC", "Ola Business", "IndiGo", "RedBus"],
    "Meals":         ["Swiggy for Business", "Zomato", "Hotel Meridian", "Cafe Coffee Day", "Dominos"],
    "Accommodation": ["OYO Business", "Taj Hotels", "Airbnb", "Lemon Tree", "FabHotels"],
    "Software":      ["AWS", "GitHub", "Zoom", "Notion", "JetBrains"],
    "Office Supplies":["Staples", "Amazon Business", "Flipkart Business", "OfficeMax", "Local Store"],
    "Miscellaneous": ["Petty Cash", "Local Vendor", "Online Store", "Amazon", "Unknown"],
}

START_DATE = date(2024, 1, 1)
END_DATE   = date(2024, 12, 31)


def random_date(start=START_DATE, end=END_DATE):
    return start + timedelta(days=random.randint(0, (end - start).days))


def random_weekday_date():
    d = random_date()
    while d.weekday() >= 5:
        d = random_date()
    return d


def random_weekend_date():
    d = random_date()
    while d.weekday() < 5:
        d = random_date()
    return d


# ── CONNECT ───────────────────────────────────────────────
conn   = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor()

print("Connected to MySQL.")

# ── 1. THRESHOLDS ─────────────────────────────────────────
print("Inserting approval thresholds...")
for category, amount in CATEGORIES.items():
    cursor.execute("""
        INSERT IGNORE INTO approval_thresholds (category, threshold_amount, description)
        VALUES (%s, %s, %s)
    """, (category, amount, f"Claims above ₹{amount:,.0f} require manager approval"))
conn.commit()

# ── 2. EMPLOYEES ──────────────────────────────────────────
print("Inserting employees...")
employee_ids = []
for _ in range(50):
    cursor.execute("""
        INSERT INTO employees (name, department, designation, joining_date, monthly_expense_limit)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        fake.name(),
        random.choice(DEPARTMENTS),
        random.choice(DESIGNATIONS),
        fake.date_between(start_date='-5y', end_date='-6m'),
        round(random.uniform(15000, 50000), 2)
    ))
employee_ids = list(range(1, 51))
conn.commit()

# ── 3. NORMAL CLAIMS ──────────────────────────────────────
print("Inserting normal expense claims...")
normal_claims = []
for emp_id in employee_ids:
    num_claims = random.randint(20, 35)   # ~2–3 claims/month
    for _ in range(num_claims):
        category = random.choice(list(CATEGORIES.keys()))
        threshold = CATEGORIES[category]
        # Normal: well below threshold, weekdays, spread across year
        amount = round(random.uniform(threshold * 0.2, threshold * 0.75), 2)
        normal_claims.append((
            emp_id,
            amount,
            category,
            random_weekday_date(),
            random.choice(VENDORS[category]),
            fake.sentence(nb_words=6),
            "APPROVED"
        ))

cursor.executemany("""
    INSERT INTO expense_claims
        (employee_id, amount, category, claim_date, vendor, description, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
""", normal_claims)
conn.commit()
print(f"  Inserted {len(normal_claims)} normal claims.")

# ── 4. FRAUD PATTERN 1: THRESHOLD TRICK ───────────────────
# 8 employees repeatedly submit just under their category threshold
print("Planting fraud pattern 1: threshold trick...")
fraud_employees_threshold = random.sample(employee_ids, 8)
threshold_claims = []
for emp_id in fraud_employees_threshold:
    category = random.choice(["Travel", "Meals", "Software", "Miscellaneous"])
    threshold = CATEGORIES[category]
    for _ in range(random.randint(6, 10)):
        # Always ₹100–₹300 below threshold
        amount = round(threshold - random.uniform(50, 300), 2)
        threshold_claims.append((
            emp_id, amount, category,
            random_weekday_date(),
            random.choice(VENDORS[category]),
            "Business expense",
            "APPROVED"
        ))

cursor.executemany("""
    INSERT INTO expense_claims
        (employee_id, amount, category, claim_date, vendor, description, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
""", threshold_claims)
conn.commit()
print(f"  Inserted {len(threshold_claims)} threshold-trick claims.")

# ── 5. FRAUD PATTERN 2: DUPLICATE SUBMISSIONS ─────────────
# 5 employees submit same amount + vendor twice within 7 days
print("Planting fraud pattern 2: duplicate submissions...")
fraud_employees_dup = random.sample(employee_ids, 5)
dup_claims = []
for emp_id in fraud_employees_dup:
    for _ in range(random.randint(2, 4)):
        category = random.choice(list(CATEGORIES.keys()))
        amount   = round(random.uniform(1000, CATEGORIES[category] * 0.8), 2)
        vendor   = random.choice(VENDORS[category])
        base_date = random_weekday_date()
        dup_date  = base_date + timedelta(days=random.randint(1, 7))
        desc = fake.sentence(nb_words=5)
        dup_claims.append((emp_id, amount, category, base_date, vendor, desc, "APPROVED"))
        dup_claims.append((emp_id, amount, category, dup_date, vendor, desc, "APPROVED"))

cursor.executemany("""
    INSERT INTO expense_claims
        (employee_id, amount, category, claim_date, vendor, description, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
""", dup_claims)
conn.commit()
print(f"  Inserted {len(dup_claims)} duplicate claims.")

# ── 6. FRAUD PATTERN 3: WEEKEND SPIKES ────────────────────
# 6 employees submit unusually high meal/travel claims on weekends
print("Planting fraud pattern 3: weekend spikes...")
fraud_employees_weekend = random.sample(employee_ids, 6)
weekend_claims = []
for emp_id in fraud_employees_weekend:
    for _ in range(random.randint(5, 9)):
        category = random.choice(["Meals", "Travel"])
        threshold = CATEGORIES[category]
        # Weekend amounts 3–4x their normal weekday pattern
        amount = round(random.uniform(threshold * 0.85, threshold * 0.99), 2)
        weekend_claims.append((
            emp_id, amount, category,
            random_weekend_date(),
            random.choice(VENDORS[category]),
            "Weekend team activity",
            "APPROVED"
        ))

cursor.executemany("""
    INSERT INTO expense_claims
        (employee_id, amount, category, claim_date, vendor, description, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
""", weekend_claims)
conn.commit()
print(f"  Inserted {len(weekend_claims)} weekend-spike claims.")

# ── 7. FRAUD PATTERN 4: FREQUENCY JUMP ────────────────────
# 4 employees suddenly submit 3x their normal claim count in Q4
print("Planting fraud pattern 4: frequency jump in Q4...")
fraud_employees_freq = random.sample(employee_ids, 4)
freq_claims = []
Q4_START = date(2024, 10, 1)
Q4_END   = date(2024, 12, 31)
for emp_id in fraud_employees_freq:
    for _ in range(random.randint(18, 25)):   # vs normal ~8 in 3 months
        category = random.choice(list(CATEGORIES.keys()))
        amount   = round(random.uniform(500, CATEGORIES[category] * 0.6), 2)
        freq_claims.append((
            emp_id, amount, category,
            random_date(Q4_START, Q4_END),
            random.choice(VENDORS[category]),
            fake.sentence(nb_words=5),
            "APPROVED"
        ))

cursor.executemany("""
    INSERT INTO expense_claims
        (employee_id, amount, category, claim_date, vendor, description, status)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
""", freq_claims)
conn.commit()
print(f"  Inserted {len(freq_claims)} frequency-jump claims.")

# ── SUMMARY ───────────────────────────────────────────────
cursor.execute("SELECT COUNT(*) FROM expense_claims")
total = cursor.fetchone()[0]
print(f"\n✅ Done. Total claims in DB: {total}")
print(f"   Fraud patterns planted across ~23 employees out of 50")
print(f"\nFraud employee IDs (save these for verification later):")
all_fraud = set(fraud_employees_threshold + fraud_employees_dup +
                fraud_employees_weekend + fraud_employees_freq)
print(f"   {sorted(all_fraud)}")

cursor.close()
conn.close()