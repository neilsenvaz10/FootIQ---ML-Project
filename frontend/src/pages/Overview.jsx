import { useState } from "react";
import { useApi } from "../lib/hooks.js";
import FeaturedMatch, { FeaturedEmpty, FeaturedError, FeaturedLoading } from "../components/home/FeaturedMatch.jsx";
import { RecentResults, UpcomingFixtures } from "../components/home/FixtureLists.jsx";
import LeagueOverview from "../components/home/LeagueOverview.jsx";
import QuickActions from "../components/home/QuickActions.jsx";
import { Spinner } from "../components/ui.jsx";

// Home dashboard (stage P4.2). One bounded request, /api/featured-fixture, feeds the featured match, the next fixtures and the latest results; the league table has its own
// requests. Each part loads, fails and retries on its own. Nothing is forecast here and nothing is shown that the store does not hold.
export default function Overview() {
  const [retry, setRetry] = useState(0);
  const { data, loading, error } = useApi("/api/featured-fixture", undefined, { retry });
  return (
    <div className="space-y-5 lg:space-y-6">
      <h1 className="sr-only">Home</h1>
      {loading && <FeaturedLoading />}
      {error && <FeaturedError error={error} onRetry={() => setRetry((n) => n + 1)} />}
      {data && (data.featured ? <FeaturedMatch data={data} /> : <FeaturedEmpty data={data} />)}

      <QuickActions />

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-6">
        <div className="min-w-0">
          {loading && <Spinner label="Loading fixtures and results…" />}
          {data && <UpcomingFixtures data={data} />}
        </div>
        <div className="min-w-0">
          <LeagueOverview freshness={data?.freshness} />
        </div>
      </div>
      {data && <RecentResults data={data} />}
    </div>
  );
}
