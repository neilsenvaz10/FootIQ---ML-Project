
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, useLocation } from "react-router-dom";
import Analytics from "../src/pages/Analytics.jsx";
import StandingsTable from "../src/components/leagues/StandingsTable.jsx";
import { levelOnPoints, playedSpread, seasonIndicators } from "../src/lib/leagues.js";
import MatchFilters from "../src/components/matches/MatchFilters.jsx";

const comps = ["EPL", "LALIGA", "BUNDESLIGA", "SERIEA", "LIGUE1"].map((key) => ({key, name:key, group:"Domestic league", sources:"openfootball", licences:"CC0"}));
const rows = [{pos:1,team:"A long football club name",played:3,won:2,drawn:1,lost:0,gf:5,ga:1,gd:4,points:7,form:["W","D","W"]},{pos:2,team:"Second club",played:4,won:2,drawn:1,lost:1,gf:4,ga:2,gd:2,points:7,form:["L","W","D","W"]}];
let requests;
let failCoverage;
function Location() { return <output data-testid="location">{useLocation().search}</output>; }
function page(route="/analytics") {return render(<MemoryRouter initialEntries={[route]}><Analytics/><Location/></MemoryRouter>);}
beforeEach(() => {
 requests=[]; failCoverage=false;
 vi.stubGlobal("fetch",vi.fn(async (url,opts) => {
  const u=new URL(url); requests.push({url:u,method:opts?.method});
  let body;
  if(u.pathname==="/api/competitions")body=comps;
  else if(u.pathname.endsWith("/seasons"))body=["2026-27","2025-26"];
  else if(u.pathname.endsWith("/dashboard"))body={season:u.searchParams.get("season"),standings:rows,summary:{matches:7,goals_per_match:2,home_win_rate:0.5,draw_rate:0.2,away_win_rate:0.3,first_date:"2026-08-01",last_date:"2026-10-10"},results:[]};
  else if(u.pathname.endsWith("/coverage")) {
   if(failCoverage)return {ok:false,status:503,json:async()=>({detail:"Coverage offline"})};
   body=[{season:"2026-27",note:"incomplete or in progress",rows_in_dataset:7,expected_matches:380},{season:"2025-26",note:"",rows_in_dataset:380,expected_matches:380}];
  }else if(u.pathname==="/api/sync/status")body={competitions:comps.map(c=>({competition_key:c.key,state:"stale",latest_result:"2026-10-10",awaiting_result:3,state_reasons:["Source is stale"]}))};
  else if(u.pathname==="/api/matches")body={items:[],today_utc:"2026-10-27"};
  else throw new Error(`Unexpected request ${u.pathname}`);
  return {ok:true,status:200,json:async()=>body};
 }));
});
afterEach(()=>{cleanup();vi.unstubAllGlobals();});

describe("Leagues P4.4",()=>{
 it("uses the newest stored season, keeps all five leagues and labels partial tables",async()=>{
  page(); await screen.findByRole("table");
  expect(screen.getByRole("radiogroup",{name:"Domestic league"})).toBeInTheDocument();
  expect(screen.getByLabelText("Season")).toHaveValue("2026-27");
  expect(screen.queryByText(/Partial season: 7 of 380/)).toBeNull();
  expect(screen.queryByText(/3 fixtures have no verified result/)).toBeNull(); // amber notices removed (Phase 4.35)
  expect(screen.getByText(/not an official tie-break/)).toBeInTheDocument();
  expect(screen.getByRole("link",{name:"League fixtures"})).toHaveAttribute("href","/matches?comp=EPL&season=2026-27&status=upcoming");
  expect(requests.every(r=>r.method==="GET")).toBe(true);
  expect(requests.filter(r=>r.url.pathname.endsWith("dashboard"))).toHaveLength(1);
 });
 it("honours historical deep links and does not apply current missing-result counts to history",async()=>{
  page("/analytics?comp=LALIGA&season=2025-26");await screen.findByRole("table");
  expect(screen.getByLabelText("Season")).toHaveValue("2025-26");
  expect(screen.getByText("Historical season")).toBeInTheDocument();
  expect(screen.queryByText(/3 fixtures have/)).not.toBeInTheDocument();
  expect(screen.getByText("Expected match count present")).toBeInTheDocument();
 });
 it("stores season changes in the URL and resets the season when changing leagues",async()=>{
  const user=userEvent.setup();page();await screen.findByRole("table");
  await user.selectOptions(screen.getByLabelText("Season"),"2025-26");
  expect(screen.getByTestId("location")).toHaveTextContent("season=2025-26");
  await user.click(screen.getByRole("radio",{name:"BUNDESLIGA"}));
  await screen.findByRole("table");expect(screen.getByTestId("location")).toHaveTextContent("?comp=BUNDESLIGA");
  expect(screen.getByLabelText("Season")).toHaveValue("2026-27");
 });
 it("rejects an unavailable season without silently showing a different table",async()=>{
  page("/analytics?comp=EPL&season=1900");await screen.findByText(/requested season is not available/);
  expect(screen.queryByRole("table")).not.toBeInTheDocument();expect(requests.some(r=>r.url.pathname.endsWith("dashboard"))).toBe(false);
 });
 it("reports coverage errors and supports a local retry",async()=>{
  page();failCoverage=true;await screen.findByRole("alert");failCoverage=false;
  await userEvent.setup().click(screen.getByRole("button",{name:"Try again"}));await screen.findByText(/not an official tie-break/);
 });
 it("requests fixtures only in Matches and keeps selected season in both requests",async()=>{
  const user=userEvent.setup();page("/analytics?comp=SERIEA&season=2025-26");await screen.findByRole("table");
  expect(requests.some(r=>r.url.pathname==="/api/matches")).toBe(false);
  await user.click(screen.getByRole("tab",{name:"Matches"}));await screen.findByText(/No scheduled fixture/);
  const calls=requests.filter(r=>r.url.pathname==="/api/matches");expect(calls).toHaveLength(2);
  expect(calls.every(r=>r.url.searchParams.get("season")==="2025-26" && r.url.searchParams.get("comp")==="SERIEA")).toBe(true);
 });
 it("provides table caption, column headers, every statistic and accessible form",()=>{
  render(<StandingsTable rows={rows} caption="Test standings"/>);
  expect(screen.getByRole("table",{name:"Test standings"})).toBeInTheDocument();
  for(const h of screen.getAllByRole("columnheader"))expect(h).toHaveAttribute("scope","col");
  expect(screen.getByText("A long football club name")).toBeInTheDocument();
  expect(screen.getAllByRole("img",{name:/last 3 results/})).toHaveLength(1);
  expect(screen.getByText("GF 5 · GA 1")).toBeInTheDocument();
 });
 it("preserves tied data rather than assigning official positions",()=>{
  const before=JSON.stringify(rows);expect([...levelOnPoints(rows)]).toHaveLength(2);
  expect(playedSpread(rows)).toEqual({min:3,max:4,even:false});expect(JSON.stringify(rows)).toBe(before);
  expect(seasonIndicators({rows,coverage:null,sync:{state:"stale",awaiting_result:3},current:false}).map(x=>x.key)).toEqual(["uneven"]);
 });
 it("discloses secondary match filters without changing URL state or selected filters",async()=>{
  const onChange=vi.fn();render(<MatchFilters comp="EPL" season="2025-26" matchday="3" status="completed" facets={{seasons:["2025-26"],matchdays:[3]}} onChange={onChange}/>);
  const toggle=screen.getByRole("button",{name:/Show season, matchday and team/});expect(toggle).toHaveAttribute("aria-expanded","false");
  await userEvent.setup().click(toggle);expect(toggle).toHaveAttribute("aria-expanded","true");
  expect(screen.getByLabelText("Season")).toHaveValue("2025-26");expect(screen.getByRole("radiogroup",{name:"Status"})).toBeInTheDocument();expect(onChange).not.toHaveBeenCalled();
 });
 it("renders stats tab with chart cards showing outcome split and team performance",async()=>{
  const user=userEvent.setup();page();await screen.findByRole("table");
  await user.click(screen.getByRole("tab",{name:"Stats"}));
  expect(screen.getByText("Win / draw / loss split")).toBeInTheDocument();
  expect(screen.getByText("Team performance")).toBeInTheDocument();
  expect(screen.getByText(/50/)).toBeInTheDocument();
 });
 it("shows outcome basis and goals-per-match stat on stats tab",async()=>{
  const user=userEvent.setup();page();await screen.findByRole("table");
  await user.click(screen.getByRole("tab",{name:"Stats"}));
  expect(screen.getByText("2.00")).toBeInTheDocument();
  expect(screen.getByText("50.0%")).toBeInTheDocument();
 });
});
