/**
 * dashboard_warden.js
 * ----------------------
 * Populates the Warden Dashboard's KPI cards and attendance chart.
 */

async function loadWardenStats() {
    const response = await apiRequest("/api/dashboard/warden", { method: "GET" });
    if (!response) return;
    const data = await response.json();
    if (!data.success) return;

    const s = data.stats;
    document.getElementById("statOpenComplaints").textContent = s.open_complaints;
    document.getElementById("statPresentToday").textContent = `${s.present_today}/${s.total_students}`;
    document.getElementById("statActiveVisitors").textContent = s.active_visitors;
    document.getElementById("statPendingMaintenance").textContent = s.pending_maintenance;

    renderDoughnutChart(
        "attendanceRateChart",
        ["Present", "Absent/Not Marked"],
        [s.present_today, Math.max(s.total_students - s.present_today, 0)]
    );
}

async function loadWelcomeUserWarden() {
    const response = await apiRequest("/api/auth/me", { method: "GET" });
    if (!response) return;
    const data = await response.json();
    if (data.success) {
        document.getElementById("welcomeName").textContent = data.user.name;
        TokenStore.save(null, null, data.user);
        populateNavbarUser();
    }
}

document.addEventListener("DOMContentLoaded", () => {
    loadWelcomeUserWarden();
    loadWardenStats();
});
