# -*- coding: utf-8 -*-
"""3D 精修版（实验分支）：Blinn-Phong / 菲涅尔 / 软阴影 / 体积光 / 景深 / 超采样。
用法：preview / segment <idx> <n> / one <t>
"""
import sys, os, json, math, subprocess
from types import SimpleNamespace
import numpy as np
from PIL import Image, ImageDraw
import physics3d as P
import scenes_v2 as S
from physics3d import Geo, C, W, H, render_v2
from scenes_v2 import (person_fine, glass_fine, knife_fine, badge_fine, phone_fine,
                       parcel_fine, keys_fine, umbrella_fine, slippers_fine,
                       oximeter_fine, toolbox_fine)
from render3d import CAM, speaker_at, ui_overlay
from render import subtitles, VIG16, NOISES
from scene3d import camera
from draw import flicker
from shots import SHOTS, FPS, DURATION, shot_at, layout_lines

HERE=os.path.dirname(os.path.abspath(__file__))
FRAMES=os.path.join(HERE,'frames_v2'); GEOM=os.path.join(HERE,'geom_v2')
# 输出目录只在命令行运行时创建，import 本模块不产生任何副作用。

# ---------------------------------------------------------------- 场景
def static_v2(scene,shot,p,t,sp):
    if scene=='corridor':
        return S.corridor_v2(elevator=min(1.0,p*2.2) if shot['id']==5 else 0.0,
                             mat_lift=False)
    if scene=='interior':
        bed=0.0
        if shot['id'] in (23,24,25,26,27,28,29): bed=min(1.0,.35+p*.65)
        elif shot['id'] in (21,22): bed=.12
        return S.interior_v2(bed_open=bed,
                             table=(shot['id'] not in (8,9,10,17,25)),
                             umbrella_rack=(shot['id']==17), cold=1.0)
    if scene=='macro':
        k=shot['kind']
        if shot['id']==12 and p<.55: k='shoes'
        if shot['id']==14 and p>=.55: k='badge'
        return S.macro_v2(k,p,t)
    return Geo()

# ---------------------------------------------------------------- 动态 + 物理动画
def dynamic_v2(g,shot,p,t,sp,scene):
    sid=shot['id']
    if scene in ('black','macro'): return
    if scene=='corridor':
        if sid==2:
            g.sphere((1.55,.10,2.35),.17,P.SKIN,'skin',lat=4,lon=8)
            for i in range(4):
                g.frustum((1.40+i*.10,.11,2.13),.035,.028,.28,7,P.SKIN,'skin')
            keys_fine(g,1.10,.04,2.52,1.1)
        elif sid==3:
            person_fine(g,1.95,2.45,'陈',facing=1,pose='down',t=t,tool=True)
        elif sid==5:
            x=-1.95+min(1,p*1.35)*.55
            person_fine(g,x,.55,'雅',facing=1,pose='walk',t=t)
            umbrella_fine(g,x-.32,.55,.55,wet=True)
            person_fine(g,1.95,2.45,'陈',facing=1,t=t,tool=True)
        elif sid==6:
            person_fine(g,-.62,1.55,'雅',facing=1,t=t)
            person_fine(g,.62,1.55,'陈',facing=-1,t=t,tool=True)
        elif sid==12:
            bob=math.sin(t*9)*.02
            person_fine(g,1.55,2.20,'陈',facing=1,t=t,pose='down')
            g.box((1.55,.06+bob,2.32),(.20,.05,.28),P.DARK,mat='rubber')
        return

    if sid==7:
        parcel_fine(g,-2.15,.90,-.35,1.0)
        person_fine(g,-.55,.35,'雅',facing=-1,t=t)
        person_fine(g,1.35,1.65,'陈',facing=-1,t=t,tool=True)
    elif sid==8:
        person_fine(g,-1.55,1.25,'陈',facing=1,pose='sit',t=t)
        toolbox_fine(g,-.95,.08,1.55,.9)
    elif sid==10:
        person_fine(g,-1.25,1.15,'陈',facing=1,t=t)
        g.sphere((-1.30,1.25,.35),.13,P.SKIN,'skin',lat=4,lon=8)
    elif sid in (11,16,19,20):
        glass_fine(g,-.45,.80,2.15,1.0); glass_fine(g,.45,.80,2.15,1.0)
        knife_fine(g,0,.81,2.35,.35,1.0); badge_fine(g,.85,.81,2.05,.9)
        if sid==16:
            person_fine(g,-1.35,2.9,'雅',facing=1,t=t)
            person_fine(g,1.35,2.9,'陈',facing=-1,t=t)
    elif sid==14:
        badge_fine(g,0,.81,2.2,1.0)
        person_fine(g,-.85,2.9,'雅',facing=1,t=t)
        person_fine(g,.85,2.9,'陈',facing=-1,t=t)
    elif sid==15:
        person_fine(g,-.35,2.3,'雅',facing=1,t=t,pose='hold_knife')
        person_fine(g,.35,2.3,'陈',facing=-1,t=t)
    elif sid==21:
        person_fine(g,2.05,3.15,'雅',facing=-1,t=t,pose='block')
        knife_fine(g,1.75,1.05,3.05,math.pi-.3,1.1)
        person_fine(g,.75,2.05,'陈',facing=1,t=t)
    elif sid==22:
        person_fine(g,-.55,2.10,'雅',facing=1,t=t,pose='down')
        g.sphere((-.42,1.42,2.02),.014,C(.45,.65,.72),'water',lat=2,lon=6)
        g.sphere((-.25,1.05,1.95),.13,P.SKIN,'skin',lat=4,lon=8)
    elif sid==23:
        person_fine(g,2.05+.35*p,3.15,'雅',facing=-1,t=t,pose='down')
        knife_fine(g,1.80,1.05-.55*p,3.05,.2+1.1*p,1.1)
    elif sid in (24,25):
        person_fine(g,2.12,3.02,'陈',facing=1,t=t)
    elif sid==26:
        person_fine(g,.75,2.45,'陈',facing=1,t=t,pose='cup')
        phone_fine(g,1.05,1.30,2.35,.8,lit=True)
    elif sid==27:
        person_fine(g,2.15,3.05,'雅',facing=-1,t=t,pose='sit',scale=.98)
        # 刀落地：自由落体 → 触地反弹 → 静止，角度随角动量变化
        y0,yg=1.05,.055
        gravity=9.8; tt=math.sqrt(2*(y0-yg)/gravity)
        if p<=.55:
            u=p/.55; y=y0-(y0-yg)*u*u; ang=.2+2.4*u
        else:
            dt=(p-.55)*1.35*tt
            v0=.34*gravity*tt
            y=max(yg,yg+v0*dt-.5*gravity*dt*dt); ang=2.6+1.4*dt
        knife_fine(g,1.75,y,2.75,ang,1.1)
    elif sid==28:
        person_fine(g,1.05,2.45,'陈',facing=-1,t=t)
        person_fine(g,2.15,3.15,'雅',facing=-1,t=t,pose='sit',scale=.9)

# ---------------------------------------------------------------- 帧
def render_frame_v2(t,want_geom=False):
    shot=shot_at(t)
    p=min(1.,max(0.,(t-shot['t0'])/max(.001,shot['t1']-shot['t0'])))
    sp=speaker_at(t)
    cfg=CAM(shot['kind'],p,sp)
    if cfg is None:
        img=Image.new('RGB',(W,H),(7,10,14))
        bake=dict(v=[],c=[],a=[],u=[],eye=[0,1,-1],target=[0,1,1],fov=50)
    else:
        eye,target,fov,scene=cfg
        g=static_v2(scene,shot,p,t,sp)
        dynamic_v2(g,shot,p,t,sp,scene)
        fl=flicker(t) if scene=='corridor' else 1.0
        use_dof=scene=='macro' or shot['id'] in (2,13,14,17,18,20,24,25,29)
        range_=2.3 if scene=='macro' else 3.2
        res=render_v2(g,eye,target,fov,t=t,flick=fl,dof=use_dof,
                      dof_range=range_,return_bake=want_geom)
        img,bake=(res if want_geom else (res,None))
        if g.ui:
            ui_overlay(img,SimpleNamespace(ui=g.ui),camera(eye,target,fov,W,H),t,p)
    subtitles(img,t)
    fade=min(1.,(t-shot['t0'])/.28,(shot['t1']-t)/.28) if shot['id'] not in (1,30) else 1.
    arr=np.asarray(img).astype(np.uint16)
    arr=(arr*VIG16[...,None])>>8
    if fade<1: arr=(arr*int(fade*256))>>8
    a16=arr.astype(np.int16)+NOISES[int(t*FPS)%8]
    out=Image.fromarray(np.clip(a16,0,255).astype(np.uint8),'RGB')
    return (out,bake) if want_geom else out

# ---------------------------------------------------------------- 输出
def preview():
    for s in SHOTS:
        tm=(s['t0']+s['t1'])/2
        img,bake=render_frame_v2(tm,True)
        img.save(os.path.join(FRAMES,'shot_%02d.jpg'%s['id']),quality=90)
        with open(os.path.join(GEOM,'g%02d.json'%s['id']),'w') as f:
            json.dump(bake,f,separators=(',',':'))
        print('v2 shot %02d %.1fs %s'%(s['id'],tm,s['kind']),flush=True)
    sheet=Image.new('RGB',(5*320,6*180),(8,10,14)); d=ImageDraw.Draw(sheet)
    for i,s in enumerate(SHOTS):
        im=Image.open(os.path.join(FRAMES,'shot_%02d.jpg'%s['id'])).resize((320,180))
        x,y=(i%5)*320,(i//5)*180; sheet.paste(im,(x,y))
        d.rectangle((x+4,y+4,x+62,y+26),fill=(10,12,16))
        d.text((x+8,y+7),'%02d  %d:%02d'%(s['id'],s['t0']//60,s['t0']%60),fill=(226,220,200))
    sheet.save(os.path.join(HERE,'contact_sheet_v2.jpg'),quality=90)
    # v1 / v2 同镜对比
    picks=(3,6,11,17,24,29)
    cmp=Image.new('RGB',(2*400*2,3*225),(8,10,14)); cd=ImageDraw.Draw(cmp)
    for i,sid in enumerate(picks):
        row,col=i//2,i%2
        bx=col*800
        for k,(folder,label) in enumerate((('frames3d','v1 低多边形'),('frames_v2','v2 物理精修'))):
            im=Image.open(os.path.join(HERE,folder,'shot_%02d.jpg'%sid)).resize((400,225))
            x,y=bx+k*400,row*225
            cmp.paste(im,(x,y))
            cd.rectangle((x+4,y+4,x+150,y+26),fill=(10,12,16))
            cd.text((x+8,y+7),'镜%02d %s'%(sid,label),fill=(226,220,200))
    cmp.save(os.path.join(HERE,'compare_3d.jpg'),quality=90)

def segment(idx,n=4):
    f0=int(idx*DURATION*FPS/n); f1=int((idx+1)*DURATION*FPS/n)
    out=os.path.join(HERE,'segv2_%d.mp4'%idx)
    cmd=['ffmpeg','-y','-hide_banner','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
         '-s','%dx%d'%(W,H),'-r',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryfast',
         '-crf','20','-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',out]
    pr=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    for i in range(f0,f1):
        pr.stdin.write(render_frame_v2(i/FPS).tobytes())
        if (i-f0)%(FPS*30)==0: print('segv2_%d %.1f/%.1f'%(idx,i/FPS,f1/FPS),flush=True)
    pr.stdin.close(); print('segv2_%d exit %d'%(idx,pr.wait()),flush=True)

if __name__=='__main__':
    os.makedirs(FRAMES,exist_ok=True); os.makedirs(GEOM,exist_ok=True)
    mode=sys.argv[1] if len(sys.argv)>1 else 'preview'
    if mode=='preview': preview()
    elif mode=='segment': segment(int(sys.argv[2]),int(sys.argv[3]) if len(sys.argv)>3 else 4)
    elif mode=='one': render_frame_v2(float(sys.argv[2])).save(os.path.join(HERE,'one_v2.png'))
    else: print('usage: render3d_v2.py preview|segment i n|one t')
