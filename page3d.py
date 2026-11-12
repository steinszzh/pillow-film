# -*- coding: utf-8 -*-
"""生成单文件 3D 交互放映页：内嵌每镜烘焙的 3D 几何，浏览器里实时投影，可绕轨旋转视角。"""
import os, io, json, base64
from PIL import Image
from shots import SHOTS, DURATION, layout_lines, act_of

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'storyboard-3d.html')

def build_data():
    """读取 3D 烘焙几何与关键帧，返回 (几何, 缩略图, 时间轴数据)。"""
    first = os.path.join(HERE, 'geom3d', 'g%02d.json' % SHOTS[0]['id'])
    if not os.path.isfile(first):
        raise SystemExit('缺少 3D 烘焙几何：请先运行 python render3d.py preview')
    geoms, thumbs, data = [], [], []
    for s in SHOTS:
        with open(os.path.join(HERE,'geom3d','g%02d.json'%s['id'])) as f:
            geoms.append(json.load(f))
        im = Image.open(os.path.join(HERE,'frames3d','shot_%02d.jpg'%s['id'])).convert('RGB').resize((240,135),Image.LANCZOS)
        buf = io.BytesIO(); im.save(buf,'JPEG',quality=70,optimize=True)
        thumbs.append('data:image/jpeg;base64,'+base64.b64encode(buf.getvalue()).decode('ascii'))
        data.append(dict(id=s['id'],t0=s['t0'],t1=s['t1'],size=s['size'],desc=s['desc'],
                         act=act_of(s['t0']),
                         lines=[[sp,tx,round(a,2),round(d,2)] for sp,tx,a,d in layout_lines(s)]))

    return geoms, thumbs, data


HTML = r'''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pillow Film · 3D 动态分镜</title>
<style>
:root{--bg:#0a0e13;--panel:#111923;--panel2:#16212c;--line:#263441;--warm:#d8a662;--cold:#9fd0e2;--text:#e7e5dd;--dim:#8b9aa6}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text);font-family:"Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif}
body{min-height:100vh;padding:22px clamp(14px,3vw,38px) 30px;background:radial-gradient(1200px 600px at 50% -10%,#16212b 0%,var(--bg) 70%)}
.app{max-width:1560px;margin:0 auto}
header{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;padding-bottom:16px;border-bottom:1px solid var(--line);margin-bottom:20px;flex-wrap:wrap}
h1{font-family:"Noto Serif CJK SC",serif;font-size:clamp(26px,3vw,38px);margin:0;letter-spacing:.08em;font-weight:600}
.sub{color:var(--dim);font-size:13px;margin-top:8px;letter-spacing:.04em}
.meta{display:flex;gap:10px;flex-wrap:wrap}
.meta span{border:1px solid var(--line);border-radius:20px;padding:5px 12px;font-size:12px;color:var(--dim)}
.meta span.hi{color:var(--cold);border-color:#34505e}
.body{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:20px;align-items:start}
@media(max-width:1080px){.body{grid-template-columns:1fr}}
.stage{position:relative;width:100%;aspect-ratio:16/9;background:#05080b;overflow:hidden;border:1px solid var(--line);border-radius:10px;box-shadow:0 24px 70px rgba(0,0,0,.6);cursor:grab}
.stage:active{cursor:grabbing}
canvas{display:block;width:100%;height:100%}
.vignette{position:absolute;inset:0;pointer-events:none;box-shadow:inset 0 0 130px 52px rgba(0,0,0,.68)}
.hud{position:absolute;top:14px;left:16px;display:flex;gap:8px;font-size:11px;letter-spacing:.08em;pointer-events:none}
.hud span{background:rgba(8,12,16,.72);border:1px solid rgba(160,180,190,.2);padding:5px 10px;border-radius:4px;color:var(--cold)}
.hud span:first-child{color:var(--warm)}
.viewbadge{position:absolute;top:14px;right:16px;font-size:11px;color:var(--dim);background:rgba(8,12,16,.72);border:1px solid var(--line);padding:5px 10px;border-radius:4px;pointer-events:none}
.subtitle{position:absolute;left:0;right:0;bottom:5.5%;text-align:center;pointer-events:none;opacity:0;transition:opacity .2s;text-shadow:0 2px 10px rgba(0,0,0,.95)}
.subtitle.on{opacity:1}
.who{font-size:12px;letter-spacing:.18em;color:#a9b7c0;margin-bottom:7px}
.line{font-size:clamp(15px,1.75vw,25px);line-height:1.5;color:#ece6d9;padding:0 8%;font-family:"Noto Serif CJK SC",serif}
.paused{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(4,7,10,.5);font-size:15px;letter-spacing:.18em;color:var(--dim);transition:opacity .3s;pointer-events:none;text-align:center;line-height:2}
.paused.hide{opacity:0}
.controls{display:flex;align-items:center;gap:9px;margin-top:14px;flex-wrap:wrap}
button,select{background:var(--panel2);color:var(--text);border:1px solid var(--line);border-radius:6px;padding:8px 12px;font-size:13px;cursor:pointer;font-family:inherit;transition:border-color .2s,background .2s}
button:hover,select:hover{border-color:var(--warm);background:#1c2a35}
button.primary{background:var(--warm);color:#17120a;border-color:var(--warm);font-weight:700;min-width:44px}
#seek{flex:1;min-width:160px;accent-color:var(--warm);height:4px;cursor:pointer}
.time{font-variant-numeric:tabular-nums;font-size:12px;color:var(--dim);min-width:88px;text-align:center}
.hint{color:#61707c;font-size:11px;margin-top:9px;letter-spacing:.03em}
.info{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px;min-height:420px}
.info .act{color:var(--warm);font-size:12px;letter-spacing:.12em}
.info .no{font-family:"Noto Serif CJK SC",serif;font-size:40px;margin:8px 0 2px}
.info .no small{font-size:13px;color:var(--dim);font-family:inherit;margin-left:8px}
.info .size{display:inline-block;border:1px solid var(--line);border-radius:4px;padding:3px 9px;font-size:11px;color:var(--cold);margin:8px 0 14px}
.info .desc{font-size:13px;line-height:1.85;color:#c3cbd1;border-left:2px solid #3a4c59;padding-left:12px}
.info .lab{font-size:11px;color:#61707c;letter-spacing:.15em;margin:20px 0 8px}
.info .ln{font-size:12px;line-height:1.7;padding:5px 8px;border-radius:4px;color:#7f8d98;border-left:2px solid transparent;margin-bottom:2px;transition:all .2s}
.info .ln b{font-weight:400;color:#687985;margin-right:8px}
.info .ln.cur{background:#1b2833;color:#e9e4d8;border-left-color:var(--warm)}
.info .tech{font-size:11px;line-height:1.9;color:#6d7d88;border-top:1px solid var(--line);margin-top:18px;padding-top:12px}
.strip{display:grid;grid-template-columns:repeat(30,minmax(0,1fr));gap:5px;margin-top:20px}
@media(max-width:760px){.strip{grid-template-columns:repeat(10,minmax(0,1fr))}}
.thumb{position:relative;aspect-ratio:16/9;border:1px solid var(--line);border-radius:4px;overflow:hidden;cursor:pointer;padding:0;background:#0b1015;transition:transform .2s,border-color .2s}
.thumb img{width:100%;height:100%;object-fit:cover;display:block;opacity:.62;transition:opacity .2s}
.thumb:hover{transform:translateY(-3px);border-color:var(--warm)}
.thumb:hover img{opacity:1}
.thumb.cur{border-color:var(--cold);box-shadow:0 0 0 1px var(--cold)}
.thumb.cur img{opacity:1}
.thumb i{position:absolute;left:3px;top:2px;font-style:normal;font-size:9px;color:#fff;text-shadow:0 1px 3px #000}
footer{margin-top:22px;padding-top:16px;border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;font-size:12px;color:#6d7d88;line-height:1.8}
footer a{color:var(--cold);text-decoration:none;border-bottom:1px dotted #4b6b7b}
footer a:hover{color:var(--warm)}
</style></head><body>
<div class="app">
<header><div><h1>Pillow Film <span style="font-size:.5em;color:var(--cold);letter-spacing:.1em">3D</span></h1>
<div class="sub">软件光栅化 3D 动态分镜 · 透视投影 / 深度排序 / 逐面光照 · 拖动可绕轨看视差</div></div>
<div class="meta"><span class="hi">真 3D 几何</span><span>5 分 30 秒</span><span>30 镜</span><span>16:9</span><span>无生成模型</span></div></header>
<div class="body">
<section>
  <div class="stage" id="stage">
    <canvas id="cv" width="1280" height="720"></canvas>
    <div class="vignette"></div>
    <div class="hud"><span id="actTag"></span><span id="shotTag"></span></div>
    <div class="viewbadge" id="viewBadge">自由视角：拖动旋转 · 滚轮变焦 · 双击复位</div>
    <div class="subtitle" id="sub"><div class="who" id="who"></div><div class="line" id="line"></div></div>
    <div class="paused" id="pausedBadge">按 空格 播放全片<br><span style="font-size:11px">画面为浏览器实时投影的 3D 几何，可任意旋转视角</span></div>
  </div>
  <div class="controls">
    <button class="primary" id="play" title="播放/暂停">▶</button>
    <button id="prev">⏮</button><button id="next">⏭</button>
    <div class="time" id="time">0:00 / 5:30</div>
    <input type="range" id="seek" min="0" max="330" step="0.1" value="0">
    <select id="speed"><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option></select>
    <button id="reset" title="复位视角">视角复位</button>
    <button id="subs">字幕 开</button>
    <button id="mute">声音 开</button>
  </div>
  <div class="hint">空格 播放／暂停 · ← → 切镜 · 拖动进度条跳转 · 倍速同步配音 · 鼠标拖动绕轨旋转、滚轮变焦</div>
</section>
<aside class="info">
  <div class="act" id="infoAct"></div><div class="no" id="infoNo"></div>
  <div class="size" id="infoSize"></div><div class="desc" id="infoDesc"></div>
  <div class="lab">本 镜 台 词</div><div id="infoLines"></div>
  <div class="tech">渲染：Python 逐帧构建 3D 面 → numpy 批量透视投影与 Lambert 光照 → 深度排序 → Pillow 多边形绘制 → ffmpeg 编码。<br>
  本页几何为同一渲染器烘焙的 3D 顶点与光照色，浏览器端只做投影，因此旋转视角会看到真实遮挡与视差。</div>
</aside></div>
<div class="strip" id="strip"></div>
<footer><div>示例工程：3D 面顶点与光照色由 Python 渲染器烘焙后内嵌，浏览器只做投影 / 深度排序 / 填充。</div>
<div>拖动可绕轨旋转视角，得到真实遮挡与视差。运行 python render3d.py preview 生成几何，再运行 python page3d.py 重建本页。</div></footer>
</div>
<audio id="au" preload="none"></audio>
<script>
const SHOTS=__DATA__, GEOM=__GEOM__, THUMBS=__THUMBS__, DUR=330;
let t=0,playing=false,speed=1,showSubs=true,curId=0,last=0,auReady=false,muted=false;
let yaw=0,pitch=0,userDist=1,dragging=false,lx=0,ly=0;
const $=id=>document.getElementById(id), au=$('au');
const cv=$('cv'), ctx=cv.getContext('2d'), W=cv.width, H=cv.height;
const fmt=s=>Math.floor(s/60)+':'+String(Math.floor(s%60)).padStart(2,'0');
const sub=(a,b)=>[a[0]-b[0],a[1]-b[1],a[2]-b[2]];
const dot=(a,b)=>a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>{const n=Math.hypot(a[0],a[1],a[2])||1;return [a[0]/n,a[1]/n,a[2]/n]};

function eyeRot(g,dist){
  const d=sub(g.eye,g.target);
  const r2=d[0]*Math.cos(yaw)-d[2]*Math.sin(yaw);
  const f2=d[0]*Math.sin(yaw)+d[2]*Math.cos(yaw);
  let horiz=Math.hypot(r2,f2)||0.0001;
  const ang=Math.atan2(d[1],horiz)+pitch;
  const len=Math.hypot(d[0],d[1],d[2])*dist;
  const ux=r2/horiz, uz=f2/horiz;
  return [g.target[0]+ux*Math.cos(ang)*len, g.target[1]+Math.sin(ang)*len, g.target[2]+uz*Math.cos(ang)*len];
}
function basis(eye,target){
  const f=norm(sub(target,eye)), r=norm(cross(f,[0,1,0]));
  return {eye,f,r,u:cross(r,f)};
}
function draw3D(g,p){
  const dist=userDist*(1-0.055*p);
  const fov=Math.max(20,g.fov-2.2*p);
  const b=basis(eyeRot(g,dist),g.target);
  const scale=(H/2)/Math.tan(fov*Math.PI/360);
  const list=[];
  for(let i=0;i<g.v.length;i++){
    const q=g.v[i]; let ok=true, pts=[],z=0;
    for(let j=0;j<4;j++){
      const d=sub(q[j],b.eye), zz=dot(d,b.f);
      if(zz<=0.06){ok=false;break}
      pts.push([W/2+dot(d,b.r)*scale/zz, H/2-dot(d,b.u)*scale/zz]); z+=zz;
    }
    if(ok) list.push({pts,z:z/4,c:g.c[i]});
  }
  list.sort((a,b)=>b.z-a.z);
  ctx.fillStyle='#070a0e'; ctx.fillRect(0,0,W,H);
  for(const f of list){
    ctx.beginPath(); ctx.moveTo(f.pts[0][0],f.pts[0][1]);
    for(let j=1;j<4;j++) ctx.lineTo(f.pts[j][0],f.pts[j][1]);
    ctx.closePath();
    ctx.fillStyle='rgb('+f.c[0]+','+f.c[1]+','+f.c[2]+')'; ctx.fill();
    ctx.strokeStyle='rgba(0,0,0,.32)'; ctx.lineWidth=1; ctx.stroke();
  }
}
function shotAt(x){return SHOTS.find(s=>x>=s.t0&&x<s.t1)||SHOTS[SHOTS.length-1]}
function setShot(s){
  if(s.id===curId)return; curId=s.id;
  $('actTag').textContent=s.act;
  $('shotTag').textContent='镜 '+String(s.id).padStart(2,'0')+'　'+fmt(s.t0)+'–'+fmt(s.t1);
  $('infoAct').textContent=s.act;
  $('infoNo').innerHTML=String(s.id).padStart(2,'0')+'<small>/ 30 镜</small>';
  $('infoSize').textContent=s.size; $('infoDesc').textContent=s.desc;
  const box=$('infoLines'); box.innerHTML='';
  const ls=s.lines.filter(l=>l[0]!=='·');
  if(!ls.length) box.innerHTML='<div class="ln" style="color:#5c6a75">（无台词 · 声音与静物叙事）</div>';
  ls.forEach(l=>{const d=document.createElement('div');d.className='ln';d.dataset.a=l[2];d.dataset.b=l[2]+l[3];
    d.innerHTML='<b>'+l[0]+'</b>'+(l[0]==='张强'?'（画外）':'')+l[1];box.appendChild(d)});
  document.querySelectorAll('.thumb').forEach(b=>b.classList.toggle('cur',+b.dataset.id===s.id));
}
function updateSub(s){
  if(!showSubs){$('sub').classList.remove('on');return}
  const l=s.lines.find(l=>l[0]!=='·'&&t>=l[2]&&t<l[2]+l[3]);
  if(!l)$('sub').classList.remove('on');
  else{$('who').textContent=l[0]==='张强'?'张强（画外）':l[0];$('line').textContent=l[1];$('sub').classList.add('on')}
  document.querySelectorAll('#infoLines .ln').forEach(n=>{
    n.classList.toggle('cur',!!l&&+n.dataset.a===+l[2]&&t>=+n.dataset.a&&t<+n.dataset.b)});
}
function render(){
  const s=shotAt(t); setShot(s); updateSub(s);
  const p=Math.max(0,Math.min(1,(t-s.t0)/(s.t1-s.t0)));
  draw3D(GEOM[s.id-1],p);
  $('time').textContent=fmt(t)+' / 5:30'; $('seek').value=t;
  $('pausedBadge').classList.toggle('hide',playing||t>0);
  $('viewBadge').textContent=(yaw||pitch||userDist!==1)?'自由视角 · 双击复位':'自由视角：拖动旋转 · 滚轮变焦';
}
function syncAudio(force){
  if(!auReady)return;
  try{au.playbackRate=speed;
    if(force||Math.abs(au.currentTime-t)>0.35)au.currentTime=t;
    if(playing&&t<DUR&&au.paused){const q=au.play();if(q&&q.catch)q.catch(()=>{})}
    if(!playing&&!au.paused)au.pause();
  }catch(e){}
}
function play(on){playing=(on===undefined)?!playing:on;$('play').textContent=playing?'❚❚':'▶';
  if(playing&&t>=DUR)t=0;$('pausedBadge').classList.toggle('hide',playing||t>0);syncAudio(true)}
function seek(x){t=Math.max(0,Math.min(DUR,x));render();syncAudio(true)}
function jump(d){const i=SHOTS.indexOf(shotAt(t));seek(SHOTS[Math.max(0,Math.min(29,i+d))].t0+.05)}
function resetView(){yaw=0;pitch=0;userDist=1;render()}

const strip=$('strip');
SHOTS.forEach((s,i)=>{const b=document.createElement('button');b.className='thumb';b.dataset.id=s.id;
  b.innerHTML='<img src="'+THUMBS[i]+'" alt="镜 '+s.id+'"><i>'+s.id+'</i>';
  b.title='镜 '+s.id+' · '+fmt(s.t0)+' · '+s.size;b.onclick=()=>seek(s.t0+.05);strip.appendChild(b)});

$('play').onclick=()=>play(); $('prev').onclick=()=>jump(-1); $('next').onclick=()=>jump(1);
$('seek').oninput=e=>seek(+e.target.value);
$('speed').onchange=e=>{speed=+e.target.value;syncAudio(false)};
$('subs').onclick=e=>{showSubs=!showSubs;e.target.textContent='字幕 '+(showSubs?'开':'关');updateSub(shotAt(t))};
$('mute').onclick=e=>{muted=!muted;au.muted=muted;e.target.textContent='声音 '+(muted?'关':'开')};
$('reset').onclick=resetView;
au.addEventListener('loadedmetadata',()=>{auReady=true;au.playbackRate=speed});
au.addEventListener('error',()=>{auReady=false;$('mute').textContent='声音不可用';$('mute').disabled=true});
document.addEventListener('keydown',e=>{
  if(e.code==='Space'){e.preventDefault();play()}
  else if(e.code==='ArrowLeft'){e.preventDefault();jump(-1)}
  else if(e.code==='ArrowRight'){e.preventDefault();jump(1)}
  else if(e.code==='Home')seek(0); else if(e.code==='End')seek(DUR-.1);
});
const stage=$('stage');
stage.addEventListener('mousedown',e=>{dragging=true;lx=e.clientX;ly=e.clientY});
window.addEventListener('mouseup',()=>{dragging=false});
window.addEventListener('mousemove',e=>{if(!dragging)return;
  yaw+=(e.clientX-lx)*.006; pitch=Math.max(-.75,Math.min(.75,pitch-(e.clientY-ly)*.004));
  lx=e.clientX;ly=e.clientY;render()});
stage.addEventListener('wheel',e=>{e.preventDefault();userDist=Math.max(.45,Math.min(2.2,userDist*(1+e.deltaY*.0012)));render()},{passive:false});
stage.addEventListener('dblclick',resetView);
function loop(ts){
  if(!last)last=ts; const dt=Math.min(.25,(ts-last)/1000); last=ts;
  if(playing){t+=dt*speed;if(t>=DUR){t=DUR;play(false)}render();
    if(Math.floor(ts/700)!==Math.floor((ts-dt*1000)/700))syncAudio(false)}
  requestAnimationFrame(loop);
}
render(); requestAnimationFrame(loop);
</script></body></html>
'''

def main():
    geoms, thumbs, data = build_data()
    html = (HTML.replace('__DATA__', json.dumps(data, ensure_ascii=False))
                .replace('__GEOM__', json.dumps(geoms, separators=(',', ':')))
                .replace('__THUMBS__', json.dumps(thumbs)))
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print('3d page:', OUT, '%.2f MB' % (os.path.getsize(OUT)/1024/1024))


if __name__ == '__main__':
    main()
