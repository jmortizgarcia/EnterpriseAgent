(function () {
  "use strict";

  const messagesEl = document.getElementById("messages");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("sendBtn");
  const providerEl = document.getElementById("provider");
  const sessionIdEl = document.getElementById("sessionId");
  const suggestionsEl = document.getElementById("suggestions");
  const sidebarEl = document.getElementById("sidebar");
  const sessionListEl = document.getElementById("sessionList");
  const newChatBtn = document.getElementById("newChatBtn");
  const exportBtn = document.getElementById("exportBtn");
  const toggleSidebarBtn = document.getElementById("toggleSidebar");
  const toastEl = document.getElementById("toast");

  const SUGGESTIONS = [
    "¿Cuál es el SLA del plan Enterprise?",
    "¿Cuánto cuesta el plan Pro?",
    "¿Cómo obtengo una API key?",
    "¿Cómo despliego mi primera app?",
    "Crea un ticket de alta prioridad porque la CPU está al 95%",
    "¿Qué significa el error 429?",
  ];

  let busy = false;
  let currentMessages = [];
  let currentStats = { input_tokens: 0, output_tokens: 0, total_cost: 0 };

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function newSessionId() {
    return "session_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
  }

  function showToast(message) {
    toastEl.textContent = message;
    toastEl.classList.add("show");
    setTimeout(() => toastEl.classList.remove("show"), 2500);
  }

  /* ======== Session Manager ======== */
  class SessionManager {
    static KEY = "enterprise_agent_sessions";

    static getAll() {
      try {
        return JSON.parse(localStorage.getItem(this.KEY) || "[]");
      } catch {
        return [];
      }
    }

    static save(sessionId, messages, stats) {
      const sessions = this.getAll();
      const idx = sessions.findIndex(s => s.id === sessionId);
      const preview = messages.length > 0 
        ? messages[messages.length - 1]?.content?.slice(0, 50) + "…" 
        : "Nueva conversación";
      const now = Date.now();

      const session = {
        id: sessionId,
        preview,
        createdAt: now,
        updatedAt: now,
        stats: stats || { input_tokens: 0, output_tokens: 0, total_cost: 0 }
      };

      if (idx >= 0) {
        sessions[idx] = { ...sessions[idx], ...session };
      } else {
        sessions.push(session);
      }

      // Límite de 50 sesiones
      if (sessions.length > 50) {
        sessions.shift();
      }

      localStorage.setItem(this.KEY, JSON.stringify(sessions));
    }

    static delete(sessionId) {
      const sessions = this.getAll().filter(s => s.id !== sessionId);
      localStorage.setItem(this.KEY, JSON.stringify(sessions));
    }
  }

  function formatDate(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "Ahora";
    if (diffMins < 60) return `Hace ${diffMins}m`;
    if (diffHours < 24) return `Hace ${diffHours}h`;
    if (diffDays < 7) return `Hace ${diffDays}d`;
    
    return date.toLocaleDateString("es-ES");
  }

  function renderSessionList() {
    const sessions = SessionManager.getAll().sort((a, b) => b.updatedAt - a.updatedAt);
    sessionListEl.innerHTML = "";

    if (sessions.length === 0) {
      sessionListEl.innerHTML = `<p style="padding: 12px; color: var(--muted); text-align: center; font-size: 12px;">No hay sesiones guardadas</p>`;
      return;
    }

    sessions.forEach(session => {
      const item = document.createElement("div");
      item.className = "session-item";
      if (session.id === sessionIdEl.value.trim()) {
        item.classList.add("active");
      }

      const content = document.createElement("div");
      content.className = "session-content";
      content.innerHTML = `
        <div class="session-title">${session.id.slice(0, 20)}</div>
        <div class="session-preview">${session.preview}</div>
      `;

      const time = document.createElement("small");
      time.style.cssText = "color: var(--muted); font-size: 11px; flex-shrink: 0;";
      time.textContent = formatDate(session.updatedAt);

      const deleteBtn = document.createElement("button");
      deleteBtn.className = "session-delete";
      deleteBtn.textContent = "✕";
      deleteBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        if (confirm("¿Borrar esta sesión?")) {
          SessionManager.delete(session.id);
          if (sessionIdEl.value.trim() === session.id) {
            newChat();
          } else {
            renderSessionList();
          }
        }
      });

      item.appendChild(content);
      item.appendChild(time);
      item.appendChild(deleteBtn);

      item.addEventListener("click", () => {
        sessionIdEl.value = session.id;
        messagesEl.innerHTML = `<div class="welcome"><h2>Sesión restaurada</h2><p>Cargando historial...</p></div>`;
        renderSessionList();
        currentMessages = [];
      });

      sessionListEl.appendChild(item);
    });
  }

  function newChat() {
    sessionIdEl.value = newSessionId();
    currentMessages = [];
    currentStats = { input_tokens: 0, output_tokens: 0, total_cost: 0 };
    messagesEl.innerHTML = `
      <div class="welcome">
        <h2>¿En qué puedo ayudarte?</h2>
        <p>Pregúntame sobre Nimbus Cloud Platform o pídeme que realice una acción.</p>
        <div class="suggestions" id="suggestions"></div>
      </div>
    `;
    renderSessionList();
    renderSuggestions();
    updateStats();
  }

  function renderSuggestions() {
    const suggEl = document.getElementById("suggestions");
    if (!suggEl) return;
    
    suggEl.innerHTML = "";
    SUGGESTIONS.forEach(s => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = s;
      b.addEventListener("click", () => {
        send(s);
      });
      suggEl.appendChild(b);
    });
  }

  function appendBubble(role, text, opts) {
    opts = opts || {};
    const wrap = document.createElement("div");
    wrap.className = "msg " + role;
    if (opts.typing) wrap.classList.add("typing");

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text || (opts.typing ? "Escribiendo" : "");
    wrap.appendChild(bubble);

    if (opts.sources && opts.sources.length) {
      const src = document.createElement("div");
      src.className = "sources";
      opts.sources.forEach(s => {
        const span = document.createElement("span");
        span.textContent = s;
        src.appendChild(span);
      });
      wrap.appendChild(src);
    }

    // Botón copiar para mensajes del agente
    if (role === "agent" && text) {
      const copyBtn = document.createElement("button");
      copyBtn.className = "copy-btn";
      copyBtn.innerHTML = "📋 Copiar";
      copyBtn.style.cssText = `
        font-size: 11px;
        padding: 4px 8px;
        margin-top: 8px;
        background: var(--accent-soft);
        border: 1px solid var(--accent);
        border-radius: 6px;
        cursor: pointer;
        color: var(--accent);
        transition: 0.2s;
      `;
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(text).then(() => {
          showToast("Copiado al portapapeles ✓");
          copyBtn.innerHTML = "✓ Copiado";
          setTimeout(() => {
            copyBtn.innerHTML = "📋 Copiar";
          }, 2000);
        });
      });
      wrap.appendChild(copyBtn);
    }

    messagesEl.appendChild(wrap);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return wrap;
  }

  function removeEl(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  function parseSources(text) {
    const sources = [];
    const re = /\[\d+\]\s+[^\n]+/g;
    let m;
    while ((m = re.exec(text)) !== null) {
      sources.push(m[0]);
    }
    return sources.length ? sources : null;
  }

  function stripSources(text) {
    return text.replace(/\[\d+\]\s+[^\n]+/g, "").trim();
  }

  function handleError(err, typingEl) {
    removeEl(typingEl);
    appendBubble("agent", "Ha ocurrido un error al contactar con el agente. Asegúrate de que Ollama esté corriendo o revisa la consola del navegador.", {});
    console.error(err);
  }

  async function updateStats() {
    const sessionId = sessionIdEl.value.trim();
    if (!sessionId) return;

    try {
      const resp = await fetch(`/agent/stats/${sessionId}`);
      if (resp.ok) {
        const data = await resp.json();
        currentStats = {
          input_tokens: data.input_tokens || 0,
          output_tokens: data.output_tokens || 0,
          total_cost: data.total_cost || 0
        };

        document.getElementById("currentTokens").textContent = 
          (currentStats.input_tokens + currentStats.output_tokens).toLocaleString();
        document.getElementById("totalCost").textContent = 
          `$${currentStats.total_cost.toFixed(4)}`;
        document.getElementById("latency").textContent = "0ms";
      }
    } catch (err) {
      console.error("Stats fetch failed:", err);
    }
  }

  function exportMarkdown() {
    const sessionId = sessionIdEl.value || "unnamed";
    let md = `# Conversación - ${sessionId}\n`;
    md += `Exportado: ${new Date().toLocaleString("es-ES")}\n\n`;

    currentMessages.forEach(m => {
      if (m.role === "user") {
        md += `## Tú\n${m.content}\n\n`;
      } else {
        md += `## Agente\n${m.content}\n\n`;
      }
    });

    md += `---\n\n**Estadísticas:**\n`;
    md += `- Tokens totales: ${currentStats.input_tokens + currentStats.output_tokens}\n`;
    md += `- Coste: $${currentStats.total_cost.toFixed(4)}\n`;
    md += `- Proveedor: ${providerEl.value}\n`;

    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `conversation_${sessionId}.md`;
    a.click();
    URL.revokeObjectURL(url);

    showToast("Conversación exportada ✓");
  }

  async function send(message) {
    if (busy) return;
    busy = true;
    sendBtn.disabled = true;

    appendBubble("user", message);
    currentMessages.push({ role: "user", content: message });

    const typingEl = appendBubble("agent", "", { typing: true });

    const provider = providerEl.value;
    const sessionId = sessionIdEl.value.trim();

    const payload = { message, provider };
    if (sessionId) payload.session_id = sessionId;

    try {
      const startTime = performance.now();
      const resp = await fetch("/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const endTime = performance.now();

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) {
        removeEl(typingEl);
        const reason = (data && data.reason) ? " (" + data.reason + ")" : "";
        appendBubble("agent", (data && data.error) ? data.error + reason : "Mensaje bloqueado." + reason, {});
        busy = false;
        sendBtn.disabled = false;
        return;
      }

      const content = data.content || "";
      const sources = parseSources(content);
      const clean = stripSources(content);

      removeEl(typingEl);
      appendBubble("agent", clean, { sources });

      currentMessages.push({ role: "agent", content: clean });

      // Guardar sesión
      if (sessionId) {
        SessionManager.save(sessionId, currentMessages, currentStats);
        renderSessionList();
        await updateStats();
      }

      // Actualizar latencia (mock)
      document.getElementById("latency").textContent = Math.round(endTime - startTime) + "ms";

    } catch (err) {
      handleError(err, typingEl);
    } finally {
      busy = false;
      sendBtn.disabled = false;
      autoResize();
    }
  }

  function autoResize() {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 160) + "px";
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    const message = input.value.trim();
    if (!message || busy) return;
    input.value = "";
    autoResize();
    send(message);
  });

  input.addEventListener("input", autoResize);
  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  sessionIdEl.addEventListener("focus", function () {
    if (!sessionIdEl.value.trim()) sessionIdEl.value = newSessionId();
  });

  newChatBtn.addEventListener("click", newChat);
  
  exportBtn.addEventListener("click", () => {
    if (currentMessages.length === 0) {
      showToast("No hay conversación para exportar");
      return;
    }
    exportMarkdown();
  });

  toggleSidebarBtn.addEventListener("click", () => {
    sidebarEl.classList.toggle("open");
  });

  // Cerrar sidebar al clickear en un item (en mobile)
  sessionListEl.addEventListener("click", () => {
    if (window.innerWidth <= 600) {
      sidebarEl.classList.remove("open");
    }
  });

  // Inicializar
  renderSessionList();
  renderSuggestions();
  newChat();

  // Actualizar stats cada 5 segundos
  setInterval(updateStats, 5000);
})();
