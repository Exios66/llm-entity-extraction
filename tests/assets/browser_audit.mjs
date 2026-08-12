import { spawn } from "node:child_process";

const CHROME = process.env.CHROME_BIN || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9333;
const SITE_PORT = Number(process.env.SITE_PORT || 8899);

const chrome = spawn(CHROME, ["--headless=new", "--disable-gpu", "--no-sandbox",
  "--remote-debugging-port=" + PORT, "--window-size=1440,1100", "about:blank"],
  { stdio: "ignore" });
const watchdog = setTimeout(() => {
  console.log("AUDIT TIMEOUT — killing chrome");
  chrome.kill("SIGKILL");
  process.exit(2);
}, 150000);

const sleep = (ms) => new Promise(r => setTimeout(r, ms));
await sleep(3000);

async function getTarget() {
  for (let i = 0; i < 20; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/json/list`);
      const ts = await res.json();
      const page = ts.find(t => t.type === "page");
      if (page) return page;
    } catch {}
    await sleep(500);
  }
  throw new Error("no page target");
}

const target = await getTarget();
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });
let msgId = 0;
const pending = new Map();
const events = [];
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) { pending.get(msg.id)(msg); pending.delete(msg.id); }
  else if (msg.method === "Runtime.exceptionThrown") events.push("EXCEPTION: " + (msg.params.exceptionDetails?.exception?.description || msg.params.exceptionDetails?.text || "?").slice(0, 300));
  else if (msg.method === "Runtime.consoleAPICalled" && msg.params.type === "error")
    events.push("CONSOLE.ERROR: " + (msg.params.args || []).map(a => a.value ?? a.description ?? "").join(" ").slice(0, 300));
};
function send(method, params = {}) {
  return new Promise((res) => {
    const id = ++msgId;
    const timer = setTimeout(() => { pending.delete(id); res({ error: "timeout" }); }, 8000);
    pending.set(id, (m) => { clearTimeout(timer); res(m); });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

await send("Runtime.enable");
await send("Page.enable");

const routes = [
  ["/", "index"],
  ["/#/task/contract_entity_extraction", "task-extraction"],
  ["/#/task/subtype_classification", "task-subtype"],
  ["/#/run/42", "run"],
  ["/#/run/42/doc/0", "doc"],
  ["/#/prompts", "prompts"],
  ["/#/benchmarks", "benchmarks"],
];

const results = [];
for (const [route, label] of routes) {
  events.length = 0;
  const nav = await send("Page.navigate", { url: `http://127.0.0.1:${SITE_PORT}${route}` });
  if (nav.error) { results.push({ label, navError: nav.error }); continue; }
  // Wait until the view actually renders (poll for content, up to 15 s) —
  // a fixed sleep races the async view fetch/render, especially on the
  // last route of a long sweep.
  let rendered = false;
  for (let i = 0; i < 30; i++) {
    await sleep(500);
    const probe = await send("Runtime.evaluate", {
      expression: `document.querySelectorAll(".card").length + ":" + (document.getElementById("chart-tip") ? "tip" : "no-tip")`,
      returnByValue: true,
    });
    const probeVal = probe.result?.result?.value || "0:";
    if (parseInt(probeVal, 10) > 0 || route === "/") { rendered = true; break; }
  }
  if (!rendered) { results.push({ label, value: { cards: 0 }, errs: [], notRendered: true }); continue; }
  await sleep(1200);
  const audit = await send("Runtime.evaluate", {
    expression: `(() => {
      const de = document.documentElement;
      const m = document.querySelector(".nav-group-menu");
      const t = document.getElementById("chart-tip");
      return {
        overflowX: de.scrollWidth - window.innerWidth,
        h1: document.querySelector("h1")?.textContent || null,
        charts: document.querySelectorAll(".chart-svg").length,
        dots: document.querySelectorAll("[data-run-id]").length,
        tipHidden: t ? t.hidden : "n/a",
        navMenuDisplay: m ? getComputedStyle(m).display : "n/a",
        tables: document.querySelectorAll("table.data").length,
        bmRows: document.querySelectorAll(".bm-row").length,
        diffLines: document.querySelectorAll(".diff-line").length,
        cards: document.querySelectorAll(".card").length,
        empty: !!document.querySelector(".empty"),
        imgBroken: [...document.images].filter(i => i.complete && i.naturalWidth === 0).length,
        svgDims: (() => { const s = document.querySelector(".chart-svg"); return s ? [s.clientWidth, s.clientHeight] : null; })(),
      };
    })()`,
    returnByValue: true,
  });
  results.push({ label, value: audit.result?.result?.value || {}, errs: [...events] });
}

clearTimeout(watchdog);
ws.close();
chrome.kill();
let fail = 0;
for (const r of results) {
  const v = r.value || {};
  const problems = [];
  if (r.navError) problems.push("navigate:" + r.navError);
  if (r.notRendered) problems.push("view did not render");
  if (r.errs.length) problems.push(r.errs.join(" | "));
  if (v.overflowX > 2) problems.push("overflowX:" + v.overflowX + "px");
  if (!v.cards) problems.push("no cards");
  if (v.empty && v.cards > 1) problems.push("unexpected empty-state");
  if (v.charts && v.svgDims && (v.svgDims[0] < 100 || v.svgDims[1] < 50)) problems.push("svg collapsed " + v.svgDims);
  if (problems.length) { fail = 1; console.log("ISSUE  " + r.label + "  " + problems.join("  ")); }
  else console.log("ok     " + r.label + `  (${v.cards} cards, ${v.charts} charts, ${v.dots} pts, ${v.tables} tables, ${v.bmRows} bm, ${v.diffLines} diff, overflow ${v.overflowX}px, nav-menu ${v.navMenuDisplay}, tip hidden=${v.tipHidden})`);
}
process.exit(fail);
