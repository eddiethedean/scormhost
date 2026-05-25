/**
 * SCORM 1.2 API shim — parent frame API synced to scormhost backend.
 */
(function (global) {
  const config = global.__SCORMHOST_SCORM12__;
  if (!config) return;

  const state = { initialized: false, terminated: false, lastError: "0" };
  const data = {
    "cmi.core.lesson_status": "not attempted",
    "cmi.core.score.raw": "0",
    "cmi.core.score.min": "0",
    "cmi.core.score.max": "100",
    "cmi.suspend_data": "",
    "cmi.core.lesson_location": "",
    "cmi.core.student_id": config.learnerId,
    "cmi.core.student_name": config.learnerName || config.learnerId,
    "cmi.core.entry": "ab-initio",
    "cmi.core.exit": "",
    "cmi.core.session_time": "00:00:00",
  };

  function applyRemote(elements) {
    if (!elements) return;
    for (const [key, value] of Object.entries(elements)) {
      if (key in data) data[key] = String(value);
    }
  }

  async function loadRemote() {
    const url = new URL(config.cmiUrl, global.location.origin);
    const res = await fetch(url.toString(), { credentials: "same-origin" });
    if (!res.ok) return;
    const body = await res.json();
    applyRemote(body.elements);
  }

  async function persistRemote() {
    const url = new URL(config.cmiUrl, global.location.origin);
    await fetch(url.toString(), {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ elements: { ...data } }),
      keepalive: true,
    });
  }

  const API = {
    LMSInitialize: function () {
      if (state.initialized) {
        state.lastError = "101";
        return "false";
      }
      state.initialized = true;
      state.terminated = false;
      state.lastError = "0";
      return "true";
    },
    LMSFinish: function () {
      if (!state.initialized || state.terminated) {
        state.lastError = "301";
        return "false";
      }
      data["cmi.core.exit"] = "suspend";
      state.terminated = true;
      void persistRemote();
      state.lastError = "0";
      return "true";
    },
    LMSGetValue: function (element) {
      if (!state.initialized || state.terminated) {
        state.lastError = "301";
        return "";
      }
      state.lastError = "0";
      return data[element] ?? "";
    },
    LMSSetValue: function (element, value) {
      if (!state.initialized || state.terminated) {
        state.lastError = "301";
        return "false";
      }
      if (!element.startsWith("cmi.")) return "false";
      data[element] = String(value);
      state.lastError = "0";
      return "true";
    },
    LMSCommit: function () {
      if (!state.initialized || state.terminated) {
        state.lastError = "301";
        return "false";
      }
      void persistRemote();
      state.lastError = "0";
      return "true";
    },
    LMSGetLastError: function () {
      return state.lastError;
    },
    LMSGetErrorString: function (code) {
      const c = code || state.lastError;
      if (c === "301") return "Not initialized";
      return "No error";
    },
    LMSGetDiagnostic: function () {
      return "";
    },
  };

  global.API = API;
  void loadRemote().then(function () {
    const iframe = document.getElementById("scormhost-content");
    if (iframe) iframe.src = config.contentUrl;
  });
})(window);
