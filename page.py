# -*- coding: utf-8 -*-
"""生成单文件可交互分镜放映页（关键帧内嵌，无外部依赖）。"""
import os, io, json, base64
from PIL import Image
from shots import SHOTS, DURATION, ACTS, layout_lines, act_of

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, 'frames')
OUT = os.path.join(HERE, 'storyboard.html')

def build_data():
    """读取 preview 生成的关键帧，返回 (base64 图片列表, 时间轴数据)。"""
    first = os.path.join(FRAMES, 'shot_%02d.jpg' % SHOTS[0]['id'])
    if not os.path.isfile(first):
        raise SystemExit('缺少关键帧：请先运行 python render.py preview')
    imgs = []
    for s in SHOTS:
        im = Image.open(os.path.join(FRAMES, 'shot_%02d.jpg' % s['id'])).convert('RGB')
        im = im.resize((960, 540), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=78, optimize=True)
        imgs.append('data:image/jpeg;base64,' + base64.b64encode(buf.getvalue()).decode('ascii'))

    data = []
    for s in SHOTS:
        data.append(dict(
            id=s['id'], t0=s['t0'], t1=s['t1'], size=s['size'], desc=s['desc'],
            act=act_of(s['t0']),
            lines=[[sp, tx, round(a,2), round(d,2)] for sp,tx,a,d in layout_lines(s)]))

    return imgs, data


HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pillow Film · 动态分镜</title>
<style>
:root{
  --bg:#0a0e13; --panel:#111923; --panel2:#16212c; --line:#263441;
  --warm:#d8a662; --cold:#9fd0e2; --text:#e7e5dd; --dim:#8b9aa6;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text);
  font-family:"Noto Sans CJK SC","PingFang SC","Microsoft YaHei",sans-serif}
body{min-height:100vh;padding:22px clamp(14px,3vw,38px) 30px;
  background:radial-gradient(1200px 600px at 50% -10%,#16212b 0%,var(--bg) 70%)}
.app{max-width:1560px;margin:0 auto}
header{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;
  padding-bottom:16px;border-bottom:1px solid var(--line);margin-bottom:20px;flex-wrap:wrap}
h1{font-family:"Noto Serif CJK SC",serif;font-size:clamp(26px,3vw,38px);margin:0;letter-spacing:.08em;font-weight:600}
.sub{color:var(--dim);font-size:13px;margin-top:8px;letter-spacing:.04em}
.meta{display:flex;gap:10px;flex-wrap:wrap}
.meta span{border:1px solid var(--line);border-radius:20px;padding:5px 12px;font-size:12px;color:var(--dim)}
.meta span:nth-child(3){color:var(--warm);border-color:#4d3d27}
.body{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:20px;align-items:start}
@media(max-width:1080px){.body{grid-template-columns:1fr}}
.stage{position:relative;width:100%;aspect-ratio:16/9;background:#05080b;overflow:hidden;
  border:1px solid var(--line);border-radius:10px;box-shadow:0 24px 70px rgba(0,0,0,.6)}
.frame{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;
  transition:opacity .42s ease;transform-origin:50% 55%}
.frame.on{opacity:1;animation:push var(--dur,10s) linear forwards}
@keyframes push{from{transform:scale(1)}to{transform:scale(1.055)}}
.vignette{position:absolute;inset:0;pointer-events:none;box-shadow:inset 0 0 130px 52px rgba(0,0,0,.72)}
.grain{position:absolute;inset:-30%;pointer-events:none;opacity:.055;mix-blend-mode:screen;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)'/%3E%3C/svg%3E");
  animation:grain .7s steps(3) infinite}
@keyframes grain{0%{transform:translate(0,0)}33%{transform:translate(-2%,1%)}66%{transform:translate(1%,-2%)}100%{transform:translate(0,0)}}
.hud{position:absolute;top:14px;left:16px;display:flex;gap:8px;font-size:11px;letter-spacing:.08em}
.hud span{background:rgba(8,12,16,.72);border:1px solid rgba(160,180,190,.2);
  padding:5px 10px;border-radius:4px;color:var(--cold)}
.hud span:first-child{color:var(--warm)}
.subtitle{position:absolute;left:0;right:0;bottom:5.5%;text-align:center;pointer-events:none;
  opacity:0;transition:opacity .2s ease;text-shadow:0 2px 10px rgba(0,0,0,.95)}
.subtitle.on{opacity:1}
.who{font-size:12px;letter-spacing:.18em;color:#a9b7c0;margin-bottom:7px}
.line{font-size:clamp(15px,1.75vw,25px);line-height:1.5;color:#ece6d9;padding:0 8%;
  font-family:"Noto Serif CJK SC",serif}
.paused{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  background:rgba(4,7,10,.55);font-size:15px;letter-spacing:.2em;color:var(--dim);
  transition:opacity .3s;pointer-events:none}
.paused.hide{opacity:0}
.controls{display:flex;align-items:center;gap:9px;margin-top:14px;flex-wrap:wrap}
button,select{background:var(--panel2);color:var(--text);border:1px solid var(--line);
  border-radius:6px;padding:8px 12px;font-size:13px;cursor:pointer;font-family:inherit;
  transition:border-color .2s,background .2s}
button:hover,select:hover{border-color:var(--warm);background:#1c2a35}
button.primary{background:var(--warm);color:#17120a;border-color:var(--warm);font-weight:700;min-width:44px}
#seek{flex:1;min-width:160px;accent-color:var(--warm);height:4px;cursor:pointer}
.time{font-variant-numeric:tabular-nums;font-size:12px;color:var(--dim);min-width:88px;text-align:center}
.hint{color:#61707c;font-size:11px;margin-top:9px;letter-spacing:.03em}
.info{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:18px;min-height:420px}
.info .act{color:var(--warm);font-size:12px;letter-spacing:.12em}
.info .no{font-family:"Noto Serif CJK SC",serif;font-size:40px;margin:8px 0 2px;color:var(--text)}
.info .no small{font-size:13px;color:var(--dim);font-family:inherit;margin-left:8px}
.info .size{display:inline-block;border:1px solid var(--line);border-radius:4px;
  padding:3px 9px;font-size:11px;color:var(--cold);margin:8px 0 14px}
.info .desc{font-size:13px;line-height:1.85;color:#c3cbd1;border-left:2px solid #3a4c59;padding-left:12px}
.info .lab{font-size:11px;color:#61707c;letter-spacing:.15em;margin:20px 0 8px}
.info .ln{font-size:12px;line-height:1.7;padding:5px 8px;border-radius:4px;color:#7f8d98;
  border-left:2px solid transparent;margin-bottom:2px;transition:all .2s}
.info .ln b{font-weight:400;color:#687985;margin-right:8px}
.info .ln.cur{background:#1b2833;color:#e9e4d8;border-left-color:var(--warm)}
.strip{display:grid;grid-template-columns:repeat(30,minmax(0,1fr));gap:5px;margin-top:20px}
@media(max-width:760px){.strip{grid-template-columns:repeat(10,minmax(0,1fr))}}
.thumb{position:relative;aspect-ratio:16/9;border:1px solid var(--line);border-radius:4px;
  overflow:hidden;cursor:pointer;padding:0;background:#0b1015;transition:transform .2s,border-color .2s}
.thumb img{width:100%;height:100%;object-fit:cover;display:block;opacity:.62;transition:opacity .2s}
.thumb:hover{transform:translateY(-3px);border-color:var(--warm)}
.thumb:hover img{opacity:1}
.thumb.cur{border-color:var(--warm);box-shadow:0 0 0 1px var(--warm)}
.thumb.cur img{opacity:1}
.thumb i{position:absolute;left:3px;top:2px;font-style:normal;font-size:9px;color:#fff;
  text-shadow:0 1px 3px #000;letter-spacing:.02em}
footer{margin-top:22px;padding-top:16px;border-top:1px solid var(--line);
  display:flex;justify-content:space-between;gap:14px;flex-wrap:wrap;
  font-size:12px;color:#6d7d88;line-height:1.8}
footer a{color:var(--cold);text-decoration:none;border-bottom:1px dotted #4b6b7b}
footer a:hover{color:var(--warm)}
.tag{color:var(--warm)}
</style>
</head>
<body>
<div class="app">
  <header>
    <div>
      <h1>Pillow Film · 动态分镜</h1>
      <div class="sub">动态分镜 · 30 镜全片 · 画面与音效均由代码绘制／合成，未使用文生图或视频生成模型</div>
    </div>
    <div class="meta"><span>5 分 30 秒</span><span>30 镜</span><span>16:9</span><span>雨夜 · 悬疑</span><span>2 人出镜 + 1 个不露脸的声音</span></div>
  </header>

  <div class="body">
    <section>
      <div class="stage" id="stage">
        <img class="frame on" id="imA" alt="分镜画面">
        <img class="frame" id="imB" alt="分镜画面">
        <div class="vignette"></div><div class="grain"></div>
        <div class="hud"><span id="actTag"></span><span id="shotTag"></span></div>
        <div class="subtitle" id="sub"><div class="who" id="who"></div><div class="line" id="line"></div></div>
        <div class="paused" id="pausedBadge">按 空格 播放　·　5:30 全片</div>
      </div>
      <div class="controls">
        <button class="primary" id="play" title="播放/暂停">▶</button>
        <button id="prev" title="上一镜">⏮</button><button id="next" title="下一镜">⏭</button>
        <div class="time" id="time">0:00 / 5:30</div>
        <input type="range" id="seek" min="0" max="330" step="0.1" value="0">
        <select id="speed" title="倍速"><option value="1">1×</option><option value="2">2×</option><option value="4">4×</option></select>
        <button id="subs" title="字幕开关">字幕 开</button>
        <button id="mute" title="声音开关">声音 开</button>
      </div>
      <div class="hint">空格 播放／暂停　·　← → 切换镜头　·　拖动进度条跳转　·　点击缩略图直达　·　倍速会同步改变配音速度</div>
    </section>

    <aside class="info">
      <div class="act" id="infoAct"></div>
      <div class="no" id="infoNo"></div>
      <div class="size" id="infoSize"></div>
      <div class="desc" id="infoDesc"></div>
      <div class="lab">本 镜 台 词</div>
      <div id="infoLines"></div>
    </aside>
  </div>

  <div class="strip" id="strip"></div>

  <footer>
    <div>示例工程：画面由 Pillow 逐帧绘制，关键帧内嵌于本页，无外部资源依赖。</div>
    <div>时间轴见 shots.py（中性占位文案）；运行 python render.py preview 生成关键帧，再运行 python page.py 重建本页。</div>
  </footer>
</div>
<audio id="au" preload="none"></audio>

<script>
const SHOTS = __DATA__;
const IMGS  = __IMGS__;
const ACTS  = __ACTS__;
const DUR = 330;
let t = 0, playing = false, speed = 1, showSubs = true, curId = 0, front = 'A';
let last = 0, auReady = false, muted = false;
const $ = id => document.getElementById(id);
const au = $('au');
const fmt = s => Math.floor(s/60) + ':' + String(Math.floor(s%60)).padStart(2,'0');

// 缩略图条
const strip = $('strip');
SHOTS.forEach((s,i)=>{
  const b = document.createElement('button');
  b.className = 'thumb'; b.dataset.id = s.id;
  b.innerHTML = '<img src="'+IMGS[i]+'" alt="镜 '+s.id+'"><i>'+s.id+'</i>';
  b.title = '镜 '+s.id+' · '+fmt(s.t0)+' · '+s.size;
  b.onclick = ()=> seek(s.t0 + 0.05);
  strip.appendChild(b);
});
const thumbs = Array.from(document.querySelectorAll('.thumb'));

function shotAt(x){ return SHOTS.find(s=> x>=s.t0 && x<s.t1) || SHOTS[SHOTS.length-1]; }

function setShot(s, instant){
  if(s.id === curId && !instant) return;
  curId = s.id;
  const hidden = front === 'A' ? $('imB') : $('imA');
  const shown  = front === 'A' ? $('imA') : $('imB');
  hidden.src = IMGS[s.id-1];
  hidden.style.setProperty('--dur', (s.t1-s.t0)+'s');
  hidden.classList.remove('on');
  void hidden.offsetWidth;
  if(instant){ shown.classList.remove('on'); }
  hidden.classList.add('on');
  shown.classList.remove('on');
  front = front === 'A' ? 'B' : 'A';
  $('actTag').textContent = s.act;
  $('shotTag').textContent = '镜 ' + String(s.id).padStart(2,'0') + '　' + fmt(s.t0) + '–' + fmt(s.t1);
  $('infoAct').textContent = s.act;
  $('infoNo').innerHTML = String(s.id).padStart(2,'0') + '<small>/ 30 镜</small>';
  $('infoSize').textContent = s.size;
  $('infoDesc').textContent = s.desc;
  const box = $('infoLines'); box.innerHTML = '';
  const ls = s.lines.filter(l=> l[0] !== '·');
  if(!ls.length){ box.innerHTML = '<div class="ln" style="color:#5c6a75">（无台词 · 声音与静物叙事）</div>'; }
  ls.forEach(l=>{
    const d = document.createElement('div');
    d.className = 'ln'; d.dataset.a = l[2]; d.dataset.b = (l[2]+l[3]);
    d.innerHTML = '<b>'+l[0]+'</b>'+ (l[0]==='张强' ? '（画外）' : '') + l[1];
    box.appendChild(d);
  });
  thumbs.forEach(b=> b.classList.toggle('cur', +b.dataset.id === s.id));
}

function updateSub(s){
  const sub = $('sub');
  if(!showSubs){ sub.classList.remove('on'); return; }
  const l = s.lines.find(l=> l[0] !== '·' && t >= l[2] && t < l[2]+l[3]);
  if(!l){ sub.classList.remove('on'); } else {
    $('who').textContent = l[0] === '张强' ? '张强（画外）' : l[0];
    $('line').textContent = l[1];
    sub.classList.add('on');
  }
  const nodes = $('infoLines').querySelectorAll('.ln');
  nodes.forEach(n=>{
    const a = +n.dataset.a, b = +n.dataset.b;
    n.classList.toggle('cur', l && +l[2]===a && t>=a && t<b);
  });
}

function render(instant){
  if(t >= DUR) t = DUR;
  const s = shotAt(t);
  setShot(s, !!instant);
  updateSub(s);
  $('time').textContent = fmt(t) + ' / 5:30';
  $('seek').value = t;
  $('pausedBadge').classList.toggle('hide', playing || t>0);
}

function syncAudio(force){
  if(!auReady) return;
  try{
    au.playbackRate = speed;
    if(force || Math.abs(au.currentTime - t) > 0.35) au.currentTime = t;
    if(playing && t < DUR && au.paused){ const p = au.play(); if(p && p.catch) p.catch(()=>{}); }
    if(!playing && !au.paused) au.pause();
  }catch(e){}
}

function play(on){
  playing = (on === undefined) ? !playing : on;
  $('play').textContent = playing ? '❚❚' : '▶';
  if(playing && t >= DUR) t = 0;
  $('pausedBadge').classList.toggle('hide', playing || t>0);
  syncAudio(true);
}
function seek(x){ t = Math.max(0, Math.min(DUR, x)); render(true); syncAudio(true); }
function jump(d){
  const s = shotAt(t);
  const i = SHOTS.indexOf(s);
  const j = Math.max(0, Math.min(SHOTS.length-1, i+d));
  seek(SHOTS[j].t0 + 0.05);
}

$('play').onclick = ()=> play();
$('prev').onclick = ()=> jump(-1);
$('next').onclick = ()=> jump(1);
$('seek').oninput = e => seek(+e.target.value);
$('speed').onchange = e => { speed = +e.target.value; syncAudio(false); };
$('subs').onclick = e => { showSubs = !showSubs; e.target.textContent = '字幕 ' + (showSubs?'开':'关'); updateSub(shotAt(t)); };
$('mute').onclick = e => { muted = !muted; au.muted = muted; e.target.textContent = '声音 ' + (muted?'关':'开'); };
au.addEventListener('loadedmetadata', ()=>{ auReady = true; au.playbackRate = speed; });
au.addEventListener('error', ()=>{ auReady = false; $('mute').textContent = '声音不可用'; $('mute').disabled = true; });
document.addEventListener('keydown', e=>{
  if(e.code==='Space'){ e.preventDefault(); play(); }
  else if(e.code==='ArrowLeft'){ e.preventDefault(); jump(-1); }
  else if(e.code==='ArrowRight'){ e.preventDefault(); jump(1); }
  else if(e.code==='Home'){ seek(0); }
  else if(e.code==='End'){ seek(DUR-0.1); }
});

function loop(ts){
  if(!last) last = ts;
  const dt = Math.min(0.25, (ts-last)/1000);
  last = ts;
  if(playing){
    t += dt*speed;
    if(t >= DUR){ t = DUR; play(false); }
    render(false);
    if(Math.floor(ts/700) !== Math.floor((ts-dt*1000)/700)) syncAudio(false);
  }
  requestAnimationFrame(loop);
}

setShot(SHOTS[0], true);
$('imA').src = IMGS[0];
$('imA').classList.add('on');
render(true);
requestAnimationFrame(loop);
</script>
</body>
</html>
'''

def main():
    imgs, data = build_data()
    html = (HTML.replace('__DATA__', json.dumps(data, ensure_ascii=False))
                .replace('__IMGS__', json.dumps(imgs))
                .replace('__ACTS__', json.dumps([a[0] for a in ACTS], ensure_ascii=False)))
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print('page:', OUT, '%.2f MB' % (os.path.getsize(OUT)/1024/1024))


if __name__ == '__main__':
    main()
