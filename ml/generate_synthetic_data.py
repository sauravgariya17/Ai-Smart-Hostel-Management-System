
#=============================================================================
# 1. ml/datasets/complaints_synthetic.csv     -> complaint text classifier
# 2. ml/datasets/occupancy_synthetic.csv      -> occupancy forecasting
# 3. ml/datasets/fee_defaulters_synthetic.csv -> fee-defaulter risk model
#=============================================================================


import csv
import os
import random
from datetime import date, timedelta

RANDOM_SEED = 42
random.seed(RANDOM_SEED)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATASETS_DIR = os.path.join(BASE_DIR, "datasets")
os.makedirs(DATASETS_DIR, exist_ok=True)


# ======================================================================
# 1. Complaint category + priority text classification dataset
# ======================================================================

COMPLAINT_TEMPLATES = {
    "electrical": {
        "phrases": [
            "the fan in my room is not working",
            "power socket near the study table is sparking",
            "there is no electricity in the corridor since morning",
            "the tube light keeps flickering all night",
            "the room's main switch board is not working",
            "short circuit near the washroom light",
            "the charging point in my room is dead",
            "the ceiling light bulb has fused",
        ],
    },
    "plumbing": {
        "phrases": [
            "the bathroom tap is leaking continuously",
            "there is no water supply in my room since yesterday",
            "the toilet flush is broken",
            "water is leaking from the ceiling in the washroom",
            "the wash basin pipe is broken and water is flooding the floor",
            "hot water is not coming in the shower",
            "the drainage in the bathroom is blocked",
        ],
    },
    "cleanliness": {
        "phrases": [
            "the corridor has not been cleaned for several days",
            "garbage is piling up near the room",
            "the common washroom is very dirty",
            "the room was not cleaned after the previous occupant left",
            "there is dust everywhere in the reading room",
            "the dustbin near my room has not been emptied",
        ],
    },
    "internet": {
        "phrases": [
            "the wifi is not working in my room",
            "internet speed is extremely slow in the hostel",
            "wifi router near my floor is not connecting",
            "the internet keeps disconnecting every few minutes",
            "no network coverage on the third floor",
        ],
    },
    "food": {
        "phrases": [
            "the food served in the mess is undercooked",
            "there was a foreign object found in the food",
            "the mess food quality has been very poor lately",
            "food was served cold today",
            "the mess timing is not being followed properly",
            "there is not enough variety in the mess menu",
        ],
    },
    "security": {
        "phrases": [
            "the main gate lock is broken",
            "an unknown person was seen loitering near the hostel at night",
            "the CCTV camera in the corridor is not working",
            "my room door lock is broken",
            "the security guard was not present at the gate last night",
            "the fire extinguisher near my floor is missing",
        ],
    },
    "other": {
        "phrases": [
            "requesting an extra bedsheet for my room",
            "the noticeboard information is outdated",
            "requesting permission to keep a personal fan",
            "the common room television remote is missing",
            "requesting a change in roommate due to personal reasons",
            "the hostel notice was not shared with everyone",
        ],
    },
}

# Priority-signal vocabulary is intentionally SHARED across every category
# (rather than category-specific) so the priority classifier learns general
# urgency language that generalizes to any complaint topic, instead of
# memorizing which words happen to co-occur with which category.
LOW_PRIORITY_PHRASES = [
    "it's a minor issue", "small inconvenience", "no rush at all",
    "happens only occasionally", "just a small request", "whenever convenient",
    "not a big deal",
]
HIGH_PRIORITY_PHRASES = [
    "this is extremely urgent", "please fix this immediately",
    "needs attention right away", "this is a safety risk",
    "please resolve as soon as possible, it's an emergency",
    "this cannot wait, please act now", "very concerning and needs immediate action",
]

PRIORITY_NEUTRAL_TEMPLATES = [
    "Please look into this when you get a chance.",
    "Kindly resolve this at your convenience.",
    "This needs to be fixed soon.",
    "Please arrange for a repair.",
    "Requesting maintenance to check this.",
]


def _make_complaint_row(category: str):
    info = COMPLAINT_TEMPLATES[category]
    phrase = random.choice(info["phrases"])

    priority_roll = random.random()
    if priority_roll < 0.34:
        priority = "low"
        modifier = random.choice(LOW_PRIORITY_PHRASES)
        text = f"{phrase.capitalize()}. {modifier.capitalize()}."
    elif priority_roll < 0.72:
        priority = "medium"
        text = f"{phrase.capitalize()}. {random.choice(PRIORITY_NEUTRAL_TEMPLATES)}"
    else:
        priority = "high"
        modifier = random.choice(HIGH_PRIORITY_PHRASES)
        text = f"{phrase.capitalize()}. {modifier.capitalize()}."

    return text, category, priority


def generate_complaints_dataset(rows_per_category: int = 70):
    path = os.path.join(DATASETS_DIR, "complaints_synthetic.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "category", "priority"])
        for category in COMPLAINT_TEMPLATES:
            for _ in range(rows_per_category):
                writer.writerow(_make_complaint_row(category))
    print(f"[complaints] wrote {rows_per_category * len(COMPLAINT_TEMPLATES)} rows -> {path}")


# ======================================================================
# 2. Hostel occupancy time-series dataset (synthetic, ~2 years daily)
# ======================================================================

def generate_occupancy_dataset(num_days: int = 730, start_capacity: int = 300):
    import math

    path = os.path.join(DATASETS_DIR, "occupancy_synthetic.csv")
    start_date = date.today() - timedelta(days=num_days)

    rows = []
    for i in range(num_days):
        current_date = start_date + timedelta(days=i)
        day_of_year = current_date.timetuple().tm_yday
        day_of_week = current_date.weekday()  # 0=Mon

        # Seasonal pattern: occupancy rises at semester start (~day 30, ~day 210),
        # dips during holidays (~day 170-190 summer break, ~day 350-365 winter break).
        seasonal = 55 + 25 * math.sin((day_of_year / 365.0) * 2 * math.pi + 1.2)

        # Slight long-term upward trend as the hostel grows more popular.
        trend = (i / num_days) * 8

        # Weekends see marginally lower on-campus occupancy (some students go home).
        weekend_dip = -4 if day_of_week >= 5 else 0

        noise = random.gauss(0, 3)

        occupancy_percent = seasonal + trend + weekend_dip + noise
        occupancy_percent = max(20.0, min(99.0, occupancy_percent))

        rows.append([current_date.isoformat(), i, day_of_week, day_of_year, round(occupancy_percent, 2)])

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "trend_index", "day_of_week", "day_of_year", "occupancy_percent"])
        writer.writerows(rows)

    print(f"[occupancy] wrote {num_days} rows -> {path}")


# ======================================================================
# 3. Fee defaulter risk dataset (synthetic student payment behavior)
# ======================================================================

def _make_defaulter_row():
    total_invoices = random.randint(1, 8)

    # Two latent behavior profiles: reliable payers vs. risky payers.
    is_risky = random.random() < 0.35

    if is_risky:
        percent_paid = round(random.uniform(0.0, 0.55), 2)
        max_days_overdue = random.randint(15, 120)
        overdue_invoice_count = random.randint(1, total_invoices)
        avg_days_to_pay = random.randint(20, 90)
    else:
        percent_paid = round(random.uniform(0.6, 1.0), 2)
        max_days_overdue = random.randint(0, 20)
        overdue_invoice_count = random.randint(0, 1)
        avg_days_to_pay = random.randint(0, 15)

    total_due = round(random.uniform(3000, 40000), 2)
    total_paid = round(total_due * percent_paid, 2)

    # Label: defaulter if paid little, has significant overdue history.
    label = 1 if (percent_paid < 0.6 and (max_days_overdue > 20 or overdue_invoice_count >= 2)) else 0

    return [
        total_invoices, total_due, total_paid, percent_paid,
        max_days_overdue, overdue_invoice_count, avg_days_to_pay, label,
    ]


def generate_fee_defaulters_dataset(num_rows: int = 600):
    path = os.path.join(DATASETS_DIR, "fee_defaulters_synthetic.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "total_invoices", "total_due", "total_paid", "percent_paid",
            "max_days_overdue", "overdue_invoice_count", "avg_days_to_pay", "is_defaulter",
        ])
        for _ in range(num_rows):
            writer.writerow(_make_defaulter_row())
    print(f"[fee_defaulters] wrote {num_rows} rows -> {path}")


if __name__ == "__main__":
    print("Generating SYNTHETIC/DEMO datasets (not real hostel data)...")
    generate_complaints_dataset()
    generate_occupancy_dataset()
    generate_fee_defaulters_dataset()
    print("Done.")
