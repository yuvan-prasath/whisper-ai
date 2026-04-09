/**
 * widget.js — NeumannBot Embeddable Widget
 * Neumann Intelligence
 * 
 * Client pastes one <script> tag on their website.
 * This file injects a chat popup automatically.
 * 
 * Usage:
 *   <script>
 *     window.NeumannBotConfig = {
 *       apiKey: "nb_xxx",
 *       orgId: "org_xxx",
 *       botName: "Aria",
 *       color: "#6366f1",
 *       apiBase: "https://your-deployment.com"
 *     };
 *   </script>
 *   <script src="https://your-deployment.com/static/widget.js" defer></script>
 */

(function () {
  const config = window.NeumannBotConfig || {};
  const API_KEY = config.apiKey || "";
  const ORG_ID = config.orgId || "";
  const BOT_NAME = config.botName || "Assistant";
  const COLOR = config.color || "#6366f1";
  const API_BASE = config.apiBase || window.location.origin;
  const SESSION_ID = "sess_" + Math.random().toString(36).substr(2, 12);

  // ── Inject CSS ──────────────────────────────────────────────
  const style = document.createElement("style");
  style.textContent = `
    #nb-launcher {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: ${COLOR};
      cursor: pointer;
      box-shadow: 0 4px 20px rgba(0,0,0,0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 99999;
      transition: transform 0.2s;
    }
    #nb-launcher:hover { transform: scale(1.1); }
    #nb-launcher svg { width: 28px; height: 28px; fill: white; }

    #nb-window {
      position: fixed;
      bottom: 90px;
      right: 24px;
      width: 360px;
      height: 520px;
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 8px 40px rgba(0,0,0,0.2);
      display: none;
      flex-direction: column;
      overflow: hidden;
      z-index: 99998;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    #nb-window.open { display: flex; }

    #nb-header {
      background: ${COLOR};
      color: white;
      padding: 16px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    #nb-header-title { font-weight: 600; font-size: 15px; }
    #nb-header-sub { font-size: 11px; opacity: 0.8; margin-top: 2px; }
    #nb-close {
      cursor: pointer;
      font-size: 20px;
      opacity: 0.8;
      background: none;
      border: none;
      color: white;
      line-height: 1;
    }
    #nb-close:hover { opacity: 1; }

    #nb-messages {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: #f8f9ff;
    }

    .nb-msg {
      max-width: 82%;
      padding: 10px 14px;
      border-radius: 12px;
      font-size: 14px;
      line-height: 1.5;
      word-wrap: break-word;
    }
    .nb-msg.bot {
      background: white;
      color: #1a1a2e;
      align-self: flex-start;
      border-bottom-left-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .nb-msg.user {
      background: ${COLOR};
      color: white;
      align-self: flex-end;
      border-bottom-right-radius: 4px;
    }
    .nb-msg.escalate {
      background: #fff3cd;
      color: #856404;
      font-size: 12px;
      align-self: center;
      border-radius: 8px;
      text-align: center;
    }

    .nb-typing {
      display: flex;
      gap: 4px;
      align-items: center;
      padding: 10px 14px;
      background: white;
      border-radius: 12px;
      align-self: flex-start;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
    }
    .nb-typing span {
      width: 6px; height: 6px;
      background: #aaa;
      border-radius: 50%;
      animation: nb-bounce 1.2s infinite;
    }
    .nb-typing span:nth-child(2) { animation-delay: 0.2s; }
    .nb-typing span:nth-child(3) { animation-delay: 0.4s; }
    @keyframes nb-bounce {
      0%, 80%, 100% { transform: translateY(0); }
      40% { transform: translateY(-6px); }
    }

    #nb-footer {
      padding: 12px;
      border-top: 1px solid #eee;
      display: flex;
      gap: 8px;
      background: white;
    }
    #nb-input {
      flex: 1;
      border: 1.5px solid #e2e8f0;
      border-radius: 8px;
      padding: 9px 12px;
      font-size: 14px;
      outline: none;
      transition: border-color 0.2s;
    }
    #nb-input:focus { border-color: ${COLOR}; }
    #nb-send {
      background: ${COLOR};
      color: white;
      border: none;
      border-radius: 8px;
      padding: 9px 16px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 500;
      transition: opacity 0.2s;
    }
    #nb-send:hover { opacity: 0.9; }
    #nb-send:disabled { opacity: 0.5; cursor: not-allowed; }

    #nb-branding {
      text-align: center;
      font-size: 10px;
      color: #aaa;
      padding: 6px;
      background: white;
    }
    #nb-branding a { color: ${COLOR}; text-decoration: none; }
  `;
  document.head.appendChild(style);

  // ── Inject HTML ─────────────────────────────────────────────
  const launcher = document.createElement("div");
  launcher.id = "nb-launcher";
  launcher.innerHTML = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
    <path d="M12 2C6.477 2 2 6.477 2 12c0 1.89.526 3.66 1.438 5.168L2 22l4.832-1.438A9.955 9.955 0 0012 22c5.523 0 10-4.477 10-10S17.523 2 12 2zm0 18a7.952 7.952 0 01-4.065-1.115l-.291-.173-3.013.896.896-3.013-.173-.291A7.952 7.952 0 014 12c0-4.418 3.582-8 8-8s8 3.582 8 8-3.582 8-8 8z"/>
  </svg>`;

  const chatWindow = document.createElement("div");
  chatWindow.id = "nb-window";
  chatWindow.innerHTML = `
    <div id="nb-header">
      <div>
        <div id="nb-header-title">${BOT_NAME}</div>
        <div id="nb-header-sub">Powered by Neumann Intelligence</div>
      </div>
      <button id="nb-close">✕</button>
    </div>
    <div id="nb-messages">
      <div class="nb-msg bot">Hi! I'm ${BOT_NAME}. How can I help you today?</div>
    </div>
    <div id="nb-footer">
      <input id="nb-input" type="text" placeholder="Type your message..." autocomplete="off" />
      <button id="nb-send">Send</button>
    </div>
    <div id="nb-branding">Powered by <a href="https://neumannintelligence.com" target="_blank">Neumann Intelligence</a></div>
  `;

  document.body.appendChild(launcher);
  document.body.appendChild(chatWindow);

  // ── Logic ───────────────────────────────────────────────────
  const msgs = document.getElementById("nb-messages");
  const input = document.getElementById("nb-input");
  const sendBtn = document.getElementById("nb-send");

  launcher.addEventListener("click", () => {
    chatWindow.classList.toggle("open");
  });

  document.getElementById("nb-close").addEventListener("click", () => {
    chatWindow.classList.remove("open");
  });

  function addMessage(text, type) {
    const div = document.createElement("div");
    div.className = `nb-msg ${type}`;
    div.textContent = text;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  function showTyping() {
    const div = document.createElement("div");
    div.className = "nb-typing";
    div.id = "nb-typing-indicator";
    div.innerHTML = "<span></span><span></span><span></span>";
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
  }

  function removeTyping() {
    const t = document.getElementById("nb-typing-indicator");
    if (t) t.remove();
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, "user");
    input.value = "";
    sendBtn.disabled = true;
    showTyping();

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY
        },
        body: JSON.stringify({
          session_id: SESSION_ID,
          message: text
        })
      });

      const data = await res.json();
      removeTyping();

      if (res.ok) {
        addMessage(data.reply, "bot");
        if (data.escalate) {
          addMessage("⚠️ This issue may need human attention. Please contact support directly.", "escalate");
        }
      } else {
        addMessage("Sorry, something went wrong. Please try again.", "bot");
      }

    } catch (err) {
      removeTyping();
      addMessage("Connection error. Please try again.", "bot");
    }

    sendBtn.disabled = false;
    input.focus();
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });

})();
