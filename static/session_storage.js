(function () {
  const ACTIVE_KEY = "baddy_active_session";
  const HISTORY_KEY = "baddy_session_history";
  const MAX_HISTORY = 20;

  function saveActive(snapshot) {
    if (!snapshot) return;
    const data = Object.assign({}, snapshot, { savedAt: new Date().toISOString() });
    localStorage.setItem(ACTIVE_KEY, JSON.stringify(data));
  }

  function loadActive() {
    try {
      const raw = localStorage.getItem(ACTIVE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch (e) {
      return null;
    }
  }

  function clearActive() {
    localStorage.removeItem(ACTIVE_KEY);
  }

  function loadHistory() {
    try {
      const raw = localStorage.getItem(HISTORY_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) {
      return [];
    }
  }

  function saveHistory(entries) {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(entries.slice(0, MAX_HISTORY)));
  }

  function archiveSession(archivePayload) {
    if (!archivePayload) return;
    const entry = {
      id: String(Date.now()),
      endedAt: new Date().toISOString(),
      gameTo: archivePayload.game_to,
      competitionMode: archivePayload.competition_mode || "doubles",
      courts: archivePayload.num_courts,
      roundsPlayed: archivePayload.round_num || 0,
      playerNames: archivePayload.player_names || [],
      standings: archivePayload.standings || [],
    };
    const history = loadHistory();
    history.unshift(entry);
    saveHistory(history);
    clearActive();
  }

  function formatDate(iso) {
    try {
      return new Date(iso).toLocaleString(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch (e) {
      return iso;
    }
  }

  function initSnapshotFromPage() {
    const el = document.getElementById("session-snapshot-data");
    if (!el || !el.textContent) return;
    try {
      const snapshot = JSON.parse(el.textContent);
      saveActive(snapshot);
    } catch (e) {
      /* ignore */
    }
  }

  function renderSetupExtras() {
    const resumeBox = document.getElementById("resume-session-box");
    const historyBox = document.getElementById("past-sessions-box");
    const historyList = document.getElementById("past-sessions-list");
    if (!resumeBox && !historyBox) return;

    const active = loadActive();
    if (resumeBox) {
      if (active && active.players_scores) {
        resumeBox.hidden = false;
        const label = document.getElementById("resume-session-label");
        if (label) {
          const mode = active.competition_mode === "singles" ? "Singles" : "Doubles";
          const round = active.round_num || 1;
          label.textContent =
            mode +
            " · Round " +
            round +
            " · " +
            Object.keys(active.players_scores).length +
            " players";
        }
      } else {
        resumeBox.hidden = true;
      }
    }

    if (historyList) {
      const history = loadHistory();
      historyList.innerHTML = "";
      if (history.length === 0) {
        const li = document.createElement("li");
        li.className = "history-empty";
        li.textContent = "No completed sessions yet.";
        historyList.appendChild(li);
      } else {
        history.forEach(function (entry) {
          const li = document.createElement("li");
          const mode =
            entry.competitionMode === "singles" ? "Singles" : "Doubles";
          const top = entry.standings && entry.standings[0];
          const topLine = top
            ? " — " + top.name + " (" + top.score + " pts)"
            : "";
          li.textContent =
            formatDate(entry.endedAt) +
            " · " +
            mode +
            " · " +
            (entry.playerNames ? entry.playerNames.length : 0) +
            " players · " +
            (entry.roundsPlayed || 0) +
            " rounds" +
            topLine;
          historyList.appendChild(li);
        });
      }
    }
  }

  function bindResumeButton() {
    const btn = document.getElementById("resume-session-btn");
    if (!btn) return;
    btn.addEventListener("click", function () {
      const active = loadActive();
      if (!active) return;
      btn.disabled = true;
      btn.textContent = "Resuming…";
      fetch("/session/restore", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(active),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (data.ok && data.redirect) {
            window.location.href = data.redirect;
          } else {
            alert(data.error || "Could not resume session.");
            btn.disabled = false;
            btn.textContent = "Resume session";
          }
        })
        .catch(function () {
          alert("Could not resume session.");
          btn.disabled = false;
          btn.textContent = "Resume session";
        });
    });
  }

  function initArchive() {
    const el = document.getElementById("archive-session-data");
    if (!el || !el.textContent) return;
    try {
      const payload = JSON.parse(el.textContent);
      archiveSession(payload);
    } catch (e) {
      /* ignore */
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    initSnapshotFromPage();
    initArchive();
    renderSetupExtras();
    bindResumeButton();
  });

  window.BaddySessionStorage = {
    saveActive: saveActive,
    loadActive: loadActive,
    clearActive: clearActive,
    loadHistory: loadHistory,
    archiveSession: archiveSession,
  };
})();
