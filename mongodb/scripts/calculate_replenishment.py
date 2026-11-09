
from pymongo import MongoClient, UpdateOne
from datetime import datetime, timezone
from math import ceil

# 1. Connexion a MongoDB
client = MongoClient("mongodb://localhost:27017/")

db = client["smart_pharmacy"]

predictions_col = db["predictions"]
stocks_col = db["stocks"]
recommendations_col = db["replenishment_recommendations"]

print("Connexion a MongoDB reussie.")

# 2. Recuperer les previsions
predictions = list(predictions_col.find())

print(f"Nombre de previsions trouvees : {len(predictions)}")

operations = []
missing_stocks = 0

# 3. Parcourir chaque prevision
for prediction in predictions:

    pharmacy_id = prediction["pharmacy_id"]
    medicine_id = prediction["medicine_id"]

    # Rechercher le stock correspondant
    stock = stocks_col.find_one({
        "pharmacy_id": pharmacy_id,
        "medicine_id": medicine_id
    })

    if stock is None:
        print(f"Stock introuvable : {pharmacy_id} - {medicine_id}")
        missing_stocks += 1
        continue

    # 4. Recuperer les valeurs
    quantity = float(stock["quantity"])
    min_threshold = float(stock["min_threshold"])
    avg_daily_demand = float(prediction["avg_daily_demand"])
    predicted_demand = float(prediction["predicted_demand_7d"])

    # 5. Calculer la couverture en jours
    if avg_daily_demand > 0:
        coverage_days = round(quantity / avg_daily_demand, 2)
    else:
        coverage_days = None

    # 6. Calculer la quantite a commander
    # Le seuil minimal est conserve comme stock de securite.
    recommended_quantity = max(
        0,
        ceil(predicted_demand + min_threshold - quantity)
    )

    # 7. Determiner le statut
    if recommended_quantity > 0:
        status = "A_COMMANDER"
    else:
        status = "STOCK_SUFFISANT"

    # 8. Construire le document
    recommendation = {
        "pharmacy_id": pharmacy_id,
        "medicine_id": medicine_id,
        "current_stock": quantity,
        "min_threshold": min_threshold,
        "avg_daily_demand": avg_daily_demand,
        "predicted_demand_7d": predicted_demand,
        "coverage_days": coverage_days,
        "recommended_quantity": recommended_quantity,
        "status": status,
        "forecast_start_date": prediction["forecast_start_date"],
        "forecast_end_date": prediction["forecast_end_date"],
        "method": prediction["method"],
        "generated_at": datetime.now(timezone.utc)
    }

    # 9. Eviter les doublons avec upsert
    operations.append(
        UpdateOne(
            {
                "pharmacy_id": pharmacy_id,
                "medicine_id": medicine_id,
                "forecast_start_date": prediction["forecast_start_date"]
            },
            {"$set": recommendation},
            upsert=True
        )
    )

# 10. Enregistrer dans MongoDB
if operations:
    result = recommendations_col.bulk_write(operations)

    print("\n===== RESULTATS =====")
    print(f"Previsions traitees : {len(operations)}")
    print(f"Nouveaux documents : {result.upserted_count}")
    print(f"Documents actualises : {result.modified_count}")
    print(f"Stocks introuvables : {missing_stocks}")

# 11. Afficher le nombre total de recommandations
total = recommendations_col.count_documents({})

print(f"\nTotal des recommandations : {total}")

# 12. Afficher quelques recommandations
print("\n===== EXEMPLES DE RECOMMANDATIONS =====")

for document in recommendations_col.find().limit(5):
    print(
        document["pharmacy_id"],
        document["medicine_id"],
        "Stock :", document["current_stock"],
        "Couverture :", document["coverage_days"],
        "Commande :", document["recommended_quantity"],
        "Statut :", document["status"]
    )

client.close()

print("\nTraitement termine avec succes.")
