import { readFileSync, writeFileSync } from "node:fs";
import { launch } from "./cdp_p44.mjs";
const root="D:/Foot IQ";
const chrome=await launch({port:9344,profile:root+"/data/supervised/phase4/p44/chrome-profile"});
const probe=readFileSync(root+"/data/supervised/phase4/tools/probe.js","utf8");
const out={};
try {
 for(const w of [1440,820,375]){
  await chrome.viewport(w,1000,1,w===375);
  await chrome.go("http://127.0.0.1:5174/analytics?comp=BUNDESLIGA",3000);
  out[w]={table:await chrome.eval(probe)};
  out[w].tableScroll=await chrome.eval(`(()=>{const t=document.querySelector('table');return t?{scrollWidth:t.parentElement.scrollWidth,clientWidth:t.parentElement.clientWidth}:null})()`);
  await chrome.eval("window.scrollTo(0,0); new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))");
  await chrome.shot(root+`/docs/mini-project/phase4/p4.4/leagues-${w}.png`,{fullPage:true});
  await chrome.eval(`document.querySelector('[role="tab"]').focus();0`);
  await chrome.key("ArrowRight");
  await chrome.key("Enter");
  await new Promise(r=>setTimeout(r,1600));
  out[w].matches=await chrome.eval(probe);
  out[w].keyboard=await chrome.eval(`({active:document.activeElement.textContent,selected:document.activeElement.getAttribute('aria-selected')})`);
  await chrome.eval("window.scrollTo(0,0); new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))");
  await chrome.shot(root+`/docs/mini-project/phase4/p4.4/fixtures-${w}.png`,{fullPage:true});
  await chrome.key("ArrowRight"); await chrome.key("Enter");
  await new Promise(r=>setTimeout(r,2200));
  out[w].stats=await chrome.eval(probe);
  await chrome.eval("window.scrollTo(0,0); new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))");
  await chrome.shot(root+`/docs/mini-project/phase4/p4.4/stats-${w}.png`,{fullPage:true});
  console.log(w,JSON.stringify(out[w]));
 }
 await chrome.viewport(375,812,1,true);
 await chrome.go("http://127.0.0.1:5174/matches?comp=EPL&season=2026-27&status=completed",1800);
 out.mobileFilters=await chrome.eval(probe);
 await chrome.eval("window.scrollTo(0,0); new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))");
  await chrome.shot(root+"/docs/mini-project/phase4/p4.4/matches-filters-375.png",{fullPage:true});
 await chrome.go("http://127.0.0.1:5174/predict?mode=gameweek&comp=EPL",1800);
 out.mobilePredictions=await chrome.eval(probe);
 await chrome.eval("window.scrollTo(0,0); new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))");
  await chrome.shot(root+"/docs/mini-project/phase4/p4.4/prediction-warnings-375.png",{fullPage:true});
}finally{
 writeFileSync(root+"/data/supervised/phase4/p44/visual_probe_final.json",JSON.stringify(out,null,2));
 await chrome.close();
}
