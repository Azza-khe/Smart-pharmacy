#  Smart Pharmacy — Big Data Project

## Présentation

**Smart Pharmacy** est un projet Big Data visant à améliorer la gestion des ventes et des stocks de plusieurs pharmacies.

Le projet combine le traitement batch des données historiques et le traitement des ventes en temps réel afin de produire des statistiques, suivre les stocks et détecter les situations de stock faible ou de rupture.

## Objectifs

- Analyser les ventes historiques des pharmacies.
- Centraliser et traiter les données avec Hadoop et Apache Spark.
- Suivre les stocks en temps réel.
- Déclencher des alertes lorsque le stock atteint un seuil critique.
- Visualiser les indicateurs à travers un dashboard.

##  Architecture du projet

Le projet est organisé en trois parties principales :

### 1. Préparation des données
- Préparation et simulation des fichiers CSV.
- Organisation des données de ventes, médicaments, pharmacies et stock initial.

### 2. HDFS & Spark Batch
- Stockage distribué des données dans HDFS.
- Traitement des ventes historiques avec Spark RDD et DataFrames.
- Jointures entre les ventes et les référentiels.
- Calcul des statistiques par pharmacie, médicament, catégorie et jour.
- Exportation des résultats analytiques en CSV.

### 3. Streaming & Dashboard
- Traitement des nouvelles ventes avec Kafka.
- Mise à jour du stock en temps réel.
- Détection des alertes de stock faible et de rupture.
- Persistance des données opérationnelles avec MongoDB.
- Visualisation des données à travers un dashboard.

##  Technologies utilisées

- **Apache Hadoop / HDFS** — Stockage distribué
- **Apache Spark** — Traitement Batch
- **Scala** — Programmation Spark
- **Apache Kafka** — Streaming des ventes
- **MongoDB** — Stockage opérationnel
- **CSV** — Format des données sources et résultats
- **Docker** — Environnement de déploiement

##  Résultats du traitement Batch

Le traitement Spark a permis d’analyser **1 443 519 transactions historiques**.

Exemples de résultats obtenus :

| Pharmacie | Ville | Quantité vendue |
|---|---|---:|
| Pharmacie El Amel | Sfax | 976 878 |
| Pharmacie Ennour | Sousse | 849 225 |
| Pharmacie La Marsa | Bizerte | 776 182 |
| Pharmacie Ibn Sina | Nabeul | 765 908 |
| Pharmacie Centrale | Tunis | 631 101 |

Les résultats sont exportés dans HDFS sous forme de fichiers CSV et peuvent être utilisés par le dashboard.

##  Répartition du travail

- **Membre 1 :** Préparation et simulation des données.
- **Membre 2 :** Stockage HDFS et traitement Spark Batch.
- **Membre 3 :** Streaming Kafka, gestion des stocks, alertes, MongoDB et dashboard.

## Gestion des alertes

Le stock est mis à jour à partir des nouvelles ventes :

- **Stock faible :** stock restant inférieur ou égal au seuil minimal.
- **Rupture de stock :** stock restant inférieur ou égal à zéro.

Les statistiques historiques Batch sont utilisées pour analyser la demande, tandis que les alertes sont déclenchées à partir des mises à jour opérationnelles en temps réel.

## 🎓Contexte académique

Projet réalisé dans le cadre du module **Big Data** à l’**École Nationale des Sciences de l’Informatique (ENSI)**, Université de la Manouba, année universitaire 2026–2027.
