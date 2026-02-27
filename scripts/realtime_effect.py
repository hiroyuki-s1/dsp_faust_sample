#!/usr/bin/env python3
"""
Guitar Pedalboard — Real-time Web UI
ブラウザ (Web Audio API) でリアルタイム DSP。追加パッケージ不要。

Usage:
  python3 scripts/realtime_effect.py [input.wav]
  → ブラウザで http://localhost:8765 を開く
"""

import sys, os, time, threading, json
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8765

# ──────────────────────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Guitar Pedalboard</title>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Tahoma,sans-serif;background:#0a0a0a;color:#e8e8e8;min-height:100vh;user-select:none}

/* ── Header ──────────────────────────────────────────────── */
header{display:flex;align-items:center;justify-content:space-between;padding:10px 18px;
  background:linear-gradient(135deg,#1a1a2e,#16213e);border-bottom:2px solid #c8a96e}
header h1{font-size:1em;letter-spacing:4px;color:#c8a96e;text-transform:uppercase}
.hctrl{display:flex;gap:8px;align-items:center}
#status{font-size:0.72em;color:#7ee787;min-width:180px;text-align:right}
button{padding:7px 13px;border:none;border-radius:4px;font-size:0.8em;font-weight:700;
  cursor:pointer;letter-spacing:1px;transition:opacity .15s,transform .1s}
button:active{transform:scale(0.96)}
button:disabled{opacity:0.4;cursor:not-allowed}
#btn-play{background:#238636;color:#fff}
#btn-stop{background:#da3633;color:#fff}
.btn-s{background:#21262d;color:#c8a96e;border:1px solid #444}
.btn-s:hover{background:#2d333b}

/* ── Board ───────────────────────────────────────────────── */
#board-wrap{padding:18px}
#board-surface{
  background:
    radial-gradient(circle at 2px 2px,rgba(255,255,255,0.025) 1px,transparent 0) 0 0 / 5px 5px,
    linear-gradient(160deg,#2c1f0e,#1a1208 50%,#2c1f0e);
  border:4px solid;border-color:#7a5c28 #4a3010 #4a3010 #7a5c28;
  border-radius:10px;padding:20px 16px 16px;position:relative;
  box-shadow:inset 0 2px 10px rgba(0,0,0,0.6),0 6px 20px rgba(0,0,0,0.7)}

/* ── Board inner: horizontal flow with IN / ... / OUT ────── */
#board-inner{display:flex;align-items:center;min-height:160px;overflow-x:auto}

/* ── IO Nodes ────────────────────────────────────────────── */
.io-node{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#3a3a3a,#1e1e1e);
  border:2px solid #555;display:flex;align-items:center;justify-content:center;
  font-size:0.6em;font-weight:700;letter-spacing:1px;flex-shrink:0}
.io-node.in{border-color:#4a9eff;color:#4a9eff}
.io-node.out{border-color:#ff6b6b;color:#ff6b6b}

/* ── Cable ───────────────────────────────────────────────── */
.cable{flex-shrink:0;display:flex;align-items:center;padding:0 3px}
.cable-line{height:3px;width:18px;background:linear-gradient(90deg,#555,#888 50%,#555);
  border-radius:2px;position:relative}
.cable-line::after{content:'';position:absolute;right:-4px;top:50%;transform:translateY(-50%);
  border-left:6px solid #888;border-top:4px solid transparent;border-bottom:4px solid transparent}

/* ── SPLIT / MERGE visual nodes ──────────────────────────── */
/*  Both are vertical flex containers that draw fork/join lines via child borders  */
.split-wrap,.merge-wrap{
  align-self:stretch;width:22px;flex-shrink:0;
  display:flex;flex-direction:column;position:relative}
/* Junction dot */
.split-wrap::before,.merge-wrap::before{
  content:'';position:absolute;
  left:50%;top:50%;transform:translate(-50%,-50%);
  width:11px;height:11px;border-radius:50%;
  background:#c8a96e;box-shadow:0 0 8px rgba(200,169,110,0.7);z-index:2}
/* Split: lines branch OUT to the right */
.split-top{flex:1;border-right:2px solid #777;border-bottom:2px solid #777;border-bottom-right-radius:7px}
.split-bot{flex:1;border-right:2px solid #777;border-top:2px solid #777;border-top-right-radius:7px}
/* Merge: lines converge IN from the right */
.merge-top{flex:1;border-left:2px solid #777;border-bottom:2px solid #777;border-bottom-left-radius:7px}
.merge-bot{flex:1;border-left:2px solid #777;border-top:2px solid #777;border-top-left-radius:7px}

/* ── Parallel Lanes (between SPLIT and MERGE) ────────────── */
.para-lanes{flex:1;display:flex;flex-direction:column;min-width:0}
.top-lane,.bot-lane{display:flex;align-items:center;min-height:130px;flex:1}
.lane-sep{
  display:flex;align-items:center;gap:10px;padding:3px 8px;
  border-top:1px solid #3a2a0a;border-bottom:1px solid #3a2a0a;
  font-size:0.7em;color:#888}
.lane-sep label{color:#c8a96e;letter-spacing:1px;white-space:nowrap}
.lane-sep input{flex:1;max-width:180px}

/* ── Drop Zone ───────────────────────────────────────────── */
.dz{width:14px;min-height:100px;display:flex;align-items:center;justify-content:center;
  flex-shrink:0;border-radius:4px;transition:width .2s,background .2s,border .2s}
.dz.over{width:52px;background:rgba(200,169,110,0.15);border:1px dashed #c8a96e}

/* ── Pedal ───────────────────────────────────────────────── */
.pedal{display:flex;flex-direction:column;align-items:center;border-radius:8px;
  padding:10px 8px 8px;cursor:grab;position:relative;min-width:96px;flex-shrink:0}
.pedal:active{cursor:grabbing}
.pedal.dragging{opacity:0.4;transform:scale(0.92)}
.screw{position:absolute;width:7px;height:7px;border-radius:50%;
  background:radial-gradient(circle at 30% 30%,#ccc,#555);border:1px solid #333}
.screw.tl{top:4px;left:4px}.screw.tr{top:4px;right:4px}
.screw.bl{bottom:4px;left:4px}.screw.br{bottom:4px;right:4px}
.pname{font-size:0.62em;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:6px}
.pknobs{display:flex;gap:6px;margin-bottom:6px}
.kwrap{display:flex;flex-direction:column;align-items:center;gap:2px}
.klbl{font-size:0.52em;color:rgba(255,255,255,0.55);letter-spacing:1px;text-transform:uppercase}
.kval{font-size:0.52em;color:#bbb}
.pfooter{display:flex;align-items:center;gap:8px}
.pswitch{width:26px;height:26px;border-radius:50%;background:radial-gradient(circle at 40% 35%,#555,#222);
  border:2px solid #555;cursor:pointer;display:flex;align-items:center;justify-content:center;
  font-size:0.7em;color:#777;transition:background .15s;pointer-events:all}
.pswitch.on{background:radial-gradient(circle at 40% 35%,#4a8,#263);border-color:#5b9;color:#aef}
.pled{width:7px;height:7px;border-radius:50%;background:#2a2a2a}
.pled.on{background:#7ee787;box-shadow:0 0 6px #7ee787}
.pdel{position:absolute;top:2px;right:2px;width:16px;height:16px;background:rgba(200,40,40,0.85);
  border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:9px;
  color:#fff;cursor:pointer;opacity:0;transition:opacity .15s;z-index:10;pointer-events:all}
.pedal:hover .pdel{opacity:1}

/* ── Single-chain row (no parallel) ─────────────────────── */
.single-lane{flex:1;display:flex;align-items:center;min-width:0}

/* ── Range input ─────────────────────────────────────────── */
input[type=range]{-webkit-appearance:none;height:4px;background:#333;border-radius:2px;outline:none;cursor:pointer}
input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:13px;height:13px;border-radius:50%;background:#c8a96e;cursor:pointer}

/* ── Palette ─────────────────────────────────────────────── */
#pal-section{background:#0e1016;border-top:2px solid #252525;padding:14px 18px 18px}
#pal-section h2{font-size:0.68em;letter-spacing:3px;color:#555;text-transform:uppercase;margin-bottom:12px}
#pal-items{display:flex;gap:10px;flex-wrap:wrap}
.pitem{display:flex;flex-direction:column;align-items:center;justify-content:center;
  width:68px;height:62px;border-radius:6px;cursor:pointer;transition:transform .15s,box-shadow .15s;
  font-size:0.62em;font-weight:700;letter-spacing:1px;text-align:center;padding:6px;gap:3px}
.pitem:hover{transform:translateY(-3px);box-shadow:0 6px 16px rgba(0,0,0,0.45)}
.pitem:active{transform:scale(0.95)}
.pitem .picon{font-size:1.5em}

/* ── Drag Ghost ──────────────────────────────────────────── */
#ghost{position:fixed;pointer-events:none;z-index:9999;opacity:0.88;display:none;
  transform:scale(0.95) rotate(2deg);padding:8px 12px;border-radius:8px;
  font-size:0.72em;font-weight:700;letter-spacing:2px;color:#fff;text-transform:uppercase;
  box-shadow:0 8px 24px rgba(0,0,0,0.6)}
</style>
</head>
<body>

<div id="ghost"></div>

<header>
  <h1>🎸 Guitar Pedalboard</h1>
  <div class="hctrl">
    <span id="status">▶ Start で再生</span>
    <button id="btn-play" onclick="startAudio()">▶ PLAY</button>
    <button id="btn-stop" onclick="stopAudio()" disabled>■ STOP</button>
    <button class="btn-s" onclick="toggleParallel()" title="分岐ケーブルを追加/削除">⑂ SPLIT</button>
    <button class="btn-s" onclick="clearBoard()" title="ボードをクリア">🗑</button>
  </div>
</header>

<div id="board-wrap">
  <div id="board-surface">
    <div id="board-inner"><!-- JS で描画 --></div>
  </div>
</div>

<div id="pal-section">
  <h2>EFFECTS — クリックまたはドラッグして配置</h2>
  <div id="pal-items"></div>
</div>

<script>
'use strict';

/* ═══════════════════════════════════════════════
   DSP UTILITIES
═══════════════════════════════════════════════ */

function makeFreeverb(SR, isRoom) {
  const sc=SR/44100, s=isRoom?0.55:1.0;
  const CD=[1116,1188,1277,1356,1422,1491,1557,1617].map(d=>Math.round(d*sc*s));
  const SP=23;
  const cl=CD.map(d=>({b:new Float32Array(d),   p:0,fs:0,n:d   }));
  const cr=CD.map(d=>({b:new Float32Array(d+SP),p:0,fs:0,n:d+SP}));
  const AD=[225,556,441,341].map(d=>Math.round(d*sc*s));
  const al=AD.map(d=>({b:new Float32Array(d),p:0,n:d}));
  const ar=AD.map(d=>({b:new Float32Array(d),p:0,n:d}));
  return{cl,cr,al,ar};
}

function procFV(fv, room, damp, mix, inL, isRoom) {
  const fbc=(isRoom?0.60:0.70)+room*0.28, dm=damp*0.40, d1m=1-dm;
  const{cl,cr,al,ar}=fv, rv=inL*0.015;
  let sL=0,sR=0;
  for(let k=0;k<8;k++){
    let c=cl[k];const ol=c.b[c.p];c.fs=ol*d1m+c.fs*dm;c.b[c.p]=rv+c.fs*fbc;c.p=(c.p+1)%c.n;sL+=ol;
    c=cr[k];const or=c.b[c.p];c.fs=or*d1m+c.fs*dm;c.b[c.p]=rv+c.fs*fbc;c.p=(c.p+1)%c.n;sR+=or;
  }
  for(let k=0;k<4;k++){
    let a=al[k];const bvl=a.b[a.p];const sl2=-sL+bvl;a.b[a.p]=sL+bvl*0.5;a.p=(a.p+1)%a.n;sL=sl2;
    a=ar[k];const bvr=a.b[a.p];const sr2=-sR+bvr;a.b[a.p]=sR+bvr*0.5;a.p=(a.p+1)%a.n;sR=sr2;
  }
  return[inL*(1-mix)+sL*mix, inL*(1-mix)+sR*mix];
}

function makePitcher(SR) {
  const G=2048,B=G*8,M=B-1,buf=new Float32Array(B);
  let wr=0;
  const gs=[{d:G,ph:0},{d:G*1.5,ph:0.5}];
  return function(x,amt){
    buf[wr&M]=x;wr++;
    if(amt<0.001)return 0;
    let out=0;
    for(const g of gs){
      const rd=wr-g.d;
      const i0=(Math.floor(rd)&M+B)&M,i1=((Math.floor(rd)+1)&M+B)&M;
      const fr=rd-Math.floor(rd),s=buf[i0]*(1-fr)+buf[i1]*fr;
      const w=0.5-0.5*Math.cos(2*Math.PI*g.ph);out+=s*w;
      g.d-=1;g.ph+=1/G;if(g.ph>=1){g.d=G*1.5;g.ph=0;}
    }
    return out*0.7071*amt;
  };
}

/* ═══════════════════════════════════════════════
   EFFECT DEFINITIONS
═══════════════════════════════════════════════ */

const FX = {
  digital_delay:{
    name:'Digital Delay',short:'DELAY',icon:'⏱',color:'#0d3a6e',light:'#4a9eff',
    params:{
      time:    {label:'TIME',min:10,max:1000,step:1,   def:300,unit:'ms'},
      feedback:{label:'FDBK',min:0, max:0.95,step:0.01,def:0.5},
      mix:     {label:'MIX', min:0, max:1,   step:0.01,def:0.4},
    },
    init(SR){return{buf:new Float32Array(Math.ceil(SR*1.05)),pos:0};},
    proc(s,p,x,SR){
      const n=Math.max(1,Math.round(p.time*SR/1000))%s.buf.length;
      const rp=(s.pos-n+s.buf.length)%s.buf.length, d=s.buf[rp];
      s.buf[s.pos]=x+d*p.feedback; s.pos=(s.pos+1)%s.buf.length;
      const o=x*(1-p.mix)+d*p.mix; return[o,o];
    }
  },
  analog_delay:{
    name:'Analog Delay',short:'ANALOG',icon:'📼',color:'#5c2a00',light:'#ff8c42',
    params:{
      time:    {label:'TIME',min:10,max:1000,step:1,   def:350,unit:'ms'},
      feedback:{label:'FDBK',min:0, max:0.95,step:0.01,def:0.5},
      mix:     {label:'MIX', min:0, max:1,   step:0.01,def:0.4},
      tone:    {label:'TONE',min:0, max:1,   step:0.01,def:0.5},
    },
    init(SR){return{buf:new Float32Array(Math.ceil(SR*1.05)),pos:0,lpZ:0};},
    proc(s,p,x,SR){
      const n=Math.max(1,Math.round(p.time*SR/1000))%s.buf.length;
      const cut=500+p.tone*6000, rc=cut/(cut+SR/(2*Math.PI));
      const rp=(s.pos-n+s.buf.length)%s.buf.length, d=s.buf[rp];
      s.lpZ=s.lpZ*(1-rc)+d*rc;
      s.buf[s.pos]=x+Math.tanh(s.lpZ*1.8)/1.8*p.feedback;
      s.pos=(s.pos+1)%s.buf.length;
      return[x*(1-p.mix)+d*p.mix, x*(1-p.mix)+d*p.mix];
    }
  },
  echo_delay:{
    name:'Echo Delay',short:'ECHO',icon:'🔁',color:'#4a3800',light:'#ffd166',
    params:{
      time: {label:'TIME', min:10,max:800, step:1,   def:220,unit:'ms'},
      decay:{label:'DECAY',min:0, max:0.95,step:0.01,def:0.6},
      mix:  {label:'MIX',  min:0, max:1,  step:0.01,def:0.4},
    },
    init(SR){return{buf:new Float32Array(Math.ceil(SR*1.6)),pos:0};},
    proc(s,p,x,SR){
      const n1=Math.max(1,Math.round(p.time*SR/1000))%s.buf.length;
      const n2=Math.min(Math.round(p.time*1.5*SR/1000),s.buf.length-1);
      const r1=(s.pos-n1+s.buf.length)%s.buf.length;
      const r2=(s.pos-n2+s.buf.length)%s.buf.length;
      const d1=s.buf[r1],d2=s.buf[r2];
      s.buf[s.pos]=x+d1*p.decay; s.pos=(s.pos+1)%s.buf.length;
      const o=x*(1-p.mix)+(d1+d2*0.55)*0.6*p.mix; return[o,o];
    }
  },
  hall_reverb:{
    name:'Hall Reverb',short:'HALL',icon:'🏛',color:'#2e0a5c',light:'#a855f7',
    params:{
      room:   {label:'ROOM',min:0,max:1,step:0.01,def:0.75},
      damping:{label:'DAMP',min:0,max:1,step:0.01,def:0.4},
      mix:    {label:'MIX', min:0,max:1,step:0.01,def:0.35},
    },
    init(SR){return{fv:makeFreeverb(SR,false)};},
    proc(s,p,x,SR){return procFV(s.fv,p.room,p.damping,p.mix,x,false);}
  },
  room_reverb:{
    name:'Room Reverb',short:'ROOM',icon:'🚪',color:'#0a3520',light:'#2ecc71',
    params:{
      room:   {label:'ROOM',min:0,max:1,step:0.01,def:0.4},
      damping:{label:'DAMP',min:0,max:1,step:0.01,def:0.6},
      mix:    {label:'MIX', min:0,max:1,step:0.01,def:0.25},
    },
    init(SR){return{fv:makeFreeverb(SR,true)};},
    proc(s,p,x,SR){return procFV(s.fv,p.room,p.damping,p.mix,x,true);}
  },
  shimmer:{
    name:'Shimmer',short:'SHIMMER',icon:'✨',color:'#5a0035',light:'#ec4899',
    params:{
      room:   {label:'ROOM',min:0,  max:1,  step:0.01,def:0.9},
      mix:    {label:'MIX', min:0,  max:1,  step:0.01,def:0.5},
      shimmer:{label:'SHIM',min:0,  max:0.9,step:0.01,def:0.6},
    },
    init(SR){return{fv:makeFreeverb(SR,false),pt:makePitcher(SR)};},
    proc(s,p,x,SR){return procFV(s.fv,p.room,0.3,p.mix,x+s.pt(x,p.shimmer),false);}
  },
};

/* ═══════════════════════════════════════════════
   BOARD STATE
   ─────────────────────────────────────────────
   topChain : 上段 (常に存在)
   botChain : 下段 (hasParallel=true のときだけ使用)

   信号フロー:
     [IN] → topChain → [OUT]                     (シリアル)
     [IN] ─⑂→ topChain ─⑃→ [OUT]               (並列)
             └→ botChain ─┘
═══════════════════════════════════════════════ */

let SR=48000, nid=1;

const board={
  topChain:[],
  botChain:null,    // null = SPLIT なし
  hasParallel:false,
  mixAB:0.5,        // 0=top only, 1=bot only
};

function getChain(cid){return cid==='bot'?board.botChain:board.topChain;}

function mkInst(type){
  const p={};
  for(const[k,v]of Object.entries(FX[type].params))p[k]=v.def;
  return{id:nid++,type,on:true,params:p,state:null};
}

function procInst(inst,x){
  if(!inst.on)return[x,x];
  const fx=FX[inst.type];
  if(!inst.state)inst.state=fx.init(SR);
  return fx.proc(inst.state,inst.params,x,SR);
}

// チェーンを順に処理。ステレオ出力は左チャンネルを次の入力に使用
function procChain(chain,x){
  let L=x,R=x;
  for(const inst of chain){const[l,r]=procInst(inst,L);L=l;R=r;}
  return[L,R];
}

/* ═══════════════════════════════════════════════
   AUDIO ENGINE
═══════════════════════════════════════════════ */

let actx,src,dsp,gain;

async function startAudio(){
  setst('⏳ 読み込み中...');
  try{
    actx=new AudioContext(); SR=actx.sampleRate;
    for(const c of[board.topChain,board.botChain].filter(Boolean))
      for(const i of c)i.state=null;

    const ab=await(await fetch('/audio')).arrayBuffer();
    const dec=await actx.decodeAudioData(ab);
    src=actx.createBufferSource();src.buffer=dec;src.loop=true;
    gain=actx.createGain();gain.gain.value=0.9;
    dsp=actx.createScriptProcessor(1024,1,2);

    dsp.onaudioprocess=(e)=>{
      const inp=e.inputBuffer.getChannelData(0);
      const oL=e.outputBuffer.getChannelData(0);
      const oR=e.outputBuffer.getChannelData(1);
      for(let i=0;i<inp.length;i++){
        const x=inp[i];
        if(board.hasParallel&&board.botChain){
          // 1つの入力を分岐 → 両チェーン並列処理 → ミックスして1出力
          const[tL,tR]=procChain(board.topChain,x);
          const[bL,bR]=procChain(board.botChain,x);
          const mx=board.mixAB;
          oL[i]=tL*(1-mx)+bL*mx;
          oR[i]=tR*(1-mx)+bR*mx;
        }else{
          const[L,R]=procChain(board.topChain,x);
          oL[i]=L;oR[i]=R;
        }
      }
    };
    src.connect(dsp);dsp.connect(gain);gain.connect(actx.destination);src.start();
    setst(`▶ Playing @ ${SR}Hz`);
    document.getElementById('btn-play').disabled=true;
    document.getElementById('btn-stop').disabled=false;
  }catch(e){setst('❌ '+e.message);console.error(e);}
}

function stopAudio(){
  src&&src.stop();actx&&actx.close();src=actx=dsp=null;
  setst('■ 停止');
  document.getElementById('btn-play').disabled=false;
  document.getElementById('btn-stop').disabled=true;
}
function setst(m){document.getElementById('status').textContent=m;}

/* ═══════════════════════════════════════════════
   CANVAS KNOBS  (上ドラッグ=増加, 下ドラッグ=減少)
═══════════════════════════════════════════════ */

const KS=44;

function drawKnob(cv){
  const{value:vs,min:ms,max:xs,color:cs}=cv.dataset;
  const v=parseFloat(vs),mn=parseFloat(ms),mx=parseFloat(xs);
  const frac=(v-mn)/(mx-mn);
  const a0=Math.PI*0.75, a1=Math.PI*2.25, angle=a0+frac*(a1-a0);
  const c=cv.getContext('2d'),cx=KS/2,cy=KS/2,r=KS/2-4;
  c.clearRect(0,0,KS,KS);
  const g=c.createRadialGradient(cx-r*.3,cy-r*.3,r*.05,cx,cy,r);
  g.addColorStop(0,'#4a4a4a');g.addColorStop(1,'#181818');
  c.beginPath();c.arc(cx,cy,r,0,Math.PI*2);c.fillStyle=g;c.fill();
  c.strokeStyle='#4a4a4a';c.lineWidth=1;c.stroke();
  c.beginPath();c.arc(cx,cy,r-3,a0,a1);c.strokeStyle='#252525';c.lineWidth=3.5;c.stroke();
  c.beginPath();c.arc(cx,cy,r-3,a0,angle);c.strokeStyle=cs||'#c8a96e';c.lineWidth=3.5;c.stroke();
  const px=cx+Math.cos(angle)*(r-6),py=cy+Math.sin(angle)*(r-6);
  c.beginPath();c.moveTo(cx,cy);c.lineTo(px,py);c.strokeStyle='rgba(255,255,255,.88)';c.lineWidth=2;c.stroke();
}

let activeKnob=null,kStartY=0,kStartV=0;

document.addEventListener('mousedown',e=>{
  if(e.target.classList.contains('knob')){
    activeKnob=e.target;kStartY=e.clientY;kStartV=parseFloat(e.target.dataset.value);
    e.preventDefault();e.stopPropagation();
  }
},true);

document.addEventListener('mousemove',e=>{
  if(!activeKnob)return;
  const cv=activeKnob,dy=kStartY-e.clientY;
  const range=parseFloat(cv.dataset.max)-parseFloat(cv.dataset.min);
  const step=parseFloat(cv.dataset.step)||0.01;
  let v=kStartV+dy*range/160;
  v=Math.max(parseFloat(cv.dataset.min),Math.min(parseFloat(cv.dataset.max),v));
  v=Math.round(v/step)*step;
  cv.dataset.value=v; cv.title=fmtv(v,cv.dataset.unit);
  const inst=findInst(parseInt(cv.dataset.iid),cv.dataset.cid);
  if(inst)inst.params[cv.dataset.pk]=v;
  drawKnob(cv);
  const vl=document.getElementById('vl-'+cv.dataset.iid+'-'+cv.dataset.pk);
  if(vl)vl.textContent=fmtv(v,cv.dataset.unit);
});

document.addEventListener('mouseup',()=>{activeKnob=null;});

function findInst(id,cid){const ch=getChain(cid);return ch&&ch.find(x=>x.id===id);}
function fmtv(v,u){return u?Math.round(v)+u:v.toFixed(2);}

/* ═══════════════════════════════════════════════
   DRAG AND DROP
═══════════════════════════════════════════════ */

const dnd={active:false,fromPal:false,fxType:null,instId:null,srcCid:null,srcIdx:null};
const ghost=document.getElementById('ghost');

function startDragPal(type,e){
  const fx=FX[type];
  Object.assign(dnd,{active:true,fromPal:true,fxType:type});
  ghost.textContent=fx.short;ghost.style.background=fx.color;ghost.style.color=fx.light;
  ghost.style.display='block';moveGhost(e);e.preventDefault();
}

function startDragPedal(id,cid,e){
  const ch=getChain(cid),idx=ch.findIndex(x=>x.id===id);
  if(idx<0)return;
  Object.assign(dnd,{active:true,fromPal:false,instId:id,srcCid:cid,srcIdx:idx});
  const fx=FX[ch[idx].type];
  ghost.textContent=fx.short;ghost.style.background=fx.color;ghost.style.color=fx.light;
  ghost.style.display='block';
  document.querySelector(`[data-iid="${id}"]`)?.classList.add('dragging');
  moveGhost(e);e.preventDefault();
}

function moveGhost(e){
  const cx=e.touches?e.touches[0].clientX:e.clientX;
  const cy=e.touches?e.touches[0].clientY:e.clientY;
  ghost.style.left=(cx-34)+'px';ghost.style.top=(cy-18)+'px';
}

document.addEventListener('mousemove',e=>{
  if(!dnd.active)return;
  moveGhost(e);
  document.querySelectorAll('.dz').forEach(dz=>{
    const r=dz.getBoundingClientRect();
    dz.classList.toggle('over',
      e.clientX>=r.left&&e.clientX<=r.right&&e.clientY>=r.top&&e.clientY<=r.bottom);
  });
});

document.addEventListener('mouseup',e=>{
  if(!dnd.active)return;
  ghost.style.display='none';
  const el=document.elementFromPoint(e.clientX,e.clientY);
  const dz=el?.closest?.('.dz');
  if(dz)doDrop(dz.dataset.cid,parseInt(dz.dataset.idx));
  clearDz();
  if(!dnd.fromPal&&dnd.instId)
    document.querySelector(`[data-iid="${dnd.instId}"]`)?.classList.remove('dragging');
  dnd.active=false;
});

document.addEventListener('keydown',e=>{
  if(e.key==='Escape'&&dnd.active){
    ghost.style.display='none';clearDz();
    if(!dnd.fromPal&&dnd.instId)
      document.querySelector(`[data-iid="${dnd.instId}"]`)?.classList.remove('dragging');
    dnd.active=false;
  }
});

function clearDz(){document.querySelectorAll('.dz.over').forEach(d=>d.classList.remove('over'));}

function doDrop(cid,idx){
  const chain=getChain(cid);if(!chain)return;
  if(dnd.fromPal){
    chain.splice(idx,0,mkInst(dnd.fxType));
  }else{
    const src=getChain(dnd.srcCid);if(!src)return;
    const inst=src.splice(dnd.srcIdx,1)[0];
    let ai=idx;
    if(dnd.srcCid===cid&&dnd.srcIdx<idx)ai--;
    chain.splice(Math.max(0,ai),0,inst);
  }
  renderBoard();
}

/* Touch */
document.addEventListener('touchstart',e=>{
  const pi=e.target.closest('.pitem');
  if(pi){startDragPal(pi.dataset.type,e.touches[0]);e.preventDefault();return;}
  const pd=e.target.closest('.pedal');
  if(pd&&!e.target.classList.contains('knob')&&
     !e.target.classList.contains('pswitch')&&!e.target.classList.contains('pdel')){
    startDragPedal(parseInt(pd.dataset.iid),pd.dataset.cid,e.touches[0]);e.preventDefault();
  }
},{passive:false});

document.addEventListener('touchmove',e=>{
  if(!dnd.active)return;
  moveGhost(e);
  const{clientX:cx,clientY:cy}=e.touches[0];
  document.querySelectorAll('.dz').forEach(dz=>{
    const r=dz.getBoundingClientRect();
    dz.classList.toggle('over',cx>=r.left&&cx<=r.right&&cy>=r.top&&cy<=r.bottom);
  });
  e.preventDefault();
},{passive:false});

document.addEventListener('touchend',e=>{
  if(!dnd.active)return;
  ghost.style.display='none';
  const t=e.changedTouches[0];
  const dz=document.elementFromPoint(t.clientX,t.clientY)?.closest?.('.dz');
  if(dz)doDrop(dz.dataset.cid,parseInt(dz.dataset.idx));
  clearDz();
  if(!dnd.fromPal&&dnd.instId)
    document.querySelector(`[data-iid="${dnd.instId}"]`)?.classList.remove('dragging');
  dnd.active=false;
});

/* ═══════════════════════════════════════════════
   RENDERING
═══════════════════════════════════════════════ */

function mkPedalHTML(inst,cid){
  const fx=FX[inst.type];
  const knobs=Object.entries(fx.params).map(([k,pd])=>{
    const v=inst.params[k]??pd.def;
    return`<div class="kwrap">
      <canvas class="knob" width="${KS}" height="${KS}"
        data-iid="${inst.id}" data-pk="${k}" data-cid="${cid}"
        data-value="${v}" data-min="${pd.min}" data-max="${pd.max}"
        data-step="${pd.step}" data-color="${fx.light}" data-unit="${pd.unit||''}"
        title="${fmtv(v,pd.unit||'')}" style="cursor:ns-resize"></canvas>
      <span class="klbl">${pd.label}</span>
      <span class="kval" id="vl-${inst.id}-${k}">${fmtv(v,pd.unit||'')}</span>
    </div>`;
  }).join('');
  return`<div class="pedal" data-iid="${inst.id}" data-cid="${cid}"
    style="background:${fx.color};box-shadow:0 4px 14px rgba(0,0,0,.55),inset 0 1px 1px rgba(255,255,255,.08)"
    onmousedown="onPedalMD(event,${inst.id},'${cid}')">
    <div class="screw tl"></div><div class="screw tr"></div>
    <div class="screw bl"></div><div class="screw br"></div>
    <div class="pdel" onclick="rmEff(${inst.id},'${cid}',event)">✕</div>
    <div class="pname" style="color:${fx.light}">${fx.short}</div>
    <div class="pknobs">${knobs}</div>
    <div class="pfooter">
      <div class="pled${inst.on?' on':''}" id="led-${inst.id}"></div>
      <div class="pswitch${inst.on?' on':''}" id="sw-${inst.id}"
        onclick="toggleInst(${inst.id},'${cid}',event)">●</div>
    </div>
  </div>`;
}

// ドロップゾーン + ペダル列を生成（IO ノードなし）
function mkLaneContent(chain, cid) {
  const empty = `<div style="flex:1;display:flex;align-items:center;justify-content:center;
    color:#4a3515;font-size:.78em;padding:0 16px;white-space:nowrap">エフェクトをドラッグ</div>`;
  let s=`<div class="dz" data-cid="${cid}" data-idx="0"></div>`;
  for(let i=0;i<chain.length;i++){
    s+=mkPedalHTML(chain[i],cid);
    s+=`<div class="cable"><div class="cable-line"></div></div>`;
    s+=`<div class="dz" data-cid="${cid}" data-idx="${i+1}"></div>`;
  }
  if(chain.length===0)s+=empty;
  return s;
}

function renderBoard(){
  const el=document.getElementById('board-inner');

  if(!board.hasParallel){
    // ─── シリアル: IN ─[topChain]─ OUT ───────────────────────
    el.innerHTML=`
      <div class="io-node in">IN</div>
      <div class="cable"><div class="cable-line"></div></div>
      <div class="single-lane">${mkLaneContent(board.topChain,'top')}</div>
      <div class="cable"><div class="cable-line"></div></div>
      <div class="io-node out">OUT</div>`;
  }else{
    // ─── 並列: IN ─⑂─[top]─⑃─ OUT ─────────────────────────
    //                └─[bot]─┘
    el.innerHTML=`
      <div class="io-node in">IN</div>
      <div class="cable"><div class="cable-line"></div></div>
      <div class="split-wrap">
        <div class="split-top"></div>
        <div class="split-bot"></div>
      </div>
      <div class="para-lanes">
        <div class="top-lane">${mkLaneContent(board.topChain,'top')}</div>
        <div class="lane-sep">
          <label>MIX</label>
          <input type="range" min="0" max="1" step="0.01" value="${board.mixAB}"
            oninput="board.mixAB=parseFloat(this.value);document.getElementById('mv').textContent=parseFloat(this.value).toFixed(2)">
          <span id="mv">${board.mixAB.toFixed(2)}</span>
          <span style="color:#555">TOP ←→ BOTTOM</span>
        </div>
        <div class="bot-lane">${mkLaneContent(board.botChain,'bot')}</div>
      </div>
      <div class="merge-wrap">
        <div class="merge-top"></div>
        <div class="merge-bot"></div>
      </div>
      <div class="cable"><div class="cable-line"></div></div>
      <div class="io-node out">OUT</div>`;
  }
  document.querySelectorAll('.knob').forEach(drawKnob);
}

function onPedalMD(e,id,cid){
  if(e.target.classList.contains('knob')||
     e.target.classList.contains('pswitch')||
     e.target.classList.contains('pdel'))return;
  startDragPedal(id,cid,e);
}
function rmEff(id,cid,e){
  e.stopPropagation();
  const ch=getChain(cid),i=ch.findIndex(x=>x.id===id);
  if(i>=0)ch.splice(i,1);renderBoard();
}
function toggleInst(id,cid,e){
  e.stopPropagation();
  const inst=findInst(id,cid);if(!inst)return;
  inst.on=!inst.on;
  document.getElementById('led-'+id)?.classList.toggle('on',inst.on);
  document.getElementById('sw-'+id)?.classList.toggle('on',inst.on);
}
function toggleParallel(){
  board.hasParallel=!board.hasParallel;
  if(board.hasParallel&&!board.botChain)board.botChain=[];
  renderBoard();
}
function clearBoard(){
  board.topChain=[];if(board.botChain)board.botChain=[];renderBoard();
}

/* ═══════════════════════════════════════════════
   PALETTE & INIT
═══════════════════════════════════════════════ */

function initPalette(){
  document.getElementById('pal-items').innerHTML=
    Object.entries(FX).map(([type,fx])=>`
      <div class="pitem" data-type="${type}"
        style="background:${fx.color};box-shadow:0 2px 8px rgba(0,0,0,.4)"
        onmousedown="startDragPal('${type}',event)"
        ondblclick="quickAdd('${type}')">
        <span class="picon">${fx.icon}</span>
        <span style="color:${fx.light}">${fx.short}</span>
      </div>`).join('');
}

function quickAdd(type){board.topChain.push(mkInst(type));renderBoard();}

initPalette();
renderBoard();
</script>
</body>
</html>"""

# ──────────────────────────────────────────────────────────────
wav_path   = ""
stop_event = threading.Event()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            self._send(200, 'text/html; charset=utf-8', HTML.encode())
        elif self.path == '/audio':
            with open(wav_path, 'rb') as f:
                data = f.read()
            self._send(200, 'audio/wav', data)
        else:
            self._send(404, 'text/plain', b'Not found')

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body   = self.rfile.read(length)
        if self.path == '/stop':
            stop_event.set()
            self._send(200, 'text/plain', b'ok')
        else:
            self._send(404, 'text/plain', b'Not found')

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', len(body))
        self.end_headers()
        self.wfile.write(body)

# ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    base     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    wav_path = sys.argv[1] if len(sys.argv) > 1 else \
               os.path.join(base, 'gen', 'guitar_clean.wav')

    if not os.path.exists(wav_path):
        print(f"ERROR: WAV not found: {wav_path}")
        sys.exit(1)

    url = f"http://localhost:{PORT}"
    print(f"Input : {wav_path}")
    print(f"UI    : {url}")
    print("Ctrl+C で終了")

    server = HTTPServer(('', PORT), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    for cmd in ['sensible-browser', 'xdg-open', 'wslview', 'explorer.exe']:
        try:
            import subprocess
            subprocess.Popen([cmd, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            break
        except FileNotFoundError:
            continue

    try:
        while not stop_event.is_set():
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        print("停止しました")
