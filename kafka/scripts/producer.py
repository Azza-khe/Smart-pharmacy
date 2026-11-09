
import json
import random
import time
import uuid
from datetime import datetime

from kafka import KafkaProducer

# Connexion au serveur Kafka depuis Windows
KAFKA_SERVER = "localhost:9094"
TOPIC = "pharmacy_sales"

# Identifiants des pharmacies
PHARMACIES = ["P001", "P002", "P003", "P004", "P005"]

# Identifiants des médicaments
MEDICINES = [
    "M001", "M002", "M003", "M004",
    "M005", "M006", "M007", "M008"
]

# Création du producteur Kafka
producer = KafkaProducer(
    bootstrap_servers=KAFKA_SERVER,
    value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    key_serializer=lambda key: key.encode("utf-8")
)

print("Connexion au producteur Kafka réussie.")
print("Simulation des ventes en cours...")
print("Appuyer sur Ctrl+C pour arrêter.\n")

try:
    while True:

        # Génération d'une vente aléatoire
        sale = {
            "sale_id": str(uuid.uuid4()),
            "pharmacy_id": random.choice(PHARMACIES),
            "medicine_id": random.choice(MEDICINES),
            "quantity": random.randint(1, 3),
            "unit_price": round(random.uniform(5, 50), 2),
            "sold_at": datetime.now().astimezone().isoformat(
                timespec="seconds"
            )
        }

        # Envoi de la vente à Kafka
        future = producer.send(
            TOPIC,
            key=sale["pharmacy_id"],
            value=sale
        )

        # Attendre la confirmation de Kafka
        metadata = future.get(timeout=10)

        print(
            f"Vente envoyée : {sale['sale_id']} | "
            f"Pharmacie : {sale['pharmacy_id']} | "
            f"Médicament : {sale['medicine_id']} | "
            f"Quantité : {sale['quantity']} | "
            f"Partition : {metadata.partition}"
        )

        # Attendre 5 secondes avant la prochaine vente
        time.sleep(5)

except KeyboardInterrupt:
    print("\nArrêt de la simulation.")

finally:
    producer.flush()
    producer.close()
    print("Producteur Kafka fermé.")
