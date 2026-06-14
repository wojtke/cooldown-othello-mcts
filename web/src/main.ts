// Cooldown Othello 6x6 — playable UI (hotseat + light AI in a Web Worker).
import {
  applyMove, BLACK, cooldownBlocked, counts, EMPTY, initialState, isTerminal,
  legalMoves, N, NN, PASS, State, Variant, WHITE, winner,
} from "./engine";
import { AIKind, configFor, isMCTS } from "./ai";

type Opponent = AIKind | "human";
type Phase = "idle" | "thinking" | "passing";

const AI_BUDGET = 10000;  // same as the experiments; the worker keeps it off-thread
const PASS_MS = 850;      // pause so a forced pass is visible
const THINK_MS = 60;      // let "thinking…" paint before the worker starts

interface Snapshot { state: State; last: number; }

const ui = {
  variant: "cooldown" as Variant,
  opponent: "uct_pb_cooldown" as Opponent,
  humanColor: BLACK,
  state: initialState(),
  phase: "idle" as Phase,
  last: -1,
  history: [] as Snapshot[],
};

let gen = 0;                                       // turn token; bump to cancel in-flight async work
let displayed: number[] = new Array(NN).fill(EMPTY); // board the DOM currently shows (for diff/animation)

const app = document.getElementById("app")!;
const worker = new Worker(new URL("./aiWorker.ts", import.meta.url), { type: "module" });
const byId = <T extends HTMLElement>(id: string) => app.querySelector("#" + id) as T;

// cached DOM refs (set in build())
const cells: HTMLButtonElement[] = [];
let elStatus: HTMLElement, elSpin: HTMLElement, elProg: HTMLElement, elProgBar: HTMLElement,
  elScoreB: HTMLElement, elScoreW: HTMLElement, elSideB: HTMLElement, elSideW: HTMLElement,
  elBoard: HTMLElement, elHint: HTMLElement, elLegend: HTMLElement, elLogCount: HTMLElement,
  selVariant: HTMLSelectElement, selOpp: HTMLSelectElement, selColor: HTMLSelectElement,
  btnUndo: HTMLButtonElement, btnNew: HTMLButtonElement,
  btnCopy: HTMLButtonElement, btnClear: HTMLButtonElement;

const busy = () => ui.phase !== "idle";
const humanTurnFor = (s: State) => ui.opponent === "human" || s.toMove === ui.humanColor;
const realMoves = (s: State) => { const m = legalMoves(s, ui.variant); return m[0] === PASS ? [] : m; };
const hasUndoTarget = () => ui.history.some(h => humanTurnFor(h.state) && realMoves(h.state).length > 0);
const name = (p: number) => (p === BLACK ? "Black" : "White");

// ---------------------------------------------------------------------------
// Game logging (for the human–computer study). Completed games accumulate in
// localStorage and are exported via the "Copy game logs" button — never shown
// inline. Each move records its decision time in ms (board-shown → move made).
// ---------------------------------------------------------------------------
const LOG_KEY = "cooldown-othello.logs.v1";
const rid = () => Math.random().toString(36).slice(2, 10);
const SESSION = rid();

interface MoveLog { ply: number; player: number; move: number; ms: number; }
interface GameLog {
  id: string; session: string; started: string; ended: string | null;
  variant: Variant; opponent: Opponent; humanColor: number | null;
  aiConfig: ReturnType<typeof configFor> | null;
  moves: MoveLog[]; undos: number;
  result: { winner: number; black: number; white: number; nPlies: number } | null;
  finished: boolean;
}

let logs: GameLog[] = [];
let currentLog: GameLog | null = null;
let turnStart = 0;

function loadLogs() {
  try { const a = JSON.parse(localStorage.getItem(LOG_KEY) || "[]"); logs = Array.isArray(a) ? a : []; }
  catch { logs = []; }
}
function saveLogs() { try { localStorage.setItem(LOG_KEY, JSON.stringify(logs)); } catch { /* quota / private mode */ } }

function startGameLog() {
  const ai = ui.opponent !== "human";
  currentLog = {
    id: rid(), session: SESSION, started: new Date().toISOString(), ended: null,
    variant: ui.variant, opponent: ui.opponent,
    humanColor: ai ? ui.humanColor : null,
    aiConfig: ai ? configFor(ui.opponent as AIKind, ui.variant, AI_BUDGET) : null,
    moves: [], undos: 0, result: null, finished: false,
  };
}
function finishGameLog() {
  if (!currentLog || currentLog.finished) return;
  const s = ui.state; const [b, w] = counts(s);
  currentLog.ended = new Date().toISOString();
  currentLog.finished = true;
  currentLog.result = { winner: winner(s), black: b, white: w, nPlies: currentLog.moves.length };
  logs.push(currentLog);
  saveLogs();
  updateLogBar();
}
function updateLogBar() {
  if (!elLogCount) return;
  const n = logs.length;
  elLogCount.textContent = n ? `${n} game${n > 1 ? "s" : ""} logged` : "no completed games yet";
  btnCopy.disabled = n === 0;
  btnClear.disabled = n === 0;
}

async function copyText(text: string): Promise<boolean> {
  try { if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(text); return true; } } catch { /* fall through */ }
  try {
    const ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.focus(); ta.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    return ok;
  } catch { return false; }
}
function flash(btn: HTMLButtonElement, text: string) {
  if (!btn.dataset.orig) btn.dataset.orig = btn.textContent || "";
  btn.textContent = text;
  setTimeout(() => { btn.textContent = btn.dataset.orig || ""; }, 1400);
}

// ---------------------------------------------------------------------------
// Turn scheduler — one place that decides what happens after every position.
// Handles human turns, AI turns, single forced passes, and double-pass endings.
// ---------------------------------------------------------------------------
function advance() {
  if (isTerminal(ui.state)) { ui.phase = "idle"; finishGameLog(); render(); return; }
  turnStart = performance.now();
  const moves = legalMoves(ui.state, ui.variant);

  if (moves.length === 1 && moves[0] === PASS) {        // current side cannot move
    ui.phase = "passing"; render();
    const myGen = gen;
    setTimeout(() => { if (myGen === gen) doMove(PASS); }, PASS_MS);
    return;
  }
  if (!humanTurnFor(ui.state)) {                          // AI to move → ask the worker
    ui.phase = "thinking";
    if (isMCTS(ui.opponent as AIKind)) elProgBar.style.width = "0%";
    render();
    const myGen = gen, s = ui.state;
    const cfg = configFor(ui.opponent as AIKind, ui.variant, AI_BUDGET);
    setTimeout(() => {
      if (myGen !== gen) return;
      worker.postMessage({
        gen: myGen, board: s.board, toMove: s.toMove, cool: [...s.cool], passes: s.passes,
        variant: ui.variant, cfg,
      });
    }, THINK_MS);
    return;
  }
  ui.phase = "idle"; render();                           // human with real moves → wait for a click
}

function doMove(m: number) {
  gen++;
  if (currentLog) {
    const ms = Math.round(performance.now() - turnStart);
    currentLog.moves.push({ ply: currentLog.moves.length, player: ui.state.toMove, move: m, ms });
  }
  ui.history.push({ state: ui.state, last: ui.last });
  ui.last = m === PASS ? -1 : m;
  ui.state = applyMove(ui.state, m, ui.variant);
  advance();
}

function onAIResult(msg: { gen: number; move: number }) {
  if (msg.gen !== gen || ui.phase !== "thinking") return;  // stale (new game / undo happened)
  doMove(msg.move);
}

function onAIProgress(msg: { gen: number; frac: number }) {
  if (msg.gen !== gen || ui.phase !== "thinking") return;
  elProgBar.style.width = (msg.frac * 100).toFixed(0) + "%";
}

function onCell(p: number) {
  if (busy() || isTerminal(ui.state) || !humanTurnFor(ui.state)) return;
  if (!legalMoves(ui.state, ui.variant).includes(p)) return;
  doMove(p);
}

function undo() {
  if (busy() || !hasUndoTarget()) return;
  gen++;                                                  // cancel anything in flight
  let snap: Snapshot | undefined, popped = 0;
  while (ui.history.length) {                             // back up to the human's last real choice
    snap = ui.history.pop()!; popped++;
    if (humanTurnFor(snap.state) && realMoves(snap.state).length) break;
    snap = undefined;
  }
  if (!snap) return;
  if (currentLog && popped) {                             // keep the log in sync with the board
    currentLog.moves.splice(Math.max(0, currentLog.moves.length - popped));
    currentLog.undos += 1;
  }
  ui.state = snap.state; ui.last = snap.last; ui.phase = "idle";
  displayed = ui.state.board.slice();                     // revert without flip animations
  render();
}

function newGame() {
  gen++;
  currentLog = null;                                      // discard unfinished game (only completed are logged)
  ui.state = initialState();
  ui.last = -1;
  ui.history = [];
  ui.phase = "idle";
  displayed = new Array(NN).fill(EMPTY);                  // opening pieces animate in
  startGameLog();
  advance();
}

// ---------------------------------------------------------------------------
// Rendering — update the persistent DOM in place (no innerHTML churn).
// ---------------------------------------------------------------------------
function animateDisc(disc: HTMLElement, oldV: number, newV: number) {
  if (oldV === EMPTY && newV !== EMPTY) {
    disc.animate([{ transform: "scale(0)" }, { transform: "scale(1)" }],
      { duration: 190, easing: "cubic-bezier(.2,.8,.3,1.3)" });
  } else if (oldV !== EMPTY && newV !== EMPTY) {          // captured → coin flip
    disc.animate([{ transform: "rotateY(0deg)" }, { transform: "rotateY(90deg)" }, { transform: "rotateY(0deg)" }],
      { duration: 300, easing: "ease-in-out" });
  }
}

function render() {
  const s = ui.state, term = isTerminal(s);
  const interactive = ui.phase === "idle" && !term && humanTurnFor(s);
  const legal = new Set(interactive ? legalMoves(s, ui.variant) : []);
  const blocked = interactive && ui.variant === "cooldown" ? cooldownBlocked(s, ui.variant) : new Set<number>();
  const [b, w] = counts(s);

  for (let p = 0; p < NN; p++) {
    const cell = cells[p], disc = cell.firstElementChild as HTMLElement;
    const oldV = displayed[p], newV = s.board[p];
    if (oldV !== newV) animateDisc(disc, oldV, newV);
    disc.className = "disc" + (newV === BLACK ? " black" : newV === WHITE ? " white" : "")
      + (s.cool.has(p) ? " chilled" : "");
    cell.classList.toggle("legal", legal.has(p));
    cell.classList.toggle("blocked", blocked.has(p));
    cell.classList.toggle("last", p === ui.last);
  }
  displayed = s.board.slice();

  elScoreB.textContent = String(b); elScoreW.textContent = String(w);
  elSideB.classList.toggle("active", !term && s.toMove === BLACK);
  elSideW.classList.toggle("active", !term && s.toMove === WHITE);

  let status: string;
  if (term) {
    const win = winner(s);
    status = win === EMPTY ? `Draw ${b}–${w}` : `${name(win)} wins ${Math.max(b, w)}–${Math.min(b, w)}`;
  } else if (ui.phase === "thinking") status = "AI is thinking…";
  else if (ui.phase === "passing") status = `${name(s.toMove)} has no move — passing…`;
  else status = humanTurnFor(s) ? "Your move" : `${name(s.toMove)} to move`;
  elStatus.textContent = status;
  elStatus.classList.toggle("over", term);
  const thinkingMCTS = ui.phase === "thinking" && isMCTS(ui.opponent as AIKind);
  elSpin.style.visibility = (ui.phase === "thinking" && !thinkingMCTS) ? "visible" : "hidden";
  elProg.classList.toggle("show", thinkingMCTS);
  elBoard.classList.toggle("over", term);

  selColor.disabled = ui.opponent === "human";
  btnUndo.disabled = busy() || !hasUndoTarget();

  const cd = ui.variant === "cooldown";
  elHint.style.display = cd ? "" : "none";
  elLegend.querySelectorAll<HTMLElement>(".cd").forEach(el => { el.style.display = cd ? "" : "none"; });
}

// ---------------------------------------------------------------------------
// One-time DOM build + listener wiring.
// ---------------------------------------------------------------------------
function build() {
  app.innerHTML = `
    <h1>Cooldown Othello <span class="sub">6×6</span></h1>
    <div class="controls">
      <label>Rules
        <select id="variant">
          <option value="cooldown">Cooldown</option>
          <option value="classic">Classic</option>
        </select>
      </label>
      <label>Opponent
        <select id="opp">
          <optgroup label="AI (weak → strong)">
            <option value="random">Random</option>
            <option value="naive_buro">Naive-Buro</option>
            <option value="cooldown_buro">Cooldown-Buro</option>
            <option value="uct">UCT</option>
            <option value="uct_pb_naive">UCT-PB-naive</option>
            <option value="uct_pb_cooldown">UCT-PB-cooldown ★</option>
          </optgroup>
          <optgroup label="Human">
            <option value="human">Hotseat</option>
          </optgroup>
        </select>
      </label>
      <label>You play
        <select id="color">
          <option value="1">Black (first)</option>
          <option value="2">White</option>
        </select>
      </label>
      <div class="btns">
        <button id="undo" title="Take back your last move (u)">Undo</button>
        <button id="new" title="New game (n)">New game</button>
      </div>
    </div>
    <div class="scorebar">
      <span class="side" id="sideB"><span class="chip black"></span><b id="scoreB">2</b></span>
      <span class="status-wrap"><span class="spinner" id="spin"></span><span class="status" id="status"></span></span>
      <span class="side" id="sideW"><b id="scoreW">2</b><span class="chip white"></span></span>
    </div>
    <div class="progress" id="prog"><div class="bar" id="progbar"></div></div>
    <div class="board" id="board" style="grid-template-columns:repeat(${N},1fr)"></div>
    <div class="legend" id="legend">
      <span class="lg"><i class="m-legal"></i>legal move</span>
      <span class="lg cd"><i class="m-chill"></i>chilled (protected 1 turn)</span>
      <span class="lg cd"><i class="m-block"></i>blocked by cooldown</span>
    </div>
    <p class="hint" id="hint"><b>Cooldown rule:</b> pieces placed or flipped last turn are
      <span class="kw">chilled</span> (cyan ring) and can't be flipped back this turn — so you can't
      immediately recapture what was just taken. A faint dashed ring marks a square that would be legal
      in classic Othello but is blocked here.</p>
    <p class="footer">In-browser ports of the six experiment players with their tuned configs;
      MCTS players search 10&thinsp;000 simulations/move (so UCT-PB-cooldown is the research player).
      <a href="https://github.com/wojtke/cooldown-othello-mcts" target="_blank" rel="noopener">source</a></p>
    <div class="logbar">
      <button id="copylog" title="Copy all completed games as JSON to the clipboard">Copy game logs</button>
      <button id="clearlog" class="ghost" title="Delete stored game logs">Clear</button>
      <span class="logcount" id="logcount"></span>
    </div>
  `;
  elBoard = byId("board"); elStatus = byId("status"); elSpin = byId("spin");
  elProg = byId("prog"); elProgBar = byId("progbar");
  elScoreB = byId("scoreB"); elScoreW = byId("scoreW"); elSideB = byId("sideB"); elSideW = byId("sideW");
  elHint = byId("hint"); elLegend = byId("legend"); elLogCount = byId("logcount");
  selVariant = byId("variant"); selOpp = byId("opp"); selColor = byId("color");
  btnUndo = byId("undo"); btnNew = byId("new");
  btnCopy = byId("copylog"); btnClear = byId("clearlog");

  selVariant.value = ui.variant; selOpp.value = ui.opponent; selColor.value = String(ui.humanColor);

  for (let p = 0; p < NN; p++) {
    const cell = document.createElement("button");
    cell.className = "cell"; cell.setAttribute("aria-label", `square ${p}`);
    const disc = document.createElement("span"); disc.className = "disc";
    cell.appendChild(disc);
    cell.addEventListener("click", () => onCell(p));
    cells.push(cell); elBoard.appendChild(cell);
  }

  selVariant.onchange = () => { ui.variant = selVariant.value as Variant; newGame(); };
  selOpp.onchange = () => { ui.opponent = selOpp.value as Opponent; newGame(); };
  selColor.onchange = () => { ui.humanColor = parseInt(selColor.value, 10); newGame(); };
  btnNew.onclick = () => newGame();
  btnUndo.onclick = () => undo();
  btnCopy.onclick = async () => {
    const ok = await copyText(JSON.stringify(logs, null, 2));
    flash(btnCopy, ok ? "Copied ✓" : "Copy failed");
    if (!ok) console.log(JSON.stringify(logs, null, 2));   // fallback: grab it from the console
  };
  btnClear.onclick = () => {
    if (logs.length && confirm(`Delete all ${logs.length} logged game(s)? This cannot be undone.`)) {
      logs = []; saveLogs(); updateLogBar();
    }
  };
  worker.onmessage = (e: MessageEvent) => {
    const m = e.data;
    if (m.type === "progress") onAIProgress(m); else onAIResult(m);
  };
  document.addEventListener("keydown", (e) => {
    if ((e.target as HTMLElement).tagName === "SELECT") return;
    if (e.key === "n") newGame();
    else if (e.key === "u") undo();
  });

  loadLogs();
  updateLogBar();
}

build();
newGame();
