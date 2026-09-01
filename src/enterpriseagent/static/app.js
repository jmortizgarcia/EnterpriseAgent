(function () {
  "use strict";

  const messagesEl = document.getElementById("messages");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("input");
  const sendBtn = document.getElementById("sendBtn");
  const cancelBtn = document.getElementById("cancelBtn");
  const providerEl = document.getElementById("provider");
  const sessionIdEl = document.getElementById("sessionId");
  const suggestionsEl = document.getElementById("suggestions");
  const sidebarEl = document.getElementById("sidebar");
  const sessionListEl = document.getElementById("sessionList");
  const newChatBtn = document.getElementById("newChatBtn");
  const exportBtn = document.getElementById("exportBtn");
  const toggleSidebarBtn = document.getElementById("toggleSidebar");
  const toastEl = document.getElementById("toast");

  // Elementos para tickets
  const chatViewEl = document.getElementById("chatView");
  const ticketViewEl = document.getElementById("ticketView");
  const chatTabEl = document.getElementById("chatTab");
  const ticketsTabEl = document.getElementById("ticketsTab");
  const ticketListEl = document.getElementById("ticketList");
  const emptyTicketsEl = document.getElementById("emptyTickets");
  const refreshTicketsBtn = document.getElementById("refreshTickets");

  const SUGGESTIONS = [
    "¿Qué es Nimbus Cloud?",
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
  let currentView = "chat"; // "chat" | "tickets"
  let abortController = null; // Para cancelar requests en progreso

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

      item.addEventListener("click", async () => {
        sessionIdEl.value = session.id;
        messagesEl.innerHTML = `<div class="welcome"><h2>Sesión restaurada</h2><p>Cargando historial...</p></div>`;
        renderSessionList();
        
        // Cargar el historial completo de la sesión
        try {
          const resp = await fetch(`/agent/history/${session.id}`);
          if (resp.ok) {
            const data = await resp.json();
            currentMessages = data.messages || [];
            
            // Limpiar pantalla y re-renderizar mensajes
            messagesEl.innerHTML = "";
            currentMessages.forEach(msg => {
              const sources = msg.role === "assistant" ? parseSources(msg.content) : null;
              const clean = msg.role === "assistant" ? stripSources(msg.content) : msg.content;
              appendBubble(msg.role, clean, { sources });
            });
            
            // Actualizar stats
            await updateStats();
          }
        } catch (err) {
          console.error("Error cargando historial:", err);
          messagesEl.innerHTML = `<div class="welcome"><h2>Error</h2><p>No se pudo cargar el historial. Intenta de nuevo.</p></div>`;
        }
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

  function formatMarkdown(text) {
    // Convertir markdown básico a HTML
    return text
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")           // **bold**
      .replace(/\*(.+?)\*/g, "<em>$1</em>")                       // *italic*
      .replace(/`([^`]+)`/g, "<code>$1</code>")                   // `code`
      .replace(/\n/g, "<br>");                                     // newlines
  }

  function appendBubble(role, text, opts) {
    opts = opts || {};
    const wrap = document.createElement("div");
    wrap.className = "msg " + role;
    if (opts.typing) wrap.classList.add("typing");

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    
    // Crear un contenedor para el texto que preserve los [N]
    const textContainer = document.createElement("div");
    textContainer.style.whiteSpace = "pre-wrap";
    textContainer.innerHTML = formatMarkdown(text || (opts.typing ? "Escribiendo" : ""));
    bubble.appendChild(textContainer);
    
    // Agregar referencias DENTRO de la burbuja si existen
    if (opts.sources && opts.sources.length) {
      const src = document.createElement("div");
      src.className = "sources";
      
      // Deduplicar referencias por número
      const sourceMap = {};
      opts.sources.forEach(s => {
        const match = s.match(/\[(\d+)\]/);
        const num = match ? match[1] : "0";
        if (!sourceMap[num]) {
          sourceMap[num] = s;
        }
      });
      
      const uniqueSources = Object.values(sourceMap);
      
      uniqueSources.forEach((s) => {
        // Formato esperado: [N] filename > title: descripción
        const match = s.match(/\[(\d+)\]\s+([^>]+)>\s*([^:]+):\s*(.+)/);
        
        const item = document.createElement("div");
        item.className = "source-item";
        
        const badge = document.createElement("span");
        badge.className = "source-badge";
        badge.textContent = match ? match[1] : "?";
        
        const textDiv = document.createElement("div");
        textDiv.className = "source-text";
        
        if (match) {
          const file = document.createElement("strong");
          file.textContent = `${match[2].trim()} - ${match[3].trim()}`;
          file.style.display = "block";
          
          const desc = document.createElement("div");
          desc.style.fontSize = "11px";
          desc.style.color = "var(--muted)";
          desc.style.marginTop = "4px";
          desc.style.lineHeight = "1.3";
          const descText = match[4].trim();
          desc.textContent = descText.length > 100 ? descText.substring(0, 100) + "…" : descText;
          
          textDiv.appendChild(file);
          textDiv.appendChild(desc);
        } else {
          // Fallback: mostrar la referencia tal cual
          textDiv.textContent = s.substring(0, 100);
        }
        
        item.appendChild(badge);
        item.appendChild(textDiv);
        src.appendChild(item);
      });
      
      bubble.appendChild(src);
    }
    
    wrap.appendChild(bubble);

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
    // Asegurar que el scroll sea después de que el DOM se renderice
    requestAnimationFrame(() => {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    });
    return wrap;
  }

  function removeEl(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  function parseSources(text) {
    const sources = [];
    // Capturar referencias en formato: * [N] filename > title: descripción
    // El patrón debe ser flexible y capturar incluso si hay espacios extras
    const re = /^\*\s*\[(\d+)\]\s+(.+?)(?:\n|$)/gm;
    let m;
    while ((m = re.exec(text)) !== null) {
      const content = m[2].trim();
      if (content && content.length > 0) {  // Solo agregar si hay contenido
        sources.push(`[${m[1]}] ${content}`);
      }
    }
    return sources.length ? sources : null;
  }

  function stripSources(text) {
    // Remover SOLO las líneas que comienzan con "* [N]" (bloque de referencias)
    // Mantener TODO lo demás, incluyendo [N] inline y la línea **Fuente:**
    return text.replace(/^\*\s*\[\d+\]\s+[^\n]+/gm, "").trim();
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

  /* ======== Gestión de Tickets ======== */
  function switchView(view) {
    currentView = view;
    
    if (view === "chat") {
      chatViewEl.classList.add("active");
      ticketViewEl.classList.remove("active");
      chatTabEl.classList.add("active");
      ticketsTabEl.classList.remove("active");
      sidebarEl.classList.remove("hidden"); // Mostrar sidebar en chat
      newChat(); // Resetear historial al ir a chat
    } else {
      chatViewEl.classList.remove("active");
      ticketViewEl.classList.add("active");
      chatTabEl.classList.remove("active");
      ticketsTabEl.classList.add("active");
      sidebarEl.classList.add("hidden"); // Ocultar sidebar en tickets
      loadTickets();
    }
  }

  async function loadTickets() {
    try {
      const resp = await fetch("/tickets");
      const data = await resp.json();
      renderTickets(data.tickets || []);
    } catch (err) {
      console.error("Error loading tickets:", err);
      showToast("Error al cargar tickets");
    }
  }

  function renderTickets(tickets) {
    ticketListEl.innerHTML = "";
    
    if (tickets.length === 0) {
      emptyTicketsEl.style.display = "flex";
      return;
    }
    
    emptyTicketsEl.style.display = "none";
    
    tickets.forEach(ticket => {
      const card = document.createElement("div");
      card.className = "ticket-card";
      card.innerHTML = `
        <div class="ticket-card-header">
          <span class="ticket-id">Ticket #${ticket.id}</span>
          <span class="ticket-priority ${ticket.priority}">${ticket.priority}</span>
        </div>
        <h3 class="ticket-title">${esc(ticket.title)}</h3>
        <p class="ticket-description">${esc(ticket.description)}</p>
      `;
      card.addEventListener("click", () => showTicketDetails(ticket));
      ticketListEl.appendChild(card);
    });
  }

  // ========== MODALES Y FORMULARIOS ==========

  const ticketModal = document.getElementById("ticketModal");
  const ticketDetailsModal = document.getElementById("ticketDetailsModal");
  const ticketForm = document.getElementById("ticketForm");
  const ticketTitle = document.getElementById("ticketTitle");
  const ticketDescription = document.getElementById("ticketDescription");
  const ticketPriority = document.getElementById("ticketPriority");
  const newTicketBtn = document.getElementById("newTicketBtn");
  const closeModal = document.getElementById("closeModal");
  const cancelTicketBtn = document.getElementById("cancelTicketBtn");
  const submitTicketBtn = document.getElementById("submitTicketBtn");
  const deleteTicketBtn = document.getElementById("deleteTicketBtn");
  const closeDetailsModalBtn = document.getElementById("closeDetailsModal");
  const closeDetailsBtn = document.getElementById("closeDetailsBtn");
  const editFromDetailsBtn = document.getElementById("editFromDetailsBtn");
  const modalTitle = document.getElementById("modalTitle");

  let currentEditingTicketId = null; // Para saber si estamos editando o creando

  function openCreateModal() {
    if (!ticketModal || !ticketForm) return;
    currentEditingTicketId = null;
    modalTitle.textContent = "Crear Ticket";
    ticketForm.reset();
    deleteTicketBtn.style.display = "none";
    submitTicketBtn.textContent = "Crear";
    ticketModal.classList.add("active");
  }

  function openEditModal(ticket) {
    if (!ticketModal || !ticketForm) return;
    currentEditingTicketId = ticket.id;
    modalTitle.textContent = `Editar Ticket #${ticket.id}`;
    ticketTitle.value = ticket.title;
    ticketDescription.value = ticket.description;
    ticketPriority.value = ticket.priority;
    deleteTicketBtn.style.display = "block";
    submitTicketBtn.textContent = "Guardar cambios";
    ticketModal.classList.add("active");
  }

  function closeTicketModal() {
    if (!ticketModal) return;
    ticketModal.classList.remove("active");
    currentEditingTicketId = null;
  }

  function showTicketDetails(ticket) {
    if (!ticketDetailsModal) return;
    const detailsEl = document.getElementById("ticketDetails");
    
    detailsEl.innerHTML = `
      <div class="detail-row">
        <div class="detail-label">ID</div>
        <div class="detail-value">#${ticket.id}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Título</div>
        <div class="detail-value">${esc(ticket.title)}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Descripción</div>
        <div class="detail-value">${esc(ticket.description)}</div>
      </div>
      <div class="detail-row">
        <div class="detail-label">Prioridad</div>
        <div class="detail-value"><span class="ticket-priority ${ticket.priority}">${ticket.priority}</span></div>
      </div>
    `;
    
    document.getElementById("detailsTitle").textContent = `Ticket #${ticket.id}`;
    
    if (editFromDetailsBtn) {
      editFromDetailsBtn.onclick = () => {
        closeDetailsModalView();
        openEditModal(ticket);
      };
    }
    
    ticketDetailsModal.classList.add("active");
  }

  function closeDetailsModalView() {
    if (!ticketDetailsModal) return;
    ticketDetailsModal.classList.remove("active");
  }

  async function submitTicketForm() {
    if (!ticketTitle || !ticketDescription) return;

    // Usar valores por defecto si están vacíos
    const title = ticketTitle.value.trim() || "Ticket sin título";
    const description = ticketDescription.value.trim() || "Sin descripción";

    const payload = {
      title: title,
      description: description,
      priority: ticketPriority.value
    };

    try {
      let url = "/tickets";
      let method = "POST";

      if (currentEditingTicketId) {
        url += `/${currentEditingTicketId}`;
        method = "PUT";
      }

      const resp = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!resp.ok) {
        showToast("Error al guardar ticket");
        return;
      }

      closeTicketModal();
      showToast(currentEditingTicketId ? "Ticket actualizado" : "Ticket creado");
      loadTickets(); // Recargar lista
    } catch (err) {
      console.error("Error submitting ticket:", err);
      showToast("Error al guardar ticket");
    }
  }

  async function deleteCurrentTicket() {
    if (!currentEditingTicketId) return;
    
    if (!confirm(`¿Eliminar ticket #${currentEditingTicketId}?`)) {
      return;
    }

    try {
      const resp = await fetch(`/tickets/${currentEditingTicketId}`, {
        method: "DELETE"
      });

      if (!resp.ok) {
        showToast("Error al eliminar ticket");
        return;
      }

      closeTicketModal();
      showToast("Ticket eliminado");
      loadTickets(); // Recargar lista
    } catch (err) {
      console.error("Error deleting ticket:", err);
      showToast("Error al eliminar ticket");
    }
  }

  // Event listeners para modales
  if (newTicketBtn) newTicketBtn.addEventListener("click", openCreateModal);
  if (closeModal) closeModal.addEventListener("click", closeTicketModal);
  if (cancelTicketBtn) cancelTicketBtn.addEventListener("click", closeTicketModal);
  if (ticketForm) ticketForm.addEventListener("submit", (e) => {
    e.preventDefault();
    submitTicketForm();
  });
  if (deleteTicketBtn) deleteTicketBtn.addEventListener("click", deleteCurrentTicket);
  if (closeDetailsBtn) closeDetailsBtn.addEventListener("click", closeDetailsModalView);

  // Cerrar modal al clickear fuera
  if (ticketModal) {
    ticketModal.addEventListener("click", (e) => {
      if (e.target === ticketModal) closeTicketModal();
    });
  }
  if (ticketDetailsModal) {
    ticketDetailsModal.addEventListener("click", (e) => {
      if (e.target === ticketDetailsModal) closeDetailsModalView();
    });
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
    cancelBtn.style.display = "inline-block"; // Mostrar botón cancelar
    abortController = new AbortController(); // Crear nuevo controller para esta request

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
        signal: abortController.signal, // Pasar el signal para cancelación
      });
      const endTime = performance.now();

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) {
        removeEl(typingEl);
        const reason = (data && data.reason) ? " (" + data.reason + ")" : "";
        appendBubble("agent", (data && data.error) ? data.error + reason : "Mensaje bloqueado." + reason, {});
        busy = false;
        sendBtn.disabled = false;
        cancelBtn.style.display = "none";
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
      // Si es un error de AbortError, simplemente limpiar (no mostrar error)
      if (err.name !== "AbortError") {
        handleError(err, typingEl);
      } else {
        removeEl(typingEl);
        showToast("Mensaje cancelado");
      }
    } finally {
      busy = false;
      sendBtn.disabled = false;
      cancelBtn.style.display = "none"; // Ocultar botón cancelar
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

  cancelBtn.addEventListener("click", () => {
    if (abortController) {
      abortController.abort(); // Cancelar la request en progreso
    }
  });

  toggleSidebarBtn.addEventListener("click", () => {
    sidebarEl.classList.toggle("open");
  });

  // Click en brand para ir al inicio
  document.getElementById("brandHome").addEventListener("click", () => {
    newChat();
  });

  // Cambiar entre vistas
  chatTabEl.addEventListener("click", () => switchView("chat"));
  ticketsTabEl.addEventListener("click", () => switchView("tickets"));
  refreshTicketsBtn.addEventListener("click", loadTickets);

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
