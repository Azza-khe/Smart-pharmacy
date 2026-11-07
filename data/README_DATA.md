# Data README - Smart Pharmacy

## Source (real data)
- Dataset: *Pharma Sales Data* (Milan Zdravkovic, Kaggle), file `salesdaily.csv`.
- One real pharmacy, 2014-2019, quantities aggregated into 8 ATC categories.
- Raw file kept intact in `data/raw/` (not committed to Git).

## Cleaning rules (data/processed/)
- Rows after cleaning: 2106 (2014-01-02 to 2019-10-08).
- Invalid dates dropped: 0; duplicated dates dropped: 0.
- Missing quantities filled with 0: 0.
- Negative quantities set to 0: 0.
- Calendar days absent from the file: 0.
- `pharma_sales_clean.csv`: long format `sale_date, medicine_id, atc_code, quantity` (quantities are daily totals and may be decimal).
- `pharma_sales_clean_wide.csv`: same data, one column per ATC code.
- Zero-quantity rows are kept; filter them in Spark (Filtering pattern).

## Big transaction history (SIMULATED from real hourly data)
- Real base: `saleshourly.csv` (hourly sales per ATC category, same cleaning rules as the daily file).
- Hourly rows used: 50532; invalid dates: 0; duplicate hours: 0; missing filled with 0: 0; negatives set to 0: 0.
- `sales_history_transactions.csv`: one row per sale, columns `sale_id, pharmacy_id, medicine_id, quantity, timestamp` (same format as the Kafka events).
- Size: 1,443,519 sale lines, 3,999,294 units, from 2014-01-02T08:01:11 to 2019-10-08T19:59:40.
- Method: units per hour, pharmacy and medicine are drawn from a Poisson distribution around the real hourly pattern, scaled by a per-pharmacy activity factor (seed 2026), then split into sale lines of 1 to 3 units with random minutes and seconds.
- History `sale_id`s start with `H` so they never collide with live Kafka ids (`S...`).
- This history is simulated; only the seasonal and daily pattern comes from real data.

## Simulated data (NOT real)
- `pharmacies.csv`: 5 fictional pharmacies (P001-P005).
- `initial_stock.csv`: random initial stocks and minimum thresholds (seed 42), one row per pharmacy/medicine.
- Demo case: P001 / M001 has stock 100 and threshold 30.
- `medicines.csv`: `medicine_id` (M001-M008) assigned by the project, one per ATC category.
- Real-time sale events (Kafka) are also simulated.

## Shared contract
- `pharmacy_id` (P001...) and `medicine_id` (M001...) are identical in every file and service.
- Event format: `{"sale_id": "S000001", "pharmacy_id": "P001", "medicine_id": "M001", "quantity": 2, "timestamp": "2026-11-06T10:30:00"}`