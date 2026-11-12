# -*- coding: utf-8 -*-
"""程序化音轨：环境音与音效由 numpy 合成；对白配音可选地由在线 TTS 生成。
输出 soundtrack.wav / soundtrack.mp3。

口径说明：画面 100% 由代码绘制，不使用生成式图像或视频模型；
但对白配音依赖 edge-tts（微软在线神经语音服务），属于外部模型服务。
台词为空时本模块只合成环境音，完全不需要网络，也不需要安装 edge-tts。
"""
import os, sys, math, asyncio, subprocess
import numpy as np
import wave
from shots import SHOTS, SFX, DURATION, layout_lines

HERE = os.path.dirname(os.path.abspath(__file__))
VOICE_DIR = os.path.join(HERE, 'voices')
SR = 44100
N = int(DURATION * SR)

VOICES = {
    '小雅': ('zh-CN-XiaoxiaoNeural', '-3%'),
    '老陈': ('zh-CN-YunjianNeural', '-8%'),
    '张强': ('zh-CN-YunxiNeural', '-35%'),
}

def _tts():
    try:
        import edge_tts
    except ImportError as e:
        raise RuntimeError(
            '对白配音需要 edge-tts：pip install edge-tts；'
            '时间轴台词为空时可完全跳过，不影响画面与环境音合成。') from e
    return edge_tts


def all_lines():
    out = []
    for sh in SHOTS:
        for sp, tx, a, d in layout_lines(sh):
            if sp == '·' or not tx:
                continue
            out.append(dict(id=len(out), sp=sp, tx=tx, a=a, d=d, shot=sh['id']))
    return out

def rate_for(it):
    v = VOICES[it['sp']][1]
    if it['shot'] == 22 and it['sp'] == '小雅':
        v = '+12%'          # 镜 22 语速突然加快
    elif it['shot'] == 23 and it['sp'] == '小雅':
        v = '-12%'          # 镜 23 又慢下来
    return v

async def _one(it, sem):
    path = os.path.join(VOICE_DIR, '%03d.mp3' % it['id'])
    if os.path.exists(path) and os.path.getsize(path) > 1200:
        return
    async with sem:
        for attempt in range(3):
            try:
                voice, _ = VOICES[it['sp']]
                comm = _tts().Communicate(it['tx'], voice, rate=rate_for(it))
                await comm.save(path)
                if os.path.getsize(path) > 1200:
                    return
            except Exception as e:
                if attempt == 2:
                    print('TTS FAIL', it['id'], it['tx'][:12], e, flush=True)
                await asyncio.sleep(0.8)

async def gen_all(items):
    os.makedirs(VOICE_DIR, exist_ok=True)
    sem = asyncio.Semaphore(6)
    await asyncio.gather(*[_one(it, sem) for it in items])

def load_voice(path, atempo=1.0):
    cmd = ['ffmpeg','-v','error','-i',path,
           '-af','atempo=%.4f' % atempo, '-f','f32le','-ac','1','-ar',str(SR),'pipe:1']
    raw = subprocess.check_output(cmd)
    return np.frombuffer(raw, dtype='<f4').copy()

# ---------------------------------------------------------------- 合成工具
def tone(freq, dur, decay=0.1, amp=1.0):
    n = int(dur*SR)
    t = np.arange(n, dtype=np.float32)/SR
    return (np.sin(2*np.pi*freq*t)*np.exp(-t/decay)*amp).astype(np.float32)

def noise(dur, seed=0):
    n = int(dur*SR)
    return np.random.default_rng(seed).normal(0,1,n).astype(np.float32)

def smooth_noise(x, factor):
    """低采样率噪声线性插值回 SR，得到柔和的低频/带通噪声"""
    m = max(2, len(x)//factor)
    small = np.random.default_rng(77).normal(0,1,m).astype(np.float32)
    return np.interp(np.arange(len(x))/factor, np.arange(m), small).astype(np.float32)

def env_exp(n, decay):
    t = np.arange(n, dtype=np.float32)/SR
    return np.exp(-t/decay).astype(np.float32)

def stack(*sigs):
    """把长度不同的短音效叠加到同一时间轴"""
    n = max(len(s) for s in sigs)
    out = np.zeros(n, dtype=np.float32)
    for s in sigs:
        out[:len(s)] += s
    return out

def add(mix, t, sig, gain=1.0):
    i = int(t*SR)
    if i < 0 or i >= len(mix): return
    j = min(len(mix), i+len(sig))
    mix[i:j] += sig[:j-i]*gain

# ---------------------------------------------------------------- 主混音
def build(items):
    mix = np.zeros(N, dtype=np.float32)

    # 雨：白噪 + 两级低通噪声，走廊/室内/结尾分别给不同包络
    white = np.random.default_rng(2026).normal(0,1,N).astype(np.float32)
    mid = smooth_noise(white, 8)
    low = smooth_noise(white, 96)
    rain = white*0.048 + mid*0.052 + low*0.030
    env = np.ones(N, dtype=np.float32)
    env[55*SR:280*SR] *= 0.62                       # 室内，雨声退到背景
    env[225*SR:238*SR] *= 1.55                      # 镜 20「雨声被放大」
    env[300*SR:] = np.linspace(1.0, 0.14, N-300*SR) # 结尾雨声渐弱
    env *= (1.0 + 0.07*np.sin(2*np.pi*np.arange(N,dtype=np.float32)/SR/6.5)).astype(np.float32)
    mix += rain*env

    # 走廊日光灯电流嗡鸣（0–55s）
    t = np.arange(0, 55*SR, dtype=np.float32)/SR
    hum = (np.sin(2*np.pi*100*t)*0.55 + np.sin(2*np.pi*200*t)*0.25 +
           np.sin(2*np.pi*50*t)*0.20)
    hum *= (0.85+0.15*np.sin(2*np.pi*t/3.1))
    add(mix, 0, hum.astype(np.float32), 0.010)

    # 室内低频氛围（55–280s）
    t = np.arange(0, 225*SR, dtype=np.float32)/SR
    drone = np.sin(2*np.pi*55*t)*0.7 + np.sin(2*np.pi*82.5*t)*0.3
    add(mix, 55, drone.astype(np.float32), 0.006)

    # 血氧仪：280–320 规律，320–327 变快
    for k, tt in enumerate(np.arange(280, 320, 1.2)):
        add(mix, float(tt), tone(880, 0.10, 0.032, 0.10))
    for tt in np.arange(320, 327, 0.55):
        add(mix, float(tt), tone(920, 0.09, 0.028, 0.115))

    # 音效事件
    for tt, kind, amp in SFX:
        if kind in ('key','knife'):
            s = stack(tone(3300,0.42,0.075,0.55),
                      tone(5100,0.32,0.055,0.35),
                      noise(0.09,3)*env_exp(int(0.09*SR),0.022)*0.30)
            add(mix, tt, s, 0.42*amp)
            add(mix, tt+0.075, tone(2600,0.22,0.055,0.16), 0.30*amp)
        elif kind == 'beep':
            add(mix, tt, tone(920,0.14,0.045,0.30), 0.55*amp)
        elif kind == 'ding':
            s = stack(tone(1046,0.95,0.30,0.34), tone(1568,0.9,0.24,0.22))
            add(mix, tt, s, 0.85*amp)
        elif kind == 'flicker':
            s = stack(noise(0.16,8)*env_exp(int(0.16*SR),0.045)*0.5,
                      tone(120,0.22,0.07,0.25))
            add(mix, tt, s, 0.30*amp)
        elif kind == 'tap':
            s = stack(tone(190,0.11,0.028,0.55),
                      noise(0.07,9)*env_exp(int(0.07*SR),0.018)*0.4)
            add(mix, tt, s, 0.45*amp)
        elif kind == 'pour':
            n = int(0.95*SR)
            s = smooth_noise(np.zeros(n,np.float32), 6)
            s *= np.sin(np.pi*np.arange(n)/n)**1.2
            s += np.sin(2*np.pi*(420+180*np.arange(n)/n)*np.arange(n)/SR)*0.12
            add(mix, tt, s.astype(np.float32), 0.16*amp)
        elif kind == 'siren':
            n = int(5.0*SR)
            t = np.arange(n, dtype=np.float32)/SR
            f = 680 + 110*np.sin(2*np.pi*t/1.7)
            phase = 2*np.pi*np.cumsum(f)/SR
            s = (np.sin(phase)*0.6 + np.sin(2*phase)*0.12)
            s *= np.clip(t/4.6,0,1)**1.5
            add(mix, tt, s.astype(np.float32), 0.10*amp)

    # 台词配音
    ok = 0
    for it in items:
        path = os.path.join(VOICE_DIR, '%03d.mp3' % it['id'])
        if not os.path.exists(path):
            continue
        maxlen = max(0.35, it['d']-0.20)
        try:
            sig = load_voice(path)
            if len(sig)/SR > maxlen:
                at = min(1.9, (len(sig)/SR)/maxlen)
                sig = load_voice(path, at)
            if len(sig)/SR > maxlen:
                sig = sig[:int(maxlen*SR)]
            gain = 1.25 if it['sp']=='小雅' else (1.30 if it['sp']=='老陈' else 0.62)
            if it['sp'] == '张强':
                # 气声、干裂：压低高频 + 尾部几乎断掉
                sig = np.convolve(sig, np.ones(5,np.float32)/5, mode='same')
                sig *= np.clip(1.0 - np.arange(len(sig))/len(sig)*0.85, 0.12, 1.0)
            add(mix, it['a']+0.05, sig, gain)
            ok += 1
        except Exception as e:
            print('voice mix fail', it['id'], e, flush=True)
    print('voices mixed:', ok, '/', len(items), flush=True)

    # 软限幅 + 归一化
    mix = np.tanh(mix*1.12)/1.12
    peak = float(np.max(np.abs(mix)))
    mix *= 0.93/max(peak, 0.93)
    pcm = (np.clip(mix,-1,1)*32767).astype(np.int16)
    wav = os.path.join(HERE, 'soundtrack.wav')
    with wave.open(wav,'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    mp3 = os.path.join(HERE, 'soundtrack.mp3')
    subprocess.run(['ffmpeg','-y','-v','error','-i',wav,'-b:a','56k',mp3], check=True)
    print('audio done', wav, mp3, flush=True)

if __name__ == '__main__':
    items = all_lines()
    print('lines:', len(items), flush=True)
    if '--no-tts' not in sys.argv:
        asyncio.run(gen_all(items))
    build(items)
