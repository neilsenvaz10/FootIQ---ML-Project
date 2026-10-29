import { createContext, useContext } from "react";
import { useApi } from "../lib/hooks.js";

const MetaContext = createContext({ data: null, loading: true, error: null });

// /api/meta (attribution, data cut-offs, limitations) is loaded once and shared by every page.
export function MetaProvider({ children }) {
  const state = useApi("/api/meta");
  return <MetaContext.Provider value={state}>{children}</MetaContext.Provider>;
}

export const useMeta = () => useContext(MetaContext);
