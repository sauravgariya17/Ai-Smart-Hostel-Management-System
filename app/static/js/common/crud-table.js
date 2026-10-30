/**
 * crud-table.js
 * ---------------
 * A single, reusable "list + search + filter + paginate + create/edit/delete"
 * table engine shared by every management page (Students, Hostels, Rooms,
 * Fees, Visitors, Attendance, Complaints, Maintenance...).
 *
 * Each module's own JS file (students.js, hostels.js, ...) simply builds a
 * config object describing its columns/fields/endpoints and hands it to
 * `new CrudTable(config).init()`. This keeps every module's markup and
 * pagination/search/filter behavior perfectly consistent while letting each
 * module define its own columns, form fields, and permissions.
 *
 * Config shape:
 * {
 *   containerId: "studentsApp",
 *   apiBase: "/api/students",
 *   title: "Students",
 *   subtitle: "Manage student records",
 *   idField: "id",
 *   searchPlaceholder: "Search by name or roll number...",
 *   filters: [{ key: "course", label: "Course", options: [{value:"CSE",label:"CSE"}, ...] }],
 *   columns: [{ key: "name", label: "Name" }, { key: "email", label: "Email" },
 *             { key: "role", label: "Role", badge: true }],
 *   formFields: [{ key:"name", label:"Full Name", type:"text", required:true }, ...],
 *   permissions: { create: true, edit: true, delete: true },
 *   rowActionsExtra: (item) => "" // optional extra HTML buttons per row
 *   onRowAction: (action, item) => {} // handle custom actions fired by rowActionsExtra
 *   transformListResponse: (data) => data.items // override if endpoint isn't the standard {items, pagination} shape
 * }
 */

class CrudTable {
    constructor(config) {
        this.config = Object.assign({
            idField: "id",
            filters: [],
            formFields: [],
            permissions: { create: true, edit: true, delete: true },
        }, config);

        this.container = document.getElementById(this.config.containerId);
        this.state = { page: 1, per_page: 10, search: "", filters: {}, items: [], pagination: null };
    }

    async init() {
        if (!this.container) return;
        this.renderShell();
        this.bindStaticEvents();
        await this.loadData();
    }

    /* ------------------------------------------------------------ */
    /* Shell / markup                                                 */
    /* ------------------------------------------------------------ */

    renderShell() {
        const { title, subtitle, searchPlaceholder, filters, permissions } = this.config;

        const filterHtml = filters.map((f) => `
            <select class="form-select form-select-sm crud-filter" data-key="${f.key}" style="max-width: 180px;">
                <option value="all">${f.label}: All</option>
                ${f.options.map((o) => `<option value="${o.value}">${o.label}</option>`).join("")}
            </select>
        `).join("");

        this.container.innerHTML = `
            <div class="panel-card">
                <div class="panel-card-header d-flex flex-wrap align-items-center justify-content-between gap-2">
                    <div>
                        <h5 class="mb-0">${title}</h5>
                        ${subtitle ? `<small class="text-muted">${subtitle}</small>` : ""}
                    </div>
                    ${permissions.create ? `
                        <button class="btn btn-primary-accent btn-sm" id="crudAddBtn">
                            <i class="bi bi-plus-lg"></i> Add New
                        </button>` : ""}
                </div>
                <div class="panel-card-body">
                    <div class="d-flex flex-wrap gap-2 mb-3">
                        ${searchPlaceholder !== false ? `
                            <div class="input-group input-group-sm" style="max-width: 260px;">
                                <span class="input-group-text"><i class="bi bi-search"></i></span>
                                <input type="text" class="form-control" id="crudSearchInput" placeholder="${searchPlaceholder || "Search..."}">
                            </div>` : ""}
                        ${filterHtml}
                    </div>

                    <div id="crudAlert" class="alert d-none" role="alert"></div>

                    <div class="table-responsive">
                        <table class="table table-hover align-middle crud-table">
                            <thead>
                                <tr>
                                    ${this.config.columns.map((c) => `<th>${c.label}</th>`).join("")}
                                    <th class="text-end">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="crudTableBody">
                                <tr><td colspan="${this.config.columns.length + 1}" class="text-center py-4 text-muted">Loading…</td></tr>
                            </tbody>
                        </table>
                    </div>

                    <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mt-2">
                        <small class="text-muted" id="crudPaginationInfo"></small>
                        <nav><ul class="pagination pagination-sm mb-0" id="crudPaginationControls"></ul></nav>
                    </div>
                </div>
            </div>

            <div class="modal fade" id="crudModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" id="crudModalTitle">Add</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div id="crudFormAlert" class="alert d-none" role="alert"></div>
                            <form id="crudForm">${this.renderFormFields()}</form>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-outline-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-primary-accent btn-sm" id="crudSaveBtn">
                                <span class="btn-text">Save</span>
                                <span class="spinner-border spinner-border-sm d-none" role="status"></span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        this.modalEl = new bootstrap.Modal(document.getElementById("crudModal"));
    }

    renderFormFields() {
        return this.config.formFields.map((field) => {
            const req = field.required ? "required" : "";
            if (field.type === "select") {
                return `
                    <div class="mb-3">
                        <label class="form-label">${field.label}</label>
                        <select class="form-select" name="${field.key}" ${req}>
                            <option value="">Select ${field.label}</option>
                            ${(field.options || []).map((o) => `<option value="${o.value}">${o.label}</option>`).join("")}
                        </select>
                    </div>`;
            }
            if (field.type === "textarea") {
                return `
                    <div class="mb-3">
                        <label class="form-label">${field.label}</label>
                        <textarea class="form-control" name="${field.key}" rows="3" ${req}></textarea>
                    </div>`;
            }
            return `
                <div class="mb-3">
                    <label class="form-label">${field.label}</label>
                    <input type="${field.type || "text"}" class="form-control" name="${field.key}" ${req} ${field.step ? `step="${field.step}"` : ""}>
                </div>`;
        }).join("");
    }

    /* ------------------------------------------------------------ */
    /* Events                                                         */
    /* ------------------------------------------------------------ */

    bindStaticEvents() {
        const searchInput = document.getElementById("crudSearchInput");
        if (searchInput) {
            let debounceTimer;
            searchInput.addEventListener("input", () => {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    this.state.search = searchInput.value.trim();
                    this.state.page = 1;
                    this.loadData();
                }, 350);
            });
        }

        document.querySelectorAll(".crud-filter").forEach((select) => {
            select.addEventListener("change", () => {
                this.state.filters[select.getAttribute("data-key")] = select.value;
                this.state.page = 1;
                this.loadData();
            });
        });

        const addBtn = document.getElementById("crudAddBtn");
        if (addBtn) addBtn.addEventListener("click", () => this.openForm(null));

        const saveBtn = document.getElementById("crudSaveBtn");
        if (saveBtn) saveBtn.addEventListener("click", () => this.submitForm());
    }

    /* ------------------------------------------------------------ */
    /* Data loading                                                   */
    /* ------------------------------------------------------------ */

    buildQueryString() {
        const params = new URLSearchParams();
        params.set("page", this.state.page);
        params.set("per_page", this.state.per_page);
        if (this.state.search) params.set("search", this.state.search);
        Object.entries(this.state.filters).forEach(([key, value]) => {
            if (value && value !== "all") params.set(key, value);
        });
        return params.toString();
    }

    async loadData() {
        const alertEl = document.getElementById("crudAlert");
        hideAlert(alertEl);

        try {
            const response = await apiRequest(`${this.config.apiBase}?${this.buildQueryString()}`, { method: "GET" });
            if (!response) return;
            const data = await response.json();

            if (!response.ok || !data.success) {
                showAlert(alertEl, data.message || "Failed to load data.");
                return;
            }

            this.state.items = this.config.transformListResponse ? this.config.transformListResponse(data) : data.items;
            this.state.pagination = data.pagination;
            this.renderRows();
            this.renderPagination();
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server.");
        }
    }

    renderRows() {
        const tbody = document.getElementById("crudTableBody");
        if (!tbody) return;

        if (!this.state.items.length) {
            tbody.innerHTML = `<tr><td colspan="${this.config.columns.length + 1}" class="text-center py-4 text-muted">No records found.</td></tr>`;
            return;
        }

        tbody.innerHTML = this.state.items.map((item) => {
            const cells = this.config.columns.map((col) => {
                let value = this.resolvePath(item, col.key);
                if (col.render) value = col.render(value, item);
                else if (col.badge) value = `<span class="table-badge table-badge-${(value || "").toString().toLowerCase()}">${value ?? "—"}</span>`;
                else value = value ?? "—";
                return `<td>${value}</td>`;
            }).join("");

            const extra = this.config.rowActionsExtra ? this.config.rowActionsExtra(item) : "";
            const editBtn = this.config.permissions.edit
                ? `<button class="icon-btn icon-btn-sm crud-edit-btn" data-id="${item[this.config.idField]}" title="Edit"><i class="bi bi-pencil"></i></button>`
                : "";
            const deleteBtn = this.config.permissions.delete
                ? `<button class="icon-btn icon-btn-sm crud-delete-btn" data-id="${item[this.config.idField]}" title="Delete"><i class="bi bi-trash text-danger"></i></button>`
                : "";

            return `<tr>${cells}<td class="text-end"><div class="d-flex gap-1 justify-content-end">${extra}${editBtn}${deleteBtn}</div></td></tr>`;
        }).join("");

        tbody.querySelectorAll(".crud-edit-btn").forEach((btn) => {
            btn.addEventListener("click", () => this.openForm(btn.getAttribute("data-id")));
        });
        tbody.querySelectorAll(".crud-delete-btn").forEach((btn) => {
            btn.addEventListener("click", () => this.deleteItem(btn.getAttribute("data-id")));
        });

        if (this.config.bindExtraRowEvents) this.config.bindExtraRowEvents(tbody, this.state.items);
    }

    resolvePath(obj, path) {
        return path.split(".").reduce((acc, key) => (acc && acc[key] !== undefined ? acc[key] : undefined), obj);
    }

    renderPagination() {
        const info = document.getElementById("crudPaginationInfo");
        const controls = document.getElementById("crudPaginationControls");
        if (!this.state.pagination || !controls) return;

        const { page, total_pages, total_items, has_prev, has_next } = this.state.pagination;
        if (info) info.textContent = `${total_items} total record(s) — page ${page} of ${Math.max(total_pages, 1)}`;

        let html = "";
        html += `<li class="page-item ${!has_prev ? "disabled" : ""}"><a class="page-link" href="#" data-page="${page - 1}">Prev</a></li>`;
        for (let p = 1; p <= Math.max(total_pages, 1); p++) {
            if (p === 1 || p === total_pages || Math.abs(p - page) <= 1) {
                html += `<li class="page-item ${p === page ? "active" : ""}"><a class="page-link" href="#" data-page="${p}">${p}</a></li>`;
            } else if (Math.abs(p - page) === 2) {
                html += `<li class="page-item disabled"><span class="page-link">…</span></li>`;
            }
        }
        html += `<li class="page-item ${!has_next ? "disabled" : ""}"><a class="page-link" href="#" data-page="${page + 1}">Next</a></li>`;

        controls.innerHTML = html;
        controls.querySelectorAll(".page-link[data-page]").forEach((link) => {
            link.addEventListener("click", (e) => {
                e.preventDefault();
                const targetPage = parseInt(link.getAttribute("data-page"), 10);
                if (targetPage >= 1 && targetPage <= Math.max(this.state.pagination.total_pages, 1)) {
                    this.state.page = targetPage;
                    this.loadData();
                }
            });
        });
    }

    /* ------------------------------------------------------------ */
    /* Create / Edit                                                  */
    /* ------------------------------------------------------------ */

    openForm(id) {
        this.editingId = id;
        const form = document.getElementById("crudForm");
        form.reset();
        hideAlert(document.getElementById("crudFormAlert"));

        document.getElementById("crudModalTitle").textContent = id ? `Edit ${this.config.title}` : `Add ${this.config.title}`;

        if (id) {
            const item = this.state.items.find((i) => String(i[this.config.idField]) === String(id));
            if (item) {
                this.config.formFields.forEach((field) => {
                    const input = form.querySelector(`[name="${field.key}"]`);
                    if (input) input.value = this.resolvePath(item, field.key) ?? "";
                });
            }
        }

        this.modalEl.show();
    }

    async submitForm() {
        const form = document.getElementById("crudForm");
        const formAlert = document.getElementById("crudFormAlert");
        const saveBtn = document.getElementById("crudSaveBtn");
        hideAlert(formAlert);

        const payload = {};
        this.config.formFields.forEach((field) => {
            const input = form.querySelector(`[name="${field.key}"]`);
            if (!input) return;
            payload[field.key] = field.type === "number" ? (input.value === "" ? null : Number(input.value)) : input.value;
        });

        if (this.config.beforeSubmit) {
            const result = this.config.beforeSubmit(payload, this.editingId);
            if (result === false) return;
        }

        setButtonLoading(saveBtn, true);

        try {
            const url = this.editingId ? `${this.config.apiBase}/${this.editingId}` : this.config.apiBase;
            const method = this.editingId ? "PUT" : "POST";

            const response = await apiRequest(url, { method, body: JSON.stringify(payload) });
            const data = await response.json();

            if (!response.ok || !data.success) {
                showAlert(formAlert, (data.errors && data.errors.join(" ")) || data.message || "Something went wrong.");
                return;
            }

            this.modalEl.hide();
            await this.loadData();
            if (this.config.onSaved) this.config.onSaved(data);
        } catch (err) {
            showAlert(formAlert, "Unable to reach the server.");
        } finally {
            setButtonLoading(saveBtn, false);
        }
    }

    async deleteItem(id) {
        if (!confirm(`Are you sure you want to delete this ${this.config.title.toLowerCase()} record?`)) return;

        try {
            const response = await apiRequest(`${this.config.apiBase}/${id}`, { method: "DELETE" });
            const data = await response.json();

            if (!response.ok || !data.success) {
                showAlert(document.getElementById("crudAlert"), data.message || "Delete failed.");
                return;
            }
            await this.loadData();
        } catch (err) {
            showAlert(document.getElementById("crudAlert"), "Unable to reach the server.");
        }
    }
}
