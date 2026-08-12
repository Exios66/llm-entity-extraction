const fs = require("fs");
const path = require("path");
const ROOT = process.cwd(); // run from the repo root
const read = (rel) => JSON.parse(fs.readFileSync(path.join(ROOT, rel), "utf8"));

const meta = read("docs/data/meta.json");
const index = read("docs/data/index.json");
const trends = read("docs/data/trends.json");
const prompts = read("docs/data/prompts.json");

const els = {};
function makeEl(id) {
  return {
    id, _html: "", value: "", textContent: "", hidden: false,
    dataset: {},
    addEventListener() {}, style: {}, classList: { toggle() {}, add() {}, remove() {} },
    set innerHTML(v) { this._html = String(v); },
    get innerHTML() { return this._html; },
    querySelector: (sel) => {
    const id = String(sel).replace(/^#/, "");
    return (els[id] ||= makeEl(id));
  },
  querySelectorAll: () => [],
    appendChild() {}, insertBefore() {},
  };
}
global.document = {
  documentElement: { dataset: {} },
  createTextNode() { return {}; },
  addEventListener() {},
  getElementById: (id) => (els[id] ||= makeEl(id)),
  querySelector: (sel) => (els[String(sel).replace(/^#/, "")] ||= makeEl(String(sel).replace(/^#/, ""))),
  querySelectorAll: () => [],
  createElement: () => makeEl("dyn"),
};
global.window = { location: { hash: "" }, addEventListener() {}, scrollTo() {} };
global.localStorage = { getItem: () => null, setItem() {} };
global.fetch = async (url) => ({ ok: true, json: async () => {
  if (url.includes("meta.json")) return meta;
  if (url.includes("index.json")) return index;
  if (url.includes("trends.json")) return trends;
  if (url.includes("prompts.json")) return prompts;
  if (url.includes("benchmarks.json")) return JSON.parse(fs.readFileSync(path.join(ROOT, "docs/data/benchmarks.json"), "utf8"));
  if (url.includes("memos.json")) return JSON.parse(fs.readFileSync(path.join(ROOT, "docs/data/memos.json"), "utf8"));
  const m = url.match(/runs\/(\d+)\.json/);
  if (m) return read(`docs/data/runs/${m[1].padStart(3, "0")}.json`);
  throw new Error("unexpected fetch " + url);
}});

const src = fs.readFileSync(path.join(ROOT, "docs/assets/site.js"), "utf8")
  .replace('document.addEventListener("DOMContentLoaded", boot);', "");
const api = new Function(src + "; return {route, renderIndex, renderGroup, renderRun, renderPrompts, renderDoc, renderBenchmarks, renderMemos, boot, state, parseHash};")();
const state = api.state;

(async () => {
  const failures = [];
  const views = [];
  // 1) index
  try { await api.renderIndex(); views.push("index OK"); }
  catch (e) { failures.push("index: " + e.message); }
  // 2) every task group
  for (const task of Object.keys(meta.tasks)) {
    try { await api.renderGroup("task", task); views.push(`task/${task} OK`); }
    catch (e) { failures.push(`task/${task}: ${e.message}`); }
  }
  // 2.5) charts must be interactive: every task view's charts carry
  //      data-run-id hooks (hover tooltip + click-to-run navigation)
  for (const task of Object.keys(meta.tasks)) {
    await api.renderGroup("task", task);
    const html = els.view?._html || "";
    // tasks with trend series must render interactive chart points
    if ((trends.tasks || {})[task] && (trends.tasks[task] || []).length) {
      const hooks = (html.match(/data-run-id=/g) || []).length;
      if (!hooks) failures.push(`task/${task}: no interactive chart points`);
    }
  }
  // 3) prompt + model groups
  const somePrompt = index.find((r) => r.prompts && r.prompts !== "—")?.prompts;
  const someModel = index[0]?.model;
  try { await api.renderGroup("prompt", somePrompt); views.push("prompt OK"); } catch (e) { failures.push("prompt: " + e.message); }
  try { await api.renderGroup("model", someModel); views.push("model OK"); } catch (e) { failures.push("model: " + e.message); }
  // 4) every run detail
  for (const r of index) {
    try { await api.renderRun(r.id); }
    catch (e) { failures.push(`run/${r.id} (${r.experiment_name}): ${e.message}`); }
  }
  views.push(`runs ${index.length} OK`);
  // 5) every document trace (first 3 docs per run to keep it fast)
  let docs = 0;
  for (const r of index) {
    const run = read(`docs/data/runs/${String(r.id).padStart(3, "0")}.json`);
    const n = Math.min(3, (run.results || []).length);
    for (let i = 0; i < n; i++) {
      try { await api.renderDoc(r.id, i); docs++; }
      catch (e) { failures.push(`doc/${r.id}/${i}: ${e.message}`); }
    }
  }
  views.push(`docs ${docs} OK`);
  // 6) prompts diff view
  try { await api.renderPrompts(); views.push("prompts OK"); } catch (e) { failures.push("prompts: " + e.message); }
  try { await api.renderBenchmarks(); views.push("benchmarks OK"); } catch (e) { failures.push("benchmarks: " + e.message); }
  try { await api.renderMemos(); views.push("memos OK"); } catch (e) { failures.push("memos: " + e.message); }

  console.log(views.join(" | "));
  if (failures.length) { console.log("FAILURES:"); failures.forEach((f) => console.log("  - " + f)); process.exit(1); }
  console.log("ALL VIEWS RENDER CLEANLY");
})();
