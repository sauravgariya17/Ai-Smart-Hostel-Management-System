/**
 * maintenance.js
 * ----------------
 * Maintenance Management page: create/track repair work orders raised
 * against rooms or common facilities.
 */

document.addEventListener("DOMContentLoaded", () => {
    const table = new CrudTable({
        containerId: "maintenanceApp",
        apiBase: "/api/maintenance",
        title: "Maintenance Request",
        subtitle: "Track repair and upkeep work orders",
        searchPlaceholder: "Search by category...",
        filters: [
            { key: "status", label: "Status", options: [
                { value: "pending", label: "Pending" }, { value: "in_progress", label: "In Progress" },
                { value: "completed", label: "Completed" }, { value: "cancelled", label: "Cancelled" },
            ]},
            { key: "priority", label: "Priority", options: [
                { value: "low", label: "Low" }, { value: "medium", label: "Medium" }, { value: "high", label: "High" },
            ]},
        ],
        columns: [
            { key: "room_number", label: "Room" },
            { key: "category", label: "Category" },
            { key: "priority", label: "Priority", badge: true },
            { key: "status", label: "Status", badge: true },
            { key: "assigned_to_name", label: "Assigned To" },
            { key: "cost", label: "Cost", render: (v) => v ? `₹${Number(v).toFixed(2)}` : "—" },
            { key: "created_at", label: "Raised On", render: (v) => v ? new Date(v).toLocaleDateString() : "—" },
        ],
        formFields: [
            { key: "room_id", label: "Room ID (optional)", type: "number" },
            { key: "category", label: "Category", type: "text", required: true },
            { key: "priority", label: "Priority", type: "select", options: [
                { value: "low", label: "Low" }, { value: "medium", label: "Medium" }, { value: "high", label: "High" },
            ]},
            { key: "description", label: "Description", type: "textarea" },
            { key: "assigned_to", label: "Assign to (User ID)", type: "number" },
            { key: "cost", label: "Estimated/Actual Cost", type: "number", step: "0.01" },
            { key: "status", label: "Status", type: "select", options: [
                { value: "pending", label: "Pending" }, { value: "in_progress", label: "In Progress" },
                { value: "completed", label: "Completed" }, { value: "cancelled", label: "Cancelled" },
            ]},
        ],
        permissions: { create: true, edit: true, delete: true },
    });

    table.init();
});
