/**
 * chatbot.js
 * ------------
 * Floating "AI Hostel Assistant" widget available on every authenticated
 * page (injected once via templates/layouts/module_page.html so it's
 * automatically present across all dashboards/modules without touching
 * every individual template).
 *
 * Talks to POST /api/ai/chatbot/ask.
 */

function buildChatbotWidget() {
    if (document.getElementById("chatbotToggleBtn")) return; // already injected

    const toggleBtn = document.createElement("button");
    toggleBtn.id = "chatbotToggleBtn";
    toggleBtn.className = "chatbot-toggle-btn";
    toggleBtn.setAttribute("aria-label", "Open Hostel Assistant");
    toggleBtn.innerHTML = `<i class="bi bi-chat-dots-fill"></i>`;

    const panel = document.createElement("div");
    panel.id = "chatbotPanel";
    panel.className = "chatbot-panel";
    panel.innerHTML = `
        <div class="chatbot-header">
            <div>
                <strong><i class="bi bi-stars me-1"></i> Hostel Assistant</strong>
                <small>Ask about your room, fees, complaints &amp; more</small>
            </div>
            <button class="chatbot-close-btn" id="chatbotCloseBtn" aria-label="Close">
                <i class="bi bi-x-lg"></i>
            </button>
        </div>
        <div class="chatbot-messages" id="chatbotMessages"></div>
        <div class="chatbot-input-row">
            <input type="text" id="chatbotInput" placeholder="Type a question..." autocomplete="off">
            <button class="chatbot-send-btn" id="chatbotSendBtn" aria-label="Send">
                <i class="bi bi-send-fill"></i>
            </button>
        </div>
    `;

    document.body.appendChild(toggleBtn);
    document.body.appendChild(panel);

    function appendMessage(text, sender) {
        const messagesEl = document.getElementById("chatbotMessages");
        const bubble = document.createElement("div");
        bubble.className = `chatbot-bubble chatbot-bubble-${sender === "user" ? "user" : "bot"}`;
        bubble.textContent = text;
        messagesEl.appendChild(bubble);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function openPanel() {
        panel.classList.add("open");
        if (!panel.dataset.greeted) {
            appendMessage("Hi! I'm your Hostel Assistant. Ask me about your room, fees, complaints, or hostel policies.", "bot");
            panel.dataset.greeted = "1";
        }
        document.getElementById("chatbotInput").focus();
    }

    function closePanel() {
        panel.classList.remove("open");
    }

    toggleBtn.addEventListener("click", () => {
        panel.classList.contains("open") ? closePanel() : openPanel();
    });
    document.getElementById("chatbotCloseBtn").addEventListener("click", closePanel);

    async function sendQuestion() {
        const input = document.getElementById("chatbotInput");
        const question = input.value.trim();
        if (!question) return;

        appendMessage(question, "user");
        input.value = "";

        const messagesEl = document.getElementById("chatbotMessages");
        const typingBubble = document.createElement("div");
        typingBubble.className = "chatbot-bubble chatbot-bubble-bot";
        typingBubble.id = "chatbotTypingIndicator";
        typingBubble.innerHTML = `<span class="spinner-border spinner-border-sm"></span>`;
        messagesEl.appendChild(typingBubble);
        messagesEl.scrollTop = messagesEl.scrollHeight;

        try {
            const response = await apiRequest("/api/ai/chatbot/ask", {
                method: "POST",
                body: JSON.stringify({ question }),
            });
            const data = await response.json();
            document.getElementById("chatbotTypingIndicator")?.remove();

            if (!response.ok || !data.success) {
                appendMessage(data.message || "Sorry, something went wrong.", "bot");
                return;
            }
            appendMessage(data.answer, "bot");
        } catch (err) {
            document.getElementById("chatbotTypingIndicator")?.remove();
            appendMessage("I couldn't reach the server just now. Please try again.", "bot");
        }
    }

    document.getElementById("chatbotSendBtn").addEventListener("click", sendQuestion);
    document.getElementById("chatbotInput").addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            sendQuestion();
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    if (TokenStore.getAccessToken()) {
        buildChatbotWidget();
    }
});
