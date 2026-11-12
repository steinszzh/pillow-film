# -*- coding: utf-8 -*-
"""2D 逐帧渲染器：Pillow 绘制 → ffmpeg 管道编码。纯代码绘制，无图像 / 视频生成模型。
用法：
  python render.py preview   # 导出 30 张关键帧 + 拼板
  python render.py full      # 逐帧写入 ffmpeg，输出无声 MP4
"""
import sys, os, math, random, subprocess
import numpy as np
from PIL import Image, ImageDraw
import draw as D
from draw import (Canvas, BW, BH, OW, OH, BG, WARM, WARM_D, COLD, COLD_D,
                  INK, SILVER, TEXT, font, flicker, rain, corridor, interior,
                  void, doorcrack, nightstand, glass, knife, badge, phone,
                  parcel, keys, umbrella, slippers, toolbox, hand, person)
from shots import SHOTS, FPS, DURATION, shot_at, layout_lines, act_of, W, H

HERE = os.path.dirname(os.path.abspath(__file__))
FRAMES = os.path.join(HERE, 'frames')
# 输出目录只在命令行运行时创建，import 本模块不产生任何副作用。

# 镜头相机：(z0, z1, cx, cy)  缓推/固定机位
CAM = {
    2:(1.30,1.30,0.68,0.86), 3:(1.05,1.08,0.62,0.52), 4:(1.0,1.0,0.5,0.5),
    5:(1.0,1.04,0.42,0.55),  6:(1.0,1.0,0.5,0.5),     7:(1.0,1.06,0.42,0.6),
    8:(1.18,1.18,0.30,0.60), 9:(1.0,1.0,0.5,0.5),    10:(1.15,1.15,0.48,0.55),
    11:(1.06,1.06,0.52,0.62),12:(1.0,1.0,0.5,0.5),   13:(1.22,1.22,0.60,0.65),
    14:(1.0,1.0,0.5,0.5),   15:(1.06,1.06,0.5,0.5),  16:(1.10,1.10,0.5,0.64),
    17:(1.0,1.12,0.46,0.58),18:(1.0,1.0,0.5,0.5),    19:(1.0,1.0,0.5,0.5),
    20:(1.04,1.10,0.52,0.52),21:(1.0,1.0,0.68,0.52), 22:(1.26,1.26,0.46,0.42),
    23:(1.0,1.0,0.66,0.52), 24:(1.0,1.0,0.5,0.5),   25:(1.28,1.36,0.5,0.60),
    26:(1.05,1.05,0.6,0.5), 27:(1.16,1.16,0.78,0.78),28:(1.10,1.10,0.5,0.5),
    29:(1.0,1.0,0.5,0.5),
}
CORRIDOR_KINDS = {'mat_hand','corridor_back','elevator','twoshot','entry_parcel'}

# ---------------------------------------------------------------- 后处理素材
_vy, _vx = np.mgrid[0:OH, 0:OW]
_r = np.sqrt((( _vx-OW/2)/(OW/2))**2 + ((_vy-OH/2)/(OH/2))**2)
VIG = np.clip(1.0 - 0.42*np.clip(_r-0.35,0,1)**1.6, 0.55, 1.0)
VIG16 = (VIG*256).astype(np.uint16)
_rng = np.random.default_rng(20261109)
NOISES = [(_rng.normal(0, 3.4, (OH,OW,1))).astype(np.int16) for _ in range(8)]
NOISES = [np.repeat(n, 3, axis=2) for n in NOISES]

_sub_grad = np.zeros((OH,OW), dtype=np.uint8)
for y in range(OH):
    if y > OH-235:
        _sub_grad[y,:] = int(150*min(1.0,(y-(OH-235))/95.0))
SUB_BG = np.zeros((OH,OW,4), dtype=np.uint8)
SUB_BG[...,3] = _sub_grad
SUB_IMG = Image.fromarray(SUB_BG, 'RGBA')

def speaker_at(t):
    for sp, tx, a, d in layout_lines(shot_at(t)):
        if a <= t < a+d and sp != '·':
            return sp
    return None

def wrap(s, f, maxw):
    out, cur = [], ''
    for ch in s:
        if f.getlength(cur+ch) > maxw and cur:
            out.append(cur); cur = ch
        else:
            cur += ch
    if cur: out.append(cur)
    return out

def subtitles(img, t):
    shot = shot_at(t)
    for sp, tx, a, d in layout_lines(shot):
        if sp == '·' or not (a <= t < a+d):
            continue
        k = min(1.0, (t-a)/0.22, (a+d-t)/0.22)
        if k <= 0: return
        img.paste(SUB_IMG, (0,0), SUB_IMG)
        dr = ImageDraw.Draw(img)
        col = (232,220,204) if sp=='小雅' else ((206,224,232) if sp=='老陈' else (178,196,202))
        small = len(tx) > 26
        f = font(30 if small else 34)
        lines = wrap(tx, f, 1040)
        if len(lines) > 2:
            f = font(26); lines = wrap(tx, f, 1060)
        base = OH - (118 if len(lines)>1 else 96)
        # 角色名
        name = font(18)
        dr.text((OW/2, base-34), sp if sp!='张强' else '张强（画外）', font=name,
                fill=tuple(int(140*q) for q in (1,1,1)), anchor='mm')
        for i, ln in enumerate(lines[:2]):
            dr.text((OW/2+1, base+i*44+1), ln, font=f, fill=(0,0,0), anchor='ma')
            dr.text((OW/2, base+i*44), ln, font=f,
                    fill=tuple(int(q*k + 10*(1-k)) for q in col), anchor='ma')
        return

# ---------------------------------------------------------------- 手机屏内容
def screen_car(c, b, t, lock=False):
    x0,y0,x1,y1 = [int(v) for v in b]
    c.rect((x0,y0,x1,y1), (14,22,29))
    c.arect((x0,y0,x1,y0+(y1-y0)*0.62), (30,46,58), 110)
    rain(c, t, b, n=70, seed=7, alpha=95, speed=300)
    cy = y0+(y1-y0)*0.60
    c.apoly([(x0+40,cy+70),(x0+110,cy+20),(x1-110,cy+18),(x1-40,cy+70),
             (x1-70,cy+96),(x0+70,cy+96)], (8,11,15), 245)
    c.apoly([(x0+120,cy+20),(x0+150,cy-16),(x1-140,cy-16),(x1-110,cy+18)], (12,17,22), 235)
    c.aline([(x0+150,cy-14),(x1-140,cy-14)], (74,92,102), 150, 2)
    c.aell((x0+80,cy+72,x0+98,cy+90), (196,62,48), 210)
    c.aell((x1-98,cy+72,x1-80,cy+90), (196,62,48), 210)
    c.arect((x0,y0+(y1-y0)*0.72,x1,y1), (26,40,48), 130)
    c.aline([(x0+30,cy+112),(x1-30,cy+112)], (58,76,86), 90, 2)
    if lock:
        c.arect(b, (3,5,8), 215)
        c.text(((x0+x1)/2, y0+70), "22:13", 30, (180,190,194), anchor='mm')
    c.flush()

def screen_group(c, b, t):
    x0,y0,x1,y1 = [int(v) for v in b]
    c.rect((x0,y0,x1,y1), (224,226,224))
    c.rect((x0,y0,x1,y0+58), (48,54,58))
    c.text(((x0+x1)/2,y0+29), "幸福里业主群（6）", 22, (222,226,226), anchor='mm')
    msgs = [("物业小李","明天上午停水检修，请储水。",False),
            ("3 楼","收到，谢谢。",False),
            ("物业小李","【停车通知】院内划线，请勿占用消防通道。",False)]
    yy = y0+90
    for who, tx, right in msgs:
        c.text((x0+18,yy), who, 16, (90,100,104))
        c.rect((x0+16,yy+26,x1-16,yy+78), (240,242,240), radius=8)
        c.text((x0+28,yy+52), tx, 18, (42,48,52), anchor='lm')
        yy += 104
    c.text(((x0+x1)/2,y0+112), "", 12, TEXT)
    c.flush()

def screen_chat(c, b, t):
    x0,y0,x1,y1 = [int(v) for v in b]
    c.rect((x0,y0,x1,y1), (222,224,222))
    c.rect((x0,y0,x1,y0+58), (48,54,58))
    c.text(((x0+x1)/2,y0+29), "妈妈", 24, (222,226,226), anchor='mm')
    c.rect((x0+16,y0+86,x0+230,y0+140), (240,242,240), radius=10)
    c.text((x0+30,y0+113), "儿子，到哪了？", 19, (42,48,52), anchor='lm')
    c.rect((x1-266,y0+164,x1-16,y0+232), (176,214,168), radius=10)
    c.text((x1-32,y0+198), "出差，信号不好。", 19, (30,48,34), anchor='rm')
    c.text((x1-32,y0+250), "昨天 19:42", 14, (128,134,136), anchor='ra')
    c.rect((x0+16,y1-70,x1-16,y1-16), (240,242,240))
    c.flush()

# ---------------------------------------------------------------- 人物背影 / 侧脸
def back_figure(c, x, foot, h, who='陈', tool=True, bend=0.0):
    col = (24,40,54) if who=='陈' else (48,50,52)
    edge = (86,132,158) if who=='陈' else (124,128,130)
    r = h*0.083
    hy = foot-h+r
    sh = foot-h*0.78 + bend*h*0.06
    wa = foot-h*0.42
    c.poly([(x-h*0.095,wa),(x,wa),(x,foot),(x-h*0.10,foot)], (16,20,24))
    c.poly([(x,wa),(x+h*0.095,wa),(x+h*0.10,foot),(x,foot)], (14,18,22))
    c.poly([(x-h*0.13,sh),(x+h*0.13,sh),(x+h*0.10,wa),(x-h*0.10,wa)], col)
    c.aline([(x+h*0.13,sh),(x+h*0.10,wa)], edge, 110, 3)
    c.rect((x-h*0.022,sh-h*0.06,x+h*0.022,sh+h*0.01), (86,76,68))
    c.ell((x-r,hy-r*1.1,x+r,hy+r*1.2), (64,62,60))
    c.poly([(x-r,hy-r*0.25),(x-r,hy-r*1.1),(x+r,hy-r*1.1),(x+r,hy-r*0.25)], (34,36,38))
    c.poly([(x-h*0.13,sh),(x-h*0.17,sh+h*0.02),(x-h*0.17,wa+h*0.04),(x-h*0.12,wa+h*0.04)], col)
    c.poly([(x+h*0.13,sh),(x+h*0.17,sh+h*0.02),(x+h*0.17,wa+h*0.04),(x+h*0.12,wa+h*0.04)], col)
    if tool:
        toolbox(c, x+h*0.22, foot-h*0.32, s=max(0.5,h/620))
    c.flush()

def side_face(c, x, y, s=1.0, light=True):
    """门缝侧脸：只画轮廓线 + 冷光"""
    col = (196,222,232) if light else (70,84,90)
    pts = [(x-60*s,y-150*s),(x-20*s,y-172*s),(x+28*s,y-150*s),(x+42*s,y-96*s),
           (x+58*s,y-70*s),(x+40*s,y-56*s),(x+46*s,y-24*s),(x+18*s,y-6*s),
           (x+10*s,y+34*s),(x-18*s,y+66*s)]
    c.aline(pts, col, 150, 4*s)
    c.aline([(x+2*s,y-78*s),(x+30*s,y-74*s)], col, 170, 3*s)
    c.flush()

# ---------------------------------------------------------------- 30 镜构图
def compose(shot, p, t, sp):
    k = shot['kind']; c = Canvas(t)
    if k == 'black':
        void(c, t)
    elif k == 'mat_hand':
        corridor(c, t, seed=2)
        c.poly([(1000,742),(1382,742),(1400,800),(1010,800)], (70,58,46))
        c.glow(1060, 800, 420, WARM, 2.6, 0.30)
        c.poly([(940,824),(1010,806),(1044,824),(972,846)], (152,164,166))
        c.aline([(958,824),(1026,808)], (214,224,226), 190, 3)
        hand(c, 1120, 786, s=1.45, grip=True, pale=False)
        c.flush()
    elif k == 'corridor_back':
        corridor(c, t, seed=4)
        back_figure(c, 1130, 726, 430, '陈', tool=True, bend=1.0)
        c.arect((926,700,1334,714), (4,6,8), 220)
        c.glow(1130, 300, 700, WARM, 3.0, 0.16)
        c.flush()
    elif k == 'phone_car':
        void(c, t)
        c.glow(800, 450, 900, (70,110,130), 3.0, 0.26)
        def scr(cc, b, tt): screen_car(cc, b, tt, lock=p>0.76)
        phone(c, 800, 450, w=430, h=770, screen=scr, t=t)
        c.flush()
    elif k == 'elevator':
        corridor(c, t, elevator=True, seed=5)
        # 电梯门开
        openw = min(1.0, p*2.2)*100
        c.rect((52,162,222-openw,690), (48,58,64))
        c.rect((222+openw,162,388,690), (48,58,64))
        c.rect((222-openw,162,222+openw,690), (10,14,19))
        c.arect((222-openw,162,222+openw,690), (110,126,132), 40)
        # 小雅收伞走出
        xx = 235 + min(1.0,p*1.4)*150*(1 if p<0.62 else 1.0)
        person(c, xx, 745, 430, '雅', facing=1, pose='stand', dim=0.92)
        umbrella(c, xx-78, 560, s=0.55, wet=True)
        back_figure(c, 1150, 720, 380, '陈', tool=True)
        c.flush()
    elif k == 'twoshot':
        f = flicker(t)
        corridor(c, t, seed=8)
        c.apoly([(0,0),(BW,0),(BW,BH),(0,BH)], (6,10,14), 165)
        c.flush()
        c.glow(700 if sp=='小雅' else 920, 280, 980,
               WARM if sp=='小雅' else (80,110,126), 2.8, 0.28)
        if sp == '老陈':
            person(c, 920, 1330, 1080, '陈', facing=-1, dim=0.94)
        else:
            person(c, 680, 1330, 1050, '雅', facing=1, dim=0.96)
        c.flush()
    elif k == 'entry_parcel':
        interior(c, t, bed_light=0.10)
        back_figure(c, 545, 1000, 900, '雅', tool=False)
        person(c, 1120, 760, 500, '陈', facing=-1, tool=True, dim=0.78)
        parcel(c, 230, 510, s=1.32)
        c.glow(230, 510, 420, WARM, 2.6, 0.28)
        c.flush()
    elif k == 'sink':
        interior(c, t, table=False, bed_light=0.05)
        # 蹲姿
        c.poly([(250,470),(390,470),(430,650),(220,650)], (30,58,78))
        c.ell((268,380,372,486), (66,62,58))
        c.poly([(268,392),(368,392),(368,430),(268,430)], (34,36,38))
        c.poly([(220,640),(430,640),(470,700),(200,700)], (22,27,31))
        toolbox(c, 540, 690, s=1.02, open_=True)
        c.line([(560,590),(610,545)], SILVER, 8)
        c.ell((600,536,650,562), (60,64,66))
        if int(t*5) % 2 == 0:
            c.aline([(150,470),(120,440)], (150,168,176), 110, 3)
            c.aline([(165,478),(138,470)], (150,168,176), 90, 3)
        c.glow(300, 520, 500, WARM, 2.8, 0.24)
        c.flush()
    elif k == 'phone_group':
        void(c, t)
        c.glow(800, 430, 850, (80,110,120), 3.0, 0.20)
        if p < 0.72:
            phone(c, 800, 450, w=430, h=770, screen=screen_group, t=t)
        else:
            c.rect((586,66,1014,834), (26,30,34), radius=28, outline=(62,68,72), width=4)
            c.ell((742,180,858,296), (34,38,42))
            c.ell((776,214,824,262), (18,22,26))
        hand(c, 1080, 700, s=1.5, grip=True)
        c.flush()
    elif k == 'glass_reflection':
        interior(c, t, table=False, bed_light=0.12)
        c.arect((470,180,760,700), (72,96,106), 70)
        person(c, 610, 760, 520, '陈', facing=1, dim=0.52)
        c.arect((470,180,760,700), (36,54,64), 95)
        c.aline([(470,180),(470,700)], (110,134,142), 90, 4)
        c.aline([(760,180),(760,700)], (110,134,142), 90, 4)
        hand(c, 780, 620, s=2.0, grip=False, pale=True)
        c.glow(700, 420, 640, WARM, 2.8, 0.18)
        c.flush()
    elif k == 'two_glasses':
        interior(c, t, table=True, bed_light=0.16)
        glass(c, 620, 600, s=1.15)
        if p < 0.18:
            c.poly([(430,420),(520,420),(540,530),(410,530)], (128,152,158))
            c.aline([(530,500),(700,560)], (168,204,214), 160, 5)
        # 第二杯：端向卧室两步，停住，再端回来
        if p < 0.34:
            gx, gy = 800, 600
        elif p < 0.62:
            u = (p-0.34)/0.28
            gx = 800 + 300*min(1.0,u*1.5)
            gy = 600 - 110*min(1.0,u*1.5)
        elif p < 0.72:
            gx, gy = 1100, 490
        else:
            u = min(1.0,(p-0.72)/0.24)
            gx = 1100 - 300*u; gy = 490 + 110*u
        hand(c, gx-52, gy-20, s=0.85, grip=True, pale=True)
        glass(c, gx, gy-70, s=1.15)
        c.glow(800, 400, 700, WARM, 2.8, 0.22)
        c.flush()
    elif k == 'shoes':
        if p < 0.50:
            void(c, t, warm=0.5)
            c.glow(800, 430, 900, WARM, 2.8, 0.22)
            c.poly([(380,300),(1180,300),(1220,520),(350,520)], (28,32,36))
            c.poly([(400,320),(1160,320),(1190,500),(370,500)], (40,44,48))
            for i in range(9):
                x = 430+i*85
                c.aline([(x,340),(x-20,480)], (62,66,70), 130, 4)
            c.ell((520,330,1060,470), (34,38,42))
            c.aline([(400,320),(1160,320)], (86,92,96), 110, 2)
            c.aline([(520,360),(1060,360)], (58,62,66), 100, 2)
            c.aline([(520,442),(1060,442)], (58,62,66), 100, 2)
            c.flush()
        else:
            interior(c, t, table=False, bed_light=0.12)
            person(c, 700, 780, 540, '陈', facing=1, tool=False, dim=0.8)
            c.poly([(860,720),(1400,720),(1460,880),(800,880)], (62,53,44))
            c.ell((900,742,1010,776), (22,26,30))
            c.aline([(910,752),(1000,752)], (66,70,72), 130, 3)
            c.flush()
    elif k == 'hand_knife':
        interior(c, t, table=True, bed_light=0.15)
        c.glow(900, 560, 620, WARM, 2.8, 0.24)
        knife(c, 930, 570, angle=-0.10, s=1.7)
        hx = 520 + min(1.0,p*1.4)*300
        hand(c, hx, 600, s=1.7, grip=p>0.62, pale=True)
        c.flush()
    elif k == 'badge':
        if p < 0.55:
            void(c, t, warm=1.0)
            c.glow(800, 500, 900, WARM, 2.8, 0.26)
            badge(c, 800, 470, s=2.5)
            hand(c, 520, 620, s=1.7, grip=True)
            c.flush()
        else:
            interior(c, t, table=True, bed_light=0.18)
            person(c, 520, 860, 660, '雅', facing=1, dim=0.88)
            person(c, 1080, 860, 680, '陈', facing=-1, dim=0.88)
            badge(c, 800, 620, s=0.72)
            c.flush()
    elif k == 'reverse_bedroom':
        c.rect((0,0,BW,BH), (14,18,22))
        c.glow(1240, 400, 700, COLD, 3.0, 0.20)
        c.flush()
        if sp == '小雅':
            person(c, 700, 1120, 840, '雅', facing=1, pose='hold_knife', dim=0.92)
            knife(c, 960, 690, angle=-0.35, s=1.1)
        else:
            person(c, 880, 1120, 840, '陈', facing=-1, dim=0.92)
            c.arect((1220,200,1300,720), COLD, 70)
        c.flush()
    elif k == 'table_still':
        interior(c, t, table=True, bed_light=0.20)
        glass(c, 560, 610, s=1.0); glass(c, 830, 610, s=1.0)
        knife(c, 700, 640, angle=0.35, s=1.05)
        badge(c, 1050, 620, s=0.78)
        person(c, 280, 900, 700, '雅', facing=1, dim=0.50)
        person(c, 1400, 900, 700, '陈', facing=-1, dim=0.48)
        c.glow(800, 560, 800, WARM, 3.0, 0.22)
        c.flush()
    elif k == 'umbrella':
        void(c, t, warm=0.7)
        c.rect((160,160,1200,770), (24,30,34), outline=(56,64,68), width=6)
        c.aline([(160,290),(1200,290)], (54,62,66), 120, 4)
        c.aline([(160,730),(1200,730)], (54,62,66), 120, 4)
        umbrella(c, 460, 690, s=1.65, wet=True)
        umbrella(c, 900, 690, s=1.95, wet=False, long=True)
        slippers(c, 400, 806, s=1.75)
        c.glow(900, 400, 760, WARM, 2.8, 0.26)
        c.glow(460, 400, 600, COLD, 2.8, 0.22)
        c.flush()
    elif k == 'keys':
        void(c, t, warm=0.9)
        c.poly([(120,600),(1480,600),(1520,900),(80,900)], (54,44,37))
        c.poly([(140,620),(1460,620),(1496,880),(104,880)], (72,58,46))
        for i in range(16):
            c.aline([(180+i*85,630),(150+i*85,870)], (48,40,34), 90, 2)
        c.poly([(140,620),(500,620),(452,486),(196,510)], (46,38,32))
        c.aline([(196,510),(452,486),(500,620)], (132,110,86), 150, 4)
        keys(c, 760, 410, s=1.55, car=True)
        c.glow(1010, 440, 740, WARM, 2.8, 0.28)
        c.flush()
    elif k == 'chat':
        void(c, t)
        c.glow(800, 380, 900, (76,108,120), 3.0, 0.20)
        phone(c, 800, 400, w=400, h=660, screen=screen_chat, t=t)
        hand(c, 1220, 700, s=1.9, grip=True, pale=True)
        knife(c, 1160, 760, angle=-0.7, s=1.0)
        c.flush()
    elif k == 'knife_tremble':
        void(c, t)
        c.arect((0,0,BW,BH), (22,32,38), 55)
        rain(c, t, (900,60,1560,800), n=110, seed=11, alpha=70, speed=520)
        j = 2.2*math.sin(t*22)
        knife(c, 760, 470+j, angle=0.22+j*0.002, s=2.9)
        c.glow(1080, 450, 760, COLD, 2.6, 0.28)
        c.flush()
    elif k == 'block_door':
        interior(c, t, table=False, bed_light=0.42)
        person(c, 1310, 800, 600, '雅', facing=-1, pose='hold_knife', dim=0.98)
        knife(c, 1130, 500, angle=math.pi-0.25, s=1.0)
        person(c, 880, 800, 570, '陈', facing=1, dim=0.72)
        c.glow(1270, 420, 620, COLD, 2.8, 0.26)
        c.flush()
    elif k == 'tears':
        void(c, t, warm=0.6)
        c.glow(700, 320, 900, WARM, 2.8, 0.22)
        person(c, 700, 1080, 900, '雅', facing=1, dim=0.86)
        ty = 330 + (p*120)
        c.aell((742, ty, 750, ty+16), (186,208,216), 190)
        hand(c, 820, 760, s=2.2, grip=True, pale=True)
        c.flush()
    elif k == 'lower_knife':
        interior(c, t, table=False, bed_light=0.35+0.55*p)
        xx = 1300 + 150*p
        person(c, xx, 800, 600, '雅', facing=-1, pose='hold_knife', dim=0.94)
        knife(c, xx-150, 480+320*p, angle=0.2+1.15*p, s=1.05)
        c.glow(1270, 420, 700, COLD, 2.8, 0.20+0.25*p)
        c.flush()
    elif k == 'door_side':
        doorcrack(c, t, width=280, cx=790, objects=False)
        side_face(c, 690, 450, s=2.5)
        hand(c, 520, 620, s=1.35, reach=True, pale=True)
        c.flush()
    elif k == 'nightstand':
        doorcrack(c, t, width=300, cx=800, objects=True)
        pulse = 0.10+0.05*math.sin(t*3.4)
        c.glow(892, 480, 240, (80,210,180), 2.6, pulse)
        c.flush()
    elif k == 'call120':
        interior(c, t, table=False, bed_light=0.85)
        person(c, 860, 900, 700, '陈', facing=1, pose='cup', dim=0.94)
        phone(c, 1030, 520, w=150, h=280, screen=lambda cc,b,tt: cc.arect(b,(70,110,120),120), t=t)
        c.glow(1270, 420, 700, COLD, 2.8, 0.30)
        c.flush()
    elif k == 'slide_down':
        interior(c, t, table=False, bed_light=0.92)
        dy = 90*min(1.0,p*1.4)
        person(c, 1330, 760+dy, 560, '雅', facing=-1, dim=0.86)
        # 刀落地
        if p < 0.55:
            ky = 530 + 300*(p/0.55)**2
            knife(c, 1080, ky, angle=0.4+2.4*(p/0.55), s=1.0)
        else:
            knife(c, 1080, 838, angle=math.pi-0.06, s=1.0)
            c.glow(1120, 838, 220, SILVER, 2.8, 0.28)
        c.glow(1270, 420, 700, COLD, 2.8, 0.30)
        c.flush()
    elif k == 'look_back':
        void(c, t)
        c.arect((1180,0,1360,BH), COLD, 80)
        c.glow(1270, 420, 700, COLD, 3.0, 0.24)
        c.flush()
        person(c, 700, 1080, 860, '陈', facing=1, dim=0.86)
        person(c, 1330, 900, 560, '雅', facing=-1, dim=0.44)
        c.flush()
    elif k == 'reach_water':
        void(c, t)
        # 左侧门缝冷光
        c.rect((120,0,300,BH), (32,52,62))
        c.glow(210, 450, 900, COLD, 2.4, 0.32)
        c.apoly([(120,0),(300,0),(340,BH),(80,BH)], COLD, 24)
        c.rect((60,0,120,BH), (12,16,20)); c.rect((300,0,360,BH), (12,16,20))
        # 右侧桌沿 + 第二杯水
        c.poly([(760,650),(1560,650),(1600,900),(720,900)], (66,49,38))
        c.poly([(776,644),(1544,644),(1580,880),(740,880)], (80,60,45))
        glass(c, 1280, 640, s=2.4, water=0.55)
        c.glow(1280, 560, 620, WARM, 2.8, 0.26)
        # 停在半空的手
        u = min(1.0, p*1.6)
        hx = 720 + 250*u
        hand(c, hx, 560, s=2.3, reach=True, pale=True)
        c.flush()
    return c.img

# ---------------------------------------------------------------- 帧合成
def render_frame(t):
    shot = shot_at(t)
    t0, t1 = shot['t0'], shot['t1']
    p = min(1.0, max(0.0, (t-t0)/max(0.001,t1-t0)))
    sp = speaker_at(t)
    base = compose(shot, p, t, sp)

    z0,z1,cx,cy = CAM.get(shot['id'], (1.0,1.0,0.5,0.5))
    z = z0 + (z1-z0)*p
    cw, ch = BW/z, BH/z
    left = max(0, min(BW-cw, cx*BW-cw/2))
    top  = max(0, min(BH-ch, cy*BH-ch/2))
    img = base.crop((int(left),int(top),int(left+cw),int(top+ch))).resize((OW,OH), Image.BILINEAR)

    subtitles(img, t)

    # 亮度：走廊灯闪 + 镜6 那一下 + 镜间转场
    k = 1.0
    if shot['kind'] in CORRIDOR_KINDS:
        k *= flicker(t)
    if 38.45 < t < 38.85:
        k *= 0.34
    fade = min(1.0, (t-t0)/0.28, (t1-t)/0.28) if shot['id'] not in (1,30) else 1.0
    k *= max(0.0, fade)

    arr = np.asarray(img).astype(np.uint16)
    arr = (arr * VIG16[...,None]) >> 8
    scale = int(max(0,min(1.0,k))*256)
    if scale != 256:
        arr = (arr * scale) >> 8
    a16 = arr.astype(np.int16) + NOISES[int(t*FPS) % 8]
    out = Image.fromarray(np.clip(a16,0,255).astype(np.uint8), 'RGB')
    return out

# ---------------------------------------------------------------- 主流程
def preview():
    for s in SHOTS:
        t = (s['t0']+s['t1'])/2
        img = render_frame(t)
        img.save(os.path.join(FRAMES, 'shot_%02d.jpg' % s['id']), quality=88)
        print('shot %02d  %6.1fs  %s' % (s['id'], t, s['kind']), flush=True)
    # 拼板
    thumbs = Image.new('RGB', (5*320, 6*180), (8,10,14))
    d = ImageDraw.Draw(thumbs)
    for i, s in enumerate(SHOTS):
        im = Image.open(os.path.join(FRAMES,'shot_%02d.jpg'%s['id'])).resize((320,180))
        x, y = (i%5)*320, (i//5)*180
        thumbs.paste(im,(x,y))
        d.rectangle((x+4,y+4,x+62,y+26), fill=(10,12,16))
        d.text((x+8,y+7), '%02d  %d:%02d'%(s['id'], s['t0']//60, s['t0']%60), fill=(226,220,200))
    thumbs.save(os.path.join(HERE,'contact_sheet.jpg'), quality=90)

def segment(idx, n=4):
    """分段渲染，供多进程并行；每段独立编码，最后用 concat 无损拼接"""
    f0 = int(idx*DURATION*FPS/n)
    f1 = int((idx+1)*DURATION*FPS/n)
    out = os.path.join(HERE, 'seg_%d.mp4' % idx)
    cmd = ['ffmpeg','-y','-hide_banner','-loglevel','error',
           '-f','rawvideo','-pix_fmt','rgb24','-s','%dx%d'%(OW,OH),'-r',str(FPS),'-i','-',
           '-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
           '-movflags','+faststart', out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(f0, f1):
        pr.stdin.write(render_frame(i/FPS).tobytes())
        if (i-f0) % (FPS*30) == 0:
            print('seg%d %.1f / %.1f s' % (idx, i/FPS, f1/FPS), flush=True)
    pr.stdin.close()
    print('seg%d exit %d' % (idx, pr.wait()), flush=True)

def full():
    out = os.path.join(HERE, 'silent.mp4')
    cmd = ['ffmpeg','-y','-hide_banner','-loglevel','error',
           '-f','rawvideo','-pix_fmt','rgb24','-s','%dx%d'%(OW,OH),'-r',str(FPS),'-i','-',
           '-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p',
           '-movflags','+faststart', out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    total = DURATION*FPS
    for i in range(total):
        t = i/FPS
        pr.stdin.write(render_frame(t).tobytes())
        if i % (FPS*30) == 0:
            print('%.1f / %d s' % (t, DURATION), flush=True)
    pr.stdin.close()
    rc = pr.wait()
    print('ffmpeg exit', rc, '->', out, flush=True)

if __name__ == '__main__':
    os.makedirs(FRAMES, exist_ok=True)
    mode = sys.argv[1] if len(sys.argv)>1 else 'preview'
    if mode == 'preview': preview()
    elif mode == 'full': full()
    elif mode == 'segment':
        segment(int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv)>3 else 4)
    elif mode == 'one':
        t = float(sys.argv[2]); render_frame(t).save(os.path.join(HERE,'one.png'))
    else:
        print('usage: render.py preview|full|segment <idx> <n>|one <t>')
