import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "./api.js";

// Pages of /api/matches (keyset pagination). The first page loads when the filters change; "load more" appends the next one. A request that belongs to filters the user
// has already left is dropped, so rows of two selections never mix.
export const PAGE_SIZE = 25;

export function useMatchPages(query) {
  const key = JSON.stringify(query);
  const current = useRef(key);
  current.current = key;
  const [state, setState] = useState({ pages: [], loading: true, error: null, more: { loading: false, error: null } });
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    const ctl = new AbortController();
    setState({ pages: [], loading: true, error: null, more: { loading: false, error: null } });
    api("/api/matches", { ...query, limit: PAGE_SIZE }, { signal: ctl.signal })
      .then((page) => {
        if (!ctl.signal.aborted) setState({ pages: [page], loading: false, error: null, more: { loading: false, error: null } });
      })
      .catch((error) => {
        if (error.name !== "AbortError" && !ctl.signal.aborted) setState((s) => ({ ...s, loading: false, error }));
      });
    return () => ctl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, retry]);

  const cursor = state.pages.at(-1)?.page.next_cursor ?? null;
  const loadMore = useCallback(() => {
    if (!cursor) return;
    const asked = key;
    setState((s) => ({ ...s, more: { loading: true, error: null } }));
    api("/api/matches", { ...query, limit: PAGE_SIZE, cursor })
      .then((page) => {
        if (current.current === asked) setState((s) => ({ ...s, pages: [...s.pages, page], more: { loading: false, error: null } }));
      })
      .catch((error) => {
        if (current.current === asked) setState((s) => ({ ...s, more: { loading: false, error } }));
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cursor, key]);

  const last = state.pages.at(-1);
  return {
    first: state.pages[0] ?? null,
    items: state.pages.flatMap((p) => p.items),
    counts: last?.counts ?? null,
    hasMore: Boolean(last?.page.has_more),
    loading: state.loading,
    error: state.error,
    more: state.more,
    loadMore,
    retry: () => setRetry((n) => n + 1),
  };
}
