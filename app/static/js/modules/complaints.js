/**
 * complaints.js
 * ---------------
 * Complaint Management page adapts to the logged-in role:
 *   Admin / Warden : full triage table (filter, assign, update status)
 *   Student        : "Raise a complaint" form + their own complaint history
 */

const COMPLAINT_CATEGORIES = [
    { value: "electrical", label: "Electrical" }, { value: "plumbing", label: "Plumbing" },
    { value: "cleanliness", label: "Cleanliness" }, { value: "internet", label: "Internet" },
    { value: "food", label: "Food" }, { value: "security", label: "Security" }, { value: "other", label: "Other" },
];

function renderStaffComplaintsView() {
    const table = new CrudTable({
        containerId: "complaintsApp",
        apiBase: "/api/complaints",
        title: "Complaint",
        subtitle: "Triage and resolve student complaints",
        searchPlaceholder: "Search by title...",
        filters: [
            { key: "status", label: "Status", options: [
                { value: "open", label: "Open" }, { value: "in_progress", label: "In Progress" },
                { value: "resolved", label: "Resolved" }, { value: "rejected", label: "Rejected" },
            ]},
            { key: "priority", label: "Priority", options: [
                { value: "low", label: "Low" }, { value: "medium", label: "Medium" }, { value: "high", label: "High" },
            ]},
            { key: "category", label: "Category", options: COMPLAINT_CATEGORIES },
        ],
        columns: [
            { key: "title", label: "Title" },
            { key: "student_name", label: "Student" },
            { key: "category", label: "Category", badge: true },
            { key: "priority", label: "Priority", badge: true },
            { key: "status", label: "Status", badge: true },
            {
                key: "ai_suggested_category",
                label: "AI Suggested",
                render: (v, item) => v
                    ? `<span class="ai-chip ai-chip-sm" title="AI confidence: ${Math.round((item.ai_confidence || 0) * 100)}%"><i class="bi bi-stars"></i> ${v} / ${item.ai_suggested_priority}</span>`
                    : "—",
            },
            { key: "created_at", label: "Raised On", render: (v) => v ? new Date(v).toLocaleDateString() : "—" },
        ],
        formFields: [],
        permissions: { create: false, edit: false, delete: false },
        rowActionsExtra: (item) => `
            <select class="form-select form-select-sm status-select" data-id="${item.id}" style="width: 130px;">
                <option value="">Update status…</option>
                <option value="in_progress" ${item.status === "in_progress" ? "selected" : ""}>In Progress</option>
                <option value="resolved" ${item.status === "resolved" ? "selected" : ""}>Resolved</option>
                <option value="rejected" ${item.status === "rejected" ? "selected" : ""}>Rejected</option>
            </select>
        `,
        bindExtraRowEvents: (tbody) => {
            tbody.querySelectorAll(".status-select").forEach((select) => {
                select.addEventListener("change", async () => {
                    if (!select.value) return;
                    const resolutionNote = ["resolved", "rejected"].includes(select.value)
                        ? (prompt("Resolution note (optional):") || "")
                        : "";
                    const response = await apiRequest(`/api/complaints/${select.getAttribute("data-id")}/status`, {
                        method: "PUT",
                        body: JSON.stringify({ status: select.value, resolution_note: resolutionNote }),
                    });
                    const data = await response.json();
                    if (!data.success) alert(data.message || "Failed to update status.");
                    table.loadData();
                });
            });
        },
    });

    table.init();
}

async function renderStudentComplaintsView() {
    const container = document.getElementById("complaintsApp");
    container.innerHTML = `
        <div class="panel-card mb-3">
            <div class="panel-card-header d-flex align-items-center justify-content-between">
                <h5 class="mb-0">Raise a Complaint</h5>
                <span class="ai-chip"><i class="bi bi-stars"></i> AI-assisted</span>
            </div>
            <div class="panel-card-body">
                <div id="raiseComplaintAlert" class="alert d-none"></div>
                <div id="aiSuggestionBox" class="ai-suggestion-box d-none"></div>
                <form id="raiseComplaintForm" class="row g-3">
                    <div class="col-sm-6">
                        <label class="form-label">Title</label>
                        <input type="text" class="form-control" name="title" required>
                    </div>
                    <div class="col-sm-3">
                        <label class="form-label">Category</label>
                        <select class="form-select" name="category">
                            <option value="">Let AI decide</option>
                            ${COMPLAINT_CATEGORIES.map((c) => `<option value="${c.value}">${c.label}</option>`).join("")}
                        </select>
                    </div>
                    <div class="col-sm-3">
                        <label class="form-label">Priority</label>
                        <select class="form-select" name="priority">
                            <option value="">Let AI decide</option>
                            <option value="low">Low</option>
                            <option value="medium">Medium</option>
                            <option value="high">High</option>
                        </select>
                    </div>
                    <div class="col-12">
                        <label class="form-label">Description</label>
                        <textarea class="form-control" name="description" rows="3"></textarea>
                    </div>
                    <div class="col-12 d-flex flex-wrap gap-2">
                        <button type="button" class="btn btn-outline-secondary btn-sm" id="aiSuggestBtn">
                            <i class="bi bi-stars"></i> AI Suggest Category &amp; Priority
                        </button>
                        <button type="submit" class="btn btn-primary-accent btn-sm" id="raiseComplaintBtn">
                            <span class="btn-text">Submit Complaint</span>
                            <span class="spinner-border spinner-border-sm d-none"></span>
                        </button>
                    </div>
                    <div class="col-12">
                        <small class="text-muted">Leave category/priority on "Let AI decide" to have them auto-classified when you submit.</small>
                    </div>
                </form>
            </div>
        </div>

        <div class="panel-card">
            <div class="panel-card-header"><h5 class="mb-0">My Complaints</h5></div>
            <div class="panel-card-body">
                <div class="table-responsive">
                    <table class="table table-hover align-middle crud-table">
                        <thead><tr><th>Title</th><th>Category</th><th>Priority</th><th>Status</th><th>AI Suggested</th><th>Raised On</th></tr></thead>
                        <tbody id="myComplaintsBody"><tr><td colspan="6" class="text-center text-muted py-4">Loading…</td></tr></tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    async function loadMyComplaints() {
        const response = await apiRequest("/api/complaints/my", { method: "GET" });
        const data = await response.json();
        const tbody = document.getElementById("myComplaintsBody");
        if (!data.success || !data.complaints.length) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No complaints raised yet.</td></tr>`;
            return;
        }
        tbody.innerHTML = data.complaints.map((c) => `
            <tr>
                <td>${c.title}</td>
                <td><span class="table-badge">${c.category}</span></td>
                <td><span class="table-badge table-badge-${c.priority}">${c.priority}</span></td>
                <td><span class="table-badge table-badge-${c.status}">${c.status}</span></td>
                <td>
                    ${c.ai_suggested_category ? `
                        <span class="ai-chip ai-chip-sm" title="AI confidence: ${Math.round((c.ai_confidence || 0) * 100)}%">
                            <i class="bi bi-stars"></i> ${c.ai_suggested_category} / ${c.ai_suggested_priority}
                        </span>` : "—"}
                </td>
                <td>${c.created_at ? new Date(c.created_at).toLocaleDateString() : "—"}</td>
            </tr>
        `).join("");
    }

    document.getElementById("aiSuggestBtn").addEventListener("click", async () => {
        const form = document.getElementById("raiseComplaintForm");
        const box = document.getElementById("aiSuggestionBox");
        const btn = document.getElementById("aiSuggestBtn");

        if (!form.title.value.trim()) {
            box.classList.remove("d-none");
            box.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i> Please enter a title first so AI has something to analyze.`;
            return;
        }

        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Analyzing…`;

        try {
            const response = await apiRequest("/api/ai/complaints/classify", {
                method: "POST",
                body: JSON.stringify({ title: form.title.value, description: form.description.value }),
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                box.classList.remove("d-none");
                box.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i> ${data.message || "Could not get an AI suggestion right now."}`;
                return;
            }

            const p = data.prediction;
            form.category.value = p.predicted_category;
            form.priority.value = p.predicted_priority;

            box.classList.remove("d-none");
            box.innerHTML = `
                <i class="bi bi-stars me-1"></i>
                AI suggests <strong>${p.predicted_category}</strong> (${Math.round(p.category_confidence * 100)}% confident)
                with <strong>${p.predicted_priority}</strong> priority (${Math.round(p.priority_confidence * 100)}% confident).
                Fields have been pre-filled — feel free to change them.
            `;
        } catch (err) {
            box.classList.remove("d-none");
            box.innerHTML = `<i class="bi bi-exclamation-circle me-1"></i> Unable to reach the AI service right now.`;
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHtml;
        }
    });

    document.getElementById("raiseComplaintForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const form = e.target;
        const alertEl = document.getElementById("raiseComplaintAlert");
        const submitBtn = document.getElementById("raiseComplaintBtn");
        hideAlert(alertEl);

        const payload = {
            title: form.title.value,
            category: form.category.value,
            priority: form.priority.value,
            description: form.description.value,
        };

        setButtonLoading(submitBtn, true);
        try {
            const response = await apiRequest("/api/complaints", { method: "POST", body: JSON.stringify(payload) });
            const data = await response.json();
            if (!response.ok || !data.success) {
                showAlert(alertEl, (data.errors && data.errors.join(" ")) || data.message || "Failed to submit complaint.");
                return;
            }
            showAlert(alertEl, "Complaint submitted successfully.", "success");
            form.reset();
            loadMyComplaints();
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server.");
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });

    loadMyComplaints();
}

document.addEventListener("DOMContentLoaded", () => {
    const user = TokenStore.getUser();
    if (user && user.role === "student") {
        renderStudentComplaintsView();
    } else {
        renderStaffComplaintsView();
    }
});
