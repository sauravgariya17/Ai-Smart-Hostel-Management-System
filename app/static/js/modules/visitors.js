/**
 * visitors.js
 * -------------
 * Visitor Management page:
 *   Admin / Warden : front-desk check-in/check-out log (full CRUD)
 *   Student        : read-only list of their own visitors
 */

function buildStaffVisitorsTable() {
    const table = new CrudTable({
        containerId: "visitorsApp",
        apiBase: "/api/visitors",
        title: "Visitor",
        subtitle: "Gate register — check visitors in and out",
        searchPlaceholder: "Search by visitor name or phone...",
        columns: [
            { key: "visitor_name", label: "Visitor" },
            { key: "student_name", label: "Meeting" },
            { key: "relation", label: "Relation" },
            { key: "phone_number", label: "Phone" },
            { key: "check_in_time", label: "Check-in", render: (v) => v ? new Date(v).toLocaleString() : "—" },
            { key: "check_out_time", label: "Check-out", render: (v) => v ? new Date(v).toLocaleString() : "—" },
            {
                key: "is_checked_out",
                label: "Status",
                render: (v) => `<span class="table-badge ${v ? "table-badge-active" : "table-badge-pending"}">${v ? "Checked out" : "Inside"}</span>`,
            },
        ],
        formFields: [
            { key: "student_id", label: "Student ID", type: "number", required: true },
            { key: "visitor_name", label: "Visitor Name", type: "text", required: true },
            { key: "relation", label: "Relation", type: "text" },
            { key: "phone_number", label: "Phone Number", type: "text" },
            { key: "id_proof_type", label: "ID Proof Type", type: "text" },
            { key: "id_proof_number", label: "ID Proof Number", type: "text" },
            { key: "purpose", label: "Purpose of Visit", type: "textarea" },
        ],
        permissions: { create: true, edit: false, delete: false },
        rowActionsExtra: (item) => item.is_checked_out
            ? ""
            : `<button class="icon-btn icon-btn-sm checkout-btn" data-id="${item.id}" title="Check out"><i class="bi bi-box-arrow-right text-danger"></i></button>`,
        bindExtraRowEvents: (tbody) => {
            tbody.querySelectorAll(".checkout-btn").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    const response = await apiRequest(`/api/visitors/${btn.getAttribute("data-id")}/check-out`, {
                        method: "PUT", body: JSON.stringify({}),
                    });
                    const data = await response.json();
                    if (data.success) table.loadData();
                    else alert(data.message || "Check-out failed.");
                });
            });
        },
    });

    return table;
}

async function renderStudentVisitorsView() {
    const container = document.getElementById("visitorsApp");
    container.innerHTML = `
        <div class="panel-card">
            <div class="panel-card-header"><h5 class="mb-0">My Visitors</h5></div>
            <div class="panel-card-body">
                <div class="table-responsive">
                    <table class="table table-hover align-middle crud-table">
                        <thead><tr><th>Visitor</th><th>Relation</th><th>Check-in</th><th>Check-out</th><th>Status</th></tr></thead>
                        <tbody id="myVisitorsBody"><tr><td colspan="5" class="text-center text-muted py-4">Loading…</td></tr></tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    const response = await apiRequest("/api/visitors/my", { method: "GET" });
    const data = await response.json();
    const tbody = document.getElementById("myVisitorsBody");

    if (data.success && data.visitors.length) {
        tbody.innerHTML = data.visitors.map((v) => `
            <tr>
                <td>${v.visitor_name}</td>
                <td>${v.relation || "—"}</td>
                <td>${v.check_in_time ? new Date(v.check_in_time).toLocaleString() : "—"}</td>
                <td>${v.check_out_time ? new Date(v.check_out_time).toLocaleString() : "—"}</td>
                <td><span class="table-badge ${v.is_checked_out ? "table-badge-active" : "table-badge-pending"}">${v.is_checked_out ? "Checked out" : "Inside"}</span></td>
            </tr>
        `).join("");
    } else {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">No visitors recorded yet.</td></tr>`;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const user = TokenStore.getUser();
    if (user && user.role === "student") {
        renderStudentVisitorsView();
        return;
    }

    const table = buildStaffVisitorsTable();
    table.init();
});
