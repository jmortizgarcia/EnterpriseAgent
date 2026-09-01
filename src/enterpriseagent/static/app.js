(function () {
  "use strict";

  const messagesEl = document.getElementById("messages");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("sendBtn");
  const providerEl = document.getElementById("provider");
  const sessionIdEl = document.getElementById("sessionId");
  const suggestionsEl = document.getElementById("suggestions");

  const SUGGESTIONS = [
    "¿Cuál es el SLA del plan Enterprise?",
    "¿Cuánto cuesta el plan Pro?",
    "¿Cómo obtengo una API key?",
    "¿Cómo despliego mi primera app?",
    "Crea un ticket de alta prioridad porque la CPU está al 95%",
    "¿Qué significa el error 429?",
  ];

  let busy = false;

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function newSessionId() {
    return "session_" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);
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
      opts.sources.forEach(function (s) {
        const span = document.createElement("span");
        span.textContent = s;
        src.appendChild(span);
      });
      wrap.appendChild(src);
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

  async function send(message) {
    if (busy) return;
    busy = true;
    sendBtn.disabled = true;

    appendBubble("user", message);

    const typingEl = appendBubble("agent", "", { typing: true });

    const provider = providerEl.value;
    const sessionId = sessionIdEl.value.trim();

    const payload = { message: message, provider: provider };
    if (sessionId) payload.session_id = sessionId;

    try {
      const resp = await fetch("/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

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
      appendBubble("agent", clean, { sources: sources });

      // Guardar sesión autogenerada si venía vacía
      if (!sessionId && data.session_id) {
        sessionIdEl.value = data.session_id;
      }
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

  SUGGESTIONS.forEach(function (s) {
    const b = document.createElement("button");
    b.type = "button";
    b.textContent = s;
    b.addEventListener("click", function () {
      send(s);
    });
    suggestionsEl.appendChild(b);
  });
})();
