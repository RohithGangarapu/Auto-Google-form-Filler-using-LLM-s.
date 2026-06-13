const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || `Request failed with status ${response.status}`);
  }
  return data;
}

export const api = {
  getModels() {
    return request("/models");
  },
  createSession(url) {
    return request("/sessions", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
  },
  getSession(sessionId) {
    return request(`/sessions/${sessionId}`);
  },
  scrape(sessionId) {
    return request(`/sessions/${sessionId}/scrape`, { method: "POST" });
  },
  answer(sessionId, context, models = []) {
    return request(`/sessions/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify({ context, models }),
    });
  },
  fill(sessionId, answers = {}) {
    return request(`/sessions/${sessionId}/fill`, {
      method: "POST",
      body: JSON.stringify({ answers }),
    });
  },
  close(sessionId) {
    return request(`/sessions/${sessionId}/close`, { method: "POST" });
  },
};
