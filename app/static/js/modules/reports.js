/**
 * reports.js
 * ------------
 * Fetches every aggregate /api/reports/* endpoint and renders the
 * corresponding chart using the shared charts.js helpers.
 */

async function loadOccupancyReport() {
    const response = await apiRequest("/api/reports/occupancy", { method: "GET" });
    const data = await response.json();
    if (!data.success) return;

    const report = data.report;
    renderBarChart(
        "occupancyChart",
        report.by_hostel.map((h) => h.hostel_name),
        report.by_hostel.map((h) => h.occupied),
        "Occupied Beds"
    );

    const statusLabels = Object.keys(report.rooms_by_status);
    renderDoughnutChart("roomStatusChart", statusLabels, statusLabels.map((s) => report.rooms_by_status[s]));
}

async function loadFeeCollectionReport() {
    const response = await apiRequest("/api/reports/fee-collection", { method: "GET" });
    const data = await response.json();
    if (!data.success) return;

    const report = data.report;
    renderLineChart(
        "collectionChart",
        report.monthly_collection.map((m) => m.month),
        report.monthly_collection.map((m) => m.amount),
        "Collected"
    );
}

async function loadComplaintsReport() {
    const response = await apiRequest("/api/reports/complaints", { method: "GET" });
    const data = await response.json();
    if (!data.success) return;

    const report = data.report;
    const categoryLabels = Object.keys(report.by_category);
    renderHorizontalBarChart("complaintsChart", categoryLabels, categoryLabels.map((c) => report.by_category[c]), "Complaints");

    const statusLabels = Object.keys(report.by_status);
    renderDoughnutChart("complaintStatusChart", statusLabels, statusLabels.map((s) => report.by_status[s]));
}

async function loadMaintenanceReport() {
    const response = await apiRequest("/api/reports/maintenance", { method: "GET" });
    const data = await response.json();
    if (!data.success) return;

    const report = data.report;
    const statusLabels = Object.keys(report.by_status);
    renderDoughnutChart("maintenanceChart", statusLabels, statusLabels.map((s) => report.by_status[s]));
}

document.addEventListener("DOMContentLoaded", () => {
    loadOccupancyReport();
    loadFeeCollectionReport();
    loadComplaintsReport();
    loadMaintenanceReport();
});
