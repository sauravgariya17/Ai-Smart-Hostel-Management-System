/**
 * students.js
 * -------------
 * Student Management page: list/search/filter/paginate students, create
 * new student accounts, edit profile fields, deactivate.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Creating/deleting student accounts is Admin-only on the backend
    // (app/students/routes.py); editing profile fields is allowed for
    // Admins and Wardens alike.
    const isAdmin = TokenStore.getUser()?.role === "admin";

    const table = new CrudTable({
        containerId: "studentsApp",
        apiBase: "/api/students",
        title: "Student",
        subtitle: "Manage student accounts, profiles, and status",
        searchPlaceholder: "Search by roll number...",
        idField: "id",
        columns: [
            { key: "name", label: "Name" },
            { key: "email", label: "Email" },
            { key: "profile.roll_number", label: "Roll No." },
            { key: "profile.course", label: "Course" },
            { key: "profile.year_of_study", label: "Year" },
            {
                key: "is_active",
                label: "Status",
                badge: true,
                render: (value) => `<span class="table-badge ${value ? "table-badge-active" : "table-badge-rejected"}">${value ? "Active" : "Inactive"}</span>`,
            },
        ],
        formFields: [
            { key: "name", label: "Full Name", type: "text", required: true },
            { key: "email", label: "Email Address", type: "email" },
            { key: "password", label: "Password (new students only)", type: "password" },
            { key: "roll_number", label: "Roll Number", type: "text" },
            { key: "course", label: "Course", type: "text" },
            { key: "year_of_study", label: "Year of Study", type: "number" },
            { key: "phone_number", label: "Phone Number", type: "text" },
            { key: "guardian_name", label: "Guardian Name", type: "text" },
            { key: "guardian_phone", label: "Guardian Phone", type: "text" },
            { key: "address", label: "Address", type: "textarea" },
        ],
        permissions: { create: isAdmin, edit: true, delete: isAdmin },
        transformListResponse: (data) => data.items, // each item is already the full user.to_dict(include_profile=True)
    });

    // The list endpoint returns items keyed like user.to_dict() (name/email/profile.*),
    // but:
    //   1. The update/delete/create endpoints live at /api/students/<id> where <id>
    //      refers to the Student.id (not the User.id) -> map "id" to profile.id.
    //   2. Edit-form prefill reads flat keys ("roll_number", "course", ...) to match
    //      the flat payload the backend PUT endpoint expects -> flatten profile.*
    //      onto the top level too (the nested "profile" object is kept as-is so the
    //      "profile.roll_number" style column paths above still resolve for display).
    table.config.idField = "profile_id";
    table.state.items = [];
    const originalTransform = table.config.transformListResponse;
    table.config.transformListResponse = (data) => originalTransform(data).map((item) => ({
        ...item,
        profile_id: item.profile ? item.profile.id : item.id,
        roll_number: item.profile ? item.profile.roll_number : undefined,
        course: item.profile ? item.profile.course : undefined,
        year_of_study: item.profile ? item.profile.year_of_study : undefined,
        phone_number: item.profile ? item.profile.phone_number : undefined,
        guardian_name: item.profile ? item.profile.guardian_name : undefined,
        guardian_phone: item.profile ? item.profile.guardian_phone : undefined,
        address: item.profile ? item.profile.address : undefined,
    }));

    table.init();
});
