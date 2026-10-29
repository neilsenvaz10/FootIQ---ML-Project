import { useSearchParams } from "react-router-dom";
import PageHeader from "../components/PageHeader.jsx";
import { TabPanel, Tabs } from "../components/ui.jsx";
import GameweekPredict, { LEAGUE_KEYS } from "./GameweekPredict.jsx";
import ManualPredict from "./Predict.jsx";

// Predictions: whole gameweeks of the five domestic leagues (saved on request) or a manual head-to-head for any of the 11 competitions.
export default function Predictions() {
  const [params, setParams] = useSearchParams();
  const comp = params.get("comp");
  const mode = params.get("mode") ?? (comp && !LEAGUE_KEYS.includes(comp) ? "manual" : "gameweek");
  const choose = (m) => {
    const next = new URLSearchParams(params);
    next.set("mode", m);
    if (m === "gameweek" && comp && !LEAGUE_KEYS.includes(comp)) next.delete("comp");
    next.delete("gw");
    setParams(next);
  };
  return (
    <>
      <PageHeader title="Predictions">Estimates from the project's frozen models, not guaranteed results. Predict a whole gameweek of a domestic league, or compare any two teams manually.</PageHeader>
      <Tabs
        idBase="predictions"
        label="Prediction mode"
        value={mode}
        onChange={choose}
        tabs={[
          { value: "gameweek", label: "Gameweek" },
          { value: "manual", label: "Manual head-to-head" },
        ]}
      />
      <TabPanel idBase="predictions" value={mode} label={mode === "gameweek" ? "Gameweek predictions" : "Manual head-to-head prediction"} className="mt-4">
        {mode === "gameweek" ? <GameweekPredict /> : <ManualPredict />}
      </TabPanel>
    </>
  );
}
