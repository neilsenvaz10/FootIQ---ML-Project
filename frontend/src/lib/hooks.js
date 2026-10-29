import { useEffect, useRef, useState } from "react";
import { api } from "./api.js";

// useApi(path, params, { retry }): loads when `path` is truthy; params are compared by value. Returns {data, loading, error}.
// `retry` is a counter: raising it fetches again (a section's "Try again" button) and is never sent to the backend.
export function useApi(path, params, { retry = 0 } = {}) {
  const [state, setState] = useState({ data: null, loading: Boolean(path), error: null });
  const key = JSON.stringify([path, params ?? {}, retry]);
  useEffect(() => {
    if (!path) {
      setState({ data: null, loading: false, error: null });
      return undefined;
    }
    const ctl = new AbortController();
    setState({ data: null, loading: true, error: null }); // never show data that belongs to the previous request
    api(path, params, { signal: ctl.signal })
      .then((data) => setState({ data, loading: false, error: null }))
      .catch((error) => {
        if (error.name !== "AbortError") setState({ data: null, loading: false, error });
      });
    return () => ctl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state;
}

// Readiness check for the club models: polls /api/health every `everyMs` until club_prediction_ready is true, then stops.
export function useClubReady(everyMs = 3000) {
  const [state, setState] = useState({ ready: false, error: null, checked: false });
  const stop = useRef(false);
  useEffect(() => {
    stop.current = false;
    let timer;
    const tick = async () => {
      try {
        const h = await api("/api/health");
        if (stop.current) return;
        setState({ ready: Boolean(h.club_prediction_ready), error: null, checked: true });
        if (!h.club_prediction_ready) timer = setTimeout(tick, everyMs);
      } catch (error) {
        if (stop.current) return;
        setState({ ready: false, error, checked: true });
        timer = setTimeout(tick, everyMs * 2);
      }
    };
    tick();
    return () => {
      stop.current = true;
      clearTimeout(timer);
    };
  }, [everyMs]);
  return state;
}
