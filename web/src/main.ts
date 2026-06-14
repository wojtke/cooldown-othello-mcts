// Cooldown Othello 6x6 — playable UI (hotseat + light AI in a Web Worker).
import {
  applyMove, BLACK, cooldownBlocked, counts, EMPTY, initialState, isTerminal,
  legalMoves, N, NN, PASS, State, Variant, WHITE, winner,
} from "./engine";
import { AIKind } from "./ai";

type Opponent = "human" | "random" | "greedy" | "mcts";
type Phase = "idle" | "thinking" | "passing";

const AI_BUDGET = 1400;   // off-thread, so we can afford a stronger search
const PASS_MS = 850;      // pause so a forced pass is visible
const THINK_MS = 60;      // let "thinking…" paint before the worker starts

interface Snapshot { state: State; last: number; }

const ui = {
  variant: "cooldown" as Variant,
  opponent: "mcts" as Opponent,
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
let elStatus: HTMLElement, elSpin: HTMLElement, elScoreB: HTMLElement, elScoreW: HTMLElement,
  elSideB: HTMLElement, elSideW: HTMLElement, elBoard: HTMLElement, elHint: HTMLElement, elLegend: HTMLElement,
  selVariant: HTMLSelectElement, selOpp: HTMLSelectElement, selColor: HTMLSelectElement,
  btnUndo: HTMLButtonElement, btnNew: HTMLButtonElement;

const busy = () => ui.phase !== "idle";
const humanTurnFor = (s: State) => ui.opponent === "human" || s.toMove === ui.humanColor;
const realMoves = (s: State) => { const m = legalMoves(s, ui.variant); return m[0] === PASS ? [] : m; };
const name = (p: number) => (p === BLACK ? "Black" : "White");

// ---------------------------------------------------------------------------
// Turn scheduler — one place that decides what happens after every position.
// Handles human turns, AI turns, single forced passes, and double-pass endings.
// ---------------------------------------------------------------------------
function advance() {
  if (isTerminal(ui.state)) { ui.phase = "idle"; render(); return; }
  const moves = legalMoves(ui.state, ui.variant);

  if (moves.length === 1 && moves[0] === PASS) {        // current side cannot move
    ui.phase = "passing"; render();
    const myGen = gen;
    setTimeout(() => { if (myGen === gen) doMove(PASS); }, PASS_MS);
    return;
  }
  if (!humanTurnFor(ui.state)) {                          // AI to move → ask the worker
    ui.phase = "thinking"; render();
    const myGen = gen, s = ui.state;
    setTimeout(() => {
      if (myGen !== gen) return;
      worker.postMessage({
        gen: myGen, board: s.board, toMove: s.toMove, cool: [...s.cool], passes: s.passes,
        variant: ui.variant, kind: ui.opponent as AIKind, budget: AI_BUDGET,
      });
    }, THINK_MS);
    return;
  }
  ui.phase = "idle"; render();                           // human with real moves → wait for a click
}

function doMove(m: number) {
  gen++;
  ui.history.push({ state: ui.state, last: ui.last });
  ui.last = m === PASS ? -1 : m;
  ui.state = applyMove(ui.state, m, ui.variant);
  advance();
}

function onAIResult(msg: { gen: number; move: number }) {
  if (msg.gen !== gen || ui.phase !== "thinking") return;  // stale (new game / undo happened)
  doMove(msg.move);
}

function onCell(p: number) {
  if (busy() || isTerminal(ui.state) || !humanTurnFor(ui.state)) return;
  if (!legalMoves(ui.state, ui.variant).includes(p)) return;
  doMove(p);
}

function undo() {
  if (busy()) return;
  gen++;                                                  // cancel anything in flight
  let snap: Snapshot | undefined;
  while (ui.history.length) {                             // back up to the human's last real choice
    snap = ui.history.pop()!;
    if (humanTurnFor(snap.state) && realMoves(snap.state).length) break;
    snap = undefined;
  }
  if (!snap) return;
  ui.state = snap.state; ui.last = snap.last; ui.phase = "idle";
  displayed = ui.state.board.slice();                     // revert without flip animations
  render();
}

function newGame() {
  gen++;
  ui.state = initialState();
  ui.last = -1;
  ui.history = [];
  ui.phase = "idle";
  displayed = new Array(NN).fill(EMPTY);                  // opening pieces animate in
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
  elSpin.style.visibility = ui.phase === "thinking" ? "visible" : "hidden";
  elBoard.classList.toggle("over", term);

  selColor.disabled = ui.opponent === "human";
  btnUndo.disabled = busy() || !ui.history.some(h => humanTurnFor(h.state) && realMoves(h.state).length > 0);

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
          <option value="mcts">AI · MCTS</option>
          <option value="greedy">AI · Greedy</option>
          <option value="random">AI · Random</option>
          <option value="human">Human (hotseat)</option>
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
    <p class="footer">Light in-browser AI for play/feel — not the tuned research player.
      <a href="https://github.com/wojtke/cooldown-othello-mcts" target="_blank" rel="noopener">source</a></p>
  `;
  elBoard = byId("board"); elStatus = byId("status"); elSpin = byId("spin");
  elScoreB = byId("scoreB"); elScoreW = byId("scoreW"); elSideB = byId("sideB"); elSideW = byId("sideW");
  elHint = byId("hint"); elLegend = byId("legend");
  selVariant = byId("variant"); selOpp = byId("opp"); selColor = byId("color");
  btnUndo = byId("undo"); btnNew = byId("new");

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
  worker.onmessage = (e: MessageEvent) => onAIResult(e.data);
  document.addEventListener("keydown", (e) => {
    if ((e.target as HTMLElement).tagName === "SELECT") return;
    if (e.key === "n") newGame();
    else if (e.key === "u") undo();
  });
}

build();
newGame();
