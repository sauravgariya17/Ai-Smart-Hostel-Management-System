/**
 * fees.js
 * ---------
 * Powers the Fee Management page's four tabs (Fee Structures, Invoices,
 * Payment History, AI Risk) plus the "Record a Payment" quick-entry form.
 */

// Fee structures and invoices are financial/policy records — creating them
// is restricted to Admins on the backend (see app/fees/routes.py). Wardens
// can still view them and record payments, but showing an "Add New" button
// that always fails with a permissions error for wardens is confusing, so
// the button is only rendered for Admins.
function isAdminUser() {
    const user = TokenStore.getUser();
    return !!user && user.role === "admin";
}

function initFeeTabs() {
    const tabs = document.querySelectorAll("#feeModuleTabs .module-tab");
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.remove("active"));
            document.querySelectorAll(".module-tab-pane").forEach((p) => p.classList.remove("active"));
            tab.classList.add("active");
            document.getElementById(tab.getAttribute("data-pane")).classList.add("active");
        });
    });
}

function initFeeStructuresTable() {
    const table = new CrudTable({
        containerId: "feeStructuresApp",
        apiBase: "/api/fees/structures",
        title: "Fee Structure",
        subtitle: "Master rent/fee rates used to generate student invoices",
        searchPlaceholder: false,
        filters: [
            { key: "academic_year", label: "Year", options: [] },
        ],
        columns: [
            { key: "hostel_name", label: "Hostel" },
            { key: "room_type", label: "Room Type" },
            { key: "academic_year", label: "Academic Year" },
            { key: "amount", label: "Amount", render: (v) => `₹${Number(v).toFixed(2)}` },
            { key: "description", label: "Description" },
        ],
        formFields: [
            { key: "academic_year", label: "Academic Year (e.g. 2026-27)", type: "text", required: true },
            { key: "room_type", label: "Room Type", type: "select", options: [
                { value: "single", label: "Single" }, { value: "double", label: "Double" },
                { value: "triple", label: "Triple" }, { value: "dormitory", label: "Dormitory" },
            ]},
            { key: "amount", label: "Amount", type: "number", step: "0.01", required: true },
            { key: "description", label: "Description", type: "textarea" },
        ],
        permissions: { create: isAdminUser(), edit: isAdminUser(), delete: isAdminUser() },
    });
    table.init();
    return table;
}

function initInvoicesTable() {
    const table = new CrudTable({
        containerId: "invoicesApp",
        apiBase: "/api/fees/invoices",
        title: "Fee Invoice",
        subtitle: "Raise and track student fee invoices",
        searchPlaceholder: false,
        filters: [
            { key: "status", label: "Status", options: [
                { value: "pending", label: "Pending" }, { value: "partial", label: "Partial" },
                { value: "paid", label: "Paid" }, { value: "overdue", label: "Overdue" },
            ]},
        ],
        columns: [
            { key: "id", label: "Invoice #" },
            { key: "student_name", label: "Student" },
            { key: "roll_number", label: "Roll No." },
            { key: "academic_year", label: "Year" },
            { key: "amount_due", label: "Due", render: (v) => `₹${Number(v).toFixed(2)}` },
            { key: "amount_paid", label: "Paid", render: (v) => `₹${Number(v).toFixed(2)}` },
            { key: "due_date", label: "Due Date" },
            { key: "status", label: "Status", badge: true },
        ],
        formFields: [
            { key: "student_id", label: "Student ID", type: "number", required: true },
            { key: "academic_year", label: "Academic Year", type: "text", required: true },
            { key: "billing_month", label: "Billing Month", type: "text" },
            { key: "amount_due", label: "Amount Due", type: "number", step: "0.01", required: true },
            { key: "due_date", label: "Due Date", type: "date", required: true },
        ],
        permissions: { create: isAdminUser(), edit: false, delete: false },
    });
    table.init();
    return table;
}

function initPaymentsTable() {
    const table = new CrudTable({
        containerId: "paymentsApp",
        apiBase: "/api/fees/payments",
        title: "Payment",
        subtitle: "Full payment history across all students",
        searchPlaceholder: false,
        filters: [
            { key: "payment_mode", label: "Mode", options: [
                { value: "cash", label: "Cash" }, { value: "card", label: "Card" }, { value: "upi", label: "UPI" },
                { value: "bank_transfer", label: "Bank Transfer" }, { value: "cheque", label: "Cheque" },
            ]},
        ],
        columns: [
            { key: "id", label: "Payment #" },
            { key: "student_name", label: "Student" },
            { key: "amount", label: "Amount", render: (v) => `₹${Number(v).toFixed(2)}` },
            { key: "payment_mode", label: "Mode", badge: true },
            { key: "transaction_reference", label: "Reference" },
            { key: "payment_date", label: "Date", render: (v) => v ? new Date(v).toLocaleString() : "—" },
            { key: "received_by_name", label: "Received By" },
        ],
        formFields: [],
        permissions: { create: false, edit: false, delete: false },
    });
    table.init();
    return table;
}

function initRecordPaymentForm(invoicesTable, paymentsTable) {
    const form = document.getElementById("recordPaymentForm");
    const alertEl = document.getElementById("paymentFormAlert");
    const submitBtn = document.getElementById("recordPaymentBtn");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideAlert(alertEl);

        const payload = {
            student_fee_id: Number(form.student_fee_id.value),
            amount: Number(form.amount.value),
            payment_mode: form.payment_mode.value,
            transaction_reference: form.transaction_reference.value,
        };

        setButtonLoading(submitBtn, true);
        try {
            const response = await apiRequest("/api/fees/payments", { method: "POST", body: JSON.stringify(payload) });
            const data = await response.json();

            if (!response.ok || !data.success) {
                showAlert(alertEl, (data.errors && data.errors.join(" ")) || data.message || "Payment failed.");
                return;
            }

            showAlert(alertEl, "Payment recorded successfully.", "success");
            form.reset();
            invoicesTable.loadData();
            paymentsTable.loadData();
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server.");
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

async function renderStudentFeesView() {
    const container = document.querySelector(".module-tabs").parentElement;
    container.innerHTML = `
        <div class="panel-card mb-3">
            <div class="panel-card-header"><h5 class="mb-0">My Invoices</h5></div>
            <div class="panel-card-body">
                <div class="table-responsive">
                    <table class="table table-hover align-middle crud-table">
                        <thead><tr><th>Academic Year</th><th>Month</th><th>Due</th><th>Paid</th><th>Balance</th><th>Due Date</th><th>Status</th></tr></thead>
                        <tbody id="myInvoicesBody"><tr><td colspan="7" class="text-center text-muted py-4">Loading…</td></tr></tbody>
                    </table>
                </div>
            </div>
        </div>
        <div class="panel-card">
            <div class="panel-card-header"><h5 class="mb-0">My Payment History</h5></div>
            <div class="panel-card-body">
                <div class="table-responsive">
                    <table class="table table-hover align-middle crud-table">
                        <thead><tr><th>Payment #</th><th>Amount</th><th>Mode</th><th>Reference</th><th>Date</th></tr></thead>
                        <tbody id="myPaymentsBody"><tr><td colspan="5" class="text-center text-muted py-4">Loading…</td></tr></tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    const invRes = await apiRequest("/api/fees/invoices/my", { method: "GET" });
    const invData = await invRes.json();
    const invBody = document.getElementById("myInvoicesBody");
    if (invData.success && invData.invoices.length) {
        invBody.innerHTML = invData.invoices.map((i) => `
            <tr>
                <td>${i.academic_year}</td><td>${i.billing_month || "—"}</td>
                <td>₹${Number(i.amount_due).toFixed(2)}</td><td>₹${Number(i.amount_paid).toFixed(2)}</td>
                <td>₹${Number(i.balance).toFixed(2)}</td><td>${i.due_date || "—"}</td>
                <td><span class="table-badge table-badge-${i.status}">${i.status}</span></td>
            </tr>
        `).join("");
    } else {
        invBody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No invoices yet.</td></tr>`;
    }

    const payRes = await apiRequest("/api/fees/payments/my", { method: "GET" });
    const payData = await payRes.json();
    const payBody = document.getElementById("myPaymentsBody");
    if (payData.success && payData.payments.length) {
        payBody.innerHTML = payData.payments.map((p) => `
            <tr>
                <td>#${p.id}</td><td>₹${Number(p.amount).toFixed(2)}</td>
                <td><span class="table-badge">${p.payment_mode}</span></td>
                <td>${p.transaction_reference || "—"}</td>
                <td>${p.payment_date ? new Date(p.payment_date).toLocaleString() : "—"}</td>
            </tr>
        `).join("");
    } else {
        payBody.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-4">No payments yet.</td></tr>`;
    }
}

function renderRiskRow(s) {
    return `
        <tr>
            <td>${s.student_name || "—"}</td>
            <td>${s.roll_number || "—"}</td>
            <td>₹${Number(s.features.total_due).toFixed(2)}</td>
            <td>
                <div class="d-flex align-items-center gap-2">
                    <div class="risk-bar-track" style="width: 60px;">
                        <div class="risk-bar-fill" style="width: ${Math.round(s.features.percent_paid * 100)}%; background: ${s.risk_level === "high" ? "var(--color-danger)" : s.risk_level === "medium" ? "var(--color-warning)" : "var(--color-success)"};"></div>
                    </div>
                    <span>${Math.round(s.features.percent_paid * 100)}%</span>
                </div>
            </td>
            <td>${s.features.max_days_overdue}</td>
            <td>${s.features.overdue_invoice_count}</td>
            <td><span class="risk-badge risk-badge-${s.risk_level}">${Math.round(s.risk_probability * 100)}% ${s.risk_level}</span></td>
        </tr>
    `;
}

async function loadFeeRiskTab() {
    const tbody = document.getElementById("riskTableBody");
    const disclaimerEl = document.getElementById("riskDisclaimer");
    const filterSelect = document.getElementById("riskLevelFilter");

    const response = await apiRequest("/api/ai/fees/defaulters", { method: "GET" });
    const data = await response.json();

    if (!response.ok || !data.success) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">Could not load risk predictions.</td></tr>`;
        return;
    }

    if (data.disclaimer && disclaimerEl) {
        disclaimerEl.querySelector("span").textContent = data.disclaimer;
    }

    function render(level) {
        const filtered = level === "all" ? data.students : data.students.filter((s) => s.risk_level === level);
        if (!filtered.length) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center text-muted py-4">No students in this risk category.</td></tr>`;
            return;
        }
        tbody.innerHTML = filtered.map(renderRiskRow).join("");
    }

    render("all");
    filterSelect.addEventListener("change", () => render(filterSelect.value));
}

document.addEventListener("DOMContentLoaded", () => {
    const user = TokenStore.getUser();
    if (user && user.role === "student") {
        renderStudentFeesView();
        return;
    }

    initFeeTabs();
    initFeeStructuresTable();
    const invoicesTable = initInvoicesTable();
    const paymentsTable = initPaymentsTable();
    initRecordPaymentForm(invoicesTable, paymentsTable);
    loadFeeRiskTab();
});
