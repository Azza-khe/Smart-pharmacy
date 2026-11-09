/* ==========================================
   SMART PHARMACY - APPLICATION JAVASCRIPT
========================================== */

const API_URL = "http://127.0.0.1:8000/api";

// Données de l'application
let stocks = [];
let alerts = [];
let predictions = [];
let medicineChart = null;
let pharmacyChart = null;

// ==========================================
// 1. UTILITAIRES
// ==========================================

function getElement(id) {
    return document.getElementById(id);
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;"
    })[char]);
}

function getValue(object, fields, fallback = "Non renseigné") {
    for (const field of fields) {
        if (object?.[field] !== undefined && object[field] !== null) {
            return object[field];
        }
    }
    return fallback;
}

function getArray(response) {
    if (Array.isArray(response)) return response;
    if (Array.isArray(response?.data)) return response.data;
    if (Array.isArray(response?.results)) return response.results;
    return [];
}

function formatNumber(value) {
    const number = Number(value);
    return Number.isFinite(number)
        ? number.toLocaleString("fr-FR")
        : "0";
}

function formatDate(value) {
    if (!value) return "";

    const date = new Date(value);

    if (Number.isNaN(date.getTime())) return "";

    return date.toLocaleString("fr-FR");
}

function showMessage(message) {
    console.log(message);
}

// ==========================================
// 2. COMMUNICATION AVEC LE BACKEND
// ==========================================

async function fetchAPI(endpoint) {
    const response = await fetch(`${API_URL}/${endpoint}`);

    if (!response.ok) {
        throw new Error(
            `Erreur API ${endpoint} : ${response.status}`
        );
    }

    return await response.json();
}

async function loadEndpoint(endpoint) {
    try {
        return await fetchAPI(endpoint);
    } catch (error) {
        console.error(error);
        return null;
    }
}

// ==========================================
// 3. CHARGEMENT DES DONNÉES
// ==========================================

async function loadDashboardData() {
    const [stocksResponse, alertsResponse, predictionsResponse] =
        await Promise.all([
            loadEndpoint("stocks"),
            loadEndpoint("alerts"),
            loadEndpoint("predictions")
        ]);

    stocks = getArray(stocksResponse);
    alerts = getArray(alertsResponse);
    predictions = getArray(predictionsResponse);

    displayMetrics();
    displayStocks();
    displayAlerts();
    displayCharts();

    checkNewAlerts(alerts);

    console.log("Données du tableau de bord actualisées.");
}

// ==========================================
// 4. INDICATEURS
// ==========================================

function displayMetrics() {
    const pharmacyIds = new Set();
    const medicineIds = new Set();

    stocks.forEach(stock => {
        const pharmacy = getValue(
            stock,
            ["pharmacy_id", "pharmacy_name"],
            null
        );

        const medicine = getValue(
            stock,
            ["medicine_id", "medicine_name"],
            null
        );

        if (pharmacy !== null) pharmacyIds.add(pharmacy);
        if (medicine !== null) medicineIds.add(medicine);
    });

    // Nombre de pharmacies
    if (getElement("pharmacy-total")) {
        getElement("pharmacy-total").textContent =
            formatNumber(pharmacyIds.size);
    }

    // Nombre de médicaments
    if (getElement("medicine-total")) {
        getElement("medicine-total").textContent =
            formatNumber(medicineIds.size);
    }

    // Nombre d'alertes actives
    if (getElement("critical-total")) {
        getElement("critical-total").textContent =
            formatNumber(alerts.length);
    }

    // Badge dans le menu latéral
    if (getElement("alert-count")) {
        getElement("alert-count").textContent =
            formatNumber(alerts.length);
    }
}

// ==========================================
// 5. AFFICHAGE DES STOCKS
// ==========================================

function displayStocks() {
    const table = getElement("stocks-table");

    if (!table) return;

    if (stocks.length === 0) {
        table.innerHTML = `
            <tr>
                <td colspan="4" class="empty-state">
                    Aucun stock disponible.
                </td>
            </tr>
        `;
        return;
    }

    table.innerHTML = stocks.map(stock => {
        const medicine = getValue(
            stock,
            ["medicine_name", "medicine_category", "medicine_id"]
        );

        const pharmacy = getValue(
            stock,
            ["pharmacy_name", "pharmacy_city", "pharmacy_id"]
        );

        const quantity = Number(
            getValue(stock, ["quantity", "current_stock"], 0)
        );

        const threshold = Number(
            getValue(stock, ["min_threshold", "minimum_stock"], 0)
        );

        const stockClass =
            quantity <= threshold ? "low" : "normal";

        return `
            <tr>
                <td>${escapeHTML(medicine)}</td>
                <td>${escapeHTML(pharmacy)}</td>
                <td>
                    <span class="stock-value ${stockClass}">
                        ${formatNumber(quantity)}
                    </span>
                </td>
                <td>${formatNumber(threshold)}</td>
            </tr>
        `;
    }).join("");
}

// ==========================================
// 6. AFFICHAGE DES ALERTES
// ==========================================

function getAlertType(alert) {
    const status = String(
        getValue(alert, ["status", "level", "type"], "")
    ).toUpperCase();

    if (
        status.includes("OUT") ||
        status.includes("RUPTURE") ||
        status.includes("CRITIQUE")
    ) {
        return "out";
    }

    return "low";
}

function displayAlerts() {
    const container = getElement("alerts-list");

    if (!container) return;

    if (alerts.length === 0) {
        container.innerHTML = `
            <p class="empty-state">
                Aucune alerte active. Tous les stocks sont sous surveillance.
            </p>
        `;
        return;
    }

    container.innerHTML = alerts.map(alert => {
        const type = getAlertType(alert);

        const medicine = getValue(
            alert,
            ["medicine_name", "medicine_category", "medicine_id"]
        );

        const pharmacy = getValue(
            alert,
            ["pharmacy_name", "pharmacy_id"]
        );

        const message = getValue(
            alert,
            ["message"],
            "Une situation nécessite votre attention."
        );

        const currentStock = getValue(
            alert,
            ["current_stock", "quantity"],
            null
        );

        const threshold = getValue(
            alert,
            ["min_threshold"],
            null
        );

        const date = formatDate(
            getValue(alert, ["created_at"], null)
        );

        return `
            <article class="alert-card ${type}">
                <div class="alert-card-icon">
                    <i data-lucide="alert-triangle"></i>
                </div>

                <div class="alert-card-content">
                    <strong>
                        ${type === "out" ? "Rupture de stock" : "Stock faible"}
                        - ${escapeHTML(medicine)}
                    </strong>

                    <p>${escapeHTML(message)}</p>

                    <div class="alert-meta">
                        Pharmacie : ${escapeHTML(pharmacy)}
                        ${currentStock !== null
                            ? ` | Stock actuel : ${escapeHTML(currentStock)}`
                            : ""}
                        ${threshold !== null
                            ? ` | Seuil minimum : ${escapeHTML(threshold)}`
                            : ""}
                        ${date ? ` | ${escapeHTML(date)}` : ""}
                    </div>
                </div>
            </article>
        `;
    }).join("");

    if (window.lucide) {
        lucide.createIcons();
    }
}

// ==========================================
// 7. GRAPHIQUE : DEMANDE PAR MÉDICAMENT
// ==========================================

function displayMedicineChart() {
    const canvas = getElement("medicine-chart");

    if (!canvas || !window.Chart) return;

    const totals = {};

    predictions.forEach(item => {
        const medicine = getValue(
            item,
            ["medicine_category", "medicine_name", "medicine_id"],
            "Autre"
        );

        const demand = Number(
            getValue(
                item,
                ["predicted_demand_7d", "predicted_demand", "avg_daily_demand"],
                0
            )
        );

        totals[medicine] = (totals[medicine] || 0) + demand;
    });

    const labels = Object.keys(totals);
    const values = Object.values(totals);

    if (medicineChart) medicineChart.destroy();

    medicineChart = new Chart(canvas, {
        type: "bar",
        data: {
            labels: labels.length ? labels : ["Aucune donnée"],
            datasets: [{
                label: "Demande prévue",
                data: labels.length ? values : [0],
                backgroundColor: "#244b3c",
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// ==========================================
// 8. GRAPHIQUE : RÉPARTITION PAR PHARMACIE
// ==========================================

function displayPharmacyChart() {
    const canvas = getElement("pharmacy-chart");

    if (!canvas || !window.Chart) return;

    const totals = {};

    predictions.forEach(item => {
        const pharmacy = getValue(
            item,
            ["pharmacy_name", "pharmacy_city", "pharmacy_id"],
            "Autre"
        );

        const demand = Number(
            getValue(
                item,
                ["predicted_demand_7d", "predicted_demand", "avg_daily_demand"],
                0
            )
        );

        totals[pharmacy] = (totals[pharmacy] || 0) + demand;
    });

    const labels = Object.keys(totals);
    const values = Object.values(totals);

    if (pharmacyChart) pharmacyChart.destroy();

    pharmacyChart = new Chart(canvas, {
        type: "doughnut",
        data: {
            labels: labels.length ? labels : ["Aucune donnée"],
            datasets: [{
                data: labels.length ? values : [1],
                backgroundColor: [
                    "#244b3c",
                    "#bd795c",
                    "#d8c6a5",
                    "#829b87",
                    "#c7a16c",
                    "#a8b9ad"
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
                    position: "bottom"
                }
            }
        }
    });
}

function displayCharts() {
    displayMedicineChart();
    displayPharmacyChart();
}

// ==========================================
// 9. NOTIFICATIONS TOAST
// ==========================================

function getToastContainer() {
    let container = getElement("toast-container");

    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    return container;
}

function getAlertKey(alert) {
    const id = alert._id || alert.id;

    if (id) return String(id);

    return [
        alert.pharmacy_id,
        alert.medicine_id,
        alert.created_at || alert.updated_at || ""
    ].join("_");
}

function getNotifiedAlerts() {
    try {
        return JSON.parse(
            localStorage.getItem("smart_pharmacy_notified_alerts") || "[]"
        );
    } catch {
        return [];
    }
}

function saveNotifiedAlerts(keys) {
    try {
        localStorage.setItem(
            "smart_pharmacy_notified_alerts",
            JSON.stringify(keys.slice(-300))
        );
    } catch (error) {
        console.warn("Impossible de sauvegarder les notifications.", error);
    }
}

function showToast(alert) {
    const container = getToastContainer();
    const type = getAlertType(alert);

    const medicine = getValue(
        alert,
        ["medicine_name", "medicine_category", "medicine_id"]
    );

    const message = getValue(
        alert,
        ["message"],
        "Une situation nécessite votre attention."
    );

    const toast = document.createElement("div");

    toast.className = `toast ${type === "out" ? "toast--out" : "toast--low"}`;

    toast.innerHTML = `
        <div class="toast-icon">
            <i data-lucide="alert-triangle"></i>
        </div>

        <div class="toast-body">
            <div class="toast-title">
                ${type === "out" ? "Rupture de stock" : "Stock faible"}
            </div>

            <div class="toast-message">
                ${escapeHTML(medicine)} : ${escapeHTML(message)}
            </div>
        </div>

        <button class="toast-close" aria-label="Fermer">
            &times;
        </button>

        <div class="toast-progress"></div>
    `;

    container.appendChild(toast);

    if (window.lucide) {
        lucide.createIcons();
    }

    const closeToast = () => {
        toast.remove();
    };

    toast.querySelector(".toast-close").addEventListener(
        "click",
        closeToast
    );

    setTimeout(closeToast, 8000);
}

function checkNewAlerts(currentAlerts) {
    const notified = getNotifiedAlerts();

    currentAlerts.forEach(alert => {
        const key = getAlertKey(alert);

        if (!notified.includes(key)) {
            showToast(alert);
            notified.push(key);
        }
    });

    saveNotifiedAlerts(notified);
}

// ==========================================
// 10. ACTUALISATION DES ALERTES
// ==========================================

async function refreshAlerts() {
    const response = await loadEndpoint("alerts");

    if (response === null) return;

    alerts = getArray(response);

    displayAlerts();
    displayMetrics();
    checkNewAlerts(alerts);
}

// ==========================================
// 11. INITIALISATION
// ==========================================

function displayCurrentDate() {
    const element = getElement("current-date");

    if (!element) return;

    element.textContent = new Date().toLocaleDateString(
        "fr-FR",
        {
            weekday: "long",
            day: "numeric",
            month: "long",
            year: "numeric"
        }
    );
}

function initializeDashboard() {
    displayCurrentDate();

    if (window.lucide) {
        lucide.createIcons();
    }

    const refreshButton = getElement("refresh-button");

    if (refreshButton) {
        refreshButton.addEventListener("click", async () => {
            refreshButton.disabled = true;

            try {
                await loadDashboardData();
            } finally {
                refreshButton.disabled = false;
            }
        });
    }

    loadDashboardData();

    // Vérification des nouvelles alertes toutes les 30 secondes
    setInterval(refreshAlerts, 30000);
}

document.addEventListener("DOMContentLoaded", initializeDashboard);