# Employee Expense Anomaly Detector

## Problem
Companies lose money to fraudulent expense claims. Most systems catch fraud after payment. This system catches it before.

## What It Does
Analyzes 1,500+ expense claims across 50 employees and flags suspicious patterns using rule-based SQL detection.

## Fraud Patterns Detected
- **Threshold Trick** — Repeated claims just below approval limits
- **Duplicate Submissions** — Same amount + vendor submitted twice within 7 days
- **Weekend Spikes** — Unusually high claims on non-working days
- **Frequency Jump** — Sudden spike in claim count vs personal historical average

## Tech Stack
- MySQL 9.7 — Core detection logic
- Python + Faker — Synthetic data generation
- Apache Superset — Dashboard & visualization

## SQL Concepts Used
- Window functions (NTILE, AVG OVER)
- CTEs (chained, 5 levels deep)
- Self joins (duplicate detection)
- Conditional aggregation (CASE WHEN)
- Subqueries (personal baseline comparison)
- Indexing (performance optimization)

## Results
- 262 anomalies flagged across 20 employees
- 5 HIGH risk, 13 MEDIUM risk employees identified
- 4 distinct fraud pattern types detected

## Dashboard
![Dashboard](screenshots/dashboard.png)
![Anomaly Breakdown](screenshots/bar_chart.png)
![Flagged Employees](screenshots/employee_table.png)

## How to Run
1. Run `sql/schema.sql` in MySQL
2. Run `python data/generate_data.py`
3. Run `sql/detection_queries.sql`
4. Run `sql/anomaly_log_insert.sql`
5. Connect Superset to MySQL and import charts