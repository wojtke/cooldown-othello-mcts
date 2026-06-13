// Cooldown Othello 6x6 — playable UI (hotseat + light AI), for "getting a feel".
import {
  applyMove, BLACK, cooldownBlocked, counts, EMPTY, initialState, isTerminal,
  legalMoves, N, PASS, State, Variant, WHITE, winner,
} from "./engine";
import { AIKind, chooseMove } from "./ai";

type Opponent = "human" | "random" | "greedy" | "mcts";

interface UI {
  variant: Variant;
  opponent: Opponent;
  humanColor: number; // BLACK or WHITE (only used vs AI)
  state: State;
  busy: boolean;
  last: number;       // last placed square (for highlight)
}

const ui: UI = {
  variant: "cooldown",
  opponent: "mcts",
  humanColor: BLACK,
  state: initialState(),
  busy: false,
  last: -1,
};

const app = document.getElementById("app")!;

function newGame() {
  ui.state = initialState();
  ui.last = -1;
  ui.busy = false;
  render();
  maybeAI();
}

function humanTurn(): boolean {
  return ui.opponent === "human" || ui.state.toMove === ui.humanColor;
}

function step(move: number) {
  ui.last = move === PASS ? -1 : move;
  ui.state = applyMove(ui.state, move, ui.variant);
  render();
}

function maybeAI() {
  if (isTerminal(ui.state) || humanTurn()) return;
  ui.busy = true;
  render();
  // defer so the board paints before the (brief) search blocks
  setTimeout(() => {
    const m = chooseMove(ui.state, ui.variant, ui.opponent as AIKind, 900);
    step(m);
    ui.busy = false;
    // chain: handle forced human pass or consecutive AI turns
    if (!isTerminal(ui.state) && !humanTurn()) maybeAI();
    else autoPassIfForced();
  }, 60);
}

function autoPassIfForced() {
  if (isTerminal(ui.state)) { render(); return; }
  if (humanTurn() && legalMoves(ui.state, ui.variant)[0] === PASS) {
    setTimeout(() => { step(PASS); maybeAI(); }, 500);
  }
}

function onCell(p: number) {
  if (ui.busy || isTerminal(ui.state) || !humanTurn()) return;
  const moves = legalMoves(ui.state, ui.variant);
  if (!moves.includes(p)) return;
  step(p);
  if (!isTerminal(ui.state) && !humanTurn()) maybeAI();
  else autoPassIfForced();
}

function render() {
  const s = ui.state;
  const moves = new Set(humanTurn() && !ui.busy ? legalMoves(s, ui.variant) : []);
  const blocked = ui.variant === "cooldown" ? cooldownBlocked(s, ui.variant) : new Set<number>();
  const [b, w] = counts(s);
  const term = isTerminal(s);

  let status: string;
  if (term) {
    const win = winner(s);
    status = win === EMPTY ? "Draw." : `${win === BLACK ? "Black" : "White"} wins ${Math.max(b, w)}–${Math.min(b, w)}.`;
  } else if (ui.busy) {
    status = "AI thinking…";
  } else if (moves.has(PASS)) {
    status = `${s.toMove === BLACK ? "Black" : "White"} has no move — passing.`;
  } else {
    status = `${s.toMove === BLACK ? "Black" : "White"} to move`;
  }

  app.innerHTML = `
    <h1>Cooldown Othello <span class="sub">6×6</span></h1>
    <div class="controls">
      <label>Rules
        <select id="variant">
          <option value="cooldown"${ui.variant === "cooldown" ? " selected" : ""}>Cooldown</option>
          <option value="classic"${ui.variant === "classic" ? " selected" : ""}>Classic</option>
        </select>
      </label>
      <label>Opponent
        <select id="opp">
          <option value="mcts"${ui.opponent === "mcts" ? " selected" : ""}>AI · MCTS</option>
          <option value="greedy"${ui.opponent === "greedy" ? " selected" : ""}>AI · Greedy</option>
          <option value="random"${ui.opponent === "random" ? " selected" : ""}>AI · Random</option>
          <option value="human"${ui.opponent === "human" ? " selected" : ""}>Human (hotseat)</option>
        </select>
      </label>
      <label>You play
        <select id="color"${ui.opponent === "human" ? " disabled" : ""}>
          <option value="1"${ui.humanColor === BLACK ? " selected" : ""}>Black (first)</option>
          <option value="2"${ui.humanColor === WHITE ? " selected" : ""}>White</option>
        </select>
      </label>
      <button id="new">New game</button>
    </div>
    <div class="scorebar">
      <span class="chip black"></span> ${b}
      <span class="status">${status}</span>
      ${w} <span class="chip white"></span>
    </div>
    <div class="board" style="grid-template-columns:repeat(${N},1fr)"></div>
    ${ui.variant === "cooldown" ? `<p class="hint">Cooldown rule: pieces placed or flipped last turn are
      <b>chilled</b> (ringed) — they can't be flipped back this turn. So after the opponent captures,
      you can't immediately recapture those pieces. Faintly-marked squares would be legal in classic
      Othello but are blocked here.</p>` : ""}
    <p class="footer">Light in-browser AI for play/feel — not the tuned research player.
      <a href="https://github.com/wojtke/cooldown-othello-mcts" target="_blank" rel="noopener">source</a></p>
  `;

  const board = app.querySelector(".board") as HTMLElement;
  for (let p = 0; p < s.board.length; p++) {
    const cell = document.createElement("button");
    cell.className = "cell";
    if (moves.has(p)) cell.classList.add("legal");
    if (blocked.has(p)) cell.classList.add("blocked");
    if (p === ui.last) cell.classList.add("last");
    const v = s.board[p];
    if (v !== EMPTY) {
      const disc = document.createElement("span");
      disc.className = "disc " + (v === BLACK ? "black" : "white");
      if (s.cool.has(p)) disc.classList.add("chilled");
      cell.appendChild(disc);
    }
    cell.addEventListener("click", () => onCell(p));
    board.appendChild(cell);
  }

  (app.querySelector("#variant") as HTMLSelectElement).onchange = (e) => {
    ui.variant = (e.target as HTMLSelectElement).value as Variant; newGame();
  };
  (app.querySelector("#opp") as HTMLSelectElement).onchange = (e) => {
    ui.opponent = (e.target as HTMLSelectElement).value as Opponent; newGame();
  };
  (app.querySelector("#color") as HTMLSelectElement).onchange = (e) => {
    ui.humanColor = parseInt((e.target as HTMLSelectElement).value, 10); newGame();
  };
  (app.querySelector("#new") as HTMLButtonElement).onclick = newGame;
}

newGame();
