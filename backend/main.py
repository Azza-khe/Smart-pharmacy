
from datetime import date, datetime
from bson import ObjectId

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from database import (
    client,
    db,
    predictions_collection,
    stocks_collection,
    recommendations_collection
)


# --------------------------------------------------
# 1. INITIALISATION DE FASTAPI
# --------------------------------------------------

app = FastAPI(
    title="Smart Pharmacy API",
    description="API de gestion intelligente des pharmacies",
    version="1.0.0"
)

# Autoriser les requêtes provenant du frontend.
# Cette configuration est adaptée au développement local.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)


# --------------------------------------------------
# 2. CONVERSION DES DONNEES MONGODB EN JSON
# --------------------------------------------------

def serialize_document(document):
    """
    Convertit les types MongoDB non compatibles JSON.
    """

    if isinstance(document, list):
        return [serialize_document(item) for item in document]

    if isinstance(document, dict):
        result = {}

        for key, value in document.items():
            result[key] = serialize_document(value)

        return result

    if isinstance(document, ObjectId):
        return str(document)

    if isinstance(document, (datetime, date)):
        return document.isoformat()

    return document


def get_documents(collection, limit=500):
    """
    Récupère les documents d'une collection.
    """

    documents = list(collection.find().limit(limit))
    return serialize_document(documents)

def enrich_documents(documents):
    medicines = {
        item["medicine_id"]: item
        for item in db.medicines.find({}, {"_id": 0})
    }

    pharmacies = {
        item["pharmacy_id"]: item
        for item in db.pharmacies.find({}, {"_id": 0})
    }

    for document in documents:
        medicine = medicines.get(document.get("medicine_id"), {})
        pharmacy = pharmacies.get(document.get("pharmacy_id"), {})

        document["medicine_category"] = medicine.get(
            "category_name", "Catégorie inconnue"
        )
        document["atc_code"] = medicine.get("atc_code", "Non disponible")

        document["pharmacy_name"] = pharmacy.get(
            "name", "Pharmacie inconnue"
        )
        document["pharmacy_city"] = pharmacy.get(
            "city", "Ville inconnue"
        )

    return documents


# --------------------------------------------------
# 3. ROUTE D'ACCUEIL
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Bienvenue dans Smart Pharmacy API",
        "documentation": "/docs",
        "status": "active"
    }


# --------------------------------------------------
# 4. VERIFICATION DU SERVEUR ET DE MONGODB
# --------------------------------------------------

@app.get("/api/health")
def health_check():

    try:
        client.admin.command("ping")

        return {
            "api": "active",
            "mongodb": "connecte",
            "database": db.name
        }

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail=f"MongoDB inaccessible : {str(error)}"
        )


# --------------------------------------------------
# 5. RECUPERATION DES PREVISIONS
# --------------------------------------------------

@app.get("/api/predictions")
def get_predictions():
    try:
        documents = get_documents(predictions_collection)
        documents = enrich_documents(documents)
        return {"total": len(documents), "data": documents}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))

# --------------------------------------------------
# 6. RECUPERATION DES STOCKS
# --------------------------------------------------

@app.get("/api/stocks")
def get_stocks():
    try:
        documents = get_documents(stocks_collection)
        documents = enrich_documents(documents)
        return {"total": len(documents), "data": documents}
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


# --------------------------------------------------
# 7. RECUPERATION DES RECOMMANDATIONS
# --------------------------------------------------

@app.get("/api/recommendations")
def get_recommendations(status: str = None):
    try:
        query = {}

        if status:
            query["status"] = status.upper()

        documents = list(
            recommendations_collection.find(query).limit(500)
        )

        documents = serialize_document(documents)
        documents = enrich_documents(documents)

        return {"total": len(documents), "data": documents}

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


# --------------------------------------------------
# 8. STATISTIQUES GENERALES
# --------------------------------------------------

@app.get("/api/stats")
def get_stats():

    try:
        total_predictions = predictions_collection.count_documents({})
        total_stocks = stocks_collection.count_documents({})
        total_recommendations = recommendations_collection.count_documents({})

        to_order = recommendations_collection.count_documents({
            "status": "A_COMMANDER"
        })

        sufficient = recommendations_collection.count_documents({
            "status": "STOCK_SUFFISANT"
        })

        total_quantity = 0

        for item in recommendations_collection.find(
            {},
            {"recommended_quantity": 1}
        ):
            total_quantity += item.get("recommended_quantity", 0)

        total_pharmacies = len(
            predictions_collection.distinct("pharmacy_id")
        )

        total_medicines = len(
            predictions_collection.distinct("medicine_id")
        )

        return {
            "total_predictions": total_predictions,
            "total_stocks": total_stocks,
            "total_recommendations": total_recommendations,
            "total_pharmacies": total_pharmacies,
            "total_medicines": total_medicines,
            "to_order": to_order,
            "sufficient_stock": sufficient,
            "total_recommended_quantity": total_quantity
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))


# --------------------------------------------------
# 9. GENERATION DES ALERTES
# --------------------------------------------------

@app.get("/api/alerts")
def get_alerts():

    try:
        stocks = list(stocks_collection.find())
        recommendations = list(recommendations_collection.find())

        stock_index = {
            (item.get("medicine_id"), item.get("pharmacy_id")): item
            for item in stocks
        }

        alerts = []

        for item in recommendations:

            medicine_id = item.get("medicine_id")
            pharmacy_id = item.get("pharmacy_id")
            coverage = item.get("coverage_days", 0)

            stock = stock_index.get((medicine_id, pharmacy_id), {})

            quantity = stock.get(
                "quantity",
                item.get("current_stock", 0)
            )

            threshold = stock.get(
                "min_threshold",
                item.get("min_threshold", 0)
            )

            if quantity <= threshold:
                level = "CRITIQUE"
                message = "Le stock est inférieur ou égal au seuil minimum."

            elif coverage < 3:
                level = "CRITIQUE"
                message = "La couverture du stock est inférieure à 3 jours."

            elif coverage < 7:
                level = "ATTENTION"
                message = "La couverture du stock est inférieure à 7 jours."

            else:
                continue

            alerts.append({
                "medicine_id": medicine_id,
                "pharmacy_id": pharmacy_id,
                "current_stock": quantity,
                "min_threshold": threshold,
                "coverage_days": coverage,
                "level": level,
                "message": message
            })

        return {
            "total": len(alerts),
            "data": serialize_document(alerts)
        }

    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
