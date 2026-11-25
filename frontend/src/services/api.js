// services/api.js – REST API client for VoxLead AI backend
// Uses native fetch. No Axios, no extra libraries.

const API_BASE = "http://localhost:8000";

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const config = {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  };

  const response = await fetch(url, config);
  if (!response.ok) {
    let errorDetail = "API error";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  // Call Lifecycle
  startCall: () => request("/api/call/start", { method: "POST" }),
  
  sendTurn: (callId, text, language = "en-IN") =>
    request(`/api/call/${callId}/turn`, {
      method: "POST",
      body: JSON.stringify({ text, language }),
    }),

  endCall: (callId) => request(`/api/call/${callId}/end`, { method: "POST" }),

  // Dashboard Data
  getLeads: () => request("/api/leads/"),
  getAppointments: () => request("/api/appointments/"),
  getAvailableSlots: () => request("/api/appointments/slots"),
  getCalls: () => request("/api/calls/"),

  // Knowledge Base
  reloadKB: () => request("/api/kb/reload", { method: "POST" }),
};
