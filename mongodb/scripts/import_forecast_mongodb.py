
import pandas as pd
from pymongo import MongoClient, UpdateOne
from pathlib import Path
from datetime import datetime

# 1. Chemin du CSV
csv_path = Path.home() / "Downloads" / "forecast_demand.csv"

# 2. Lecture des previsions
df = pd.read_csv(
    csv_path,
    dtype={
        "pharmacy_id": str,
        "medicine_id": str
    }
)

print("Nombre de previsions lues :", len(df))

# 3. Verification des colonnes
required_columns = [
    "pharmacy_id",
    "medicine_id",
    "avg_daily_demand",
    "predicted_demand_7d",
    "history_end_date",
    "forecast_start_date",
    "forecast_end_date",
    "method"
]

missing = set(required_columns) - set(df.columns)

if missing:
    raise ValueError("Colonnes manquantes : " + str(missing))

if df[required_columns].isnull().any().any():
    raise ValueError("Le CSV contient des valeurs manquantes.")

# 4. Connexion MongoDB
client = MongoClient(
    "mongodb://localhost:27017/",
    serverSelectionTimeoutMS=5000
)

client.admin.command("ping")

db = client["smart_pharmacy"]
collection = db["predictions"]

# 5. Index unique pour eviter les doublons
collection.create_index(
    [
        ("pharmacy_id", 1),
        ("medicine_id", 1),
        ("forecast_start_date", 1)
    ],
    unique=True
)

# 6. Preparation des operations
operations = []

for record in df.to_dict(orient="records"):

    record["avg_daily_demand"] = float(
        record["avg_daily_demand"]
    )

    record["predicted_demand_7d"] = float(
        record["predicted_demand_7d"]
    )

    record["imported_at"] = datetime.now()

    operations.append(
        UpdateOne(
            {
                "pharmacy_id": record["pharmacy_id"],
                "medicine_id": record["medicine_id"],
                "forecast_start_date": record["forecast_start_date"]
            },
            {"$set": record},
            upsert=True
        )
    )

# 7. Insertion ou mise a jour
if operations:
    result = collection.bulk_write(
        operations,
        ordered=False
    )

    print("\nImportation terminee !")
    print("Nouveaux documents :", result.upserted_count)
    print("Documents modifies :", result.modified_count)
    print("Documents correspondants :", result.matched_count)

# 8. Verification
print(
    "\nNombre total de previsions :",
    collection.count_documents({})
)

print("\nExemple de prevision :")

document = collection.find_one(
    {},
    {"_id": 0}
)

print(document)

client.close()
