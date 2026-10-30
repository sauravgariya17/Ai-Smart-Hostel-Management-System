/**
 * rooms.js
 * ----------
 * Powers the Room Management page's four tabs:
 *   Rooms         : full CRUD via CrudTable
 *   Allocations   : list + create allocation + vacate action via CrudTable
 *   Transfers     : custom table with Approve/Reject actions
 *   Availability  : custom read-only grid of rooms with free beds
 */

let hostelOptionsCache = [];

/* ------------------------------------------------------------------ */
/* Tab switching                                                        */
/* ------------------------------------------------------------------ */

function initRoomTabs() {
    const tabs = document.querySelectorAll("#roomModuleTabs .module-tab");
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            tabs.forEach((t) => t.classList.remove("active"));
            document.querySelectorAll(".module-tab-pane").forEach((p) => p.classList.remove("active"));
            tab.classList.add("active");
            document.getElementById(tab.getAttribute("data-pane")).classList.add("active");
        });
    });
}

/* ------------------------------------------------------------------ */
/* Rooms tab                                                            */
/* ------------------------------------------------------------------ */

async function fetchHostelSelectOptions() {
    const res = await fetch("/api/hostels/all", {
        headers: { Authorization: `Bearer ${TokenStore.getAccessToken()}` },
    });
    const data = await res.json();
    if (!data.success) return [];
    return data.hostels.map((h) => ({ value: h.id, label: h.name }));
}

async function initRoomsTab() {
    const hostelOptions = await fetchHostelSelectOptions();

    const table = new CrudTable({
        containerId: "roomsApp",
        apiBase: "/api/rooms",
        title: "Room",
        subtitle: "Manage room inventory across all hostels",
        searchPlaceholder: "Search by room number...",
        filters: [
            { key: "room_type", label: "Type", options: [
                { value: "single", label: "Single" }, { value: "double", label: "Double" },
                { value: "triple", label: "Triple" }, { value: "dormitory", label: "Dormitory" },
            ]},
            { key: "status", label: "Status", options: [
                { value: "available", label: "Available" }, { value: "full", label: "Full" }, { value: "maintenance", label: "Maintenance" },
            ]},
        ],
        columns: [
            { key: "hostel_name", label: "Hostel" },
            { key: "room_number", label: "Room No." },
            { key: "room_type", label: "Type", badge: true },
            { key: "capacity", label: "Capacity" },
            { key: "occupied_beds", label: "Occupied" },
            { key: "monthly_rent", label: "Rent", render: (v) => `₹${Number(v).toFixed(2)}` },
            { key: "status", label: "Status", badge: true },
        ],
        formFields: [
            { key: "hostel_id", label: "Hostel", type: "select", required: true, options: hostelOptions },
            { key: "room_number", label: "Room Number", type: "text", required: true },
            { key: "floor", label: "Floor", type: "number" },
            { key: "room_type", label: "Room Type", type: "select", required: true, options: [
                { value: "single", label: "Single" }, { value: "double", label: "Double" },
                { value: "triple", label: "Triple" }, { value: "dormitory", label: "Dormitory" },
            ]},
            { key: "capacity", label: "Capacity (beds)", type: "number", required: true },
            { key: "monthly_rent", label: "Monthly Rent", type: "number", step: "0.01", required: true },
            { key: "status", label: "Status", type: "select", options: [
                { value: "available", label: "Available" }, { value: "full", label: "Full" }, { value: "maintenance", label: "Maintenance" },
            ]},
        ],
        permissions: { create: true, edit: true, delete: true },
    });

    await table.init();
}

/* ------------------------------------------------------------------ */
/* Allocations tab                                                      */
/* ------------------------------------------------------------------ */

async function initAllocationsTab() {
    const table = new CrudTable({
        containerId: "allocationsApp",
        apiBase: "/api/rooms/allocations",
        title: "Allocation",
        subtitle: "Assign students to rooms and vacate when they leave",
        searchPlaceholder: false,
        filters: [
            { key: "status", label: "Status", options: [
                { value: "active", label: "Active" }, { value: "vacated", label: "Vacated" },
            ]},
        ],
        columns: [
            { key: "student_name", label: "Student" },
            { key: "roll_number", label: "Roll No." },
            { key: "room_number", label: "Room" },
            { key: "hostel_name", label: "Hostel" },
            { key: "allocated_date", label: "Allocated On" },
            { key: "status", label: "Status", badge: true },
        ],
        formFields: [
            { key: "student_id", label: "Student ID", type: "number", required: true },
            { key: "room_id", label: "Room ID", type: "number", required: true },
            { key: "remarks", label: "Remarks", type: "textarea" },
        ],
        permissions: { create: true, edit: false, delete: false },
        rowActionsExtra: (item) => item.status === "active"
            ? `<button class="icon-btn icon-btn-sm vacate-btn" data-id="${item.id}" title="Vacate"><i class="bi bi-box-arrow-right text-danger"></i></button>`
            : "",
        bindExtraRowEvents: (tbody) => {
            tbody.querySelectorAll(".vacate-btn").forEach((btn) => {
                btn.addEventListener("click", async () => {
                    if (!confirm("Vacate this student's room allocation?")) return;
                    const response = await apiRequest(`/api/rooms/allocations/${btn.getAttribute("data-id")}/vacate`, {
                        method: "PUT", body: JSON.stringify({}),
                    });
                    const data = await response.json();
                    if (data.success) window.__allocationsTable.loadData();
                    else alert(data.message || "Failed to vacate room.");
                });
            });
        },
    });

    window.__allocationsTable = table;
    await table.init();
}

/* ------------------------------------------------------------------ */
/* Transfers tab                                                        */
/* ------------------------------------------------------------------ */

async function loadTransfers() {
    const tbody = document.getElementById("transfersTableBody");
    const alertEl = document.getElementById("transfersAlert");
    hideAlert(alertEl);

    const response = await apiRequest("/api/rooms/transfers?per_page=50", { method: "GET" });
    const data = await response.json();

    if (!response.ok || !data.success) {
        showAlert(alertEl, data.message || "Failed to load transfer requests.");
        return;
    }

    if (!data.items.length) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center text-muted py-4">No transfer requests.</td></tr>`;
        return;
    }

    tbody.innerHTML = data.items.map((t) => `
        <tr>
            <td>${t.student_name || "—"}</td>
            <td>${t.current_room_number || "—"}</td>
            <td>${t.requested_room_number || "—"}</td>
            <td>${t.reason || "—"}</td>
            <td><span class="table-badge table-badge-${t.status}">${t.status}</span></td>
            <td class="text-end">
                ${t.status === "pending" ? `
                    <button class="btn btn-sm btn-outline-success approve-transfer-btn" data-id="${t.id}"><i class="bi bi-check-lg"></i></button>
                    <button class="btn btn-sm btn-outline-danger reject-transfer-btn" data-id="${t.id}"><i class="bi bi-x-lg"></i></button>
                ` : "—"}
            </td>
        </tr>
    `).join("");

    tbody.querySelectorAll(".approve-transfer-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const response = await apiRequest(`/api/rooms/transfers/${btn.getAttribute("data-id")}/approve`, { method: "PUT", body: JSON.stringify({}) });
            const data = await response.json();
            if (!data.success) showAlert(document.getElementById("transfersAlert"), data.message || "Approval failed.");
            loadTransfers();
        });
    });
    tbody.querySelectorAll(".reject-transfer-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            const remarks = prompt("Reason for rejection (optional):") || "";
            const response = await apiRequest(`/api/rooms/transfers/${btn.getAttribute("data-id")}/reject`, { method: "PUT", body: JSON.stringify({ remarks }) });
            const data = await response.json();
            if (!data.success) showAlert(document.getElementById("transfersAlert"), data.message || "Rejection failed.");
            loadTransfers();
        });
    });
}

/* ------------------------------------------------------------------ */
/* Availability tab                                                     */
/* ------------------------------------------------------------------ */

async function loadAvailability(roomType = "all") {
    const grid = document.getElementById("availabilityGrid");
    grid.innerHTML = `<div class="col-12 text-center text-muted py-4">Loading…</div>`;

    const params = new URLSearchParams();
    if (roomType !== "all") params.set("room_type", roomType);

    const response = await apiRequest(`/api/rooms/available?${params.toString()}`, { method: "GET" });
    const data = await response.json();

    if (!data.success || !data.rooms.length) {
        grid.innerHTML = `<div class="col-12 text-center text-muted py-4">No available rooms right now.</div>`;
        return;
    }

    grid.innerHTML = data.rooms.map((r) => `
        <div class="col-sm-6 col-lg-4 col-xl-3">
            <div class="stat-mini">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <span class="stat-mini-label">${r.hostel_name || "Hostel"}</span>
                        <div class="stat-mini-value">Room ${r.room_number}</div>
                    </div>
                    <span class="table-badge table-badge-active">${r.available_beds} free</span>
                </div>
                <div class="text-muted small mt-2">
                    ${r.room_type} · ₹${Number(r.monthly_rent).toFixed(2)}/mo · Floor ${r.floor ?? "-"}
                </div>
            </div>
        </div>
    `).join("");
}

/* ------------------------------------------------------------------ */
/* Student self-service view                                            */
/* ------------------------------------------------------------------ */

async function renderStudentRoomsView() {
    const main = document.querySelector(".module-tabs").parentElement;
    main.innerHTML = `
        <div class="panel-card mb-3">
            <div class="panel-card-header"><h5 class="mb-0">My Current Room</h5></div>
            <div class="panel-card-body" id="myRoomInfo">
                <p class="text-muted mb-0">Loading…</p>
            </div>
        </div>

        <div class="panel-card mb-3">
            <div class="panel-card-header"><h5 class="mb-0">Request a Room Transfer</h5></div>
            <div class="panel-card-body">
                <div id="transferRequestAlert" class="alert d-none"></div>
                <form id="transferRequestForm" class="row g-3">
                    <div class="col-sm-4">
                        <label class="form-label">Requested Room ID</label>
                        <input type="number" class="form-control" name="requested_room_id" required>
                        <div class="form-text">See the Availability list below for open room IDs.</div>
                    </div>
                    <div class="col-sm-8">
                        <label class="form-label">Reason</label>
                        <input type="text" class="form-control" name="reason">
                    </div>
                    <div class="col-12">
                        <button type="submit" class="btn btn-primary-accent btn-sm" id="transferRequestBtn">
                            <span class="btn-text">Submit Request</span>
                            <span class="spinner-border spinner-border-sm d-none"></span>
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <div class="panel-card mb-3">
            <div class="panel-card-header"><h5 class="mb-0">My Transfer Requests</h5></div>
            <div class="panel-card-body">
                <div class="table-responsive">
                    <table class="table table-hover align-middle crud-table">
                        <thead><tr><th>Requested Room</th><th>Reason</th><th>Status</th><th>Requested On</th></tr></thead>
                        <tbody id="myTransfersBody"><tr><td colspan="4" class="text-center text-muted py-4">Loading…</td></tr></tbody>
                    </table>
                </div>
            </div>
        </div>

        <div class="panel-card mb-3">
            <div class="panel-card-header d-flex align-items-center justify-content-between">
                <h5 class="mb-0">Smart Room Recommendations</h5>
                <span class="ai-chip"><i class="bi bi-stars"></i> AI-powered</span>
            </div>
            <div class="panel-card-body">
                <p class="text-muted small">Tell us your preferences and our recommendation engine will rank the best-matching available rooms for you.</p>
                <form id="recommendForm" class="row g-3 mb-3">
                    <div class="col-sm-3">
                        <label class="form-label">Room Type</label>
                        <select class="form-select form-select-sm" name="room_type">
                            <option value="">Any</option>
                            <option value="single">Single</option>
                            <option value="double">Double</option>
                            <option value="triple">Triple</option>
                            <option value="dormitory">Dormitory</option>
                        </select>
                    </div>
                    <div class="col-sm-3">
                        <label class="form-label">Max Monthly Rent</label>
                        <input type="number" class="form-control form-control-sm" name="max_rent" placeholder="e.g. 5000">
                    </div>
                    <div class="col-sm-3">
                        <label class="form-label">Preferred Floor</label>
                        <input type="number" class="form-control form-control-sm" name="preferred_floor" placeholder="e.g. 2">
                    </div>
                    <div class="col-sm-3 d-flex align-items-end">
                        <button type="submit" class="btn btn-primary-accent btn-sm w-100" id="recommendBtn">
                            <span class="btn-text"><i class="bi bi-stars"></i> Recommend Rooms</span>
                            <span class="spinner-border spinner-border-sm d-none"></span>
                        </button>
                    </div>
                </form>
                <div id="recommendAlert" class="alert d-none"></div>
                <div class="row g-3" id="recommendResults"></div>
            </div>
        </div>

        <div class="panel-card">
            <div class="panel-card-header d-flex flex-wrap align-items-center justify-content-between gap-2">
                <h5 class="mb-0">Room Availability</h5>
                <select class="form-select form-select-sm" id="availabilityRoomTypeFilter" style="max-width: 200px;">
                    <option value="all">All Room Types</option>
                    <option value="single">Single</option>
                    <option value="double">Double</option>
                    <option value="triple">Triple</option>
                    <option value="dormitory">Dormitory</option>
                </select>
            </div>
            <div class="panel-card-body"><div class="row g-3" id="availabilityGrid"></div></div>
        </div>
    `;

    async function loadMyRoom() {
        const response = await apiRequest("/api/rooms/allocations/my", { method: "GET" });
        const data = await response.json();
        const box = document.getElementById("myRoomInfo");
        if (data.success && data.allocation) {
            const a = data.allocation;
            box.innerHTML = `
                <div class="d-flex flex-wrap gap-4">
                    <div><span class="stat-mini-label">Room</span><div class="stat-mini-value">${a.room_number}</div></div>
                    <div><span class="stat-mini-label">Hostel</span><div class="stat-mini-value">${a.hostel_name || "—"}</div></div>
                    <div><span class="stat-mini-label">Allocated On</span><div class="stat-mini-value">${a.allocated_date}</div></div>
                </div>
            `;
        } else {
            box.innerHTML = `<p class="text-muted mb-0">You do not currently have a room allocated. Please contact the hostel admin.</p>`;
        }
    }

    async function loadMyTransfers() {
        const response = await apiRequest("/api/rooms/transfers/my", { method: "GET" });
        const data = await response.json();
        const tbody = document.getElementById("myTransfersBody");
        if (data.success && data.transfer_requests.length) {
            tbody.innerHTML = data.transfer_requests.map((t) => `
                <tr>
                    <td>${t.requested_room_number || "—"}</td>
                    <td>${t.reason || "—"}</td>
                    <td><span class="table-badge table-badge-${t.status}">${t.status}</span></td>
                    <td>${t.requested_at ? new Date(t.requested_at).toLocaleDateString() : "—"}</td>
                </tr>
            `).join("");
        } else {
            tbody.innerHTML = `<tr><td colspan="4" class="text-center text-muted py-4">No transfer requests yet.</td></tr>`;
        }
    }

    document.getElementById("transferRequestForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const form = e.target;
        const alertEl = document.getElementById("transferRequestAlert");
        const btn = document.getElementById("transferRequestBtn");
        hideAlert(alertEl);

        setButtonLoading(btn, true);
        try {
            const response = await apiRequest("/api/rooms/transfers", {
                method: "POST",
                body: JSON.stringify({ requested_room_id: Number(form.requested_room_id.value), reason: form.reason.value }),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                showAlert(alertEl, (data.errors && data.errors.join(" ")) || data.message || "Failed to submit request.");
                return;
            }
            showAlert(alertEl, "Transfer request submitted.", "success");
            form.reset();
            loadMyTransfers();
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server.");
        } finally {
            setButtonLoading(btn, false);
        }
    });

    async function requestRoom(roomId, reasonText) {
        const alertEl = document.getElementById("recommendAlert");
        hideAlert(alertEl);
        try {
            const response = await apiRequest("/api/rooms/transfers", {
                method: "POST",
                body: JSON.stringify({ requested_room_id: roomId, reason: reasonText }),
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                showAlert(alertEl, (data.errors && data.errors.join(" ")) || data.message || "Failed to submit request.");
                return;
            }
            showAlert(alertEl, `Request submitted for Room ${data.transfer_request.requested_room_number}.`, "success");
            loadMyTransfers();
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server.");
        }
    }

    function renderRecommendations(recommendations) {
        const container = document.getElementById("recommendResults");
        if (!recommendations.length) {
            container.innerHTML = `<div class="col-12 text-center text-muted py-3">No matching rooms found — try widening your preferences.</div>`;
            return;
        }

        container.innerHTML = recommendations.map((r) => `
            <div class="col-sm-6 col-lg-4">
                <div class="stat-mini recommend-card">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <span class="stat-mini-label">${r.hostel_name || "Hostel"} · Room ${r.room_number}</span>
                            <div class="stat-mini-value">${r.match_score}% match</div>
                        </div>
                        <span class="ai-chip ai-chip-sm"><i class="bi bi-stars"></i> #${r.match_rank}</span>
                    </div>
                    <div class="text-muted small mt-2 mb-2">
                        ${r.room_type} · ₹${Number(r.monthly_rent).toFixed(2)}/mo · Floor ${r.floor ?? "-"} · ${r.available_beds} bed(s) free
                    </div>
                    <button class="btn btn-outline-secondary btn-sm w-100 request-room-btn" data-room-id="${r.id}">
                        Request This Room
                    </button>
                </div>
            </div>
        `).join("");

        container.querySelectorAll(".request-room-btn").forEach((btn) => {
            btn.addEventListener("click", () => requestRoom(Number(btn.getAttribute("data-room-id")), "Requested via AI room recommendation."));
        });
    }

    document.getElementById("recommendForm").addEventListener("submit", async (e) => {
        e.preventDefault();
        const form = e.target;
        const alertEl = document.getElementById("recommendAlert");
        const btn = document.getElementById("recommendBtn");
        hideAlert(alertEl);
        setButtonLoading(btn, true);

        const params = new URLSearchParams();
        if (form.room_type.value) params.set("room_type", form.room_type.value);
        if (form.max_rent.value) params.set("max_rent", form.max_rent.value);
        if (form.preferred_floor.value) params.set("preferred_floor", form.preferred_floor.value);

        try {
            const response = await apiRequest(`/api/ai/rooms/recommend?${params.toString()}`, { method: "GET" });
            const data = await response.json();
            if (!response.ok || !data.success) {
                showAlert(alertEl, data.message || "Could not fetch recommendations.");
                return;
            }
            renderRecommendations(data.recommendations);
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server.");
        } finally {
            setButtonLoading(btn, false);
        }
    });

    document.getElementById("availabilityRoomTypeFilter").addEventListener("change", (e) => loadAvailability(e.target.value));

    await loadMyRoom();
    await loadMyTransfers();
    await loadAvailability();
}

/* ------------------------------------------------------------------ */
/* Init                                                                  */
/* ------------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", async () => {
    const user = TokenStore.getUser();

    if (user && user.role === "student") {
        await renderStudentRoomsView();
        return;
    }

    initRoomTabs();
    await initRoomsTab();
    await initAllocationsTab();
    await loadTransfers();
    await loadAvailability();

    document.getElementById("availabilityRoomTypeFilter").addEventListener("change", (e) => {
        loadAvailability(e.target.value);
    });
});
