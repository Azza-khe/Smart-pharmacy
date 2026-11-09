
from datetime import datetime, timedelta

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, substring, sum as spark_sum,
    avg, max as spark_max, lit, round
)

# 1. Initialisation de Spark
spark = SparkSession.builder \
    .appName("SmartPharmacyDemandForecast") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")

# 2. Chemins HDFS
input_path = (
    "hdfs://hadoop-master:9000/"
    "data/raw/pharma_sales/sales_history_transactions.csv"
)

output_path = (
    "hdfs://hadoop-master:9000/"
    "data/processed/forecast_demand"
)

print("Lecture des ventes historiques...")

# 3. Lecture des transactions
sales = spark.read \
    .option("header", "true") \
    .csv(input_path)

sales = sales.withColumn(
    "sale_date",
    substring(col("timestamp"), 1, 10)
)

sales = sales.withColumn(
    "quantity",
    col("quantity").cast("double")
)

# 4. Recuperer la derniere date historique
last_date_string = sales.agg(
    spark_max("sale_date").alias("last_date")
).collect()[0]["last_date"]

last_date = datetime.strptime(
    last_date_string, "%Y-%m-%d"
).date()

print("Derniere date historique :", last_date)

# 5. Construire les 7 derniers jours calendaires
last_7_dates = [
    (last_date - timedelta(days=i)).strftime("%Y-%m-%d")
    for i in range(6, -1, -1)
]

print("Periode de reference :", last_7_dates)

# 6. Calculer les ventes quotidiennes
daily_sales = sales.filter(
    col("sale_date").isin(last_7_dates)
).groupBy(
    "pharmacy_id", "medicine_id", "sale_date"
).agg(
    spark_sum("quantity").alias("daily_quantity")
)

# 7. Recuperer tous les couples pharmacie-medicament
pairs = sales.select(
    "pharmacy_id", "medicine_id"
).distinct().collect()

# 8. Construire un calendrier complet de 7 jours
# Les jours sans vente seront consideres comme zero.
calendar_rows = []

for pair in pairs:
    for day in last_7_dates:
        calendar_rows.append((
            pair["pharmacy_id"],
            pair["medicine_id"],
            day
        ))

calendar = spark.createDataFrame(
    calendar_rows,
    ["pharmacy_id", "medicine_id", "sale_date"]
)

# 9. Ajouter les ventes quotidiennes au calendrier
complete_sales = calendar.join(
    daily_sales,
    ["pharmacy_id", "medicine_id", "sale_date"],
    "left"
)

complete_sales = complete_sales.na.fill(
    0,
    subset=["daily_quantity"]
)

# 10. Calculer la moyenne et la demande prevue
forecast = complete_sales.groupBy(
    "pharmacy_id", "medicine_id"
).agg(
    round(avg("daily_quantity"), 2).alias(
        "avg_daily_demand"
    ),
    spark_sum("daily_quantity").alias(
        "predicted_demand_7d"
    )
)

# 11. Ajouter les dates de prevision
forecast_start = (
    last_date + timedelta(days=1)
).strftime("%Y-%m-%d")

forecast_end = (
    last_date + timedelta(days=7)
).strftime("%Y-%m-%d")

forecast = forecast.withColumn(
    "history_end_date", lit(last_date_string)
).withColumn(
    "forecast_start_date", lit(forecast_start)
).withColumn(
    "forecast_end_date", lit(forecast_end)
).withColumn(
    "method", lit("MOVING_AVERAGE_7D")
)

# 12. Enregistrer les resultats dans HDFS
forecast.coalesce(1).write \
    .mode("overwrite") \
    .option("header", "true") \
    .csv(output_path)

print("Previsions calculees avec succes.")
print("Nombre de couples :", len(pairs))
print("Debut des previsions :", forecast_start)
print("Fin des previsions :", forecast_end)
print("Resultats enregistres dans :", output_path)

forecast.show(20, False)

spark.stop()
