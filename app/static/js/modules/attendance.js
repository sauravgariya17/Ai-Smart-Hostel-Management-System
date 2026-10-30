/**
 * attendance.js
 * ---------------
 * Attendance Management page: a quick "mark attendance" form plus a
 * searchable/filterable/paginated history table.
 */

function initAttendanceTable() {
    return new CrudTable({
        containerId: "attendanceApp",
        apiBase: "/api/attendance",
        title: "Attendance",
        subtitle: "Daily attendance history",
        searchPlaceholder: false,
        filters: [
            { key: "status", label: "Status", options: [
                { value: "present", label: "Present" }, { value: "absent", label: "Absent" }, { value: "leave", label: "Leave" },
            ]},
        ],
        columns: [
            { key: "student_name", label: "Student" },
            { key: "roll_number", label: "Roll No." },
            { key: "attendance_date", label: "Date" },
            { key: "status", label: "Status", badge: true },
            { key: "remarks", label: "Remarks" },
        ],
        formFields: [],
        permissions: { create: false, edit: false, delete: false },
    });
}

function initMarkAttendanceForm(table) {
    const form = document.getElementById("markAttendanceForm");
    const alertEl = document.getElementById("markAttendanceAlert");
    const submitBtn = document.getElementById("markAttendanceBtn");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideAlert(alertEl);

        const payload = {
            student_id: Number(form.student_id.value),
            attendance_date: form.attendance_date.value || undefined,
            status: form.status.value,
            remarks: form.remarks.value,
        };

        setButtonLoading(submitBtn, true);
        try {
            const response = await apiRequest("/api/attendance", { method: "POST", body: JSON.stringify(payload) });
            const data = await response.json();

            if (!response.ok || !data.success) {
                showAlert(alertEl, (data.errors && data.errors.join(" ")) || data.message || "Failed to mark attendance.");
                return;
            }

            showAlert(alertEl, "Attendance recorded.", "success");
            form.reset();
            table.loadData();
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server.");
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

async function renderStudentAttendanceView() {
    const wrapper = document.querySelector(".panel-card").parentElement;
    wrapper.innerHTML = `
        <div class="panel-card">
            <div class="panel-card-header"><h5 class="mb-0">My Attendance History</h5></div>
            <div class="panel-card-body">
                <div class="table-responsive">
                    <table class="table table-hover align-middle crud-table">
                        <thead><tr><th>Date</th><th>Status</th><th>Remarks</th></tr></thead>
                        <tbody id="myAttendanceBody"><tr><td colspan="3" class="text-center text-muted py-4">Loading…</td></tr></tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    const response = await apiRequest("/api/attendance/my", { method: "GET" });
    const data = await response.json();
    const tbody = document.getElementById("myAttendanceBody");

    if (data.success && data.attendance.length) {
        tbody.innerHTML = data.attendance.map((a) => `
            <tr>
                <td>${a.attendance_date}</td>
                <td><span class="table-badge table-badge-${a.status}">${a.status}</span></td>
                <td>${a.remarks || "—"}</td>
            </tr>
        `).join("");
    } else {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-muted py-4">No attendance records yet.</td></tr>`;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const user = TokenStore.getUser();
    if (user && user.role === "student") {
        renderStudentAttendanceView();
        return;
    }

    const table = initAttendanceTable();
    table.init();
    initMarkAttendanceForm(table);
});
