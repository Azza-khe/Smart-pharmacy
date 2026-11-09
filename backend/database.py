
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Charger les paramètres du fichier .env
load_dotenv()

# Paramètres MongoDB
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb://localhost:27017"
)

DATABASE_NAME = os.getenv(
    "DATABASE_NAME",
    "smart_pharmacy"
)

# Créer la connexion
client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=5000
)

# Sélectionner la base de données
db = client[DATABASE_NAME]

# Collections utilisées par l'application
predictions_collection = db["predictions"]
stocks_collection = db["stocks"]
recommendations_collection = db["replenishment_recommendations"]


def test_connection():
    """
    Vérifie la connexion à MongoDB.
    """
    try:
        client.admin.command("ping")
        print("Connexion MongoDB réussie !")
        print(f"Base de données : {DATABASE_NAME}")

        print("Collections disponibles :")
        print(f"- predictions : {predictions_collection.count_documents({})} documents")
        print(f"- stocks : {stocks_collection.count_documents({})} documents")
        print(
            "- replenishment_recommendations : "
            f"{recommendations_collection.count_documents({})} documents"
        )

        return True

    except Exception as error:
        print("Erreur de connexion à MongoDB :")
        print(error)
        return False
