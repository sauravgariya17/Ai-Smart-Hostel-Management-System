/**
 * main.js
 * ---------
 * Shared, page-agnostic front-end logic:
 *   - JWT/token storage helpers (localStorage)
 *   - Authenticated fetch wrapper with automatic access-token refresh
 *   - Sidebar toggle (mobile) + role-based nav visibility
 *   - Navbar user info population + logout
 *   - Auth guard for protected pages (e.g. /dashboard)
 *   - Small UI helpers (password visibility toggle, alert rendering)
 *
 * Loaded on every page via base.html.
 */

// Used directly by auth.js for login/forgot-password/reset-password calls
// (those happen before a token exists, so they bypass apiRequest()).
const AUTH_API_BASE = "/api/auth";
const STORAGE_KEYS = {
    ACCESS: "hostel_access_token",
    REFRESH: "hostel_refresh_token",
    USER: "hostel_user",
};

/* ------------------------------------------------------------------ */
/* Token / User storage                                                */
/* ------------------------------------------------------------------ */

const TokenStore = {
    getAccessToken: () => localStorage.getItem(STORAGE_KEYS.ACCESS),
    getRefreshToken: () => localStorage.getItem(STORAGE_KEYS.REFRESH),
    getUser: () => {
        const raw = localStorage.getItem(STORAGE_KEYS.USER);
        return raw ? JSON.parse(raw) : null;
    },
    save: (accessToken, refreshToken, user) => {
        if (accessToken) localStorage.setItem(STORAGE_KEYS.ACCESS, accessToken);
        if (refreshToken) localStorage.setItem(STORAGE_KEYS.REFRESH, refreshToken);
        if (user) localStorage.setItem(STORAGE_KEYS.USER, JSON.stringify(user));
    },
    updateAccessToken: (accessToken) => {
        localStorage.setItem(STORAGE_KEYS.ACCESS, accessToken);
    },
    clear: () => {
        localStorage.removeItem(STORAGE_KEYS.ACCESS);
        localStorage.removeItem(STORAGE_KEYS.REFRESH);
        localStorage.removeItem(STORAGE_KEYS.USER);
    },
};

/* ------------------------------------------------------------------ */
/* Authenticated fetch wrapper with silent token refresh               */
/* ------------------------------------------------------------------ */

/**
 * `path` must be a full API path, e.g. "/api/students" or "/api/auth/me" —
 * every module (students/hostels/rooms/fees/...) calls this the same way.
 */
// A fake Response-like object used in place of `null` for unrecoverable
// request failures, so every call site can safely do
// `const data = await response.json();` without special-casing null.
function _fakeErrorResponse(status, message) {
    return {
        ok: false,
        status,
        json: async () => ({ success: false, message }),
    };
}

async function apiRequest(path, options = {}, retry = true) {
    const headers = Object.assign(
        { "Content-Type": "application/json" },
        options.headers || {}
    );

    const accessToken = TokenStore.getAccessToken();
    if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

    let response;
    try {
        response = await fetch(path, { ...options, headers });
    } catch (err) {
        // A genuine network failure (server down, no connection, blocked by
        // CORS, wrong URL, etc.) — fetch() throws instead of resolving.
        return _fakeErrorResponse(
            0,
            "Unable to reach the server. Please check your connection and try again."
        );
    }

    if (response.status === 401 && retry) {
        const refreshed = await tryRefreshToken();
        if (refreshed) {
            return apiRequest(path, options, false);
        }
        TokenStore.clear();
        window.location.href = "/login";
        return _fakeErrorResponse(401, "Your session has expired. Please log in again.");
    }

    return response;
}

async function tryRefreshToken() {
    const refreshToken = TokenStore.getRefreshToken();
    if (!refreshToken) return false;

    try {
        const res = await fetch(`${AUTH_API_BASE}/refresh`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${refreshToken}`,
            },
        });
        if (!res.ok) return false;
        const data = await res.json();
        TokenStore.updateAccessToken(data.access_token);
        return true;
    } catch (err) {
        return false;
    }
}

/* ------------------------------------------------------------------ */
/* UI helpers                                                          */
/* ------------------------------------------------------------------ */

function showAlert(el, message, type = "error") {
    if (!el) return;
    el.classList.remove("d-none", "alert-app-error", "alert-app-success");
    el.classList.add(type === "error" ? "alert-app-error" : "alert-app-success");
    el.textContent = message;
}

function hideAlert(el) {
    if (!el) return;
    el.classList.add("d-none");
}

function setButtonLoading(btn, isLoading) {
    if (!btn) return;
    const text = btn.querySelector(".btn-text");
    const spinner = btn.querySelector(".spinner-border");
    btn.disabled = isLoading;
    if (text) text.classList.toggle("d-none", isLoading);
    if (spinner) spinner.classList.toggle("d-none", !isLoading);
}

function initPasswordToggles() {
    document.querySelectorAll(".toggle-password").forEach((btn) => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-target");
            const input = document.getElementById(targetId);
            if (!input) return;
            const icon = btn.querySelector("i");
            const isPassword = input.type === "password";
            input.type = isPassword ? "text" : "password";
            if (icon) {
                icon.classList.toggle("bi-eye", !isPassword);
                icon.classList.toggle("bi-eye-slash", isPassword);
            }
        });
    });
}

/* ------------------------------------------------------------------ */
/* Sidebar (mobile) toggle                                             */
/* ------------------------------------------------------------------ */

function initSidebarToggle() {
    const toggleBtn = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("appSidebar");
    if (!toggleBtn || !sidebar) return;

    toggleBtn.addEventListener("click", () => sidebar.classList.toggle("open"));

    document.addEventListener("click", (event) => {
        if (
            sidebar.classList.contains("open") &&
            !sidebar.contains(event.target) &&
            !toggleBtn.contains(event.target)
        ) {
            sidebar.classList.remove("open");
        }
    });
}

/* ------------------------------------------------------------------ */
/* Navbar: populate user info + role-based nav + logout                */
/* ------------------------------------------------------------------ */

function populateNavbarUser() {
    const user = TokenStore.getUser();
    if (!user) return;

    const initialEl = document.getElementById("navAvatarInitial");
    const nameEl = document.getElementById("navUserName");
    const roleEl = document.getElementById("navUserRole");

    if (initialEl) initialEl.textContent = (user.name || "U").trim().charAt(0).toUpperCase();
    if (nameEl) nameEl.textContent = user.name || "User";
    if (roleEl) roleEl.textContent = user.role || "role";

    // Reveal only the sidebar nav group matching this user's role.
    document.querySelectorAll("[data-role-nav]").forEach((group) => {
        group.classList.toggle("d-none", group.getAttribute("data-role-nav") !== user.role);
    });
}

function initLogout() {
    const logoutBtn = document.getElementById("logoutBtn");
    if (!logoutBtn) return;

    logoutBtn.addEventListener("click", async (event) => {
        event.preventDefault();
        try {
            await apiRequest("/api/auth/logout", { method: "POST" }, false);
        } catch (err) {
            /* ignore network errors on logout */
        } finally {
            TokenStore.clear();
            window.location.href = "/login";
        }
    });
}

/* ------------------------------------------------------------------ */
/* Auth guard for protected pages                                      */
/* ------------------------------------------------------------------ */

function guardProtectedPage() {
    const protectedPaths = [
        "/dashboard", "/admin/dashboard", "/warden/dashboard", "/student/dashboard",
        "/students", "/wardens", "/hostels", "/rooms", "/fees", "/visitors", "/attendance",
        "/complaints", "/maintenance", "/notifications", "/reports",
    ];
    if (!protectedPaths.includes(window.location.pathname)) return;

    if (!TokenStore.getAccessToken()) {
        window.location.href = "/login";
    }
}

/* ------------------------------------------------------------------ */
/* Notification badge                                                   */
/* ------------------------------------------------------------------ */

async function initNotificationBadge() {
    const dot = document.getElementById("navNotifDot");
    if (!dot || !TokenStore.getAccessToken()) return;

    try {
        const response = await apiRequest("/api/notifications/unread-count", { method: "GET" }, false);
        if (!response || !response.ok) return;
        const data = await response.json();
        dot.classList.toggle("d-none", !(data.unread_count > 0));
    } catch (err) {
        /* silently ignore — badge is a non-critical UI affordance */
    }
}

/* ------------------------------------------------------------------ */
/* Active nav-link highlighting                                        */
/* ------------------------------------------------------------------ */

function highlightActiveNavLink() {
    const currentPath = window.location.pathname;
    document.querySelectorAll(".sidebar-nav .nav-link").forEach((link) => {
        const linkPath = new URL(link.href, window.location.origin).pathname;
        link.classList.toggle("active", linkPath === currentPath);
    });
}

/* ------------------------------------------------------------------ */
/* Init                                                                 */
/* ------------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", () => {
    guardProtectedPage();
    initPasswordToggles();
    initSidebarToggle();
    populateNavbarUser();
    initLogout();
    initNotificationBadge();
    highlightActiveNavLink();
});
