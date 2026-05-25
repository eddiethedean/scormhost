/**
 * SCORM 2004 4th Edition API shim (subset) for scormhost.
 */
(function (global) {
  const config = global.__SCORMHOST_SCORM2004__;
  if (!config) return;

  const state = { initialized: false, terminated: false, lastError: "0" };
  const data = {
    "cmi.completion_status": "unknown",
    "cmi.success_status": "unknown",
    "cmi.score.scaled": "",
    "cmi.suspend_data": "",
    "cmi.location": "",
    "cmi.entry": "ab-initio",
    "cmi.learner_id": config.learnerId,
    "cmi.learner_name": config.learnerName || config.learnerId,
  };

  function applyRemote(elements) {
    if (!elements) return;
    for (const [key, value] of Object.entries(elements)) {
      data[key] = String(value);
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

  const API_1484_11 = {
    Initialize: function () {
      if (state.initialized) return "false";
      state.initialized = true;
      state.terminated = false;
      return "true";
    },
    Terminate: function () {
      if (!state.initialized || state.terminated) return "false";
      state.terminated = true;
      void persistRemote();
      return "true";
    },
    GetValue: function (element) {
      if (!state.initialized || state.terminated) return "";
      return data[element] ?? "";
    },
    SetValue: function (element, value) {
      if (!state.initialized || state.terminated) return "false";
      data[element] = String(value);
      return "true";
    },
    Commit: function () {
      if (!state.initialized || state.terminated) return "false";
      void persistRemote();
      return "true";
    },
    GetLastError: function () {
      return state.lastError;
    },
    GetErrorString: function () {
      return "No error";
    },
    GetDiagnostic: function () {
      return "";
    },
  };

  global.API_1484_11 = API_1484_11;
  void loadRemote().then(function () {
    const iframe = document.getElementById("scormhost-content");
    if (iframe) iframe.src = config.contentUrl;
  });
})(window);
