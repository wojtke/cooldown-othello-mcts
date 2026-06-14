(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))i(s);new MutationObserver(s=>{for(const a of s)if(a.type==="childList")for(const r of a.addedNodes)r.tagName==="LINK"&&r.rel==="modulepreload"&&i(r)}).observe(document,{childList:!0,subtree:!0});function n(s){const a={};return s.integrity&&(a.integrity=s.integrity),s.referrerPolicy&&(a.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?a.credentials="include":s.crossOrigin==="anonymous"?a.credentials="omit":a.credentials="same-origin",a}function i(s){if(s.ep)return;s.ep=!0;const a=n(s);fetch(s.href,a)}})();const y=6,b=36,p=0,f=1,g=2,S=-1,ne=[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]],M=(e,t)=>e*y+t,se=e=>[Math.floor(e/y),e%y],ae=(()=>{const e=[];for(let t=0;t<b;t++){const[n,i]=se(t),s=[];for(const[a,r]of ne){const c=[];let u=n+a,l=i+r;for(;u>=0&&u<y&&l>=0&&l<y;)c.push(M(u,l)),u+=a,l+=r;s.push(c)}e.push(s)}return e})();function H(){const e=new Array(b).fill(p);return e[M(2,2)]=g,e[M(2,3)]=f,e[M(3,2)]=f,e[M(3,3)]=g,{board:e,toMove:f,cool:new Set,passes:0}}const U=e=>e===g?f:g;function P(e,t,n,i){const s=U(i),a=[];for(const r of ae[n]){const c=[];let u=!1;for(const l of r){const m=e[l];if(m===s){c.push(l),t.has(l)||(u=!0);continue}if(m===i){if(c.length&&u)for(const k of c)t.has(k)||a.push(k);break}break}}return a}function A(e,t){const n=[];for(let i=0;i<b;i++)e.board[i]===p&&P(e.board,e.cool,i,e.toMove).length&&n.push(i);return n.length?n:[S]}function le(e,t,n){const i=U(e.toMove);if(t===S)return{board:e.board.slice(),toMove:i,cool:new Set,passes:e.passes+1};const s=P(e.board,e.cool,t,e.toMove);if(!s.length)throw new Error("illegal move "+t);const a=e.board.slice();a[t]=e.toMove;for(const c of s)a[c]=e.toMove;const r=n==="cooldown"?new Set([t,...s]):new Set;return{board:a,toMove:i,cool:r,passes:0}}const Y=e=>e.passes>=2;function _(e){let t=0,n=0;for(const i of e.board)i===f?t++:i===g&&n++;return[t,n]}function ie(e){const[t,n]=_(e);return t>n?f:n>t?g:p}function re(e,t){if(t!=="cooldown")return new Set;const n=new Set,i=new Set(A(e));for(let s=0;s<b;s++)e.board[s]===p&&P(e.board,new Set,s,e.toMove).length&&!i.has(s)&&n.add(s);return n}const ce=1400,de=850,pe=60,o={variant:"cooldown",opponent:"mcts",humanColor:f,state:H(),phase:"idle",last:-1,history:[]};let h=0,B=new Array(b).fill(p);const j=document.getElementById("app"),F=new Worker(new URL("/cooldown-othello-mcts/assets/aiWorker-DVmUSQb6.js",import.meta.url),{type:"module"}),d=e=>j.querySelector("#"+e),K=[];let W,V,z,Q,J,X,O,Z,ee,I,N,L,$,D;const q=()=>o.phase!=="idle",w=e=>o.opponent==="human"||e.toMove===o.humanColor,te=e=>{const t=A(e);return t[0]===S?[]:t},T=e=>e===f?"Black":"White";function oe(){if(Y(o.state)){o.phase="idle",C();return}const e=A(o.state);if(e.length===1&&e[0]===S){o.phase="passing",C();const t=h;setTimeout(()=>{t===h&&R(S)},de);return}if(!w(o.state)){o.phase="thinking",C();const t=h,n=o.state;setTimeout(()=>{t===h&&F.postMessage({gen:t,board:n.board,toMove:n.toMove,cool:[...n.cool],passes:n.passes,variant:o.variant,kind:o.opponent,budget:ce})},pe);return}o.phase="idle",C()}function R(e){h++,o.history.push({state:o.state,last:o.last}),o.last=e===S?-1:e,o.state=le(o.state,e,o.variant),oe()}function ue(e){e.gen!==h||o.phase!=="thinking"||R(e.move)}function fe(e){q()||Y(o.state)||!w(o.state)||A(o.state).includes(e)&&R(e)}function G(){if(q())return;h++;let e;for(;o.history.length&&(e=o.history.pop(),!(w(e.state)&&te(e.state).length));)e=void 0;e&&(o.state=e.state,o.last=e.last,o.phase="idle",B=o.state.board.slice(),C())}function v(){h++,o.state=H(),o.last=-1,o.history=[],o.phase="idle",B=new Array(b).fill(p),oe()}function he(e,t,n){t===p&&n!==p?e.animate([{transform:"scale(0)"},{transform:"scale(1)"}],{duration:190,easing:"cubic-bezier(.2,.8,.3,1.3)"}):t!==p&&n!==p&&e.animate([{transform:"rotateY(0deg)"},{transform:"rotateY(90deg)"},{transform:"rotateY(0deg)"}],{duration:300,easing:"ease-in-out"})}function C(){const e=o.state,t=Y(e),n=o.phase==="idle"&&!t&&w(e),i=new Set(n?A(e):[]),s=n&&o.variant==="cooldown"?re(e,o.variant):new Set,[a,r]=_(e);for(let l=0;l<b;l++){const m=K[l],k=m.firstElementChild,x=B[l],E=e.board[l];x!==E&&he(k,x,E),k.className="disc"+(E===f?" black":E===g?" white":"")+(e.cool.has(l)?" chilled":""),m.classList.toggle("legal",i.has(l)),m.classList.toggle("blocked",s.has(l)),m.classList.toggle("last",l===o.last)}B=e.board.slice(),z.textContent=String(a),Q.textContent=String(r),J.classList.toggle("active",!t&&e.toMove===f),X.classList.toggle("active",!t&&e.toMove===g);let c;if(t){const l=ie(e);c=l===p?`Draw ${a}–${r}`:`${T(l)} wins ${Math.max(a,r)}–${Math.min(a,r)}`}else o.phase==="thinking"?c="AI is thinking…":o.phase==="passing"?c=`${T(e.toMove)} has no move — passing…`:c=w(e)?"Your move":`${T(e.toMove)} to move`;W.textContent=c,W.classList.toggle("over",t),V.style.visibility=o.phase==="thinking"?"visible":"hidden",O.classList.toggle("over",t),L.disabled=o.opponent==="human",$.disabled=q()||!o.history.some(l=>w(l.state)&&te(l.state).length>0);const u=o.variant==="cooldown";Z.style.display=u?"":"none",ee.querySelectorAll(".cd").forEach(l=>{l.style.display=u?"":"none"})}function ge(){j.innerHTML=`
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
    <div class="board" id="board" style="grid-template-columns:repeat(${y},1fr)"></div>
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
  `,O=d("board"),W=d("status"),V=d("spin"),z=d("scoreB"),Q=d("scoreW"),J=d("sideB"),X=d("sideW"),Z=d("hint"),ee=d("legend"),I=d("variant"),N=d("opp"),L=d("color"),$=d("undo"),D=d("new"),I.value=o.variant,N.value=o.opponent,L.value=String(o.humanColor);for(let e=0;e<b;e++){const t=document.createElement("button");t.className="cell",t.setAttribute("aria-label",`square ${e}`);const n=document.createElement("span");n.className="disc",t.appendChild(n),t.addEventListener("click",()=>fe(e)),K.push(t),O.appendChild(t)}I.onchange=()=>{o.variant=I.value,v()},N.onchange=()=>{o.opponent=N.value,v()},L.onchange=()=>{o.humanColor=parseInt(L.value,10),v()},D.onclick=()=>v(),$.onclick=()=>G(),F.onmessage=e=>ue(e.data),document.addEventListener("keydown",e=>{e.target.tagName!=="SELECT"&&(e.key==="n"?v():e.key==="u"&&G())})}ge();v();
