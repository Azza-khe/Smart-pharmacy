
/*
 * Smart Pharmacy
 * Interface connectee a FastAPI et MongoDB.
 */

// --------------------------------------------------
// 1. CONFIGURATION ET DONNEES
// --------------------------------------------------

const API_URL = "http://127.0.0.1:8000/api";

let predictions = [];
let stocks = [];
let recommendations = [];
let alerts = [];
let statistics = {};

let medicineChart = null;
let pharmacyChart = null;

// --------------------------------------------------
// 2. FONCTIONS UTILITAIRES
// --------------------------------------------------

function getElement(id) {
    return document.getElementById(id);
}

function formatNumber(value) {
    return new Intl.NumberFormat("fr-FR", {
        maximumFractionDigits: 2
    }).format(Number(value) || 0);
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, character => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[character]);
}

function getMedicineName(item) {
    const category = item.medicine_category || item.medicine_id;
    const code = item.atc_code ? ` (${item.atc_code})` : "";

    return `${category}${code}`;
}

function getPharmacyName(item) {
    const name = item.pharmacy_name || item.pharmacy_id || "Pharmacie inconnue";
    const city = item.pharmacy_city ? ` — ${item.pharmacy_city}` : "";

    return `${name}${city}`;
}

function showMessage(elementId, message) {
    const element = getElement(elementId);

    if (element) {
        element.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">${escapeHTML(message)}</td>
            </tr>
        `;
    }
}

// --------------------------------------------------
// 3. RECUPERATION DES DONNEES DEPUIS FASTAPI
// --------------------------------------------------

async function fetchAPI(endpoint) {
    const response = await fetch(`${API_URL}/${endpoint}`);

    if (!response.ok) {
        throw new Error(`Erreur API ${endpoint} : ${response.status}`);
    }

    return await response.json();
}

async function loadDashboardData() {
    const [
        predictionsResult,
        stocksResult,
        recommendationsResult,
        alertsResult,
        statisticsResult
    ] = await Promise.all([
        fetchAPI("predictions"),
        fetchAPI("stocks"),
        fetchAPI("recommendations"),
        fetchAPI("alerts"),
        fetchAPI("stats")
    ]);

    predictions = predictionsResult.data || [];
    stocks = stocksResult.data || [];
    recommendations = recommendationsResult.data || [];
    alerts = alertsResult.data || [];
    statistics = statisticsResult || {};

    console.log("Données récupérées depuis MongoDB :", {
        predictions: predictions.length,
        stocks: stocks.length,
        recommendations: recommendations.length,
        alerts: alerts.length
    });
}

// --------------------------------------------------
// 4. AFFICHAGE DES INDICATEURS
// --------------------------------------------------

function displayMetrics() {
    const pharmaciesCount = new Set(
        predictions.map(item => item.pharmacy_id)
    ).size;

    const medicinesCount = new Set(
        predictions.map(item => item.medicine_id)
    ).size;

    const criticalCount = alerts.filter(
        item => item.level === "CRITIQUE"
    ).length;

    getElement("pharmacy-total").textContent =
        statistics.total_pharmacies ?? pharmaciesCount;

    getElement("medicine-total").textContent =
        statistics.total_medicines ?? medicinesCount;

    getElement("replenishment-total").textContent =
        statistics.to_order ?? recommendations.filter(
            item => item.status === "A_COMMANDER"
        ).length;

    getElement("critical-total").textContent = alerts.length;

    const alertCount = getElement("alert-count");

    if (alertCount) {
        alertCount.textContent = alerts.length;
    }
}

// --------------------------------------------------
// 5. AFFICHAGE DES PREVISIONS
// --------------------------------------------------

function displayPredictions() {
    const tbody = getElement("forecasts-table");

    if (!predictions.length) {
        showMessage("forecasts-table", "Aucune prévision disponible.");
        return;
    }

    tbody.innerHTML = predictions.map(item => {
        const startDate = item.forecast_start_date || "";
        const endDate = item.forecast_end_date || "";

        const period = startDate && endDate
            ? `${startDate} – ${endDate}`
            : "Non renseignée";

        return `
            <tr>
                <td><strong>${escapeHTML(getMedicineName(item))}</strong></td>
                <td>${escapeHTML(getPharmacyName(item))}</td>
                <td>${formatNumber(item.avg_daily_demand)} unités</td>
                <td><strong>${formatNumber(item.predicted_demand_7d)} unités</strong></td>
                <td>${escapeHTML(period)}</td>
            </tr>
        `;
    }).join("");
}

// --------------------------------------------------
// 6. AFFICHAGE DES STOCKS
// --------------------------------------------------

function displayStocks() {
    const tbody = getElement("stocks-table");

    if (!stocks.length) {
        showMessage("stocks-table", "Aucun stock disponible.");
        return;
    }

    tbody.innerHTML = stocks.map(item => {
        const quantity = Number(item.quantity) || 0;
        const threshold = Number(item.min_threshold) || 0;
        const isLow = quantity <= threshold;

        return `
            <tr>
                <td><strong>${escapeHTML(getMedicineName(item))}</strong></td>
                <td>${escapeHTML(getPharmacyName(item))}</td>
                <td>${formatNumber(quantity)} unités</td>
                <td>
                    <span class="status-label ${isLow ? "status-danger" : "status-success"}">
                        ${formatNumber(threshold)} unités
                    </span>
                </td>
            </tr>
        `;
    }).join("");
}

// --------------------------------------------------
// 7. AFFICHAGE DES RECOMMANDATIONS
// --------------------------------------------------

function displayRecommendations() {
    const tbody = getElement("replenishment-table");

    if (!recommendations.length) {
        showMessage("replenishment-table", "Aucune recommandation disponible.");
        return;
    }

    tbody.innerHTML = recommendations.map(item => {
        const toOrder = item.status === "A_COMMANDER";

        return `
            <tr>
                <td><strong>${escapeHTML(getMedicineName(item))}</strong></td>
                <td>${escapeHTML(getPharmacyName(item))}</td>
                <td><strong>${formatNumber(item.recommended_quantity)} unités</strong></td>
                <td>
                    <span class="status-label ${toOrder ? "status-warning" : "status-success"}">
                        ${toOrder ? "À commander" : "Stock suffisant"}
                    </span>
                </td>
            </tr>
        `;
    }).join("");
}

// --------------------------------------------------
// 8. AFFICHAGE DES ALERTES
// --------------------------------------------------

function displayAlerts() {
    const alertList = getElement("alerts-list");

    getElement("alert-count").textContent = alerts.length;

    if (!alerts.length) {
        alertList.innerHTML = `
            <p class="empty-state">Aucune alerte pour le moment.</p>
        `;
        return;
    }

    const sortedAlerts = [...alerts].sort((a, b) => {
        const priority = { CRITIQUE: 0, ATTENTION: 1 };
        return (priority[a.level] ?? 2) - (priority[b.level] ?? 2);
    });

    alertList.innerHTML = sortedAlerts.map(item => {
        const critical = item.level === "CRITIQUE";

        // Les alertes sont enrichies à partir des données déjà chargées.
        const reference = [...stocks, ...predictions].find(
            data =>
                data.medicine_id === item.medicine_id &&
                data.pharmacy_id === item.pharmacy_id
        ) || item;

        return `
            <article class="alert-item">
                <div class="alert-icon ${critical ? "critical" : "warning"}">
                    <i data-lucide="${critical ? "alert-circle" : "alert-triangle"}"></i>
                </div>

                <div class="alert-content">
                    <strong>
                        ${critical ? "Stock critique" : "Stock à surveiller"}
                    </strong>
                    <p>
                        ${escapeHTML(getMedicineName(reference))} ·
                        ${escapeHTML(getPharmacyName(reference))}
                        · ${escapeHTML(item.message)}
                        Couverture : ${formatNumber(item.coverage_days)} jours.
                    </p>
                </div>

                <span class="status-label ${critical ? "status-danger" : "status-warning"}">
                    ${critical ? "Critique" : "Attention"}
                </span>
            </article>
        `;
    }).join("");

    if (typeof lucide !== "undefined") {
        lucide.createIcons();
    }
}

// --------------------------------------------------
// 9. GRAPHIQUES
// --------------------------------------------------

function displayCharts() {
    if (typeof Chart === "undefined") {
        console.warn("Chart.js n'a pas pu être chargé.");
        return;
    }

    // Détruire les anciens graphiques avant actualisation.
    if (medicineChart) medicineChart.destroy();
    if (pharmacyChart) pharmacyChart.destroy();

    // Demande prévue par catégorie de médicament.
    const medicineTotals = {};

    predictions.forEach(item => {
        const name = getMedicineName(item);

        medicineTotals[name] =
            (medicineTotals[name] || 0) +
            (Number(item.predicted_demand_7d) || 0);
    });

    medicineChart = new Chart(getElement("medicine-chart"), {
        type: "bar",
        data: {
            labels: Object.keys(medicineTotals),
            datasets: [{
                label: "Demande prévue (unités)",
                data: Object.values(medicineTotals),
                backgroundColor: "#47765c",
                borderRadius: 6,
                maxBarThickness: 42
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: "#eeeeea" }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });

    // Répartition de la demande par pharmacie.
    const pharmacyTotals = {};

    predictions.forEach(item => {
        const name = getPharmacyName(item);

        pharmacyTotals[name] =
            (pharmacyTotals[name] || 0) +
            (Number(item.predicted_demand_7d) || 0);
    });

    pharmacyChart = new Chart(getElement("pharmacy-chart"), {
        type: "doughnut",
        data: {
            labels: Object.keys(pharmacyTotals),
            datasets: [{
                data: Object.values(pharmacyTotals),
                backgroundColor: [
                    "#244c3b",
                    "#c4775b",
                    "#d8c6a3",
                    "#819b82",
                    "#b8a58b"
                ],
                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        usePointStyle: true,
                        padding: 15,
                        font: { size: 10 }
                    }
                }
            }
        }
    });
}

// --------------------------------------------------
// 10. DATE ET ACTUALISATION
// --------------------------------------------------

function displayCurrentDate() {
    const today = new Date();

    getElement("current-date").textContent =
        today.toLocaleDateString("fr-FR", {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric"
        });
}

// --------------------------------------------------
// 11. INITIALISATION DU TABLEAU DE BORD
// --------------------------------------------------

async function initializeDashboard() {
    const refreshButton = getElement("refresh-button");

    if (refreshButton) {
        refreshButton.disabled = true;
    }

    try {
        await loadDashboardData();

        displayCurrentDate();
        displayMetrics();
        displayPredictions();
        displayStocks();
        displayRecommendations();
        displayAlerts();
        displayCharts();

        if (typeof lucide !== "undefined") {
            lucide.createIcons();
        }

        console.log("Tableau de bord actualisé avec succès.");

    } catch (error) {
        console.error("Erreur de chargement :", error);

        const message =
            "Impossible de charger les données. Vérifiez que FastAPI et MongoDB fonctionnent.";

        showMessage("forecasts-table", message);
        showMessage("stocks-table", message);
        showMessage("replenishment-table", message);

        getElement("alerts-list").innerHTML = `
            <p class="empty-state">${escapeHTML(message)}</p>
        `;

    } finally {
        if (refreshButton) {
            refreshButton.disabled = false;
        }
    }
}

// --------------------------------------------------
// 12. NAVIGATION ET EVENEMENTS
// --------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".nav-link").forEach(link => {
        link.addEventListener("click", () => {
            document.querySelectorAll(".nav-link").forEach(item => {
                item.classList.remove("active");
            });

            link.classList.add("active");
        });
    });

    getElement("refresh-button").addEventListener("click", () => {
        initializeDashboard();
    });

    initializeDashboard();
});
