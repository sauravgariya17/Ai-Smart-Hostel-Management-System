/**
 * auth.js
 * ---------
 * Page-specific logic for:
 *   - Login page (role tabs + login form submit)
 *   - Forgot password page
 *   - Reset password page
 *   - Dashboard page profile/stat population
 *
 * Relies on TokenStore / apiRequest / showAlert / setButtonLoading
 * defined in main.js (loaded before this file).
 */

/* ------------------------------------------------------------------ */
/* LOGIN PAGE                                                          */
/* ------------------------------------------------------------------ */

function initLoginPage() {
    const form = document.getElementById("loginForm");
    if (!form) return;

    const roleTabs = document.querySelectorAll(".role-tab");
    const roleInput = document.getElementById("loginRole");
    const alertEl = document.getElementById("loginAlert");
    const submitBtn = document.getElementById("loginSubmitBtn");

    roleTabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            roleTabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            roleInput.value = tab.getAttribute("data-role");
        });
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideAlert(alertEl);

        const role = roleInput.value;
        const email = document.getElementById("loginEmail").value.trim();
        const password = document.getElementById("loginPassword").value;

        if (!email || !password) {
            showAlert(alertEl, "Please enter both email and password.");
            return;
        }

        setButtonLoading(submitBtn, true);

        try {
            const response = await fetch(`${AUTH_API_BASE}/${role}/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                showAlert(alertEl, data.message || "Login failed. Please check your credentials.");
                return;
            }

            TokenStore.save(data.access_token, data.refresh_token, data.user);
            const roleRoutes = { admin: "/admin/dashboard", warden: "/warden/dashboard", student: "/student/dashboard" };
            window.location.href = roleRoutes[data.user.role] || "/dashboard";
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server. Please try again.");
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

/* ------------------------------------------------------------------ */
/* STUDENT REGISTRATION PAGE                                            */
/* ------------------------------------------------------------------ */

function initStudentRegisterPage() {
    const form = document.getElementById("studentRegisterForm");
    if (!form) return;

    const alertEl = document.getElementById("registerAlert");
    const submitBtn = document.getElementById("registerSubmitBtn");

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideAlert(alertEl);

        const name = document.getElementById("registerName").value.trim();
        const roll_number = document.getElementById("registerRoll").value.trim();
        const email = document.getElementById("registerEmail").value.trim();
        const password = document.getElementById("registerPassword").value;
        const confirmPassword = document.getElementById("registerConfirmPassword").value;
        const course = document.getElementById("registerCourse").value.trim();
        const yearValue = document.getElementById("registerYear").value;
        const phone_number = document.getElementById("registerPhone").value.trim();
        const guardian_name = document.getElementById("registerGuardian").value.trim();

        if (!name || !roll_number || !email || !password) {
            showAlert(alertEl, "Please fill in name, roll number, email, and password.");
            return;
        }
        if (password !== confirmPassword) {
            showAlert(alertEl, "Passwords do not match.");
            return;
        }
        if (password.length < 8) {
            showAlert(alertEl, "Password must be at least 8 characters long.");
            return;
        }

        const payload = {
            name, email, password, roll_number,
            course: course || null,
            year_of_study: yearValue ? Number(yearValue) : null,
            phone_number: phone_number || null,
            guardian_name: guardian_name || null,
        };

        setButtonLoading(submitBtn, true);

        try {
            const response = await fetch(`${AUTH_API_BASE}/student/register`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                const message = data.message || (Array.isArray(data.errors) ? data.errors.join(" ") : "Registration failed.");
                showAlert(alertEl, message);
                return;
            }

            showAlert(alertEl, "Student account created successfully. Redirecting to login…", "success");
            form.reset();
            setTimeout(() => {
                window.location.href = "/login";
            }, 1200);
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server. Please try again.");
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

/* ------------------------------------------------------------------ */
/* FORGOT PASSWORD PAGE                                                 */
/* ------------------------------------------------------------------ */

function initForgotPasswordPage() {
    const form = document.getElementById("forgotPasswordForm");
    if (!form) return;

    const alertEl = document.getElementById("forgotAlert");
    const submitBtn = document.getElementById("forgotSubmitBtn");

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideAlert(alertEl);

        const email = document.getElementById("forgotEmail").value.trim();
        if (!email) {
            showAlert(alertEl, "Please enter your registered email address.");
            return;
        }

        setButtonLoading(submitBtn, true);

        try {
            const response = await fetch(`${AUTH_API_BASE}/forgot-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email }),
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                showAlert(alertEl, data.message || "Something went wrong. Please try again.");
                return;
            }

            showAlert(alertEl, data.message, "success");
            form.reset();
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server. Please try again.");
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

/* ------------------------------------------------------------------ */
/* RESET PASSWORD PAGE                                                  */
/* ------------------------------------------------------------------ */

function initResetPasswordPage() {
    const form = document.getElementById("resetPasswordForm");
    if (!form) return;

    const alertEl = document.getElementById("resetAlert");
    const submitBtn = document.getElementById("resetSubmitBtn");

    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");

    if (!token) {
        showAlert(alertEl, "Reset link is invalid or missing a token. Please request a new one.");
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        hideAlert(alertEl);

        const newPassword = document.getElementById("newPassword").value;
        const confirmPassword = document.getElementById("confirmPassword").value;

        if (!token) {
            showAlert(alertEl, "Reset link is invalid or missing a token. Please request a new one.");
            return;
        }
        if (newPassword !== confirmPassword) {
            showAlert(alertEl, "Passwords do not match.");
            return;
        }

        setButtonLoading(submitBtn, true);

        try {
            const response = await fetch(`${AUTH_API_BASE}/reset-password`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token, new_password: newPassword }),
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                showAlert(alertEl, data.message || "Unable to reset password. Please try again.");
                return;
            }

            showAlert(alertEl, `${data.message} Redirecting to login…`, "success");
            setTimeout(() => (window.location.href = "/login"), 1800);
        } catch (err) {
            showAlert(alertEl, "Unable to reach the server. Please try again.");
        } finally {
            setButtonLoading(submitBtn, false);
        }
    });
}

/* ------------------------------------------------------------------ */
/* DASHBOARD PAGE                                                       */
/* ------------------------------------------------------------------ */

async function initDashboardPage() {
    const welcomeName = document.getElementById("welcomeName");
    if (!welcomeName) return; // not on dashboard page

    const response = await apiRequest("/api/auth/me", { method: "GET" });
    if (!response) return;

    const data = await response.json();
    if (!data.success) return;

    const user = data.user;
    TokenStore.save(null, null, user); // refresh cached user snapshot

    welcomeName.textContent = user.name;
    const roleBadge = document.getElementById("welcomeRoleBadge");
    if (roleBadge) roleBadge.textContent = user.role;

    const setText = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value ?? "—";
    };
    setText("profileName", user.name);
    setText("profileEmail", user.email);
    setText("profileRole", user.role);
    setText("profileStatus", user.is_active ? "Active" : "Inactive");

    populateNavbarUser();
}

/* ------------------------------------------------------------------ */
/* Init                                                                  */
/* ------------------------------------------------------------------ */

document.addEventListener("DOMContentLoaded", () => {
    initLoginPage();
    initStudentRegisterPage();
    initForgotPasswordPage();
    initResetPasswordPage();
    initDashboardPage();
});
