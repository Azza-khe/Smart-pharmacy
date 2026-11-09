
import csv
from pathlib import Path
from datetime import datetime

from pymongo import MongoClient

# 1. Connexion a MongoDB
client = MongoClient("mongodb://localhost:27017/")

# Verification de la connexion
client.admin.command("ping")
print("Connexion MongoDB reussie.")

# 2. Selection de la base de donnees
db = client["smart_pharmacy"]

# 3. Emplacement des fichiers CSV
DOSSIER = Path.home() / "Downloads"

# 4. Fonction pour lire un fichier CSV
def lire_csv(nom_fichier):
    chemin = DOSSIER / nom_fichier

    if not chemin.exists():
        raise FileNotFoundError(f"Fichier introuvable : {chemin}")

    with open(chemin, "r", encoding="utf-8-sig", newline="") as fichier:
        return list(csv.DictReader(fichier))


# 5. Importer les pharmacies
pharmacies = lire_csv("pharmacies.csv")

for pharmacie in pharmacies:
    db.pharmacies.replace_one(
        {"pharmacy_id": pharmacie["pharmacy_id"]},
        pharmacie,
        upsert=True
    )

print(f"Pharmacies importees : {len(pharmacies)}")


# 6. Importer les medicaments
medicines = lire_csv("medicines.csv")

for medicine in medicines:
    db.medicines.replace_one(
        {"medicine_id": medicine["medicine_id"]},
        medicine,
        upsert=True
    )

print(f"Medicaments importes : {len(medicines)}")


# 7. Importer les stocks initiaux
stocks = lire_csv("initial_stock.csv")

for stock in stocks:
    document = {
        "pharmacy_id": stock["pharmacy_id"],
        "medicine_id": stock["medicine_id"],
        "quantity": int(stock["quantity"]),
        "min_threshold": int(stock["min_threshold"]),
        "updated_at": datetime.fromisoformat(stock["updated_at"])
    }

    db.stocks.replace_one(
        {
            "pharmacy_id": document["pharmacy_id"],
            "medicine_id": document["medicine_id"]
        },
        document,
        upsert=True
    )

print(f"Stocks importes : {len(stocks)}")


# 8. Creer des index pour eviter les doublons
db.pharmacies.create_index("pharmacy_id", unique=True)
db.medicines.create_index("medicine_id", unique=True)
db.stocks.create_index(
    [("pharmacy_id", 1), ("medicine_id", 1)],
    unique=True
)


# 9. Afficher les resultats
print("\n--- Verification MongoDB ---")
print("Nombre de pharmacies :", db.pharmacies.count_documents({}))
print("Nombre de medicaments :", db.medicines.count_documents({}))
print("Nombre de stocks :", db.stocks.count_documents({}))

print("\nImportation terminee avec succes.")

client.close()
