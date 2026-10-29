// Thin client for the FootIQ FastAPI backend. No prediction or statistics logic lives in the frontend.
export const API_URL = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function buildUrl(path, params = {}) {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") q.set(k, String(v));
  }
  const qs = q.toString();
  return `${API_URL}${path}${qs ? `?${qs}` : ""}`;
}

// The backend always answers errors with {"detail": "<message>"}.
export async function api(path, params, { signal, method = "GET", body } = {}) {
  let res;
  try {
    res = await fetch(buildUrl(path, params), body === undefined ? { signal, method } : { signal, method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(`Cannot reach the backend at ${API_URL}. Is it running?`, 0);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(typeof detail === "string" ? detail : JSON.stringify(detail), res.status);
  }
  return res.json();
}
