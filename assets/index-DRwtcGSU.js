(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))a(s);new MutationObserver(s=>{for(const l of s)if(l.type==="childList")for(const d of l.addedNodes)d.tagName==="LINK"&&d.rel==="modulepreload"&&a(d)}).observe(document,{childList:!0,subtree:!0});function n(s){const l={};return s.integrity&&(l.integrity=s.integrity),s.referrerPolicy&&(l.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?l.credentials="include":s.crossOrigin==="anonymous"?l.credentials="omit":l.credentials="same-origin",l}function a(s){if(s.ep)return;s.ep=!0;const l=n(s);fetch(s.href,l)}})();const S=6,v=36,p=0,g=1,b=2,C=-1,be=[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]],L=(e,t)=>e*S+t,ve=e=>[Math.floor(e/S),e%S],we=(()=>{const e=[];for(let t=0;t<v;t++){const[n,a]=ve(t),s=[];for(const[l,d]of be){const u=[];let f=n+l,i=a+d;for(;f>=0&&f<S&&i>=0&&i<S;)u.push(L(f,i)),f+=l,i+=d;s.push(u)}e.push(s)}return e})();function z(){const e=new Array(v).fill(p);return e[L(2,2)]=b,e[L(2,3)]=g,e[L(3,2)]=g,e[L(3,3)]=b,{board:e,toMove:g,cool:new Set,passes:0}}const Q=e=>e===b?g:b;function Y(e,t,n,a){const s=Q(a),l=[];for(const d of we[n]){const u=[];let f=!1;for(const i of d){const w=e[i];if(w===s){u.push(i),t.has(i)||(f=!0);continue}if(w===a){if(u.length&&f)for(const k of u)t.has(k)||l.push(k);break}break}}return l}function _(e,t){const n=[];for(let a=0;a<v;a++)e.board[a]===p&&Y(e.board,e.cool,a,e.toMove).length&&n.push(a);return n.length?n:[C]}function ye(e,t,n){const a=Q(e.toMove);if(t===C)return{board:e.board.slice(),toMove:a,cool:new Set,passes:e.passes+1};const s=Y(e.board,e.cool,t,e.toMove);if(!s.length)throw new Error("illegal move "+t);const l=e.board.slice();l[t]=e.toMove;for(const u of s)l[u]=e.toMove;const d=n==="cooldown"?new Set([t,...s]):new Set;return{board:l,toMove:a,cool:d,passes:0}}const G=e=>e.passes>=2;function R(e){let t=0,n=0;for(const a of e.board)a===g?t++:a===b&&n++;return[t,n]}function V(e){const[t,n]=R(e);return t>n?g:n>t?b:p}function Se(e,t){if(t!=="cooldown")return new Set;const n=new Set,a=new Set(_(e));for(let s=0;s<v;s++)e.board[s]===p&&Y(e.board,new Set,s,e.toMove).length&&!a.has(s)&&n.add(s);return n}function X(e,t,n){const a={kind:e,budget:n,c:Math.SQRT2,wH:0,wMob:1,lambdaC:1,heuristicAware:null},s=t==="classic";switch(e){case"random":return a;case"naive_buro":return{...a,wMob:4.7536};case"cooldown_buro":return{...a,wMob:2.488,lambdaC:.519};case"uct":return{...a,c:s?2.2324:.516};case"uct_pb_naive":return{...a,heuristicAware:!1,c:s?.7462:1.1085,wH:s?2.4157:1.1208};case"uct_pb_cooldown":return{...a,heuristicAware:!0,c:s?.7174:.5412,wH:s?5.0215:8.706}}}const Z=1e4,Ce=850,Me=60,o={variant:"cooldown",opponent:"uct_pb_cooldown",humanColor:g,state:z(),phase:"idle",last:-1,history:[]};let m=0,E=new Array(v).fill(p);const ee=document.getElementById("app"),te=new Worker(new URL("/cooldown-othello-mcts/assets/aiWorker-C_-fDcif.js",import.meta.url),{type:"module"}),r=e=>ee.querySelector("#"+e),oe=[];let $,ne,se,ae,le,ie,P,re,ce,W,B,O,T,D,j,x,H;const q=()=>o.phase!=="idle",M=e=>o.opponent==="human"||e.toMove===o.humanColor,de=e=>{const t=_(e);return t[0]===C?[]:t},ue=()=>o.history.some(e=>M(e.state)&&de(e.state).length>0),I=e=>e===g?"Black":"White",pe="cooldown-othello.logs.v1",fe=()=>Math.random().toString(36).slice(2,10),ke=fe();let h=[],c=null,he=0;function Le(){try{const e=JSON.parse(localStorage.getItem(pe)||"[]");h=Array.isArray(e)?e:[]}catch{h=[]}}function ge(){try{localStorage.setItem(pe,JSON.stringify(h))}catch{}}function Te(){const e=o.opponent!=="human";c={id:fe(),session:ke,started:new Date().toISOString(),ended:null,variant:o.variant,opponent:o.opponent,humanColor:e?o.humanColor:null,aiConfig:e?X(o.opponent,o.variant,Z):null,moves:[],undos:0,result:null,finished:!1}}function Ne(){if(!c||c.finished)return;const e=o.state,[t,n]=R(e);c.ended=new Date().toISOString(),c.finished=!0,c.result={winner:V(e),black:t,white:n,nPlies:c.moves.length},h.push(c),ge(),U()}function U(){if(!W)return;const e=h.length;W.textContent=e?`${e} game${e>1?"s":""} logged`:"no completed games yet",x.disabled=e===0,H.disabled=e===0}async function _e(e){var t;try{if((t=navigator.clipboard)!=null&&t.writeText)return await navigator.clipboard.writeText(e),!0}catch{}try{const n=document.createElement("textarea");n.value=e,n.style.position="fixed",n.style.opacity="0",document.body.appendChild(n),n.focus(),n.select();const a=document.execCommand("copy");return document.body.removeChild(n),a}catch{return!1}}function Ae(e,t){e.dataset.orig||(e.dataset.orig=e.textContent||""),e.textContent=t,setTimeout(()=>{e.textContent=e.dataset.orig||""},1400)}function me(){if(G(o.state)){o.phase="idle",Ne(),N();return}he=performance.now();const e=_(o.state);if(e.length===1&&e[0]===C){o.phase="passing",N();const t=m;setTimeout(()=>{t===m&&F(C)},Ce);return}if(!M(o.state)){o.phase="thinking",N();const t=m,n=o.state,a=X(o.opponent,o.variant,Z);setTimeout(()=>{t===m&&te.postMessage({gen:t,board:n.board,toMove:n.toMove,cool:[...n.cool],passes:n.passes,variant:o.variant,cfg:a})},Me);return}o.phase="idle",N()}function F(e){if(m++,c){const t=Math.round(performance.now()-he);c.moves.push({ply:c.moves.length,player:o.state.toMove,move:e,ms:t})}o.history.push({state:o.state,last:o.last}),o.last=e===C?-1:e,o.state=ye(o.state,e,o.variant),me()}function Be(e){e.gen!==m||o.phase!=="thinking"||F(e.move)}function Oe(e){q()||G(o.state)||!M(o.state)||_(o.state).includes(e)&&F(e)}function K(){if(q()||!ue())return;m++;let e,t=0;for(;o.history.length&&(e=o.history.pop(),t++,!(M(e.state)&&de(e.state).length));)e=void 0;e&&(c&&t&&(c.moves.splice(Math.max(0,c.moves.length-t)),c.undos+=1),o.state=e.state,o.last=e.last,o.phase="idle",E=o.state.board.slice(),N())}function y(){m++,c=null,o.state=z(),o.last=-1,o.history=[],o.phase="idle",E=new Array(v).fill(p),Te(),me()}function xe(e,t,n){t===p&&n!==p?e.animate([{transform:"scale(0)"},{transform:"scale(1)"}],{duration:190,easing:"cubic-bezier(.2,.8,.3,1.3)"}):t!==p&&n!==p&&e.animate([{transform:"rotateY(0deg)"},{transform:"rotateY(90deg)"},{transform:"rotateY(0deg)"}],{duration:300,easing:"ease-in-out"})}function N(){const e=o.state,t=G(e),n=o.phase==="idle"&&!t&&M(e),a=new Set(n?_(e):[]),s=n&&o.variant==="cooldown"?Se(e,o.variant):new Set,[l,d]=R(e);for(let i=0;i<v;i++){const w=oe[i],k=w.firstElementChild,J=E[i],A=e.board[i];J!==A&&xe(k,J,A),k.className="disc"+(A===g?" black":A===b?" white":"")+(e.cool.has(i)?" chilled":""),w.classList.toggle("legal",a.has(i)),w.classList.toggle("blocked",s.has(i)),w.classList.toggle("last",i===o.last)}E=e.board.slice(),se.textContent=String(l),ae.textContent=String(d),le.classList.toggle("active",!t&&e.toMove===g),ie.classList.toggle("active",!t&&e.toMove===b);let u;if(t){const i=V(e);u=i===p?`Draw ${l}–${d}`:`${I(i)} wins ${Math.max(l,d)}–${Math.min(l,d)}`}else o.phase==="thinking"?u="AI is thinking…":o.phase==="passing"?u=`${I(e.toMove)} has no move — passing…`:u=M(e)?"Your move":`${I(e.toMove)} to move`;$.textContent=u,$.classList.toggle("over",t),ne.style.visibility=o.phase==="thinking"?"visible":"hidden",P.classList.toggle("over",t),T.disabled=o.opponent==="human",D.disabled=q()||!ue();const f=o.variant==="cooldown";re.style.display=f?"":"none",ce.querySelectorAll(".cd").forEach(i=>{i.style.display=f?"":"none"})}function Ee(){ee.innerHTML=`
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
    <div class="board" id="board" style="grid-template-columns:repeat(${S},1fr)"></div>
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
  `,P=r("board"),$=r("status"),ne=r("spin"),se=r("scoreB"),ae=r("scoreW"),le=r("sideB"),ie=r("sideW"),re=r("hint"),ce=r("legend"),W=r("logcount"),B=r("variant"),O=r("opp"),T=r("color"),D=r("undo"),j=r("new"),x=r("copylog"),H=r("clearlog"),B.value=o.variant,O.value=o.opponent,T.value=String(o.humanColor);for(let e=0;e<v;e++){const t=document.createElement("button");t.className="cell",t.setAttribute("aria-label",`square ${e}`);const n=document.createElement("span");n.className="disc",t.appendChild(n),t.addEventListener("click",()=>Oe(e)),oe.push(t),P.appendChild(t)}B.onchange=()=>{o.variant=B.value,y()},O.onchange=()=>{o.opponent=O.value,y()},T.onchange=()=>{o.humanColor=parseInt(T.value,10),y()},j.onclick=()=>y(),D.onclick=()=>K(),x.onclick=async()=>{const e=await _e(JSON.stringify(h,null,2));Ae(x,e?"Copied ✓":"Copy failed"),e||console.log(JSON.stringify(h,null,2))},H.onclick=()=>{h.length&&confirm(`Delete all ${h.length} logged game(s)? This cannot be undone.`)&&(h=[],ge(),U())},te.onmessage=e=>Be(e.data),document.addEventListener("keydown",e=>{e.target.tagName!=="SELECT"&&(e.key==="n"?y():e.key==="u"&&K())}),Le(),U()}Ee();y();
