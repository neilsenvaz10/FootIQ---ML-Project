import { lazy, Suspense } from "react";
import { Spinner } from "../components/ui.jsx";
const SeasonSimulator = lazy(() => import("./SeasonSimulator.jsx"));

// Simulations: the domestic league season simulator. (The World Cup simulator, Simulator.jsx, belongs to a competition outside the six-competition scope: kept in the repository, not routed.)
export default function Simulations() {
  return (
    <Suspense fallback={<Spinner />}>
      <SeasonSimulator />
    </Suspense>
  );
}
