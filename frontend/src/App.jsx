import { lazy, Suspense } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import { MetaProvider } from "./components/MetaContext.jsx";
import PageHeader from "./components/PageHeader.jsx";
import { ButtonLink, Spinner } from "./components/ui.jsx";
const Overview = lazy(() => import("./pages/Overview.jsx"));
const Matches = lazy(() => import("./pages/Matches.jsx"));
const Analytics = lazy(() => import("./pages/Analytics.jsx"));
const TeamComparison = lazy(() => import("./pages/TeamComparison.jsx"));
const Predictions = lazy(() => import("./pages/Predictions.jsx"));
const Simulations = lazy(() => import("./pages/Simulations.jsx"));
const Models = lazy(() => import("./pages/Models.jsx"));
// Development only: the token and component sheet is not part of the production build (import.meta.env.DEV is false there).
const DesignSystem = import.meta.env.DEV ? lazy(() => import("./pages/DesignSystem.jsx")) : null;

// "Predict" was renamed "Predictions"; /predictions goes to the page that existed before, keeping ?comp= and the rest of the link.
function PredictionsRedirect() {
  const { search, hash } = useLocation();
  return <Navigate to={{ pathname: "/predict", search, hash }} replace />;
}

function NotFound() {
  return (
    <div>
      <PageHeader title="Page not found">There is nothing at this address.</PageHeader>
      <ButtonLink to="/">Back to Home</ButtonLink>
    </div>
  );
}

export default function App() {
  return (
    <MetaProvider>
      <Suspense fallback={<Spinner />}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Overview />} />
            <Route path="matches" element={<Matches />} />
            <Route path="analytics" element={<Analytics />} />
            <Route path="compare" element={<TeamComparison />} />
            <Route path="predict" element={<Predictions />} />
            <Route path="predictions" element={<PredictionsRedirect />} />
            <Route path="worldcup" element={<Simulations />} />
            <Route path="simulations" element={<Simulations />} />
            <Route path="models" element={<Models />} />
            {DesignSystem && <Route path="design" element={<DesignSystem />} />}
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </Suspense>
    </MetaProvider>
  );
}
