
import json
from datetime import datetime, timezone

from kafka import KafkaConsumer
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

# Configuration
KAFKA_SERVER = "localhost:9094"
TOPIC = "validated_sales"
GROUP_ID = "smart-pharmacy-mongodb-consumer"

MONGO_URI = "mongodb://localhost:27017/"
DATABASE = "smart_pharmacy"

# Connexion MongoDB
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[DATABASE]

pharmacies = db.pharmacies
medicines = db.medicines
stocks = db.stocks
sales = db.sales
alerts = db.alerts

# Connexion Kafka
consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=[KAFKA_SERVER],
    group_id=GROUP_ID,
    auto_offset_reset="earliest",
    enable_auto_commit=False,
    value_deserializer=lambda value: json.loads(value.decode("utf-8"))
)

print("Connexion Kafka et MongoDB reussie.")
print("En attente de ventes validees...\n")


def save_sale(record):
    """Enregistre une vente sans accepter les doublons."""
    try:
        sales.insert_one(record)
        return True
    except DuplicateKeyError:
        print("Vente deja enregistree :", record["sale_id"])
        return False

def update_stock_alert(pharmacy_id, medicine_id, current_stock, min_threshold):
    """
    Cree, actualise ou resout une alerte selon le niveau du stock.
    """

    now = datetime.now(timezone.utc)

    # Determiner le statut du stock
    if current_stock <= 0:
        status = "OUT"
        message = (
            f"Rupture de stock : aucune unite restante "
            f"pour le medicament {medicine_id}."
        )

    elif current_stock <= min_threshold:
        status = "LOW"
        message = (
            f"Stock faible : {current_stock} unites restantes, "
            f"seuil minimal : {min_threshold}."
        )

    else:
        status = "NORMAL"
        message = "Le stock est revenu a un niveau normal."

    # Si le stock est normal, resoudre une ancienne alerte active
    if status == "NORMAL":

        result = alerts.update_one(
            {
                "pharmacy_id": pharmacy_id,
                "medicine_id": medicine_id,
                "is_active": True
            },
            {
                "$set": {
                    "is_active": False,
                    "status": "RESOLVED",
                    "current_stock": current_stock,
                    "message": message,
                    "updated_at": now,
                    "resolved_at": now
                }
            }
        )

        if result.modified_count > 0:
            print("Alerte resolue :", medicine_id)

        return

    # Creer ou actualiser une alerte LOW ou OUT
    alert_data = {
        "pharmacy_id": pharmacy_id,
        "medicine_id": medicine_id,
        "status": status,
        "current_stock": current_stock,
        "min_threshold": min_threshold,
        "message": message,
        "is_active": True,
        "updated_at": now
    }

    try:
        alerts.update_one(
            {
                "pharmacy_id": pharmacy_id,
                "medicine_id": medicine_id,
                "is_active": True
            },
            {
                "$set": alert_data,
                "$setOnInsert": {
                    "created_at": now
                }
            },
            upsert=True
        )

        print(
            "ALERTE", status,
            "| Pharmacie :", pharmacy_id,
            "| Medicament :", medicine_id,
            "| Stock :", current_stock,
            "| Seuil :", min_threshold
        )

    except DuplicateKeyError:
        # Protection supplementaire contre une creation simultanee
        alerts.update_one(
            {
                "pharmacy_id": pharmacy_id,
                "medicine_id": medicine_id,
                "is_active": True
            },
            {
                "$set": alert_data
            }
        )


def refresh_all_stock_alerts():
    """
    Verifie tous les stocks et actualise les alertes dans MongoDB.
    """

    print("\nVerification de tous les stocks...")

    total = 0

    for stock in stocks.find():
        update_stock_alert(
            stock["pharmacy_id"],
            stock["medicine_id"],
            stock["quantity"],
            stock["min_threshold"]
        )
        total += 1

    print("Verification terminee :", total, "stocks examines.\n")

def process_sale(sale):
    sale_id = sale["sale_id"]
    pharmacy_id = sale["pharmacy_id"]
    medicine_id = sale["medicine_id"]
    quantity = int(sale["quantity"])
    unit_price = float(sale["unit_price"])

    sold_at = datetime.fromisoformat(
        sale["sold_at"].replace("Z", "+00:00")
    )

    # Verifier si la vente existe deja
    existing_sale = sales.find_one({"sale_id": sale_id})

    if existing_sale:
        print("Vente deja traitee :", sale_id)
        return

    # Verifier l'existence de la pharmacie et du medicament
    if not pharmacies.find_one({"pharmacy_id": pharmacy_id}):
        save_sale({
            **sale,
            "status": "REJECTED",
            "rejection_reason": "Pharmacie inconnue",
            "processed_at": datetime.now(timezone.utc)
        })
        print("Vente rejetee : pharmacie inconnue")
        return

    if not medicines.find_one({"medicine_id": medicine_id}):
        save_sale({
            **sale,
            "status": "REJECTED",
            "rejection_reason": "Medicament inconnu",
            "processed_at": datetime.now(timezone.utc)
        })
        print("Vente rejetee : medicament inconnu")
        return

    # Rechercher le stock correspondant
    stock = stocks.find_one({
        "pharmacy_id": pharmacy_id,
        "medicine_id": medicine_id
    })

    if stock is None:
        save_sale({
            **sale,
            "status": "REJECTED",
            "rejection_reason": "Stock introuvable",
            "processed_at": datetime.now(timezone.utc)
        })
        print("Vente rejetee : stock introuvable")
        return

    # Verifier si cette vente a deja diminue le stock
    if sale_id in stock.get("processed_sale_ids", []):
        stock_after = stock["quantity"]
    else:
        # Mise a jour atomique du stock :
        # decrement uniquement si le stock est suffisant
        # et si cette vente n'a pas deja ete appliquee.
        result = stocks.update_one(
            {
                "pharmacy_id": pharmacy_id,
                "medicine_id": medicine_id,
                "quantity": {"$gte": quantity},
                "processed_sale_ids": {"$ne": sale_id}
            },
            {
                "$inc": {"quantity": -quantity},
                "$addToSet": {"processed_sale_ids": sale_id},
                "$set": {"updated_at": datetime.now(timezone.utc)}
            }
        )

        updated_stock = stocks.find_one({
            "pharmacy_id": pharmacy_id,
            "medicine_id": medicine_id
        })

        # Si la mise a jour a echoue, verifier pourquoi
        if result.modified_count == 0:
            if sale_id in updated_stock.get("processed_sale_ids", []):
                stock_after = updated_stock["quantity"]
            else:
                save_sale({
                    **sale,
                    "status": "REJECTED",
                    "rejection_reason": "Stock insuffisant",
                    "processed_at": datetime.now(timezone.utc)
                })
                print(
                    "Vente rejetee : stock insuffisant |",
                    medicine_id,
                    "| Stock :", updated_stock["quantity"]
                )
                return
        else:
            stock_after = updated_stock["quantity"]

    # Enregistrer la vente traitee
    record = {
        **sale,
        "sold_at": sold_at,
        "total_amount": round(quantity * unit_price, 2),
        "status": "PROCESSED",
        "stock_after": stock_after,
        "processed_at": datetime.now(timezone.utc)
    }

    save_sale(record)

    print(
        "Vente traitee :", sale_id,
        "| Pharmacie :", pharmacy_id,
        "| Medicament :", medicine_id,
        "| Quantite :", quantity,
        "| Stock restant :", stock_after
    )

        # Mettre a jour l'alerte correspondante dans MongoDB
    update_stock_alert(
        pharmacy_id,
        medicine_id,
        stock_after,
        updated_stock["min_threshold"]
    )


try:
    # Verifier les stocks avant de recevoir les nouvelles ventes
    refresh_all_stock_alerts()

    for message in consumer:
        try:
            process_sale(message.value)

            # Confirmer le message seulement apres traitement
            consumer.commit()

        except Exception as error:
            print("Erreur de traitement :", error)
            print("Message non confirme. Arret du consommateur.")
            break

except KeyboardInterrupt:
    print("\nArret du consommateur.")

finally:
    consumer.close()
    mongo_client.close()
    print("Connexions fermees.")
