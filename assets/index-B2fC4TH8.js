(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const o of document.querySelectorAll('link[rel="modulepreload"]'))c(o);new MutationObserver(o=>{for(const l of o)if(l.type==="childList")for(const a of l.addedNodes)a.tagName==="LINK"&&a.rel==="modulepreload"&&c(a)}).observe(document,{childList:!0,subtree:!0});function n(o){const l={};return o.integrity&&(l.integrity=o.integrity),o.referrerPolicy&&(l.referrerPolicy=o.referrerPolicy),o.crossOrigin==="use-credentials"?l.credentials="include":o.crossOrigin==="anonymous"?l.credentials="omit":l.credentials="same-origin",l}function c(o){if(o.ep)return;o.ep=!0;const l=n(o);fetch(o.href,l)}})();const M=6,I=36,w=0,f=1,g=2,m=-1,G=[[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]],k=(e,t)=>e*M+t,K=e=>[Math.floor(e/M),e%M],Q=(()=>{const e=[];for(let t=0;t<I;t++){const[n,c]=K(t),o=[];for(const[l,a]of G){const i=[];let s=n+l,u=c+a;for(;s>=0&&s<M&&u>=0&&u<M;)i.push(k(s,u)),s+=l,u+=a;o.push(i)}e.push(o)}return e})();function x(){const e=new Array(I).fill(w);return e[k(2,2)]=g,e[k(2,3)]=f,e[k(3,2)]=f,e[k(3,3)]=g,{board:e,toMove:f,cool:new Set,passes:0}}const O=e=>e===g?f:g;function T(e,t,n,c){const o=O(c),l=[];for(const a of Q[n]){const i=[];let s=!1;for(const u of a){const d=e[u];if(d===o){i.push(u),t.has(u)||(s=!0);continue}if(d===c){if(i.length&&s)for(const p of i)t.has(p)||l.push(p);break}break}}return l}function h(e,t){const n=[];for(let c=0;c<I;c++)e.board[c]===w&&T(e.board,e.cool,c,e.toMove).length&&n.push(c);return n.length?n:[m]}function L(e,t,n){const c=O(e.toMove);if(t===m)return{board:e.board.slice(),toMove:c,cool:new Set,passes:e.passes+1};const o=T(e.board,e.cool,t,e.toMove);if(!o.length)throw new Error("illegal move "+t);const l=e.board.slice();l[t]=e.toMove;for(const i of o)l[i]=e.toMove;const a=n==="cooldown"?new Set([t,...o]):new Set;return{board:l,toMove:c,cool:a,passes:0}}const b=e=>e.passes>=2;function R(e){let t=0,n=0;for(const c of e.board)c===f?t++:c===g&&n++;return[t,n]}function H(e){const[t,n]=R(e);return t>n?f:n>t?g:w}function z(e,t){if(t!=="cooldown")return new Set;const n=new Set,c=new Set(h(e));for(let o=0;o<I;o++)e.board[o]===w&&T(e.board,new Set,o,e.toMove).length&&!c.has(o)&&n.add(o);return n}const F=[100,-20,10,10,-20,100,-20,-50,-2,-2,-50,-20,10,-2,-1,-1,-2,10,10,-2,-1,-1,-2,10,-20,-50,-2,-2,-50,-20,100,-20,10,10,-20,100];let q=1234567;function Y(){return q=q*1103515245+12345&2147483647,q/2147483647}const E=e=>e[Math.floor(Y()*e.length)];function J(e,t){const n=O(t);let c=0;for(let o=0;o<I;o++)e[o]===t?c+=F[o]:e[o]===n&&(c-=F[o]);return c}function U(e,t){const n=h(e);if(n.length===1)return n[0];let c=-1/0,o=[];for(const l of n){const a=L(e,l,t),i=J(a.board,e.toMove);i>c+1e-9?(c=i,o=[l]):i>=c-1e-9&&o.push(l)}return E(o)}function V(e,t){let n=e;for(;!b(n);)n=L(n,E(h(n)),t);return n}const X=(e,t)=>{const n=H(e);return n===w?.5:n===t?1:0},W=(e,t,n,c)=>({state:e,parent:t,move:n,children:[],untried:h(e),n:0,w:0});function Z(e,t,n){const c=h(e);if(c.length===1)return c[0];const o=Math.SQRT2,l=W(e,null,-2);for(let i=0;i<n;i++){let s=l;for(;s.untried.length===0&&s.children.length>0&&!b(s.state);){let p=s.children[0],$=-1/0;for(const v of s.children){const j=1-v.w/v.n,D=o*Math.sqrt(Math.log(s.n)/v.n),B=j+D;B>$&&($=B,p=v)}s=p}if(s.untried.length&&!b(s.state)){const p=Math.floor(Y()*s.untried.length),$=s.untried.splice(p,1)[0],v=W(L(s.state,$,t),s,$);s.children.push(v),s=v}const u=V(s.state,t);let d=s;for(;d;)d.n++,d.w+=X(u,d.state.toMove),d=d.parent}let a=l.children[0];for(const i of l.children)i.n>a.n&&(a=i);return a.move}function ee(e,t,n,c=800){return h(e)[0]===m?m:n==="random"?E(h(e)):n==="greedy"?U(e,t):Z(e,t,c)}const r={variant:"cooldown",opponent:"mcts",humanColor:f,state:x(),busy:!1,last:-1},y=document.getElementById("app");function C(){r.state=x(),r.last=-1,r.busy=!1,N(),A()}function S(){return r.opponent==="human"||r.state.toMove===r.humanColor}function P(e){r.last=e===m?-1:e,r.state=L(r.state,e,r.variant),N()}function A(){b(r.state)||S()||(r.busy=!0,N(),setTimeout(()=>{const e=ee(r.state,r.variant,r.opponent,900);P(e),r.busy=!1,!b(r.state)&&!S()?A():_()},60))}function _(){if(b(r.state)){N();return}S()&&h(r.state)[0]===m&&setTimeout(()=>{P(m),A()},500)}function te(e){r.busy||b(r.state)||!S()||!h(r.state).includes(e)||(P(e),!b(r.state)&&!S()?A():_())}function N(){const e=r.state,t=new Set(S()&&!r.busy?h(e):[]),n=r.variant==="cooldown"?z(e,r.variant):new Set,[c,o]=R(e),l=b(e);let a;if(l){const s=H(e);a=s===w?"Draw.":`${s===f?"Black":"White"} wins ${Math.max(c,o)}–${Math.min(c,o)}.`}else r.busy?a="AI thinking…":t.has(m)?a=`${e.toMove===f?"Black":"White"} has no move — passing.`:a=`${e.toMove===f?"Black":"White"} to move`;y.innerHTML=`
    <h1>Cooldown Othello <span class="sub">6×6</span></h1>
    <div class="controls">
      <label>Rules
        <select id="variant">
          <option value="cooldown"${r.variant==="cooldown"?" selected":""}>Cooldown</option>
          <option value="classic"${r.variant==="classic"?" selected":""}>Classic</option>
        </select>
      </label>
      <label>Opponent
        <select id="opp">
          <option value="mcts"${r.opponent==="mcts"?" selected":""}>AI · MCTS</option>
          <option value="greedy"${r.opponent==="greedy"?" selected":""}>AI · Greedy</option>
          <option value="random"${r.opponent==="random"?" selected":""}>AI · Random</option>
          <option value="human"${r.opponent==="human"?" selected":""}>Human (hotseat)</option>
        </select>
      </label>
      <label>You play
        <select id="color"${r.opponent==="human"?" disabled":""}>
          <option value="1"${r.humanColor===f?" selected":""}>Black (first)</option>
          <option value="2"${r.humanColor===g?" selected":""}>White</option>
        </select>
      </label>
      <button id="new">New game</button>
    </div>
    <div class="scorebar">
      <span class="chip black"></span> ${c}
      <span class="status">${a}</span>
      ${o} <span class="chip white"></span>
    </div>
    <div class="board" style="grid-template-columns:repeat(${M},1fr)"></div>
    ${r.variant==="cooldown"?`<p class="hint">Cooldown rule: pieces placed or flipped last turn are
      <b>chilled</b> (ringed) — they can't be flipped back this turn. So after the opponent captures,
      you can't immediately recapture those pieces. Faintly-marked squares would be legal in classic
      Othello but are blocked here.</p>`:""}
    <p class="footer">Light in-browser AI for play/feel — not the tuned research player.
      <a href="https://github.com/wojtke/cooldown-othello-mcts" target="_blank" rel="noopener">source</a></p>
  `;const i=y.querySelector(".board");for(let s=0;s<e.board.length;s++){const u=document.createElement("button");u.className="cell",t.has(s)&&u.classList.add("legal"),n.has(s)&&u.classList.add("blocked"),s===r.last&&u.classList.add("last");const d=e.board[s];if(d!==w){const p=document.createElement("span");p.className="disc "+(d===f?"black":"white"),e.cool.has(s)&&p.classList.add("chilled"),u.appendChild(p)}u.addEventListener("click",()=>te(s)),i.appendChild(u)}y.querySelector("#variant").onchange=s=>{r.variant=s.target.value,C()},y.querySelector("#opp").onchange=s=>{r.opponent=s.target.value,C()},y.querySelector("#color").onchange=s=>{r.humanColor=parseInt(s.target.value,10),C()},y.querySelector("#new").onclick=C}C();
