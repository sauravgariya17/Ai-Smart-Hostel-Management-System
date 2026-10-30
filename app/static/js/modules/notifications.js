/**
 * notifications.js
 * ------------------
 * Notification System page: paginated list of personal + role-broadcast
 * notifications, mark-as-read actions, and (admin-only) broadcast form.
 */

async function loadNotificationsList() {
    const listEl = document.getElementById("notificationsList");
    const response = await apiRequest("/api/notifications?per_page=20", { method: "GET" });
    const data = await response.json();

    if (!data.success || !data.items.length) {
        listEl.innerHTML = `<div class="text-center text-muted py-5">No notifications yet.</div>`;
        return;
    }

    const iconByType = { info: "bi-info-circle", success: "bi-check-circle", warning: "bi-exclamation-triangle", danger: "bi-x-circle" };
    const bgByType = { info: "bg-soft-info", success: "bg-soft-success", warning: "bg-soft-warning", danger: "bg-soft-accent" };

    listEl.innerHTML = data.items.map((n) => `
        <div class="notif-item ${n.is_read ? "" : "unread"}" data-id="${n.id}">
            <div class="notif-dot-icon ${bgByType[n.notif_type] || "bg-soft-info"}">
                <i class="bi ${iconByType[n.notif_type] || "bi-bell"}"></i>
            </div>
            <div class="flex-grow-1">
                <strong>${n.title}</strong>
                <p class="mb-1 text-muted small">${n.message}</p>
                <span class="notif-time">${n.created_at ? new Date(n.created_at).toLocaleString() : ""}</span>
            </div>
            ${n.is_read ? "" : `<button class="icon-btn icon-btn-sm mark-read-btn" data-id="${n.id}" title="Mark as read"><i class="bi bi-check-lg"></i></button>`}
        </div>
    `).join("");

    listEl.querySelectorAll(".mark-read-btn").forEach((btn) => {
        btn.addEventListener("click", async () => {
            await apiRequest(`/api/notifications/${btn.getAttribute("data-id")}/read`, { method: "PUT", body: JSON.stringify({}) });
            loadNotificationsList();
        });
    });
}

function initBroadcastForm() {
    const user = TokenStore.getUser();
    if (!user || user.role !== "admin") return;

    document.getElementById("broadcastCard").classList.remove("d-none");

    const form = document.getElementById("broadcastForm");
    const alertEl = document.getElementById("broadcastAlert");
    const submitBtn = document.getElementById("broadcastBtn");

    form.addEventListener("submit", async (e) => {
        e.preventDefault();
        hideAlert(alertEl);

        const payload = {
            target_role: form.target_role.value,
            notif_type: form.notif_type.value,
            title: form.title.value,
            message: form.message.value,
        };

        setButtonLoading(submitBtn, true);
        try {
            const response = await apiRequest("/api/notifications/broadcast", { method: "POST", body: JSON.stringify(payload) });
            const data = await response.json();
            if (!response.ok || !data.success) {
                showAlert(alertEl, (data.errors && data.errors.join(" ")) || data.message || "Broadcast failed.");
                return;
            }
            showAlert(alertEl, "Broadcast sent successfully.", "success");
            form.reset();
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server.");
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    loadNotificationsList();
    initBroadcastForm();

    const markAllBtn = document.getElementById("markAllReadBtn");
    if (markAllBtn) {
        markAllBtn.addEventListener("click", async () => {
            await apiRequest("/api/notifications/read-all", { method: "PUT", body: JSON.stringify({}) });
            loadNotificationsList();
        });
    }
});
