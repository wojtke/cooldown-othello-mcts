(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const s of document.querySelectorAll('link[rel="modulepreload"]'))a(s);new MutationObserver(s=>{for(const l of s)if(l.type==="childList")for(const d of l.addedNodes)d.tagName==="LINK"&&d.rel==="modulepreload"&&a(d)}).observe(document,{childList:!0,subtree:!0});function n(s){const l={};return s.integrity&&(l.integrity=s.integrity),s.referrerPolicy&&(l.referrerPolicy=s.referrerPolicy),s.crossOrigin==="use-credentials"?l.credentials="include":s.crossOrigin==="anonymous"?l.credentials="omit":l.credentials="same-origin",l}function a(s){if(s.ep)return;s.ep=!0;const l=n(s);fetch(s.href,l)}})();const C=6,w=36,f=0,m=1,v=2,M=-1,Se=[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]],L=(e,t)=>e*C+t,Ce=e=>[Math.floor(e/C),e%C],Me=(()=>{const e=[];for(let t=0;t<w;t++){const[n,a]=Ce(t),s=[];for(const[l,d]of Se){const p=[];let g=n+l,u=a+d;for(;g>=0&&g<C&&u>=0&&u<C;)p.push(L(g,u)),g+=l,u+=d;s.push(p)}e.push(s)}return e})();function V(){const e=new Array(w).fill(f);return e[L(2,2)]=v,e[L(2,3)]=m,e[L(3,2)]=m,e[L(3,3)]=v,{board:e,toMove:m,cool:new Set,passes:0}}const X=e=>e===v?m:v;function Y(e,t,n,a){const s=X(a),l=[];for(const d of Me[n]){const p=[];let g=!1;for(const u of d){const r=e[u];if(r===s){p.push(u),t.has(u)||(g=!0);continue}if(r===a){if(p.length&&g)for(const y of p)t.has(y)||l.push(y);break}break}}return l}function A(e,t){const n=[];for(let a=0;a<w;a++)e.board[a]===f&&Y(e.board,e.cool,a,e.toMove).length&&n.push(a);return n.length?n:[M]}function ke(e,t,n){const a=X(e.toMove);if(t===M)return{board:e.board.slice(),toMove:a,cool:new Set,passes:e.passes+1};const s=Y(e.board,e.cool,t,e.toMove);if(!s.length)throw new Error("illegal move "+t);const l=e.board.slice();l[t]=e.toMove;for(const p of s)l[p]=e.toMove;const d=n==="cooldown"?new Set([t,...s]):new Set;return{board:l,toMove:a,cool:d,passes:0}}const G=e=>e.passes>=2;function R(e){let t=0,n=0;for(const a of e.board)a===m?t++:a===v&&n++;return[t,n]}function Z(e){const[t,n]=R(e);return t>n?m:n>t?v:f}function Le(e,t){if(t!=="cooldown")return new Set;const n=new Set,a=new Set(A(e));for(let s=0;s<w;s++)e.board[s]===f&&Y(e.board,new Set,s,e.toMove).length&&!a.has(s)&&n.add(s);return n}const ee=e=>e==="uct"||e==="uct_pb_naive"||e==="uct_pb_cooldown";function te(e,t,n){const a={kind:e,budget:n,c:Math.SQRT2,wH:0,wMob:1,lambdaC:1,heuristicAware:null},s=t==="classic";switch(e){case"random":return a;case"naive_buro":return{...a,wMob:4.7536};case"cooldown_buro":return{...a,wMob:2.488,lambdaC:.519};case"uct":return{...a,c:s?2.2324:.516};case"uct_pb_naive":return{...a,heuristicAware:!1,c:s?.7462:1.1085,wH:s?2.4157:1.1208};case"uct_pb_cooldown":return{...a,heuristicAware:!0,c:s?.7174:.5412,wH:s?5.0215:8.706}}}const oe=1e4,Te=850,_e=60,o={variant:"cooldown",opponent:"uct_pb_cooldown",humanColor:m,state:V(),phase:"idle",last:-1,history:[]};let b=0,E=new Array(w).fill(f);const ne=document.getElementById("app"),se=new Worker(new URL("/cooldown-othello-mcts/assets/aiWorker-BdrT33Ei.js",import.meta.url),{type:"module"}),i=e=>ne.querySelector("#"+e),ae=[];let P,le,ie,q,re,ce,de,pe,$,ue,fe,W,N,O,T,H,z,x,U;const F=()=>o.phase!=="idle",k=e=>o.opponent==="human"||e.toMove===o.humanColor,ge=e=>{const t=A(e);return t[0]===M?[]:t},he=()=>o.history.some(e=>k(e.state)&&ge(e.state).length>0),I=e=>e===m?"Black":"White",me="cooldown-othello.logs.v1",be=()=>Math.random().toString(36).slice(2,10),Ae=be();let h=[],c=null,ve=0;function Be(){try{const e=JSON.parse(localStorage.getItem(me)||"[]");h=Array.isArray(e)?e:[]}catch{h=[]}}function we(){try{localStorage.setItem(me,JSON.stringify(h))}catch{}}function Ne(){const e=o.opponent!=="human";c={id:be(),session:Ae,started:new Date().toISOString(),ended:null,variant:o.variant,opponent:o.opponent,humanColor:e?o.humanColor:null,aiConfig:e?te(o.opponent,o.variant,oe):null,moves:[],undos:0,result:null,finished:!1}}function Oe(){if(!c||c.finished)return;const e=o.state,[t,n]=R(e);c.ended=new Date().toISOString(),c.finished=!0,c.result={winner:Z(e),black:t,white:n,nPlies:c.moves.length},h.push(c),we(),D()}function D(){if(!W)return;const e=h.length;W.textContent=e?`${e} game${e>1?"s":""} logged`:"no completed games yet",x.disabled=e===0,U.disabled=e===0}async function xe(e){var t;try{if((t=navigator.clipboard)!=null&&t.writeText)return await navigator.clipboard.writeText(e),!0}catch{}try{const n=document.createElement("textarea");n.value=e,n.style.position="fixed",n.style.opacity="0",document.body.appendChild(n),n.focus(),n.select();const a=document.execCommand("copy");return document.body.removeChild(n),a}catch{return!1}}function Ee(e,t){e.dataset.orig||(e.dataset.orig=e.textContent||""),e.textContent=t,setTimeout(()=>{e.textContent=e.dataset.orig||""},1400)}function ye(){if(G(o.state)){o.phase="idle",Oe(),_();return}ve=performance.now();const e=A(o.state);if(e.length===1&&e[0]===M){o.phase="passing",_();const t=b;setTimeout(()=>{t===b&&J(M)},Te);return}if(!k(o.state)){o.phase="thinking",ee(o.opponent)&&(q.style.width="0%"),_();const t=b,n=o.state,a=te(o.opponent,o.variant,oe);setTimeout(()=>{t===b&&se.postMessage({gen:t,board:n.board,toMove:n.toMove,cool:[...n.cool],passes:n.passes,variant:o.variant,cfg:a})},_e);return}o.phase="idle",_()}function J(e){if(b++,c){const t=Math.round(performance.now()-ve);c.moves.push({ply:c.moves.length,player:o.state.toMove,move:e,ms:t})}o.history.push({state:o.state,last:o.last}),o.last=e===M?-1:e,o.state=ke(o.state,e,o.variant),ye()}function Ie(e){e.gen!==b||o.phase!=="thinking"||J(e.move)}function Pe(e){e.gen!==b||o.phase!=="thinking"||(q.style.width=(e.frac*100).toFixed(0)+"%")}function $e(e){F()||G(o.state)||!k(o.state)||A(o.state).includes(e)&&J(e)}function Q(){if(F()||!he())return;b++;let e,t=0;for(;o.history.length&&(e=o.history.pop(),t++,!(k(e.state)&&ge(e.state).length));)e=void 0;e&&(c&&t&&(c.moves.splice(Math.max(0,c.moves.length-t)),c.undos+=1),o.state=e.state,o.last=e.last,o.phase="idle",E=o.state.board.slice(),_())}function S(){b++,c=null,o.state=V(),o.last=-1,o.history=[],o.phase="idle",E=new Array(w).fill(f),Ne(),ye()}function We(e,t,n){t===f&&n!==f?e.animate([{transform:"scale(0)"},{transform:"scale(1)"}],{duration:190,easing:"cubic-bezier(.2,.8,.3,1.3)"}):t!==f&&n!==f&&e.animate([{transform:"rotateY(0deg)"},{transform:"rotateY(90deg)"},{transform:"rotateY(0deg)"}],{duration:300,easing:"ease-in-out"})}function _(){const e=o.state,t=G(e),n=o.phase==="idle"&&!t&&k(e),a=new Set(n?A(e):[]),s=n&&o.variant==="cooldown"?Le(e,o.variant):new Set,[l,d]=R(e);for(let r=0;r<w;r++){const y=ae[r],j=y.firstElementChild,K=E[r],B=e.board[r];K!==B&&We(j,K,B),j.className="disc"+(B===m?" black":B===v?" white":"")+(e.cool.has(r)?" chilled":""),y.classList.toggle("legal",a.has(r)),y.classList.toggle("blocked",s.has(r)),y.classList.toggle("last",r===o.last)}E=e.board.slice(),re.textContent=String(l),ce.textContent=String(d),de.classList.toggle("active",!t&&e.toMove===m),pe.classList.toggle("active",!t&&e.toMove===v);let p;if(t){const r=Z(e);p=r===f?`Draw ${l}–${d}`:`${I(r)} wins ${Math.max(l,d)}–${Math.min(l,d)}`}else o.phase==="thinking"?p="AI is thinking…":o.phase==="passing"?p=`${I(e.toMove)} has no move — passing…`:p=k(e)?"Your move":`${I(e.toMove)} to move`;P.textContent=p,P.classList.toggle("over",t);const g=o.phase==="thinking"&&ee(o.opponent);le.style.visibility=o.phase==="thinking"&&!g?"visible":"hidden",ie.classList.toggle("show",g),$.classList.toggle("over",t),T.disabled=o.opponent==="human",H.disabled=F()||!he();const u=o.variant==="cooldown";ue.style.display=u?"":"none",fe.querySelectorAll(".cd").forEach(r=>{r.style.display=u?"":"none"})}function He(){ne.innerHTML=`
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
    <div class="board" id="board" style="grid-template-columns:repeat(${C},1fr)"></div>
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
  `,$=i("board"),P=i("status"),le=i("spin"),ie=i("prog"),q=i("progbar"),re=i("scoreB"),ce=i("scoreW"),de=i("sideB"),pe=i("sideW"),ue=i("hint"),fe=i("legend"),W=i("logcount"),N=i("variant"),O=i("opp"),T=i("color"),H=i("undo"),z=i("new"),x=i("copylog"),U=i("clearlog"),N.value=o.variant,O.value=o.opponent,T.value=String(o.humanColor);for(let e=0;e<w;e++){const t=document.createElement("button");t.className="cell",t.setAttribute("aria-label",`square ${e}`);const n=document.createElement("span");n.className="disc",t.appendChild(n),t.addEventListener("click",()=>$e(e)),ae.push(t),$.appendChild(t)}N.onchange=()=>{o.variant=N.value,S()},O.onchange=()=>{o.opponent=O.value,S()},T.onchange=()=>{o.humanColor=parseInt(T.value,10),S()},z.onclick=()=>S(),H.onclick=()=>Q(),x.onclick=async()=>{const e=await xe(JSON.stringify(h,null,2));Ee(x,e?"Copied ✓":"Copy failed"),e||console.log(JSON.stringify(h,null,2))},U.onclick=()=>{h.length&&confirm(`Delete all ${h.length} logged game(s)? This cannot be undone.`)&&(h=[],we(),D())},se.onmessage=e=>{const t=e.data;t.type==="progress"?Pe(t):Ie(t)},document.addEventListener("keydown",e=>{e.target.tagName!=="SELECT"&&(e.key==="n"?S():e.key==="u"&&Q())}),Be(),D()}He();S();
