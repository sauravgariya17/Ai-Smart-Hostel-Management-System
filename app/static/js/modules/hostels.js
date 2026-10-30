/**
 * hostels.js
 * ------------
 * Hostel Management page: CRUD for hostels (buildings). Block
 * management is accessible from the room management page's hostel
 * selector, so this page focuses on top-level hostel records.
 */

document.addEventListener("DOMContentLoaded", async () => {
    // Hostel records are Admin-only to create/edit/delete on the backend
    // (app/hostels/routes.py). Wardens can still view this page (e.g. if
    // linked directly) but shouldn't see action buttons that will 403.
    const isAdmin = TokenStore.getUser()?.role === "admin";

    let wardenOptions = [];
    try {
        const response = await apiRequest("/api/wardens?per_page=100", { method: "GET" });
        if (response && response.ok) {
            const data = await response.json();
            if (data.success) {
                wardenOptions = data.items.map((w) => ({
                    value: String(w.id),
                    label: `${w.name} (${w.employee_id})`,
                }));
            }
        }
    } catch (err) {
        // The hostel page still works if no warden exists yet.
    }

    const table = new CrudTable({
        containerId: "hostelsApp",
        apiBase: "/api/hostels",
        title: "Hostel",
        subtitle: "Manage hostel buildings and their basic details",
        searchPlaceholder: "Search by name or address...",
        filters: [
            { key: "hostel_type", label: "Type", options: [
                { value: "boys", label: "Boys" },
                { value: "girls", label: "Girls" },
                { value: "co_ed", label: "Co-ed" },
            ]},
        ],
        columns: [
            { key: "name", label: "Hostel Name" },
            { key: "hostel_type", label: "Type", badge: true },
            { key: "address", label: "Address" },
            { key: "total_floors", label: "Floors" },
            { key: "total_rooms", label: "Rooms" },
            { key: "warden_name", label: "Warden" },
            {
                key: "is_active",
                label: "Status",
                render: (value) => `<span class="table-badge ${value ? "table-badge-active" : "table-badge-rejected"}">${value ? "Active" : "Inactive"}</span>`,
            },
        ],
        formFields: [
            { key: "name", label: "Hostel Name", type: "text", required: true },
            { key: "hostel_type", label: "Hostel Type", type: "select", required: true, options: [
                { value: "boys", label: "Boys" },
                { value: "girls", label: "Girls" },
                { value: "co_ed", label: "Co-ed" },
            ]},
            { key: "address", label: "Address", type: "textarea" },
            { key: "total_floors", label: "Total Floors", type: "number" },
        ],
        permissions: { create: isAdmin, edit: isAdmin, delete: isAdmin },
    });

    table.init();
});
