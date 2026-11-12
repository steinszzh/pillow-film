# -*- coding: utf-8 -*-
"""3D 逐帧渲染：自写透视投影 + 面中心深度排序 + Lambert 光照；机位支持推轨 / 摇镜 / 变焦。
用法：preview / segment <idx> <n> / one <t>
"""
import sys, os, math, json, subprocess
import numpy as np
from PIL import Image, ImageDraw
import scene3d as S
from scene3d import (Mesh, camera, project_points, render, person3d, glass3d,
                     knife3d, badge3d, phone3d, parcel3d, keys3d, umbrella3d,
                     slippers3d, oximeter3d, toolbox3d)
from draw import font, flicker
from render import subtitles, VIG16, NOISES
from shots import SHOTS, FPS, DURATION, shot_at, layout_lines, act_of

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, 'frames3d')
GEOM = os.path.join(HERE, 'geom3d')
# 输出目录只在命令行运行时创建，import 本模块不产生任何副作用。
W,H = 1280,720

# ---------------------------------------------------------------- 机位表
# e0/e1 相机轨迹；q0/q1 注视点；f0/f1 视角。运动即 3D 推轨 / 摇镜 / 变焦。
def CAM(kind, p, sp):
    lerp = lambda a,b: tuple(a[i]+(b[i]-a[i])*p for i in range(3))
    if kind == 'black': return None
    base = {
      'mat_hand':      dict(e0=(1.05,.42,1.15), e1=(1.28,.36,1.45), q0=(1.62,.05,2.45), q1=(1.62,.03,2.45), f0=42,f1=36, scene='corridor'),
      'corridor_back': dict(e0=(0,1.55,-2.05), e1=(.35,1.55,-1.35), q0=(2.05,1.25,2.45), q1=(2.05,1.20,2.45), f0=54,f1=48, scene='corridor'),
      'phone_car':     dict(e0=(-.55,1.25,-.55), e1=(.35,1.22,-.35), q0=(0,1.15,2.0), q1=(0,1.15,2.0), f0=44,f1=40, scene='macro'),
      'elevator':      dict(e0=(0,1.55,-2.1), e1=(-.45,1.5,-1.35), q0=(-1.9,1.35,.55), q1=(-1.7,1.35,.7), f0=56,f1=50, scene='corridor'),
      'twoshot':       dict(e0=(-2.0,1.62,-1.15), e1=(-1.85,1.60,-1.0), q0=(-.62,1.45,1.55), q1=(-.62,1.43,1.55), f0=44,f1=42, scene='corridor'),
      'entry_parcel':  dict(e0=(.25,1.62,-1.15), e1=(-.15,1.58,-.75), q0=(-2.0,1.05,.15), q1=(-2.0,1.02,.15), f0=56,f1=50, scene='interior'),
      'sink':          dict(e0=(-.75,1.25,-.35), e1=(-1.0,1.15,.05), q0=(-2.05,.62,1.1), q1=(-2.05,.60,1.1), f0=48,f1=42, scene='interior'),
      'phone_group':   dict(e0=(-.45,1.25,-.6), e1=(.35,1.22,-.45), q0=(0,1.15,2.0), q1=(0,1.15,2.0), f0=44,f1=41, scene='macro'),
      'glass_reflection': dict(e0=(-1.0,1.62,-.85), e1=(-.75,1.60,-.6), q0=(-1.65,1.35,1.2), q1=(-1.65,1.32,1.2), f0=48,f1=44, scene='interior'),
      'two_glasses':   dict(e0=(-.55,1.28,.25), e1=(.35,1.24,.35), q0=(0,.90,2.25), q1=(0,.88,2.25), f0=46,f1=42, scene='macro'),
      'shoes':         dict(e0=(1.0,1.45,-1.1), e1=(1.25,1.4,-.7), q0=(1.62,.15,2.45), q1=(1.62,.15,2.45), f0=52,f1=48, scene='corridor'),
      'hand_knife':    dict(e0=(-.45,1.3,.15), e1=(.25,1.25,.25), q0=(0,.88,2.2), q1=(0,.88,2.2), f0=44,f1=40, scene='macro'),
      'badge':         dict(e0=(-.5,1.3,.1), e1=(.35,1.25,.2), q0=(0,1.0,2.0), q1=(0,1.0,2.0), f0=44,f1=40, scene='macro'),
      'reverse_bedroom': dict(e0=(1.55,1.62,-.55), e1=(1.40,1.60,-.40), q0=(.35,1.45,2.3), q1=(.35,1.43,2.3), f0=46,f1=43, scene='interior'),
      'table_still':   dict(e0=(0,1.62,.55), e1=(.18,1.52,.85), q0=(0,.82,2.2), q1=(0,.80,2.2), f0=48,f1=43, scene='interior'),
      'umbrella':      dict(e0=(-.15,1.45,-1.90), e1=(-.5,1.35,-1.40), q0=(-1.55,.65,.1), q1=(-1.55,.62,.1), f0=54,f1=48, scene='interior'),
      'keys':          dict(e0=(-.6,1.25,.0), e1=(.45,1.20,.15), q0=(0,.92,2.0), q1=(0,.92,2.0), f0=44,f1=40, scene='macro'),
      'chat':          dict(e0=(-.4,1.25,-.5), e1=(.3,1.22,-.4), q0=(0,1.15,2.0), q1=(0,1.15,2.0), f0=44,f1=41, scene='macro'),
      'knife_tremble': dict(e0=(-.4,1.28,.1), e1=(.3,1.24,.2), q0=(0,1.05,2.0), q1=(0,1.05,2.0), f0=42,f1=38, scene='macro'),
      'block_door':    dict(e0=(-.2,1.55,.5), e1=(.15,1.5,.9), q0=(2.25,1.2,3.15), q1=(2.25,1.18,3.15), f0=54,f1=48, scene='interior'),
      'tears':         dict(e0=(-1.95,1.65,-.15), e1=(-1.75,1.62,.05), q0=(-.55,1.48,2.1), q1=(-.55,1.45,2.1), f0=40,f1=37, scene='interior'),
      'lower_knife':   dict(e0=(.25,1.55,1.0), e1=(.55,1.52,1.3), q0=(2.25,1.15,3.15), q1=(2.45,1.1,3.3), f0=50,f1=44, scene='interior'),
      'door_side':     dict(e0=(2.30,1.40,3.28), e1=(2.34,1.38,3.34), q0=(3.9,1.2,3.55), q1=(3.9,1.15,3.55), f0=36,f1=33, scene='interior'),
      'nightstand':    dict(e0=(2.32,1.28,3.34), e1=(2.44,1.24,3.40), q0=(3.75,1.02,3.55), q1=(3.78,.98,3.55), f0=42,f1=38, scene='interior'),
      'call120':       dict(e0=(-.65,1.6,-.25), e1=(-.45,1.58,-.05), q0=(1.0,1.38,2.5), q1=(1.0,1.36,2.5), f0=50,f1=46, scene='interior'),
      'slide_down':    dict(e0=(1.05,.62,1.35), e1=(1.25,.55,1.65), q0=(2.3,.65,3.15), q1=(2.3,.55,3.15), f0=48,f1=43, scene='interior'),
      'look_back':     dict(e0=(-.5,1.6,.5), e1=(-.3,1.58,.7), q0=(1.8,1.42,2.9), q1=(1.85,1.4,2.9), f0=46,f1=42, scene='interior'),
      'reach_water':   dict(e0=(-.5,1.3,.15), e1=(.25,1.25,.25), q0=(.2,.9,2.2), q1=(.2,.9,2.2), f0=44,f1=40, scene='macro'),
    }
    d = base.get(kind)
    if d is None: return None
    if kind == 'twoshot' and sp == '老陈':
        d = dict(d, e0=(2.0,1.62,-1.15), e1=(1.85,1.60,-1.0), q0=(.62,1.45,1.55), q1=(.62,1.43,1.55))
    if kind == 'reverse_bedroom' and sp == '小雅':
        d = dict(d, e0=(-1.55,1.62,-.55), e1=(-1.40,1.60,-.40), q0=(-.35,1.45,2.3), q1=(-.35,1.43,2.3))
    if kind == 'shoes' and p < .55:
        d = dict(d, e0=(-.5,1.28,.0), e1=(.35,1.24,.1), q0=(0,1.0,2.0), q1=(0,1.0,2.0), f0=44,f1=40, scene='macro')
    if kind == 'badge' and p >= .55:
        d = dict(d, e0=(0,1.6,-1.1), e1=(.2,1.58,-.8), q0=(0,1.2,2.2), q1=(0,1.2,2.2), f0=52,f1=48, scene='interior')
    return (lerp(d['e0'],d['e1']), lerp(d['q0'],d['q1']), d['f0']+(d['f1']-d['f0'])*p, d['scene'])

# ---------------------------------------------------------------- 场景缓存
_cache = {}
def static_scene(scene, shot, p, t, sp):
    """每帧重建：门缝开合、伞架、特写道具等状态要随镜头进度变化"""
    if scene == 'corridor':
        return S.scene_corridor(elevator=(shot['id']==5), mat_lift=False, gap=False)
    if scene == 'interior':
        bed = 0.0
        if shot['id'] in (23,24,25,26,27,28,29): bed = min(1.0, .35+p*.65)
        elif shot['id'] in (21,22): bed = .12
        return S.scene_interior(bed_open=bed, door_closed=True,
                                table=(shot['id'] not in (8,9,10,17,25)),
                                umbrella_rack=(shot['id']==17))
    if scene == 'macro':
        k = shot['kind']
        if shot['id']==12 and p<.55: k='shoes'
        if shot['id']==14 and p>=.55: k='badge'
        return S.scene_macro(k, p, t)
    return Mesh()

# ---------------------------------------------------------------- 动态元素
def dynamic(m, shot, p, t, sp, scene):
    k, sid = shot['kind'], shot['id']
    if scene == 'black': return
    if scene == 'corridor':
        if sid == 2:
            # 压平地垫的手：掌 + 四指（低多边形）
            m.box((1.55,.10,2.35),(.42,.12,.42),S.SKIN)
            for i in range(4):
                m.box((1.40+i*.10,.11,2.13),(.075,.07,.30),S.SKIN)
            m.box((1.10,.03,2.52),(.30,.035,.10),S.SILVER)
            m.box((1.12,.05,2.48),(.10,.05,.08),S.GLASS,em=S.GLASS)
        elif sid == 3:
            person3d(m, 1.95, 2.45, '陈', facing=-1, pose='stand', t=t, tool=True)
        elif sid == 5:
            x = -1.95 + min(1,p*1.35)*.55
            person3d(m, x, .55, '雅', facing=1, pose='walk', t=t)
            umbrella3d(m, x-.32,.55,.55,wet=True)
            person3d(m, 1.95, 2.45, '陈', facing=-1, t=t, tool=True)
        elif sid == 6:
            person3d(m, -.62, 1.55, '雅', facing=1, t=t)
            person3d(m, .62, 1.55, '陈', facing=-1, t=t, tool=True)
        elif sid == 12:
            person3d(m, 1.55, 2.20, '陈', facing=1, t=t, pose='down')
        return
    if scene == 'macro': return   # 舞台自带道具

    # 客厅通用元素
    if sid == 7:
        parcel3d(m, -2.15, .90, -.35, 1.0)
        person3d(m, -.55, .35, '雅', facing=-1, t=t)
        person3d(m, 1.35, 1.65, '陈', facing=-1, t=t, tool=True)
    elif sid == 8:
        person3d(m, -1.55, 1.25, '陈', facing=1, pose='sit', t=t)
        toolbox3d(m, -.95, 1.55, .9)
    elif sid == 10:
        person3d(m, -1.25, 1.15, '陈', facing=1, t=t)
        m.box((-1.30,1.25,.35),(.35,.10,.35),S.SKIN)
    elif sid in (11,16,19,20):
        glass3d(m, -.45,.80,2.15,1.0); glass3d(m, .45,.80,2.15,1.0)
        knife3d(m, 0,.81,2.35,.35,1.0)
        badge3d(m, .85,.81,2.05,.9)
        if sid == 16:
            person3d(m,-1.35,2.9,'雅',facing=1,t=t)
            person3d(m, 1.35,2.9,'陈',facing=-1,t=t)
    elif sid == 14:
        badge3d(m, 0,.81,2.2,1.0)
        person3d(m,-.85,2.9,'雅',facing=1,t=t)
        person3d(m, .85,2.9,'陈',facing=-1,t=t)
    elif sid == 15:
        person3d(m,-.35,2.3,'雅',facing=1,t=t,pose='hold_knife')
        person3d(m, .35,2.3,'陈',facing=-1,t=t)
    elif sid == 17:
        pass  # 伞架已在静态场景
    elif sid == 21:
        person3d(m, 2.05,3.15,'雅',facing=-1,t=t,pose='block')
        knife3d(m,1.75,1.05,3.05,math.pi-.3,1.1)
        person3d(m, .75,2.05,'陈',facing=1,t=t)
    elif sid == 22:
        person3d(m,-.55,2.10,'雅',facing=1,t=t,pose='down')
        m.prism((-.42,1.42,2.02),.012,.05,6,S.GLASS,em=S.GLASS)
        m.box((-.25,1.05,1.95),(.28,.10,.32),S.SKIN)
    elif sid == 23:
        person3d(m, 2.05+.35*p,3.15,'雅',facing=-1,t=t,pose='down')
        knife3d(m,1.80,1.05-.55*p,3.05,.2+1.1*p,1.1)
    elif sid in (24,25):
        person3d(m, 2.12,3.02,'陈',facing=1,t=t)
    elif sid == 26:
        person3d(m, .75,2.45,'陈',facing=1,t=t,pose='cup')
        phone3d(m, 1.05,1.30,2.35,.8,lit=True)
    elif sid == 27:
        person3d(m, 2.15,3.05,'雅',facing=-1,t=t,pose='sit')
        knife3d(m,1.75,.06,2.75,math.pi-.1,1.1)
    elif sid == 28:
        person3d(m, 1.05,2.45,'陈',facing=-1,t=t)
        person3d(m, 2.15,3.15,'雅',facing=-1,t=t,pose='sit',scale=.9)
    elif sid == 29:
        pass
    if sid in (7,14,15,16,21,22,23,26,27,28):
        m.shadow(0,2.2,1.2)

# ---------------------------------------------------------------- 屏幕 UI 叠加
def ui_overlay(img, m, cam, t, p):
    if not m.ui: return
    dr = ImageDraw.Draw(img)
    for anchor, kind, pp in m.ui:
        # 把 3D 屏幕面的四角投影出来，UI 精确贴在屏幕上（随推轨一起透视）
        s3 = 2.7 if kind in ('car','group') else 2.5
        w3,h3 = .23*s3, .45*s3
        corners = np.array([[-w3/2,1.15-h3/2,1.985],[w3/2,1.15-h3/2,1.985],
                            [w3/2,1.15+h3/2,1.985],[-w3/2,1.15+h3/2,1.985]],np.float32)
        P,Z = project_points(corners,cam)
        if (Z<=.06).any(): continue
        bx0,by0 = float(P[:,0].min()), float(P[:,1].min())
        bx1,by1 = float(P[:,0].max()), float(P[:,1].max())
        if bx1-bx0 < 24 or by1-by0 < 40: continue
        sc = (by1-by0)/270.0
        w,h = int(150*sc), int(270*sc)
        cx = (bx0+bx1)/2
        cy = (by0+by1)/2
        x0,y0 = int(cx-w/2), int(cy-h/2)
        if kind=='car':
            dr.rectangle((x0,y0,x0+w,y0+h), fill=(12,20,27))
            dr.rectangle((x0+3,y0+3,x0+w-3,y0+h-3), outline=(70,86,92), width=2)
            cy2 = y0+int(h*.62)
            dr.polygon([(x0+18,cy2+26),(x0+40,cy2+6),(x0+w-40,cy2+6),
                        (x0+w-18,cy2+26),(x0+w-28,cy2+34),(x0+28,cy2+34)], fill=(8,12,16))
            dr.polygon([(x0+45,cy2+6),(x0+58,cy2-8),(x0+w-58,cy2-8),(x0+w-45,cy2+6)], fill=(14,20,25))
            dr.ellipse((x0+22,cy2+24,x0+30,cy2+30), fill=(170,58,46))
            dr.ellipse((x0+w-30,cy2+24,x0+w-22,cy2+30), fill=(170,58,46))
            for i in range(26):
                rx = (i*37+int(t*180))%w; ry = (i*53+int(t*260))%h
                dr.line([(x0+rx,y0+ry),(x0+rx-3,y0+ry+10)], fill=(40,64,76), width=1)
            if pp>.76:
                dr.rectangle((x0,y0,x0+w,y0+h), fill=(4,7,10))
                dr.text((cx,y0+34),'22:13',font=font(int(20*sc)),fill=(180,190,194),anchor='ma')
        elif kind=='group':
            dr.rectangle((x0,y0,x0+w,y0+h), fill=(222,224,222))
            dr.rectangle((x0,y0,x0+w,y0+int(26*sc)), fill=(48,54,58))
            dr.text((cx,y0+int(13*sc)),'幸福里业主群（6）',font=font(int(11*sc)),fill=(222,226,226),anchor='mm')
            msgs=['明天上午停水检修，请储水。','收到，谢谢。','【停车通知】院内划线']
            yy=y0+int(38*sc)
            for msg in msgs:
                dr.text((x0+int(7*sc),yy),'物业小李',font=font(int(8*sc)),fill=(90,100,104))
                dr.rectangle((x0+int(6*sc),yy+int(10*sc),x0+w-int(6*sc),yy+int(28*sc)),fill=(240,242,240))
                dr.text((x0+int(10*sc),yy+int(19*sc)),msg,font=font(int(9*sc)),fill=(42,48,52),anchor='lm')
                yy+=int(34*sc)
        elif kind=='chat':
            dr.rectangle((x0,y0,x0+w,y0+h), fill=(222,224,222))
            dr.rectangle((x0,y0,x0+w,y0+int(26*sc)), fill=(48,54,58))
            dr.text((cx,y0+int(13*sc)),'妈妈',font=font(int(12*sc)),fill=(222,226,226),anchor='mm')
            dr.rectangle((x0+int(6*sc),y0+int(34*sc),x0+int(90*sc),y0+int(56*sc)),fill=(240,242,240))
            dr.text((x0+int(10*sc),y0+int(45*sc)),'儿子，到哪了？',font=font(int(9*sc)),fill=(42,48,52),anchor='lm')
            dr.rectangle((x0+w-int(108*sc),y0+int(64*sc),x0+w-int(6*sc),y0+int(92*sc)),fill=(176,214,168))
            dr.text((x0+w-int(10*sc),y0+int(78*sc)),'出差，信号不好。',font=font(int(9*sc)),fill=(30,48,34),anchor='rm')
            dr.text((x0+w-int(10*sc),y0+int(100*sc)),'昨天 19:42',font=font(int(8*sc)),fill=(128,134,136),anchor='ra')

# ---------------------------------------------------------------- 帧
def speaker_at(t):
    for sp,tx,a,d in layout_lines(shot_at(t)):
        if a<=t<a+d and sp!='·': return sp
    return None

def make_geometry(m, cam):
    """烘焙 3D 面 + 光照后颜色，供网页端实时投影（可绕轨看视差）"""
    V = np.stack(m.v); eye=cam[0]
    center = V.mean(axis=1)
    n = np.cross(V[:,1]-V[:,0], V[:,2]-V[:,0])
    n = n/np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-6)
    flip = np.einsum('ij,ij->i',n,eye-center)<0
    n[flip]*=-1
    Cols = np.array(m.c,dtype=np.float32); Ems=np.array(m.em,dtype=np.float32)
    col = Cols*np.array(S.AMBIENT,np.float32)+Ems
    for lp,lc,inte,rad in m.lights:
        lv=lp-center; dist=np.linalg.norm(lv,axis=1,keepdims=True)
        ld=lv/np.maximum(dist,1e-4)
        lam=np.clip(np.einsum('ij,ij->i',n,ld),0,1)[:,None]
        att=1/(1+(dist/rad)**2)
        col += Cols*lc[None,:]*(lam*inte*att)
    c8=np.clip(col*255,0,255).astype(np.uint8)
    return dict(v=np.round(V,3).tolist(), c=c8.tolist(),
                eye=[round(float(x),3) for x in cam[0]],
                target=[round(float(x),3) for x in _last_target],
                fov=round(float(_last_fov),2))

def render_frame(t, want_geom=False):
    global _last_target,_last_fov
    shot = shot_at(t)
    p = min(1.,max(0.,(t-shot['t0'])/max(.001,shot['t1']-shot['t0'])))
    sp = speaker_at(t)
    cfg = CAM(shot['kind'], p, sp)
    if cfg is None:
        img = Image.new('RGB',(W,H),(8,11,15))
        geom = dict(v=[],c=[],eye=[0,1,-1],target=[0,1,1],fov=50)
    else:
        eye,target,fov,scene = cfg
        _last_target,_last_fov = target,fov
        cam = camera(eye,target,fov,W,H)
        m = static_scene(scene, shot, p, t, sp)
        dynamic(m, shot, p, t, sp, scene)
        fl = flicker(t) if scene=='corridor' else 1.0
        img = render(m, cam, t=t, flick=fl)
        ui_overlay(img, m, cam, t, p)
        geom = make_geometry(m,cam) if want_geom else None

    subtitles(img,t)
    fade = min(1.,(t-shot['t0'])/.28,(shot['t1']-t)/.28) if shot['id'] not in (1,30) else 1.
    arr = np.asarray(img).astype(np.uint16)
    arr = (arr*VIG16[...,None])>>8
    if fade<1: arr=(arr*int(fade*256))>>8
    a16 = arr.astype(np.int16)+NOISES[int(t*FPS)%8]
    out = Image.fromarray(np.clip(a16,0,255).astype(np.uint8),'RGB')
    return (out,geom) if want_geom else out

_last_target=(0,1,2); _last_fov=50

def preview():
    for s in SHOTS:
        t=(s['t0']+s['t1'])/2
        img,geom = render_frame(t,True)
        img.save(os.path.join(FRAMES,'shot_%02d.jpg'%s['id']),quality=88)
        with open(os.path.join(GEOM,'g%02d.json'%s['id']),'w') as f:
            json.dump(geom,f,separators=(',',':'))
        print('3D shot %02d %.1fs %s'%(s['id'],t,s['kind']),flush=True)
    sheet=Image.new('RGB',(5*320,6*180),(8,10,14)); d=ImageDraw.Draw(sheet)
    for i,s in enumerate(SHOTS):
        im=Image.open(os.path.join(FRAMES,'shot_%02d.jpg'%s['id'])).resize((320,180))
        x,y=(i%5)*320,(i//5)*180; sheet.paste(im,(x,y))
        d.rectangle((x+4,y+4,x+62,y+26),fill=(10,12,16))
        d.text((x+8,y+7),'%02d  %d:%02d'%(s['id'],s['t0']//60,s['t0']%60),fill=(226,220,200))
    sheet.save(os.path.join(HERE,'contact_sheet_3d.jpg'),quality=90)

def segment(idx,n=4):
    f0=int(idx*DURATION*FPS/n); f1=int((idx+1)*DURATION*FPS/n)
    out=os.path.join(HERE,'seg3d_%d.mp4'%idx)
    cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
         '-s','%dx%d'%(W,H),'-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast',
         '-crf','21','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',out]
    pr=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    for i in range(f0,f1):
        pr.stdin.write(render_frame(i/FPS).tobytes())
        if (i-f0)%(FPS*30)==0: print('seg3d%d %.1f/%.1f'%(idx,i/FPS,f1/FPS),flush=True)
    pr.stdin.close(); print('seg3d%d exit %d'%(idx,pr.wait()),flush=True)

if __name__=='__main__':
    os.makedirs(FRAMES,exist_ok=True); os.makedirs(GEOM,exist_ok=True)
    mode=sys.argv[1] if len(sys.argv)>1 else 'preview'
    if mode=='preview': preview()
    elif mode=='segment': segment(int(sys.argv[2]),int(sys.argv[3]) if len(sys.argv)>3 else 4)
    elif mode=='one': render_frame(float(sys.argv[2])).save(os.path.join(HERE,'one3d.png'))
    else: print('usage: render3d.py preview|segment i n|one t')
