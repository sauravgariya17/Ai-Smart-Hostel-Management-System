/**
 * dashboard_student.js
 * ------------------------
 * Populates the Student Dashboard's personal KPI cards.
 */

function formatCurrencyStudent(value) {
    return `₹${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

async function loadStudentStats() {
    const response = await apiRequest("/api/dashboard/student", { method: "GET" });
    if (!response) return;
    const data = await response.json();
    if (!data.success) return;

    const s = data.stats;
    document.getElementById("statMyRoom").textContent = s.room_number ? `${s.room_number}` : "Not allocated";
    document.getElementById("statFeeDue").textContent = formatCurrencyStudent(s.total_fee_due);
    document.getElementById("statMyComplaints").textContent = s.open_complaints;
    document.getElementById("statAttendanceRate").textContent = `${s.attendance_rate_percent}%`;
}

async function loadWelcomeUserStudent() {
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
    loadWelcomeUserStudent();
    loadStudentStats();
});
