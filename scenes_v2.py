# -*- coding: utf-8 -*-
"""精修 3D 场景：细分曲面、真实细节与物理材质。"""
import math
import numpy as np
from physics3d import (Geo, C, MAT, WALL, WALL2, FLOOR, CEIL, DOOR, DOOR_DK,
                       WOOD, WOOD_D, BLUE, BLUE_D, GREY, GREY_D, SKIN, DARK,
                       GLASS, WATER, SILVER, RED, PAPER, GREEN)

# ---------------------------------------------------------------- 人物
def person_fine(g,x,z,who='陈',facing=1,pose='stand',t=0.0,tool=False,scale=1.0):
    """球头 + 锥台躯干 + 分段管状四肢 + 关节球，服装与道具细节"""
    s=scale; cloth=BLUE if who=='陈' else GREY; dark=BLUE_D if who=='陈' else GREY_D
    ry=0 if facing==1 else math.pi
    swing=math.sin(t*7)*.25 if pose=='walk' else 0.0
    drop=.40 if pose=='sit' else 0.0
    fx=1 if facing==1 else -1
    # 腿：大腿/小腿/鞋
    for side in (-1,1):
        sx=x+side*.13*s
        g.frustum((sx,.55*s-drop*.35,z),(.085*s),(.065*s),(.72*s-drop*.2),8,dark,'cloth')
        g.frustum((sx,.19*s-drop*.15,z+side*.01),(.065*s),(.05*s),(.40*s),8,dark,'cloth')
        g.box((sx,.035*s,z+.05*s*fx),(.16*s,.075*s,.28*s),DARK,mat='rubber',bevel=.01*s)
        g.box((sx,.012*s,z+.05*s*fx),(.17*s,.025*s,.29*s),C(.10,.11,.11),mat='rubber')
        g.sphere((sx,.84*s-drop*.3,z),.075*s,dark,mat='cloth',lat=3,lon=6)
    # 躯干（上宽下窄）+ 肩
    g.frustum((x,1.14*s-drop,z),(.185*s),(.245*s),(.70*s),14,cloth,'cloth')
    for side in (-1,1):
        g.sphere((x+side*.245*s,1.44*s-drop,z),.085*s,cloth,'cloth',lat=3,lon=6)
    # 领口 V / 门襟 / 口袋
    g.face([(x-.06*s,1.49*s-drop,z-.151*s),(x+.06*s,1.49*s-drop,z-.151*s),
            (x,1.36*s-drop,z-.16*s),(x,1.36*s-drop,z-.16*s)],DARK,mat='cloth')
    g.box((x,1.13*s-drop,z-.152*s),(.012*s,.55*s,.008*s),tuple(q*.7 for q in cloth),mat='cloth')
    g.box((x-.13*s,1.05*s-drop,z-.153*s),(.13*s,.11*s,.008*s),tuple(q*.86 for q in cloth),mat='cloth')
    g.box((x+.13*s,1.05*s-drop,z-.153*s),(.13*s,.11*s,.008*s),tuple(q*.86 for q in cloth),mat='cloth')
    # 颈 / 头 / 发
    g.frustum((x,1.56*s-drop,z),.052*s,.05*s,.13*s,8,SKIN,'skin')
    hy=1.72*s-drop
    g.sphere((x,hy,z),.135*s,SKIN,'skin',lat=6,lon=11)
    g.sphere((x,hy+.045*s,z-.012*s),.139*s,DARK,'cloth',lat=3,lon=10)
    if who=='雅':
        g.frustum((x-.16*s*fx,hy-.13*s,z-.09*s*fx),.055*s,.025*s,.34*s,8,DARK,'cloth')
        g.box((x,hy-.02*s,z+.132*s),(.05*s,.012*s,.008*s),C(.30,.26,.24),mat='skin')
    else:
        g.box((x,hy+.10*s,z),(.20*s,.02*s,.19*s),C(.15,.16,.17),mat='cloth',bevel=.008*s)
    # 手臂：上臂 + 前臂 + 手，姿态角驱动
    for side in (-1,1):
        a=0.0
        if side==1 and pose in ('hold_knife','reach','block'): a=-1.05 if pose!='reach' else -1.35
        if side==-1 and pose=='cup': a=-.75
        if pose=='down': a=.55
        if pose=='walk': a=swing*side
        sx=x+side*.30*s; sy=1.30*s-drop
        g.frustum((sx,sy-.16*s,z),.062*s,.052*s,.38*s,8,cloth,'cloth',close=False)
        # 前臂绕肩旋转
        ex=sx+math.sin(a)*.30*s; ey=sy-.32*s-math.cos(a)*.30*s
        g.frustum(((sx+ex)/2,(sy-.30*s+ey)/2,z+.05*s*math.sin(a)),.05*s,.04*s,.34*s,8,cloth,'cloth',close=False)
        g.sphere((ex,ey,z+.05*s*math.sin(a)),.055*s,SKIN,'skin',lat=3,lon=6)
        g.sphere((sx,sy-.30*s,z),.05*s,cloth,'cloth',lat=3,lon=6)
        g.box((sx,sy-.30*s,z-.055*s),(.10*s,.05*s,.012*s),tuple(q*.8 for q in cloth),mat='cloth')
    if who=='陈':   # 旧钢表
        g.box((x+.31*s,1.06*s-drop,z-.055*s),(.075*s,.022*s,.075*s),SILVER,mat='steel',bevel=.006*s)
        g.box((x+.31*s,1.06*s-drop,z-.095*s),(.02*s,.03*s,.01*s),C(.45,.55,.58),mat='glass')
    if tool:
        toolbox_fine(g,x-.55*s,.24*s,z+.12*s,.9*s)
    g.shadow(x,z,1.75*s,.42*s)

# ---------------------------------------------------------------- 道具
def glass_fine(g,x,y,z,s=1.0,water=.55):
    r=.062*s; h=.20*s
    g.tube((x,y+h/2,z),r,h,14,GLASS,'glass',thick=.010*s)
    g.disc((x,y+.012*s,z),r-.012*s,tuple(q*.8 for q in GLASS),mat='glass',sides=14,up=False)
    wh=h*water
    g.disc((x,y+wh,z),r-.014*s,WATER,mat='water',sides=14)
    g.frustum((x,y+wh/2,z),r-.016*s,r-.016*s,wh,14,WATER,'water',close=False)
    g.box((x-.035*s,y+h*.6*s,z-r),(.012*s,h*.55*s,.006*s),C(.75,.88,.90),mat='glass')

def knife_fine(g,x,y,z,angle=0.0,s=1.0):
    """楔形刀刃 + 刀背 + 刀柄 + 铆钉"""
    L=.42*s; w=.055*s
    co,si=math.cos(angle),math.sin(angle)
    def P(a,b,c): return (x+a*co-b*si,y+c,z+a*si+b*co)
    g.face([P(0,-w,0),P(L*.72,-w*.8,0),P(L,0,.006*s),P(0,w,0)],SILVER,mat='steel')
    g.face([P(0,-w,.014*s),P(L*.72,-w*.8,.006*s),P(L,0,.006*s),P(0,w,.014*s)],
           C(.70,.76,.78),mat='steel',vn=[(0,1,0)]*4)
    g.face([P(0,-w,0),P(0,w,0),P(0,w,.014*s),P(0,-w,.014*s)],C(.50,.56,.58),mat='steel')
    g.box((x-.22*s*co,y,z-.22*s*si),(.17*s,.032*s,.075*s),WOOD_D,mat='wood',rot=(0,angle,0),bevel=.008*s)
    for k in (-.26,-.18):
        g.sphere((x+k*s*co,y+.02*s,z+k*s*si),.008*s,SILVER,'steel',lat=2,lon=5)

def badge_fine(g,x,y,z,s=1.0,open_=True):
    g.box((x,y,z),(.34*s,.024*s,.24*s),RED,mat='paint',bevel=.012*s)
    if open_:
        g.box((x,y+.016*s,z),(.31*s,.008*s,.21*s),C(.50,.27,.21),mat='paper')
        g.sphere((x-.085*s,y+.023*s,z),.033*s,C(.78,.70,.48),'metal',lat=3,lon=8)
        g.box((x+.07*s,y+.023*s,z-.045*s),(.16*s,.004*s,.012*s),C(.72,.62,.44),mat='paper')
        g.box((x+.06*s,y+.023*s,z+.015*s),(.13*s,.004*s,.010*s),C(.60,.52,.38),mat='paper')
    g.box((x,y+.018*s,z+.11*s),(.22*s,.003*s,.012*s),C(.70,.58,.36),mat='paper')

def phone_fine(g,x,y,z,s=1.0,lit=True,tilt=0.0):
    g.box((x,y,z),(.26*s,.50*s,.028*s),DARK,mat='dark',rot=(0,0,tilt),bevel=.02*s)
    g.box((x,y,z-.017*s),(.235*s,.462*s,.004*s),C(.045,.10,.13),mat='screen',
          em=C(.045,.10,.13),rot=(0,0,tilt))
    g.box((x,y+.235*s,z-.019*s),(.07*s,.006*s,.003*s),C(.16,.19,.20),mat='metal')
    g.sphere((x,y-.232*s,z-.019*s),.012*s,C(.18,.20,.21),'metal',lat=2,lon=6)
    g.box((x+.133*s,y+.08*s,z),(.006*s,.07*s,.014*s),SILVER,mat='steel')

def parcel_fine(g,x,y,z,s=1.0):
    g.box((x,y,z),(.48*s,.24*s,.30*s),C(.46,.36,.25),mat='paper',bevel=.012*s)
    g.box((x,y+.125*s,z),(.46*s,.012*s,.28*s),C(.54,.43,.30),mat='paper')
    g.box((x,y,z-.152*s),(.30*s,.13*s,.005*s),PAPER,mat='paper')
    g.box((x-.04*s,y,z-.156*s),(.20*s,.012*s,.003*s),C(.20,.22,.20),mat='paper')
    g.box((x,y+.13*s,z),(.06*s,.004*s,.30*s),C(.66,.60,.48),mat='paper')

def keys_fine(g,x,y,z,s=1.0):
    g.tube((x,y,z),.075*s,.020*s,12,SILVER,'steel',thick=.012*s)
    for i,a in enumerate((.45,1.45,2.5)):
        bx=x+math.cos(a)*.16*s; bz=z+math.sin(a)*.16*s
        g.box((bx,y-.012*s,bz),(.21*s,.012*s,.026*s),SILVER,mat='steel',rot=(0,a,0),bevel=.004*s)
        for k in range(3):
            g.box((bx+(.06-k*.035)*s,y-.02*s,bz),(.018*s,.018*s,.03*s),SILVER,mat='steel')
    g.box((x+.27*s,y-.01*s,z+.17*s),(.27*s,.055*s,.14*s),C(.10,.16,.21),mat='paint',bevel=.02*s)
    for k in range(3):
        g.sphere((x+(.18+k*.08)*s,y+.021*s,z+.17*s),.018*s,SILVER,'steel',lat=2,lon=6)
    g.box((x+.27*s,y+.021*s,z+.17*s),(.12*s,.004*s,.04*s),GREEN,mat='screen',em=GREEN)
    g.box((x+.43*s,y-.01*s,z+.17*s),(.14*s,.018*s,.045*s),SILVER,mat='steel',bevel=.006*s)

def umbrella_fine(g,x,z,s=1.0,wet=False,long=False):
    h=(1.15 if long else .95)*s
    g.frustum((x,h/2,z),.014*s,.012*s,h,8,SILVER,'steel',close=False)
    g.sphere((x,h+.01*s,z),.022*s,SILVER,'steel',lat=2,lon=6)
    # 伞面 12 段 + 伞骨
    g.frustum((x,h*.78*s,z),.30*s,.012*s,.30*s,12,C(.13,.21,.27) if not wet else C(.17,.28,.34),
              'cloth')
    for i in range(10):
        a=2*math.pi*i/10
        g.box((x+.15*s*math.cos(a),h*.80*s,z+.15*s*math.sin(a)),
              (.006*s,.008*s,.30*s),C(.35,.40,.42),mat='steel',rot=(0,-a,0))
    g.frustum((x,.03*s,z),.025*s,.016*s,.12*s,8,WOOD_D,'wood',close=False)
    if wet:
        for i in range(7):
            a=2*math.pi*i/7
            g.sphere((x+.26*s*math.cos(a),h*.78*s,z+.26*s*math.sin(a)),.009*s,
                     C(.42,.66,.74),'water',lat=2,lon=5)

def slippers_fine(g,x,z,s=1.0):
    for dx in (0,.17*s):
        g.box((x+dx,.028*s,z),(.14*s,.045*s,.29*s),C(.27,.23,.21),mat='rubber',bevel=.02*s)
        g.frustum((x+dx,.055*s,z-.055*s),.055*s,.07*s,.045*s,8,C(.34,.29,.26),'cloth')

def oximeter_fine(g,x,y,z,s=1.0):
    g.box((x,y,z),(.17*s,.095*s,.115*s),DARK,mat='paint',bevel=.02*s)
    g.box((x,y,z-.061*s),(.125*s,.058*s,.004*s),C(.05,.18,.15),mat='screen',em=C(.05,.18,.15))
    g.box((x-.04*s,y+.015*s,z-.064*s),(.04*s,.018*s,.003*s),GREEN,mat='screen',em=GREEN)
    g.sphere((x+.065*s,y+.05*s,z),.012*s,SILVER,'steel',lat=2,lon=6)

def toolbox_fine(g,x,y,z,s=1.0):
    g.box((x,y+.12*s,z),(.42*s,.24*s,.26*s),DARK,mat='dark',bevel=.02*s)
    g.box((x,y+.245*s,z),(.18*s,.045*s,.05*s),SILVER,mat='steel',bevel=.01*s)
    g.box((x,y+.14*s,z-.132*s),(.07*s,.05*s,.008*s),SILVER,mat='steel')
    g.box((x-.16*s,y+.06*s,z-.132*s),(.04*s,.03*s,.008*s),C(.45,.30,.18),mat='paint')

def nightstand_fine(g,x,y,z,s=1.0):
    g.box((x,y,z),(.86*s,.92*s,.72*s),C(.23,.25,.26),mat='wood',bevel=.02*s)
    g.box((x,y+.47*s,z),(.90*s,.045*s,.76*s),C(.30,.32,.33),mat='wood',bevel=.012*s)
    for dy in (.16,-.16):
        g.box((x,y+dy*s,z-.365*s),(.72*s,.26*s,.008*s),C(.26,.28,.29),mat='wood')
        g.sphere((x,y+dy*s,z-.375*s),.018*s,SILVER,'steel',lat=2,lon=6)

# ---------------------------------------------------------------- 走廊
def corridor_v2(elevator=0.0, mat_lift=False):
    g=Geo()
    g.face([(-2.2,0,-2.5),(2.2,0,-2.5),(2.2,0,4.2),(-2.2,0,4.2)],FLOOR,mat='tile')
    g.face([(-2.2,2.7,-2.5),(-2.2,2.7,4.2),(2.2,2.7,4.2),(2.2,2.7,-2.5)],CEIL,mat='wall')
    g.face([(-2.2,0,-2.5),(-2.2,2.7,-2.5),(-2.2,2.7,4.2),(-2.2,0,4.2)],WALL2,mat='wall')
    g.face([(2.2,0,4.2),(2.2,2.7,4.2),(2.2,2.7,-2.5),(2.2,0,-2.5)],WALL,mat='wall')
    g.face([(-2.2,0,4.2),(2.2,0,4.2),(2.2,2.7,4.2),(-2.2,2.7,4.2)],WALL2,mat='wall')
    # 踢脚线 / 墙裙 / 天花接缝
    for sx in (-2.19,2.19):
        g.box((sx,.075, .85),(.02,.15,6.7),C(.18,.17,.15),mat='wood')
        g.box((sx,.95, .85),(.012,.022,6.7),C(.20,.19,.17),mat='paint')
    for z in np.arange(-2,4.2,.62):
        g.box((0,.001,z),(4.38,.003,.012),C(.075,.075,.078),mat='tile')
        g.box((0,2.695,z),(4.38,.004,.02),C(.10,.11,.12),mat='wall')
    # 窗：外框 + 内玻璃 + 十字格（雨在外侧）
    g.box((0,1.65,4.17),(1.92,1.38,.07),C(.22,.26,.28),mat='paint',bevel=.02)
    g.face([(-.88,1.02,4.12),(.88,1.02,4.12),(.88,2.28,4.12),(-.88,2.28,4.12)],
           C(.10,.17,.21),mat='glass',vn=[(0,0,-1)]*4)
    g.box((0,1.65,4.11),(.045,1.32,.035),C(.28,.32,.34),mat='paint')
    g.box((0,1.65,4.11),(1.80,.045,.035),C(.28,.32,.34),mat='paint')
    g.rain_volume((-.86, .86, 1.02, 2.26, 4.10), n=130, g=9.8)
    # 电梯门 + 按钮
    g.box((-2.14,1.25,.4),(.06,2.42,1.32),C(.20,.24,.27),mat='paint',bevel=.02)
    off=.60*float(elevator)
    for zz in (.4-off,.4+off):
        g.box((-2.10,1.25,zz),(.035,2.32,.56),C(.27,.32,.35),mat='steel',bevel=.012)
    if elevator>.15: g.box((-2.07,1.25,.4),(.03,2.30,off*2),C(.035,.055,.065),mat='dark')
    g.box((-2.06,1.55,1.16),(.035,.34,.10),C(.18,.21,.22),mat='steel')
    for yy in (1.63,1.48):
        g.sphere((-2.035,yy,1.16),.018,C(.55,.60,.60),'steel',lat=2,lon=6)
    # 602 门：门框 / 门板 / 门牌 / 把手 / 猫眼 / 门缝
    g.box((2.13,1.25,2.45),(.10,2.48,1.36),C(.26,.28,.28),mat='paint',bevel=.02)
    g.box((2.09,1.24,2.45),(.05,2.32,1.22),DOOR,mat='paint',bevel=.015)
    g.box((2.055,1.24,2.45),(.008,2.20,1.10),C(.14,.18,.21),mat='paint')
    g.box((2.02,2.05,2.45),(.015,.24,.40),C(.16,.19,.20),mat='steel',bevel=.01)
    for k,dx in enumerate((-.13,0,.13)):   # 602
        g.box((2.012+dx*.02,2.05,2.45+dx),(.006,.15,.055),PAPER,mat='paper')
    g.sphere((2.01,1.18,2.92),.045,SILVER,'steel',lat=4,lon=8)
    g.box((2.01,1.18,2.84),(.03,.028,.16),SILVER,mat='steel',bevel=.008)
    g.sphere((2.01,1.82,2.45),.022,C(.55,.60,.58),'glass',lat=3,lon=6)
    g.box((2.09,.025,2.45),(.06,.025,1.22),C(.035,.045,.05),mat='dark')
    # 地垫：纤维边 + 掀角
    g.box((1.62,.014,2.45),(.98,.022,.74),C(.25,.20,.16),mat='cloth',bevel=.02)
    for i in range(12):
        g.box((1.16+i*.08,.028,2.10),(.018,.006,.06),C(.31,.25,.20),mat='cloth')
        g.box((1.16+i*.08,.028,2.80),(.018,.006,.06),C(.31,.25,.20),mat='cloth')
    if mat_lift:
        g.face([(1.14,.02,2.12),(1.95,.02,2.12),(1.86,.30,2.55),(1.25,.26,2.55)],
               C(.20,.16,.13),mat='cloth')
    # 灯管：发光体 + 支架 + 镇流器 + 体积光
    g.box((0,2.62,.55),(.16,.075,2.5),C(.85,.72,.45),mat='screen',em=C(.62,.50,.28))
    g.box((0,2.665,.55),(.34,.04,2.7),C(.18,.19,.19),mat='steel',bevel=.02)
    for zz in (-.6,1.7):
        g.box((0,2.63,zz),(.22,.09,.10),C(.24,.25,.25),mat='steel')
    g.beam([(-.18,2.58,-1.1),(.18,2.58,-1.1),(1.5,0,3.9),(-1.5,0,3.9)],
           C(.42,.33,.18),alpha=.055,layers=2)
    g.light((0,2.5,.6),C(1.0,.78,.48),1.55,7.0,glow=((216,168,98),1250,.30))
    g.light((0,1.6,4.0),C(.35,.55,.68),.55,6.0)
    return g

# ---------------------------------------------------------------- 客厅 + 卧室
def interior_v2(bed_open=0.0, table=True, umbrella_rack=True, cold=1.0):
    g=Geo()
    g.face([(-2.6,0,-1.5),(2.6,0,-1.5),(2.6,0,5.2),(-2.6,0,5.2)],FLOOR,mat='tile')
    g.face([(-2.6,2.7,-1.5),(-2.6,2.7,5.2),(2.6,2.7,5.2),(2.6,2.7,-1.5)],CEIL,mat='wall')
    g.face([(-2.6,0,-1.5),(-2.6,2.7,-1.5),(-2.6,2.7,5.2),(-2.6,0,5.2)],WALL2,mat='wall')
    g.face([(-2.6,0,5.2),(2.6,0,5.2),(2.6,2.7,5.2),(-2.6,2.7,5.2)],WALL2,mat='wall')
    g.face([(2.6,0,-1.5),(2.6,2.7,-1.5),(2.6,2.7,2.35),(2.6,0,2.35)],WALL,mat='wall')
    g.face([(2.6,0,4.15),(2.6,2.7,4.15),(2.6,2.7,5.2),(2.6,0,5.2)],WALL,mat='wall')
    g.face([(2.6,2.35,2.35),(2.6,2.35,4.15),(2.6,2.7,4.15),(2.6,2.7,2.35)],WALL,mat='wall')
    for z in np.arange(-1.5,5.2,.62):
        g.box((0,.001,z),(5.18,.003,.012),C(.075,.075,.078),mat='tile')
    g.box((-2.58,.075,1.85),(.02,.15,6.7),C(.18,.17,.15),mat='wood')
    # 卧室门框 / 两块门板 / 门缝冷光柱 / 地面光斑
    g.box((2.55,1.25,3.25),(.12,2.5,1.88),C(.24,.26,.27),mat='paint',bevel=.02)
    g.box((2.52,1.2,2.79),(.055,2.35,.86),DOOR_DK,mat='paint',bevel=.012)
    g.box((2.52,1.2,3.90+bed_open*.35),(.055,2.35,.56),DOOR_DK,mat='paint',bevel=.012)
    g.sphere((2.47,1.10,3.02),.04,SILVER,'steel',lat=3,lon=7)
    if bed_open>.05:
        zz=3.23+.35*bed_open
        g.beam([(2.50,2.30,3.23),(2.50,2.30,zz),(3.9,.02,zz+.35),(3.9,.02,3.30)],
               C(.34,.56,.66),alpha=.055*bed_open*cold,layers=2)
        g.face([(2.62,.01,3.23),(3.8,.01,3.23),(4.2,.01,4.3),(2.62,.01,4.3)],
               C(.18,.30,.36),mat=(0,.9,.10*bed_open*cold),unlit=True)
    # 卧室
    g.face([(2.62,0,2.35),(5.0,0,2.35),(5.0,0,4.5),(2.62,0,4.5)],C(.12,.14,.15),mat='tile')
    nightstand_fine(g,3.75,.48,3.55,1.0)
    glass_fine(g,3.55,.96,3.42,.9,.5)
    g.box((3.95,.99,3.70),(.30,.035,.22),PAPER,mat='paper',bevel=.01)
    oximeter_fine(g,4.00,1.05,3.36,1.0)
    phone_fine(g,3.42,1.02,3.78,.55,lit=False)
    g.box((3.40,.99,3.95),(.008,.008,.30),C(.15,.17,.18),mat='rubber')
    g.box((4.55,.95,3.1),(.55,1.85,.12),C(.19,.22,.24),mat='wood',bevel=.02)
    g.box((4.45,.48,3.25),(.55,.06,.55),C(.22,.25,.26),mat='wood',bevel=.015)
    for dx in (-.22,.22):
        for dz in (-.2,.2):
            g.box((4.45+dx,.23,3.25+dz),(.045,.46,.045),WOOD_D,mat='wood')
    for k in range(5):     # 椅背上的毯子（下垂）
        g.face([(4.28,1.75-k*.18,3.16),(4.82,1.75-k*.18,3.16),
                (4.80,1.60-k*.18,3.04),(4.30,1.60-k*.18,3.04)],
               C(.21,.24,.25) if k%2 else C(.24,.27,.28),mat='cloth')
    slippers_fine(g,3.30,4.20,.9)
    g.box((3.90,1.25,3.20),(.16,.05,.16),C(.65,.78,.84),mat='screen',em=C(.35,.55,.68))
    g.light((3.85,1.35,3.30),C(.55,.82,1.0),1.9,3.2,glow=((168,210,226),720,.22*cold))
    # 厨房：橱柜 / 水槽 / 龙头 / 玻璃隔断
    g.box((-2.15,.45,1.1),(.85,.90,1.5),C(.19,.22,.24),mat='wood',bevel=.02)
    g.box((-2.15,.92,1.1),(.90,.05,1.55),C(.29,.32,.33),mat='steel',bevel=.012)
    g.box((-2.0,.925,1.0),(.46,.02,.56),DARK,mat='steel')
    g.frustum((-2.30,1.05,.85),.022,.018,.28,8,SILVER,'steel',close=False)
    g.box((-2.18,1.19,.85),(.14,.025,.025),SILVER,mat='steel',bevel=.008)
    g.box((-2.25,1.9,1.1),(.5,.55,1.5),C(.23,.26,.28),mat='wood',bevel=.02)
    g.face([(-1.65,.9,-.6),(-1.65,2.5,-.6),(-1.65,2.5,1.9),(-1.65,.9,1.9)],
           C(.16,.24,.28),mat='glass',vn=[(1,0,0)]*4)
    g.box((-1.64,1.70,-.6),(.03,1.6,.03),C(.34,.40,.42),mat='steel')
    # 鞋柜 + 伞架
    g.box((-2.15,.42,-.35),(.75,.84,1.0),WOOD_D,mat='wood',bevel=.02)
    for dy in (.60,.25):
        g.box((-2.15,dy,-.35),(.72,.30,.008),C(.28,.21,.15),mat='wood')
        g.sphere((-1.95,dy,-.35),.02,SILVER,'steel',lat=2,lon=6)
    if umbrella_rack:
        g.tube((-1.55,.18,.05),.19,.36,12,C(.17,.20,.22),'steel',thick=.02)
        umbrella_fine(g,-1.62,.02,.72,wet=True)
        umbrella_fine(g,-1.42,.10,1.02,long=True)
        slippers_fine(g,-2.10,.55,1.0)
    # 餐桌：桌面倒角 / 四腿 / 横撑 / 木纹
    if table:
        g.box((0,.74,2.2),(1.85,.085,1.05),WOOD,mat='wood',bevel=.03)
        g.box((0,.79,2.2),(1.90,.018,1.10),C(.40,.29,.20),mat='wood',bevel=.02)
        for dx in (-.80,.80):
            for dz in (-.42,.42):
                g.box((dx,.37,2.2+dz),(.085,.74,.085),WOOD_D,mat='wood',bevel=.012)
        g.box((0,.25,2.2-.42),(1.6,.045,.045),WOOD_D,mat='wood')
        for i in range(5):
            g.box((-.75+i*.37,.788,2.2),(.008,.002,1.0),C(.32,.23,.16),mat='wood')
        g.shadow(0,2.2,.8,1.1)
    # 吊灯：灯罩 / 灯泡 / 吊杆 / 体积光锥 / 桌面光斑
    g.box((0,2.55,2.0),(.018,.30,.018),C(.32,.28,.20),mat='steel')
    g.frustum((0,2.32,2.0),.31,.10,.24,14,C(.38,.30,.19),'steel')
    g.sphere((0,2.24,2.0),.10,C(.90,.74,.42),'screen',lat=4,lon=8)
    g.beam([(-.12,2.24,1.88),(.12,2.24,1.88),(1.35,.79,3.0),(-1.35,.79,3.0)],
           C(.40,.31,.17),alpha=.05,layers=2)
    g.face([(-.75,.795,1.75),(.75,.795,1.75),(.85,.795,2.65),(-.85,.795,2.65)],
           C(.30,.23,.14),mat=(0,.9,.10),unlit=True)
    g.light((0,2.32,2.0),C(1.0,.78,.48),1.65,6.5,glow=((216,168,98),1180,.34))
    return g

# ---------------------------------------------------------------- 特写舞台
def macro_v2(kind,p,t):
    g=Geo()
    g.face([(-3,0,4),(3,0,4),(3,3,4),(-3,3,4)],C(.085,.10,.12),mat='wall')
    g.face([(-3,0,-1),(3,0,-1),(3,0,4),(-3,0,4)],C(.095,.095,.10),mat='tile')
    warm=kind in ('badge','keys','reach_water','two_glasses','mat_hand','nightstand')
    g.light((.8,2.1,1.0),C(1.0,.78,.48) if warm else C(.55,.78,.92),2.0,4.2,
            glow=((216,168,98) if warm else (120,170,200),900,.30))
    g.light((-1.2,1.5,1.2),C(.35,.48,.58),.55,5.0)
    if kind=='phone_car':
        phone_fine(g,0,1.15,2.0,2.7,lit=p<.76); g.ui((0,1.15,1.985),'car',p)
    elif kind=='phone_group':
        phone_fine(g,0,1.15,2.0,2.7,lit=p<.72); g.ui((0,1.15,1.985),'group',p)
    elif kind=='chat':
        phone_fine(g,0,1.15,2.0,2.5,lit=True); g.ui((0,1.15,1.985),'chat',p)
    elif kind=='badge':
        g.box((0,.78,2.3),(2.8,.10,1.3),WOOD,mat='wood',bevel=.03)
        badge_fine(g,0,.86,2.0,3.2)
        g.sphere((-.72,.92,2.0),.16,SKIN,'skin',lat=4,lon=8)
        for i in range(4):
            g.frustum((-.85+i*.07,1.02,1.88),.028,.022,.20,6,SKIN,'skin')
    elif kind=='keys':
        g.box((0,.78,2.3),(2.8,.10,1.3),C(.24,.20,.16),mat='cloth',bevel=.02)
        keys_fine(g,-.15,.88,2.0,3.2)
    elif kind=='shoes':
        g.box((0,1.0,2.0),(1.5,.16,.9),C(.15,.17,.19),mat='rubber',rot=(.35,.2,0),bevel=.03)
        for i in range(7):
            g.box((-.55+i*.18,.92,2.0),(.05,.012,.82),C(.25,.27,.29),mat='rubber')
    elif kind=='knife_tremble':
        j=math.sin(t*20)*.02
        knife_fine(g,.1,1.05+j,2.0,.15+j,3.4)
    elif kind in ('hand_knife','reach_water','two_glasses'):
        g.box((0,.78,2.3),(2.8,.10,1.3),WOOD,mat='wood',bevel=.03)
        if kind=='hand_knife':
            knife_fine(g,.55,.88,2.15,-.1,2.0)
            g.sphere((-.55,.94,2.1),.17,SKIN,'skin',lat=4,lon=8)
            for i in range(4): g.frustum((-.68+i*.07,1.04,1.96),.03,.024,.22,6,SKIN,'skin')
        elif kind=='reach_water':
            glass_fine(g,1.05,.86,2.2,2.4,.55)
            g.sphere((-.45,1.02,2.1),.17,SKIN,'skin',lat=4,lon=8)
            for i in range(4): g.frustum((-.58+i*.07,1.14,1.94),.028,.022,.24,6,SKIN,'skin')
        else:
            glass_fine(g,-.45,.84,2.2,1.5,.55)
            gx=-.1+.7*min(1,p*1.6) if p<.7 else .6
            glass_fine(g,gx,.84,2.2,1.5,.55)
            g.sphere((gx-.22,.94,2.1),.11,SKIN,'skin',lat=3,lon=6)
    elif kind=='nightstand':
        nightstand_fine(g,0,.55,2.35,1.5)
        glass_fine(g,-.45,1.13,2.2,1.4,.5)
        g.box((.35,1.15,2.5),(.45,.04,.32),PAPER,mat='paper',bevel=.01)
        oximeter_fine(g,.48,1.20,2.18,1.5)
        phone_fine(g,-.65,1.16,2.55,.75,lit=False)
        g.box((1.25,1.4,2.8),(.4,1.9,.12),C(.19,.22,.24),mat='cloth',bevel=.02)
    elif kind=='mat_hand':
        g.box((0,.78,2.3),(2.8,.10,1.4),C(.24,.20,.16),mat='cloth',bevel=.02)
        g.sphere((.45,.94,2.1),.20,SKIN,'skin',lat=5,lon=9)
        for i in range(4):
            g.frustum((.28+i*.11,1.02,1.88),.042,.03,.32,7,SKIN,'skin')
        keys_fine(g,-.75,.88,2.35,1.2)
    return g
