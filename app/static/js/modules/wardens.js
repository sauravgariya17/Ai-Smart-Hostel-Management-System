/**
 * Warden management page.
 */
document.addEventListener("DOMContentLoaded", () => {
    // Managing warden accounts (create/edit/deactivate) is Admin-only on
    // the backend (app/wardens/routes.py). Wardens themselves can only
    // view this list if linked directly.
    const isAdmin = TokenStore.getUser()?.role === "admin";

    const table = new CrudTable({
        containerId: "wardensApp",
        apiBase: "/api/wardens",
        title: "Warden",
        subtitle: "Manage warden accounts and hostel responsibilities",
        searchPlaceholder: "Search by name or email...",
        columns: [
            { key: "name", label: "Name" },
            { key: "email", label: "Email" },
            { key: "employee_id", label: "Employee ID" },
            { key: "designation", label: "Designation" },
            { key: "phone_number", label: "Phone" },
            { key: "is_active", label: "Status", render: (value) =>
                `<span class="table-badge ${value ? "table-badge-active" : "table-badge-rejected"}">${value ? "Active" : "Inactive"}</span>` },
        ],
        formFields: [
            { key: "name", label: "Full Name", type: "text", required: true },
            { key: "email", label: "Email Address", type: "email", required: true },
            { key: "password", label: "Password", type: "password", required: true },
            { key: "employee_id", label: "Employee ID", type: "text", required: true },
            { key: "phone_number", label: "Phone Number", type: "text" },
            { key: "designation", label: "Designation", type: "text" },
            { key: "assigned_block", label: "Assigned Block", type: "text" },
            { key: "joining_date", label: "Joining Date", type: "date" },
        ],
        permissions: { create: isAdmin, edit: isAdmin, delete: isAdmin },
        idField: "profile_id",
    });

    // Password is required when creating, but not when editing.
    const originalOpenForm = table.openForm.bind(table);
    table.openForm = (id) => {
        originalOpenForm(id);
        const passwordInput = document.querySelector('#crudForm [name="password"]');
        if (passwordInput) passwordInput.required = !id;
    };

    table.init();
});
