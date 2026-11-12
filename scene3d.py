# -*- coding: utf-8 -*-
"""软件 3D 渲染器：透视投影 + 深度排序 + 逐面 Lambert 光照。
全部几何由代码生成，无模型文件、无 3D 库、无生成式图像模型。
坐标：X 右 / Y 上 / Z 深；地面 Y=0。
"""
import math
import numpy as np
from PIL import Image, ImageDraw
from draw import glow

# ---------------------------------------------------------------- 颜色
def C(r,g,b): return (float(r),float(g),float(b))
WALL    = C(.13,.15,.17)
WALL2   = C(.10,.12,.14)
FLOOR   = C(.10,.095,.095)
CEIL    = C(.08,.09,.10)
DOOR    = C(.12,.16,.19)
DOOR_DK = C(.06,.08,.10)
WOOD    = C(.26,.18,.13)
WOOD_D  = C(.16,.12,.09)
BLUE    = C(.12,.28,.42)
BLUE_D  = C(.08,.18,.28)
GREY    = C(.24,.26,.27)
GREY_D  = C(.15,.17,.18)
SKIN    = C(.24,.21,.19)
DARK    = C(.05,.07,.09)
GLASS   = C(.34,.52,.58)
WATER   = C(.20,.38,.46)
SILVER  = C(.48,.54,.56)
RED     = C(.34,.13,.11)
PAPER   = C(.62,.60,.55)
GREEN   = C(.18,.58,.46)
BG      = (7,10,14)
AMBIENT = (.11,.13,.16)

def rot_mat(rx=0, ry=0, rz=0):
    cx,sx = math.cos(rx), math.sin(rx)
    cy,sy = math.cos(ry), math.sin(ry)
    cz,sz = math.cos(rz), math.sin(rz)
    Rx = np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]])
    Ry = np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]])
    Rz = np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]])
    return Rz @ Ry @ Rx

class Mesh:
    """所有面统一 4 顶点（三角形重复一点），便于 numpy 批量投影"""
    def __init__(self):
        self.v = []      # (4,3)
        self.c = []      # (3,)
        self.em = []     # (3,) emissive
        self.lights = [] # (pos(3), color(3), intensity, radius)
        self.shadows = []# (x, z, size)
        self.glows = []  # (pos(3), color, size, strength)
        self.ui = []     # (anchor(3), kind, data)
        self.rainbox = None

    def face(self, verts, col, em=(0,0,0)):
        pts = list(verts)
        if len(pts) == 3: pts = pts + [pts[2]]
        if len(pts) != 4: raise ValueError('face needs 3 or 4 verts')
        self.v.append(np.array(pts, dtype=np.float32))
        self.c.append(col); self.em.append(em)

    def box(self, c, s, col, rot=(0,0,0), em=(0,0,0), shade=1.0):
        cx,cy,cz = c; sx,sy,sz = s
        x0,x1 = cx-sx/2, cx+sx/2
        y0,y1 = cy-sy/2, cy+sy/2
        z0,z1 = cz-sz/2, cz+sz/2
        pts = np.array([[x0,y0,z0],[x1,y0,z0],[x1,y1,z0],[x0,y1,z0],
                        [x0,y0,z1],[x1,y0,z1],[x1,y1,z1],[x0,y1,z1]], dtype=np.float32)
        if any(rot):
            R = rot_mat(*rot); pts = (pts-np.array(c)) @ R.T + np.array(c)
        p = [tuple(v) for v in pts]
        # 六个面；shade 让不同朝向略有色差（法线光照仍会再算）
        self.face([p[0],p[1],p[2],p[3]], col, em)
        self.face([p[5],p[4],p[7],p[6]], col, em)
        self.face([p[4],p[0],p[3],p[7]], col, em)
        self.face([p[1],p[5],p[6],p[2]], col, em)
        self.face([p[3],p[2],p[6],p[7]], col, em)
        self.face([p[4],p[5],p[1],p[0]], col, em)

    def prism(self, c, r, h, sides=8, col=GREY, em=(0,0,0)):
        cx,cy,cz = c
        y0,y1 = cy-h/2, cy+h/2
        ang = [2*math.pi*i/sides for i in range(sides)]
        bot = [(cx+r*math.cos(a), y0, cz+r*math.sin(a)) for a in ang]
        top = [(cx+r*math.cos(a), y1, cz+r*math.sin(a)) for a in ang]
        for i in range(sides):
            j = (i+1)%sides
            self.face([bot[i],bot[j],top[j],top[i]], col, em)
            self.face([(cx,y1,cz),top[i],top[j],top[j]], col, em)
            self.face([(cx,y0,cz),bot[j],bot[i],bot[i]], col, em)

    def cone(self, c, r, h, sides=8, col=BLUE):
        cx,cy,cz = c
        ang = [2*math.pi*i/sides for i in range(sides)]
        base = [(cx+r*math.cos(a), cy, cz+r*math.sin(a)) for a in ang]
        apex = (cx, cy+h, cz)
        for i in range(sides):
            j=(i+1)%sides
            self.face([base[i],base[j],apex,apex], col)

    def light(self, pos, col, intensity=1.0, radius=6.0, glow=None):
        self.lights.append((np.array(pos,dtype=np.float32), np.array(col,dtype=np.float32), intensity, radius))
        if glow:
            self.glows.append((pos, glow[0], glow[1], glow[2]))

    def shadow(self, x, z, size=1.0):
        self.shadows.append((x,z,size))

    def merge(self, other):
        self.v += other.v; self.c += other.c; self.em += other.em
        self.lights += other.lights; self.shadows += other.shadows
        self.glows += other.glows; self.ui += other.ui
        if other.rainbox: self.rainbox = other.rainbox
        return self

    def clone(self):
        m = Mesh(); return m.merge(self)

# ---------------------------------------------------------------- 相机数学
def normalize(v):
    n = np.linalg.norm(v)
    return v/n if n > 1e-9 else v

def camera(eye, target, fov=50.0, W=1280, H=720):
    f = normalize(np.array(target,dtype=np.float32)-np.array(eye,dtype=np.float32))
    r = normalize(np.cross(f, np.array([0,1,0],dtype=np.float32)))
    u = np.cross(r, f)
    scale = (H/2)/math.tan(math.radians(fov)/2)
    return np.array(eye,dtype=np.float32), r, u, f, scale, W, H

def project_points(V, cam):
    """V: (...,3) -> (...,2) 屏幕坐标 + (...,) 深度"""
    eye,r,u,f,scale,W,H = cam
    d = V - eye
    x = np.dot(d, r); y = np.dot(d, u); z = np.dot(d, f)
    zz = np.maximum(z, 0.06)
    return np.stack([W/2 + x*scale/zz, H/2 - y*scale/zz], axis=-1), z

# ---------------------------------------------------------------- 渲染
def render(mesh, cam, t=0.0, flick=1.0, grain=None):
    W,H = int(cam[5]), int(cam[6])
    eye = cam[0]
    img = Image.new('RGB',(W,H), BG)
    dr = ImageDraw.Draw(img)
    if not mesh.v:
        return img

    V = np.stack(mesh.v)                  # (M,4,3)
    Cols = np.array(mesh.c, dtype=np.float32)
    Ems  = np.array(mesh.em, dtype=np.float32)
    S, Z = project_points(V.reshape(-1,3), cam)
    S = S.reshape(-1,4,2); Z = Z.reshape(-1,4)
    ok = (Z > 0.06).all(axis=1) & (S[:,:,0].max(axis=1)>-300) & (S[:,:,0].min(axis=1)<W+300)
    if not ok.any():
        return img
    idx = np.nonzero(ok)[0]
    S, Z, Cols, Ems, V = S[idx], Z[idx], Cols[idx], Ems[idx], V[idx]
    depth = Z.mean(axis=1)

    center = V.mean(axis=1)
    n = np.cross(V[:,1]-V[:,0], V[:,2]-V[:,0])
    nl = np.linalg.norm(n, axis=1, keepdims=True)
    n = n/np.maximum(nl,1e-6)
    # 双面光照：法线统一翻向相机
    to_eye = eye-center
    flip = (np.einsum('ij,ij->i', n, to_eye) < 0)
    n[flip] *= -1

    amb = np.array(AMBIENT, dtype=np.float32)
    col = Cols*amb + Ems
    for lp, lc, inte, radius in mesh.lights:
        lv = lp-center
        dist = np.linalg.norm(lv, axis=1, keepdims=True)
        ld = lv/np.maximum(dist,1e-4)
        lam = np.clip(np.einsum('ij,ij->i', n, ld), 0, 1)[:,None]
        att = 1.0/(1.0+(dist/radius)**2)
        k = lam*inte*att*flick
        col += Cols*lc[None,:]*k
    # 距离雾
    fog = np.clip((depth-5.0)/16.0, 0, .52)[:,None]
    bgc = np.array(BG,dtype=np.float32)/255.0
    col = col*(1-fog) + bgc*fog
    col8 = np.clip(col*255, 0, 255).astype(np.uint8)

    # 地面柔和投影阴影
    for (x,z,sz) in mesh.shadows:
        s,zz = project_points(np.array([[x,0.02,z]],dtype=np.float32), cam)
        if zz[0] > 0.06:
            g = glow(int(220*sz/max(zz[0],1)), (0,0,0), 2.0, 0.45)
            w = g.size[0]
            img.paste(g, (int(s[0,0]-w/2), int(s[0,1]-w/4)), g)

    order = np.argsort(-depth)
    for i in order:
        pts = [(int(S[i,j,0]), int(S[i,j,1])) for j in range(4)]
        cc = tuple(int(v) for v in col8[i])
        edge = tuple(max(0,int(v*.45)) for v in col8[i])
        dr.polygon(pts, fill=cc, outline=edge, width=1)

    # 光源在屏幕空间的光晕
    for (pos, gcol, gsize, strength) in mesh.glows:
        s,zz = project_points(np.array([pos],dtype=np.float32), cam)
        if zz[0] > 0.06:
            size = int(gsize/max(zz[0],1.0))
            size = max(20, min(1400, size))
            g = glow(size, gcol, 2.6, strength*flick)
            img.paste(g, (int(s[0,0]-size/2), int(s[0,1]-size/2)), g)

    # 窗外雨丝
    if mesh.rainbox:
        s,zz = project_points(np.array(mesh.rainbox,dtype=np.float32), cam)
        if (zz>0.06).all():
            x0,y0 = s.min(axis=0); x1,y1 = s.max(axis=0)
            x0=max(0,int(x0)); x1=min(W,int(x1)); y0=max(0,int(y0)); y1=min(H,int(y1))
            rng = np.random.default_rng(7)
            for k in range(90):
                bx = rng.uniform(x0,x1) if x1>x0 else x0
                by = rng.uniform(y0,y1) if y1>y0 else y0
                yy = y0 + ((by-y0 + t*330) % max(1,(y1-y0)))
                xx = bx + (yy-by)*.22
                if x0<=xx<=x1 and y0<=yy<=y1:
                    dr.line([(xx,yy),(xx-4,yy+14)], fill=(46,70,84), width=1)
    return img

# ---------------------------------------------------------------- 人物
def person3d(m, x, z, who='陈', facing=1, pose='stand', t=0.0, tool=False, scale=1.0):
    """低多边形人物：躯干/头/四肢，朝向 facing(1 面向 +Z, -1 背向)"""
    cloth = BLUE if who=='陈' else GREY
    dark  = BLUE_D if who=='陈' else GREY_D
    s = scale
    ry = 0 if facing==1 else math.pi
    swing = math.sin(t*7)*0.30 if pose=='walk' else 0.0
    drop = 0.42 if pose=='sit' else 0.0
    # 腿
    m.box((x-.13*s, .42*s-drop*.4, z), (.20*s,.84*s-drop*.5,.22*s), dark, rot=(swing,ry,0))
    m.box((x+.13*s, .42*s-drop*.4, z), (.20*s,.84*s-drop*.5,.22*s), dark, rot=(-swing,ry,0))
    # 躯干（略微上宽）
    m.box((x, 1.12*s-drop, z), (.52*s,.72*s,.30*s), cloth, rot=(0,ry,0))
    # 肩
    m.box((x, 1.46*s-drop, z), (.62*s,.14*s,.30*s), cloth, rot=(0,ry,0))
    # 颈 + 头
    m.box((x, 1.55*s-drop, z), (.13*s,.14*s,.13*s), SKIN, rot=(0,ry,0))
    m.prism((x, 1.72*s-drop, z), .145*s, .30*s, 8, SKIN)
    m.prism((x, 1.84*s-drop, z), .152*s, .13*s, 8, DARK)
    if who=='雅':   # 低马尾
        m.box((x-.16*s, 1.60*s-drop, z-.14*s*facing), (.10*s,.36*s,.10*s), DARK, rot=(.25,ry,0))
    # 手臂
    if pose in ('hold_knife','reach','block'):
        a = -1.05 if pose!='reach' else -1.35
        m.box((x+.38*s, 1.25*s-drop, z+.20*s), (.15*s,.62*s,.15*s), cloth, rot=(a,ry,0))
        m.box((x-.38*s, 1.18*s-drop, z), (.15*s,.60*s,.15*s), cloth, rot=(0,ry,0))
    elif pose=='cup':
        m.box((x-.38*s, 1.26*s-drop, z+.16*s), (.15*s,.58*s,.15*s), cloth, rot=(-.75,ry,0))
        m.box((x+.38*s, 1.20*s-drop, z), (.15*s,.58*s,.15*s), cloth, rot=(0,ry,0))
    elif pose=='down':
        m.box((x-.38*s, 1.05*s-drop, z), (.15*s,.58*s,.15*s), cloth, rot=(.25,ry,0))
        m.box((x+.38*s, 1.02*s-drop, z+.08*s), (.15*s,.58*s,.15*s), cloth, rot=(.65,ry,0))
    else:
        m.box((x-.38*s, 1.16*s-drop, z), (.15*s,.60*s,.15*s), cloth, rot=(0,ry,0))
        m.box((x+.38*s, 1.16*s-drop, z), (.15*s,.60*s,.15*s), cloth, rot=(0,ry,0))
    if tool:
        m.box((x-.55*s, .68*s, z+.10*s), (.34*s,.24*s,.24*s), DARK)
        m.box((x-.55*s, .84*s, z+.10*s), (.16*s,.06*s,.06*s), SILVER)
    m.shadow(x,z,.35*s)

# ---------------------------------------------------------------- 道具
def glass3d(m, x, y, z, s=1.0, water=.58):
    m.prism((x,y+.09*s,z), .055*s, .18*s, 8, GLASS)
    m.prism((x,y+.02*s+.10*s*water/2,z), .046*s, .10*s*water, 8, WATER)

def knife3d(m, x, y, z, angle=0.0, s=1.0):
    m.box((x,y,z), (.42*s,.018*s,.055*s), SILVER, rot=(0,angle,0))
    m.box((x-.28*s,y,z), (.16*s,.028*s,.065*s), WOOD_D, rot=(0,angle,0))

def badge3d(m, x, y, z, s=1.0, open_=True):
    m.box((x,y,z), (.34*s,.022*s,.24*s), RED)
    if open_:
        m.box((x,y+.014*s,z), (.30*s,.006*s,.20*s), C(.52,.28,.22))
        m.prism((x-.09*s,y+.02*s,z), .035*s, .006*s, 8, PAPER)

def phone3d(m, x, y, z, s=1.0, lit=True, tilt=0.0):
    m.box((x,y,z), (.26*s,.50*s,.026*s), DARK, rot=(0,0,tilt))
    if lit:
        m.box((x,y,z-.015*s), (.23*s,.45*s,.006*s), C(.05,.12,.16), em=C(.05,.12,.16), rot=(0,0,tilt))

def parcel3d(m, x, y, z, s=1.0):
    m.box((x,y,z), (.48*s,.24*s,.30*s), C(.48,.38,.26))
    m.box((x,y+.125*s,z), (.46*s,.012*s,.28*s), C(.56,.45,.31))
    m.box((x,y,z-.152*s), (.30*s,.13*s,.006*s), PAPER)

def keys3d(m, x, y, z, s=1.0):
    m.prism((x,y,z), .07*s, .012*s, 10, SILVER)
    for i,a in enumerate((.5,1.4,2.4)):
        bx = x+math.cos(a)*.14*s; bz = z+math.sin(a)*.14*s
        m.box((bx,y-.02*s,bz), (.20*s,.012*s,.028*s), SILVER, rot=(0,a,0))
    m.box((x+.26*s,y-.02*s,z+.16*s), (.26*s,.05*s,.13*s), C(.10,.16,.20))
    m.box((x+.26*s,y+.008*s,z+.16*s), (.16*s,.004*s,.06*s), GREEN, em=GREEN)

def umbrella3d(m, x, z, s=1.0, wet=False, long=False):
    h = (1.15 if long else .95)*s
    m.prism((x,h/2,z), .014*s, h, 6, SILVER)
    m.cone((x,h*.72,z), .30*s, .34*s, 8, C(.14,.22,.28) if not wet else C(.18,.30,.36))
    m.prism((x,h+.36*s,z), .02*s, .06*s, 6, SILVER)

def slippers3d(m, x, z, s=1.0):
    for dx in (0,.16*s):
        m.box((x+dx,.035*s,z), (.13*s,.055*s,.28*s), C(.28,.24,.22))

def oximeter3d(m, x, y, z, s=1.0):
    m.box((x,y,z), (.16*s,.09*s,.11*s), DARK)
    m.box((x,y,z-.058*s), (.12*s,.055*s,.004*s), GREEN, em=C(.10,.32,.26))

def toolbox3d(m, x, z, s=1.0):
    m.box((x,.16*s,z), (.42*s,.24*s,.26*s), DARK)
    m.box((x,.30*s,z), (.20*s,.05*s,.06*s), SILVER)

# ---------------------------------------------------------------- 场景：走廊
def scene_corridor(elevator=False, mat_lift=False, gap=False, car_photo=False):
    m = Mesh()
    # 地面 / 天花 / 墙
    m.face([(-2.2,0,-2.5),(2.2,0,-2.5),(2.2,0,4.2),(-2.2,0,4.2)], FLOOR)
    m.face([(-2.2,2.7,-2.5),(-2.2,2.7,4.2),(2.2,2.7,4.2),(2.2,2.7,-2.5)], CEIL)
    m.face([(-2.2,0,-2.5),(-2.2,2.7,-2.5),(-2.2,2.7,4.2),(-2.2,0,4.2)], WALL2)
    m.face([(2.2,0,4.2),(2.2,2.7,4.2),(2.2,2.7,-2.5),(2.2,0,-2.5)], WALL)
    m.face([(-2.2,0,4.2),(2.2,0,4.2),(2.2,2.7,4.2),(-2.2,2.7,4.2)], WALL2)
    # 地板透视格线
    for z in np.arange(-2,4.2,.6):
        m.face([(-2.2,.004,z),(2.2,.004,z),(2.2,.004,z+.012),(-2.2,.004,z+.012)], C(.10,.10,.11))
    # 尽头窗（雨）
    m.face([(-.9,1.0,4.18),(.9,1.0,4.18),(.9,2.3,4.18),(-.9,2.3,4.18)], C(.11,.19,.23))
    m.box((0,1.65,4.16), (1.86,.05,.05), SILVER)
    m.box((0,1.65,4.15), (.05,1.36,.05), SILVER)
    m.rainbox = [(-.88,1.02,4.1),(.88,1.02,4.1),(.88,2.28,4.1),(-.88,2.28,4.1)]
    # 电梯（左墙）
    m.box((-2.16,1.25,.4), (.05,2.4,1.25), C(.20,.25,.28))
    m.box((-2.13,1.25,.4-(.58 if elevator else 0)), (.035,2.3,.55), C(.27,.33,.36))
    m.box((-2.13,1.25,.4+(.58 if elevator else 0)), (.035,2.3,.55), C(.27,.33,.36))
    if elevator:
        m.box((-2.10,1.25,.4), (.03,2.3,1.10), C(.05,.09,.11))
    # 602 门（右墙）
    m.box((2.14,1.25,2.45), (.06,2.35,1.25), DOOR)
    m.box((2.10,1.95,2.45), (.02,.28,.42), C(.16,.19,.20))
    m.prism((2.08,1.15,2.92), .045, .03, 8, C(.62,.52,.32))
    if gap:
        m.box((2.10,.035,2.45), (.03,.02,1.20), C(.62,.48,.28), em=C(.30,.20,.08))
    # 地垫 + 掀起一角
    m.box((1.62,.012,2.45), (.95,.02,.72), C(.26,.21,.17))
    if mat_lift:
        m.face([(1.18,.02,2.12),(1.95,.02,2.12),(1.86,.30,2.55),(1.25,.26,2.55)], C(.20,.16,.13))
    # 灯管
    m.box((0,2.62,.55), (.16,.08,2.5), C(.72,.60,.38), em=C(.72,.60,.38))
    m.box((0,2.66,.55), (.34,.04,2.7), CEIL)
    # 墙皮剥落（浅色薄板）
    for (x,z,y,w,h) in ((2.18,3.5,1.6,.5,.3),(-2.18,2.2,1.9,.6,.25)):
        m.box((x,y,z), (.012,h,w), C(.24,.27,.28))
    m.light((0,2.5,.6), C(1.0,.78,.48), 1.45, 7.0, glow=((216,168,98), 1200, .30))
    m.light((0,1.6,4.0), C(.35,.55,.68), .55, 6.0)
    return m

# ---------------------------------------------------------------- 场景：客厅 + 卧室
def scene_interior(bed_open=0.0, table=True, door_closed=True, umbrella_rack=True):
    m = Mesh()
    # 房间壳体
    m.face([(-2.6,0,-1.5),(2.6,0,-1.5),(2.6,0,5.2),(-2.6,0,5.2)], FLOOR)
    m.face([(-2.6,2.7,-1.5),(-2.6,2.7,5.2),(2.6,2.7,5.2),(2.6,2.7,-1.5)], CEIL)
    m.face([(-2.6,0,-1.5),(-2.6,2.7,-1.5),(-2.6,2.7,5.2),(-2.6,0,5.2)], WALL2)
    m.face([(-2.6,0,5.2),(2.6,0,5.2),(2.6,2.7,5.2),(-2.6,2.7,5.2)], WALL2)
    # 右墙分两段，中间是卧室门洞
    m.face([(2.6,0,-1.5),(2.6,2.7,-1.5),(2.6,2.7,2.35),(2.6,0,2.35)], WALL)
    m.face([(2.6,0,4.15),(2.6,2.7,4.15),(2.6,2.7,5.2),(2.6,0,5.2)], WALL)
    m.face([(2.6,2.35,2.35),(2.6,2.35,4.15),(2.6,2.7,4.15),(2.6,2.7,2.35)], WALL)
    for z in np.arange(-1.5,5.2,.7):
        m.face([(-2.6,.004,z),(2.6,.004,z),(2.6,.004,z+.012),(-2.6,.004,z+.012)], C(.10,.10,.11))
    # 卧室门板：始终只留一道可变的缝，门板真实遮挡卧室
    m.box((2.56,1.2,2.79), (.07,2.35,.88), DOOR_DK)
    m.box((2.56,1.2,3.90+bed_open*.35), (.07,2.35,.56), DOOR_DK)
    # 卧室（X>2.6）：只从门缝可见
    m.face([(2.62,0,2.35),(5.0,0,2.35),(5.0,0,4.5),(2.62,0,4.5)], C(.13,.15,.16))
    m.box((3.75,.48,3.55), (.85,.95,.72), C(.24,.26,.27))     # 床头柜
    m.box((3.75,.96,3.55), (.90,.05,.76), C(.31,.33,.34))
    glass3d(m, 3.55, .98, 3.42, .9)
    m.box((3.95,.99,3.70), (.30,.03,.22), PAPER)               # 纱布
    oximeter3d(m, 4.00, 1.04, 3.36, 1.0)
    phone3d(m, 3.42, 1.02, 3.78, .55, lit=False)
    m.box((4.55,.95,3.1), (.55,1.85,.12), C(.20,.23,.25))      # 椅背
    m.box((4.45,.48,3.25), (.55,.06,.55), C(.23,.26,.27))      # 椅座
    slippers3d(m, 3.30, 4.20, .9)
    m.light((3.85,1.35,3.30), C(.55,.82,1.0), 1.9, 3.2, glow=((168,210,226), 700, .22))
    # 厨房（左）
    m.box((-2.15,.45,1.1), (.85,.90,1.5), C(.20,.23,.25))
    m.box((-2.15,.92,1.1), (.90,.06,1.55), C(.30,.33,.34))
    m.box((-2.0,.94,1.0), (.45,.02,.55), DARK)                 # 水槽
    m.box((-2.25,1.9,1.1), (.5,.55,1.5), C(.24,.27,.29))
    m.face([(-1.65,.9,-.6),(-1.65,2.5,-.6),(-1.65,2.5,1.9),(-1.65,.9,1.9)], C(.18,.26,.30))
    # 鞋柜 + 伞架
    m.box((-2.15,.42,-.35), (.75,.84,1.0), WOOD_D)
    if umbrella_rack:
        m.prism((-1.55,.18,.05), .18, .36, 8, C(.18,.21,.23))
        umbrella3d(m,-1.62,.02,.72,wet=True)
        umbrella3d(m,-1.42,.10,1.02,long=True)
        slippers3d(m,-2.10,.55,1.0)
    # 餐桌
    if table:
        m.box((0,.74,2.2), (1.85,.09,1.05), WOOD)
        m.box((0,.79,2.2), (1.90,.02,1.10), C(.42,.31,.22))
        for dx in (-.80,.80):
            for dz in (-.42,.42):
                m.box((dx,.37,2.2+dz), (.09,.74,.09), WOOD_D)
        m.shadow(0,2.2,1.5)
    # 吊灯
    m.box((0,2.55,2.0), (.02,.30,.02), C(.35,.30,.22))
    m.cone((0,2.30,2.0), .30, .22, 8, C(.40,.32,.20))
    m.prism((0,2.27,2.0), .30, .06, 8, C(.85,.68,.38), em=C(.55,.42,.20))
    m.light((0,2.32,2.0), C(1.0,.78,.48), 1.55, 6.5, glow=((216,168,98), 1150, .34))
    return m

# ---------------------------------------------------------------- 场景：特写舞台
def scene_macro(kind, p, t):
    """手机 / 证件 / 钥匙 / 鞋底 / 刀尖 / 杯子等 3D 特写"""
    m = Mesh()
    m.face([(-3,0,4),(3,0,4),(3,3,4),(-3,3,4)], C(.09,.11,.13))
    m.face([(-3,0,-1),(3,0,-1),(3,0,4),(-3,0,4)], C(.10,.10,.11))
    warm = kind in ('badge','keys','reach_water','two_glasses')
    m.light((.8,2.1,1.0), C(1.0,.78,.48) if warm else C(.55,.78,.92), 2.0, 4.2,
            glow=((216,168,98) if warm else (120,170,200), 900, .30))
    if kind == 'phone_car':
        phone3d(m, 0, 1.15, 2.0, 2.7, lit=(p<.76))
        m.ui.append(((0,1.15,1.98),'car',p))
    elif kind == 'phone_group':
        phone3d(m, 0, 1.15, 2.0, 2.7, lit=(p<.72))
        m.ui.append(((0,1.15,1.98),'group',p))
    elif kind == 'chat':
        phone3d(m, 0, 1.15, 2.0, 2.5, lit=True)
        m.ui.append(((0,1.15,1.98),'chat',p))
    elif kind == 'badge':
        badge3d(m, 0, 1.0, 2.0, 3.2)
        m.box((-.75,.88,2.0), (.5,.10,.55), SKIN)
    elif kind == 'keys':
        keys3d(m, -.15, .92, 2.0, 3.2)
        m.box((0,.86,2.35), (2.2,.06,1.0), C(.26,.21,.17))
    elif kind == 'shoes':
        m.box((0,1.0,2.0), (1.5,.16,.9), C(.16,.18,.20), rot=(.35,.2,0))
        for i in range(7):
            m.box((-.55+i*.18,.92,2.0), (.05,.01,.82), C(.26,.28,.30))
    elif kind == 'knife_tremble':
        knife3d(m, .1, 1.05, 2.0, .15+math.sin(t*20)*.02, 3.4)
    elif kind == 'hand_knife' or kind == 'reach_water':
        m.box((0,.78,2.3), (2.6,.10,1.2), WOOD)
        if kind=='hand_knife':
            knife3d(m, .55, .88, 2.15, -.1, 2.0)
            m.box((-.55,.94,2.1), (.42,.12,.55), SKIN)
        else:
            glass3d(m, 1.05, .86, 2.2, 2.4)
            m.box((-.45,1.02,2.1), (.42,.12,.5), SKIN)
    elif kind == 'two_glasses':
        m.box((0,.78,2.3), (2.6,.10,1.2), WOOD)
        glass3d(m, -.45, .84, 2.2, 1.5)
        gx = -.1 + .7*min(1,p*1.6) if p<.7 else .6
        glass3d(m, gx, .84, 2.2, 1.5)
        m.box((gx-.22,.94,2.1), (.28,.10,.35), SKIN)
    elif kind == 'nightstand':
        m.box((0,.55,2.35), (1.6,1.1,1.0), C(.24,.26,.27))
        m.box((0,1.12,2.35), (1.65,.06,1.05), C(.31,.33,.34))
        glass3d(m, -.45, 1.13, 2.2, 1.4)
        m.box((.35,1.15,2.5), (.45,.04,.32), PAPER)
        oximeter3d(m, .48, 1.20, 2.18, 1.5)
        phone3d(m, -.65, 1.16, 2.55, .75, lit=False)
        m.box((1.25,1.4,2.8), (.4,1.9,.12), C(.20,.23,.25))
    elif kind == 'mat_hand':
        m.box((0,.85,2.2), (2.4,.08,1.4), C(.26,.21,.17))
        m.box((.45,1.0,2.1), (.55,.14,.6), SKIN)
        m.box((-.65,.92,2.35), (.32,.04,.12), SILVER)
    return m
