/**
 * dashboard_admin.js
 * ---------------------
 * Populates the Admin Dashboard's KPI cards and charts.
 */

function formatCurrency(value) {
    return `₹${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

async function loadAdminStats() {
    const response = await apiRequest("/api/dashboard/admin", { method: "GET" });
    if (!response) return;
    const data = await response.json();
    if (!data.success) return;

    const s = data.stats;
    document.getElementById("statTotalStudents").textContent = s.total_students;
    document.getElementById("statRoomsOccupied").textContent = `${s.rooms_occupied}/${s.rooms_occupied + s.rooms_available}`;
    document.getElementById("statOpenComplaints").textContent = s.open_complaints;
    document.getElementById("statTotalWardens").textContent = s.total_wardens;
    document.getElementById("statOccupancyRate").textContent = `${s.occupancy_rate_percent}%`;
    document.getElementById("statFeeCollected").textContent = formatCurrency(s.total_fee_collected);
    document.getElementById("statFeeOutstanding").textContent = formatCurrency(s.total_fee_outstanding);
    document.getElementById("statVisitorsToday").textContent = s.visitors_today;
}

async function loadAdminCharts() {
    const occRes = await apiRequest("/api/reports/occupancy", { method: "GET" });
    if (occRes) {
        const occData = await occRes.json();
        if (occData.success) {
            renderBarChart(
                "dashOccupancyChart",
                occData.report.by_hostel.map((h) => h.hostel_name),
                occData.report.by_hostel.map((h) => h.occupied),
                "Occupied"
            );
        }
    }

    const feeRes = await apiRequest("/api/reports/fee-collection", { method: "GET" });
    if (feeRes) {
        const feeData = await feeRes.json();
        if (feeData.success) {
            renderLineChart(
                "dashCollectionChart",
                feeData.report.monthly_collection.map((m) => m.month),
                feeData.report.monthly_collection.map((m) => m.amount),
                "Collected"
            );
        }
    }
}

async function loadWelcomeUser() {
    const response = await apiRequest("/api/auth/me", { method: "GET" });
    if (!response) return;
    const data = await response.json();
    if (data.success) {
        document.getElementById("welcomeName").textContent = data.user.name;
        TokenStore.save(null, null, data.user);
        populateNavbarUser();
    }
}

async function loadOccupancyForecastWidget() {
    const response = await apiRequest("/api/ai/occupancy/forecast?days=30", { method: "GET" });
    if (!response) return;
    const data = await response.json();
    if (!data.success) return;

    const disclaimerEl = document.getElementById("occupancyForecastDisclaimer");
    if (disclaimerEl) disclaimerEl.textContent = data.disclaimer || "";

    renderLineChart(
        "dashOccupancyForecastChart",
        data.forecast.map((f) => f.date),
        data.forecast.map((f) => f.predicted_occupancy_percent),
        "Predicted Occupancy %"
    );
}

async function loadFeeDefaulterWidget() {
    const response = await apiRequest("/api/ai/fees/defaulters", { method: "GET" });
    if (!response) return;
    const data = await response.json();
    if (!data.success) return;

    const allRisk = data.students;
    document.getElementById("riskHighCount").textContent = allRisk.filter((s) => s.risk_level === "high").length;
    document.getElementById("riskMediumCount").textContent = allRisk.filter((s) => s.risk_level === "medium").length;
    document.getElementById("riskLowCount").textContent = allRisk.filter((s) => s.risk_level === "low").length;

    const listEl = document.getElementById("topRiskStudentsList");
    const topRisky = allRisk.filter((s) => s.risk_level !== "low").slice(0, 5);

    if (!topRisky.length) {
        listEl.innerHTML = `<p class="text-muted mb-0">No students currently flagged as at-risk.</p>`;
        return;
    }

    listEl.innerHTML = topRisky.map((s) => `
        <div class="d-flex align-items-center justify-content-between py-2" style="border-bottom: 1px solid var(--color-border);">
            <div>
                <strong>${s.student_name || "—"}</strong>
                <div class="text-muted" style="font-size: .72rem;">${s.roll_number || ""}</div>
            </div>
            <span class="risk-badge risk-badge-${s.risk_level}">${Math.round(s.risk_probability * 100)}% ${s.risk_level}</span>
        </div>
    `).join("");
}

document.addEventListener("DOMContentLoaded", () => {
    loadWelcomeUser();
    loadAdminStats();
    loadAdminCharts();
    loadOccupancyForecastWidget();
    loadFeeDefaulterWidget();
});
