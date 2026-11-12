# -*- coding: utf-8 -*-
"""纯代码绘制库：场景 / 人物 / 道具 / 光效。无任何外部图像素材。"""
import math
import random
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
W, H = 1280, 720            # 输出分辨率；绘制原语不依赖时间轴，可独立使用

BW, BH = 1600, 900          # 内部绘制画布（留出推镜余量）
OW, OH = W, H               # 输出画布

BG      = (9, 13, 18)
WALL    = (25, 30, 36)
WALL2   = (19, 24, 30)
FLOOR   = (15, 19, 24)
DOOR    = (31, 40, 47)
WOOD    = (56, 42, 34)
WARM    = (216, 168, 98)
WARM_D  = (108, 82, 50)
COLD    = (168, 210, 226)
COLD_D  = (62, 96, 112)
SKIN    = (128, 112, 100)
SKIN_L  = (186, 160, 136)
BLUE    = (42, 78, 104)
BLUE_L  = (92, 145, 176)
GREY    = (82, 86, 90)
GREY_L  = (146, 150, 154)
INK     = (12, 16, 21)
SILVER  = (162, 176, 184)
RED     = (116, 48, 42)
TEXT    = (226, 224, 216)

# 字体：用环境变量覆盖，并提供多平台候选；全部找不到时回退 Pillow 内置字体。
import os as _os
SC_INDEX = 2                 # Noto CJK .ttc 中简体中文的 face index

def _font_candidates(env_name, defaults):
    override = _os.environ.get(env_name)
    return [p for p in ([override] if override else []) + defaults
            if p and _os.path.exists(p)]

FONT_SANS = _font_candidates('PILLOW_FILM_FONT_SANS', [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/System/Library/Fonts/PingFang.ttc',
    'C:/Windows/Fonts/msyh.ttc',
])
FONT_SERIF = _font_candidates('PILLOW_FILM_FONT_SERIF', [
    '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf',
])

_fc = {}
def font(size, serif=False):
    key = (size, serif)
    if key not in _fc:
        _fc[key] = ImageFont(size, serif)
    return _fc[key]

def ImageFont(size, serif):
    from PIL import ImageFont as IF
    for path in (FONT_SERIF if serif else FONT_SANS):
        try:
            return IF.truetype(path, size, index=SC_INDEX)
        except Exception:
            try:
                return IF.truetype(path, size)
            except Exception:
                continue
    try:
        return IF.load_default(size=size)
    except TypeError:
        return IF.load_default()

_gbase = {}
_gim = {}
def glow(size, color, power=2.2, strength=1.0):
    """径向光晕：alpha 底图只算一次，强度变化复用（避免逐帧 mgrid/sqrt）"""
    size = int(size)
    s = max(0.05, round(strength/0.05)*0.05)
    s = min(s, 1.0)
    k2 = (size, color, power, s)
    if k2 in _gim:
        return _gim[k2]
    k1 = (size, color, power)
    if k1 not in _gbase:
        r = size / 2.0
        yy, xx = np.mgrid[0:size, 0:size]
        d = np.sqrt(((xx-r)/r)**2 + ((yy-r)/r)**2)
        a = np.clip(1.0-d, 0, 1)**power
        _gbase[k1] = (a*255).astype(np.uint8)
    base = _gbase[k1]
    arr = np.empty((size, size, 4), dtype=np.uint8)
    arr[..., 0] = color[0]; arr[..., 1] = color[1]; arr[..., 2] = color[2]
    arr[..., 3] = ((base.astype(np.uint16) * int(s*256)) >> 8).astype(np.uint8)
    im = Image.fromarray(arr, 'RGBA')
    _gim[k2] = im
    return im

_cone = None
def lamp_cone():
    """吊灯光锥：边缘柔和渐隐的预生成 RGBA 贴图（避免硬三角形）"""
    global _cone
    if _cone is None:
        yy, xx = np.mgrid[0:BH, 0:BW]
        y0, y1 = 190.0, 790.0
        half = 62 + np.clip((yy-y0)/(y1-y0),0,1)*430
        d = np.abs(xx-820.0) - half
        a = np.clip(1.0 - d/95.0, 0, 1)**1.4
        a *= np.clip((yy-y0)/90.0,0,1) * np.clip((y1-yy)/210.0,0,1)
        a *= ((yy>=y0)&(yy<=y1))
        arr = np.zeros((BH,BW,4), dtype=np.uint8)
        arr[...,0],arr[...,1],arr[...,2] = WARM
        arr[...,3] = (a*46).astype(np.uint8)
        _cone = Image.fromarray(arr,'RGBA')
    return _cone

class Canvas:
    def __init__(self, t, bg=BG):
        self.t = t
        self.img = Image.new('RGB', (BW, BH), bg)
        self.d = ImageDraw.Draw(self.img)
        self.layer = Image.new('RGBA', (BW, BH), (0,0,0,0))
        self.ld = ImageDraw.Draw(self.layer)
        self.dirty = False

    def flush(self):
        if not self.dirty:
            return
        self.img.paste(self.layer, (0,0), self.layer)
        self.ld.rectangle((0,0,BW,BH), fill=(0,0,0,0))
        self.dirty = False

    def rect(self, box, fill, outline=None, width=1, radius=0):
        width, radius = int(width), int(radius)
        if radius:
            self.d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=width)

    def poly(self, pts, fill, outline=None, width=1):
        self.d.polygon(pts, fill=fill)
        if outline:
            self.d.line(list(pts)+[pts[0]], fill=outline, width=int(width), joint='curve')

    def ell(self, box, fill, outline=None, width=1):
        self.d.ellipse(box, fill=fill, outline=outline, width=int(width))

    def line(self, pts, fill, width=1):
        self.d.line(pts, fill=fill, width=int(width), joint='curve')

    def arect(self, box, color, alpha, radius=0):
        a = int(alpha)
        if radius:
            self.ld.rounded_rectangle(box, radius=int(radius), fill=(*color, a))
        else:
            self.ld.rectangle(box, fill=(*color, a))
        self.dirty = True

    def apoly(self, pts, color, alpha):
        self.ld.polygon(pts, fill=(*color, int(alpha)))
        self.dirty = True

    def aell(self, box, color, alpha):
        self.ld.ellipse(box, fill=(*color, int(alpha)))
        self.dirty = True

    def aline(self, pts, color, alpha, width=1):
        self.ld.line(pts, fill=(*color, int(alpha)), width=int(width), joint='curve')
        self.dirty = True

    def glow(self, cx, cy, size, color, power=2.2, strength=1.0):
        g = glow(size, color, power, strength)
        self.img.paste(g, (int(cx-size/2), int(cy-size/2)), g)

    def text(self, xy, s, size, color=TEXT, serif=False, anchor='la', spacing=0):
        self.d.text(xy, s, font=font(size, serif), fill=color, anchor=anchor, spacing=spacing)


def flicker(t, base=1.0):
    """日光灯：不稳定 + 偶发骤暗"""
    v = base * (0.93 + 0.07*math.sin(t*8.3) + 0.035*math.sin(t*31.7))
    phase = t % 7.3
    if 0.18 < phase < 0.30 or 3.86 < phase < 3.94:
        v *= 0.42
    return v


def rain(c, t, box, n=110, seed=3, alpha=105, speed=430, slant=7):
    """区域内斜向雨丝"""
    x0, y0, x1, y1 = box
    rng = random.Random(seed)
    span = (y1-y0) + 40
    for i in range(n):
        bx = rng.uniform(x0-20, x1+20)
        by = rng.uniform(y0, y1)
        ln = rng.uniform(10, 26)
        y = y0 + ((by - y0 + t*speed*(0.7+0.6*rng.random())) % span)
        x = bx + (y-by)*0.22
        if x0 <= x <= x1 and y0 <= y <= y1:
            a = int(alpha*rng.uniform(0.35, 1.0))
            c.aline([(x, y), (x-slant*ln/20, y+ln)], (150, 180, 196), a, 1)


# ---------------------------------------------------------------- 场景
def corridor(c, t, lamp=True, door_gap=False, elevator=False, seed=1):
    """六楼走廊：左电梯、中窗、右 602 铁门、地垫、顶灯"""
    f = flicker(t) if lamp else 1.0
    c.rect((0,0,BW,BH), WALL2)
    # 墙面分块 + 剥落
    c.rect((0,0,BW,690), WALL)
    c.poly([(0,690),(BW,690),(BW,BH),(0,BH)], FLOOR)
    c.aline([(0,690),(BW,690)], (70,66,56), 90, 2)
    for i in range(11):
        x = i*155 + 20
        c.aline([(x,690),(x-90,BH)], (26,31,37), 55, 1)
    for i in range(4):
        yy = 250 + i*105
        c.aline([(0,yy),(BW,yy+8)], (29,34,40), 70, 1)
    rng = random.Random(seed)
    for i in range(7):
        x, y = rng.uniform(430,880), rng.uniform(120,560)
        w, h = rng.uniform(30,90), rng.uniform(12,42)
        c.poly([(x,y),(x+w,y-6),(x+w*0.8,y+h),(x-6,y+h*0.8)], (31,36,41))

    # 尽头小窗（雨）
    c.rect((470,150,700,430), (12,18,25), outline=(56,62,66), width=8)
    c.aline([(585,150),(585,430)], (56,62,66), 140, 6)
    c.aline([(470,290),(700,290)], (56,62,66), 140, 6)
    c.arect((478,158,692,422), (36,54,66), 90)
    rain(c, t, (478,158,692,422), n=95, seed=seed, alpha=120)
    c.glow(585, 285, 420, (60,92,112), 2.6, 0.35)

    # 电梯（左）
    if elevator:
        c.rect((40,150,400,700), (34,42,48), outline=(70,78,82), width=6)
        gap = 8
        c.rect((52,162,222-gap,690), (48,58,64))
        c.rect((222+gap,162,388,690), (48,58,64))
        c.aline([(222,162),(222,690)], (14,18,22), 220, 10)
    else:
        c.rect((40,150,400,700), (29,35,40), outline=(62,68,72), width=6)
        c.aline([(220,162),(220,690)], (14,18,22), 200, 4)

    # 602 门
    c.rect((900,120,1360,730), (22,27,32), outline=(64,70,74), width=10)
    c.rect((922,142,1338,712), DOOR)
    c.aline([(922,300),(1338,300)], (38,48,55), 120, 3)
    c.aline([(922,560),(1338,560)], (38,48,55), 120, 3)
    c.rect((1180,405,1220,438), (12,16,20))
    c.ell((1270,410,1292,432), (128,116,84))
    c.rect((1010,190,1130,250), (44,50,54), radius=6)
    c.text((1070,220), "602", 42, (196,190,176), anchor='mm')
    c.rect((922,700,1338,716), (8,11,14))
    if door_gap:
        c.arect((926,702,1334,712), (198,172,110), 150)

    # 地垫
    c.poly([(860,720),(1400,720),(1460,880),(800,880)], (46,40,35))
    c.poly([(878,734),(1382,734),(1436,866),(824,866)], (62,53,44))
    for i in range(9):
        x = 890 + i*60
        c.aline([(x,740),(x-22,860)], (48,41,34), 90, 2)

    # 顶灯管
    c.rect((300,40,1300,86), (16,20,24), outline=(58,62,62), width=4)
    lit = int(150*f)
    c.rect((320,52,1280,74), (lit+40, int(lit*0.83), int(lit*0.52)))
    c.glow(800, 66, 1300, WARM, 3.0, 0.42)
    c.apoly([(230,86),(1370,86),(BW,900),(0,900)], WARM, int(16*f))
    c.flush()
    return f


def interior(c, t, lamp=True, bed_light=0.0, table=True):
    """客厅兼厨房：吊灯、餐桌、水槽、玻璃隔断、鞋柜伞架、卧室门"""
    c.rect((0,0,BW,BH), WALL2)
    c.rect((0,0,BW,660), WALL)
    c.poly([(0,660),(BW,660),(BW,BH),(0,BH)], FLOOR)
    for i in range(9):
        c.aline([(i*210-100,660),(i*210-260,BH)], (27,31,36), 60, 1)

    # 厨房（左）
    c.rect((0,250,470,690), (22,28,33), outline=(52,58,62), width=5)
    c.rect((20,470,450,660), (34,40,44))
    c.rect((50,485,250,530), (16,20,24))        # 水槽
    c.ell((120,490,180,505), (10,14,18))
    c.rect((270,400,440,460), (42,48,52))       # 吊柜
    c.line([(150,485),(150,440),(150,410)], (110,118,120), 7)
    c.line([(150,410),(205,410)], (110,118,120), 7)
    c.aline([(470,180),(470,700)], (96,116,124), 40, 6)   # 玻璃隔断框

    # 鞋柜 + 伞架（左下）
    c.rect((40,560,330,700), (48,38,32), outline=(70,56,44), width=4)
    c.aline([(40,630),(330,630)], (70,56,44), 120, 3)
    c.ell((300,610,322,632), (150,132,100))
    c.rect((350,590,430,700), (30,34,38))
    c.line([(360,600),(360,690)], (74,80,84), 5)
    c.line([(420,600),(420,690)], (74,80,84), 5)

    # 卧室门（右）
    c.rect((1250,110,1560,720), (21,26,31), outline=(60,66,70), width=8)
    c.rect((1272,132,1538,700), (34,39,44))
    c.ell((1480,400,1500,420), (140,126,94))
    if bed_light > 0:
        c.arect((1266,140,1278,698), COLD, int(210*bed_light))
        c.glow(1272, 420, 520, COLD, 3.0, 0.34*bed_light)

    # 吊灯 + 光锥
    c.line([(820,0),(820,120)], (66,62,54), 5)
    c.poly([(770,120),(870,120),(900,180),(740,180)], (52,46,36))
    c.ell((742,168,898,196), (196,152,86))
    if lamp:
        c.glow(820, 190, 700, WARM, 2.4, 0.50)
        cone = lamp_cone()
        c.img.paste(cone, (0,0), cone)
    c.flush()

    # 餐桌
    if table:
        c.poly([(430,565),(1150,565),(1270,700),(310,700)], (66,49,38))
        c.poly([(445,558),(1135,558),(1250,684),(330,684)], (80,60,45))
        c.aline([(445,558),(1135,558)], (132,102,72), 90, 3)
        c.poly([(330,684),(1250,684),(1250,706),(330,706)], (44,33,26))
    c.flush()


def void(c, t, warm=0.0):
    c.rect((0,0,BW,BH), (7,10,14))
    if warm:
        c.glow(800, 450, 1200, WARM, 3.0, 0.10*warm)
    c.flush()


def doorcrack(c, t, width=170, cx=800, objects=True, face=False):
    """只拍一道门缝：冷白台灯光漏出，不出现床上的人"""
    c.rect((0,0,BW,BH), (5,8,11))
    left, right = cx-width/2, cx+width/2
    # 门框暗边
    c.rect((left-70,0,left,BH), (13,17,21))
    c.rect((right,0,right+70,BH), (13,17,21))
    c.aline([(left-70,0),(left-70,BH)], (44,50,54), 100, 3)
    c.aline([(right+70,0),(right+70,BH)], (44,50,54), 100, 3)
    # 光带
    c.rect((left,0,right,BH), (36,52,60))
    c.glow(cx, 450, 900, COLD, 2.0, 0.30)
    c.apoly([(left,0),(right,0),(right+30,BH),(left-30,BH)], COLD, 26)
    c.flush()
    if objects:
        nightstand(c, t, cx, width)
    if face:
        pass
    return left, right


def nightstand(c, t, cx=800, width=170):
    """镜 25：床头柜静物组（不拍人）"""
    # 柜体
    c.rect((cx-150, 560, cx+150, 900), (48,52,54))
    c.rect((cx-160, 548, cx+160, 574), (66,70,72))
    c.aline([(cx,574),(cx,900)], (34,38,40), 80, 2)
    # 半杯水 + 小勺
    c.arect((cx-112, 420, cx-52, 550), (150,186,196), 120)
    c.arect((cx-108, 478, cx-56, 546), (110,162,178), 165)
    c.aline([(cx-112,478),(cx-52,478)], (206,228,232), 190, 2)
    c.line([(cx-92,428),(cx-78,478)], (178,190,192), 5)
    c.ell((cx-96,418,cx-84,430), (190,200,202))
    # 纱布
    c.arect((cx-20,500,cx+74,548), (206,204,190), 210)
    for i in range(5):
        c.aline([(cx-14+i*17,504),(cx-14+i*17,544)], (170,168,158), 90, 1)
    # 指夹血氧仪
    c.rect((cx+52, 452, cx+130, 512), (28,36,40), radius=8)
    c.rect((cx+60, 460, cx+122, 492), (16,44,44), radius=4)
    c.text((cx+91, 476), "98", 27, (96,226,190), anchor='mm')
    c.text((cx+91, 502), "72", 13, (120,150,150), anchor='mm')
    # 充电中的男式手机
    c.rect((cx-146, 452, cx-118, 522), (18,22,26), radius=4)
    c.rect((cx-143, 456, cx-121, 516), (40,58,64), radius=2)
    c.line([(cx-132,522),(cx-132,560),(cx-100,560)], (100,106,108), 4)
    # 椅背毯子（背景轮廓）
    c.apoly([(cx-260,300),(cx-160,300),(cx-150,620),(cx-270,620)], (44,50,54), 170)
    c.apoly([(cx-262,300),(cx-176,300),(cx-186,470),(cx-272,450)], (66,72,76), 150)
    # 女式拖鞋（地面）
    c.ell((cx+70, 790, cx+160, 830), (86,74,70))
    c.ell((cx+82, 796, cx+148, 818), (108,94,88))
    c.flush()


# ---------------------------------------------------------------- 道具
def glass(c, x, y, s=1.0, water=0.55, alpha=190):
    w, h = 46*s, 88*s
    c.arect((x-w/2, y-h, x+w/2, y), (148,182,190), int(alpha*0.45))
    wh = h*water
    c.arect((x-w/2+3, y-wh, x+w/2-3, y-3), (96,148,166), int(alpha*0.72))
    c.aline([(x-w/2,y-h),(x-w/2,y)], (206,226,230), int(alpha*0.8), 2)
    c.aline([(x+w/2,y-h),(x+w/2,y)], (206,226,230), int(alpha*0.8), 2)
    c.aline([(x-w/2,y),(x+w/2,y)], (206,226,230), int(alpha*0.8), 2)
    c.aline([(x-w/2+3,y-wh),(x+w/2-3,y-wh)], (180,214,220), int(alpha*0.9), 2)
    c.aline([(x-w/2+7,y-h+8),(x-w/2+7,y-12)], (226,238,238), int(alpha*0.5), 3)


def knife(c, x, y, angle=0.0, s=1.0, blade=(176,188,194)):
    """水果刀，angle 为弧度，0 = 水平向右"""
    L, hw = 150*s, 9*s
    def pt(a, b):
        return (x + a*math.cos(angle) - b*math.sin(angle),
                y + a*math.sin(angle) + b*math.cos(angle))
    c.poly([pt(0,-hw), pt(L*0.72,-hw*0.8), pt(L,0), pt(L*0.72,hw*0.8), pt(0,hw)], blade)
    c.poly([pt(-56*s,-hw*1.5), pt(0,-hw*1.5), pt(0,hw*1.5), pt(-56*s,hw*1.5)], (44,34,28))
    c.aline([pt(10,-hw*0.5),pt(L*0.7,-hw*0.4)], (226,234,236), 150, 2)


def badge(c, x, y, s=1.0, open_=True):
    w, h = 190*s, 128*s
    c.rect((x-w/2,y-h/2,x+w/2,y+h/2), (52,26,26), radius=6*s)
    c.rect((x-w/2+8*s,y-h/2+8*s,x+w/2-8*s,y+h/2-8*s), (86,44,38), radius=4*s)
    if open_:
        c.ell((x-w*0.28,y-24*s,x-w*0.28+46*s,y+22*s), (168,150,116))
        c.aline([(x-w*0.05,y-8*s),(x+w*0.34,y-8*s)], (196,178,142), 160, 4*s)
        c.aline([(x-w*0.05,y+16*s),(x+w*0.24,y+16*s)], (150,132,102), 130, 3*s)
    c.text((x, y+h/2-18*s), "公安", int(16*s), (214,196,160), anchor='mm')
    c.flush()


def phone(c, x, y, w=230, h=430, screen=None, t=0, angle=0):
    """手机本体；screen 是回调"""
    c.rect((x-w/2,y-h/2,x+w/2,y+h/2), (10,13,17), radius=28, outline=(62,68,72), width=4)
    c.rect((x-w/2+12,y-h/2+30,x+w/2-12,y+h/2-30), (18,26,31), radius=10)
    c.rect((x-w*0.16,y-h/2+14,x+w*0.16,y-h/2+21), (30,36,40), radius=4)
    if screen:
        screen(c, (x-w/2+12, y-h/2+30, x+w/2-12, y+h/2-30), t)


def parcel(c, x, y, s=1.0, label=True):
    w, h = 250*s, 150*s
    c.poly([(x-w/2,y-h*0.5),(x+w/2,y-h*0.5),(x+w/2,y+h*0.4),(x-w/2,y+h*0.4)], (126,102,72))
    c.poly([(x-w/2,y-h*0.5),(x+w*0.02,y-h*0.5),(x+w*0.02,y+h*0.4),(x-w/2,y+h*0.4)], (148,120,86))
    c.poly([(x-w/2,y-h*0.5),(x+w/2,y-h*0.5),(x+w/2+26*s,y-h*0.62),(x-w/2+26*s,y-h*0.62)], (96,78,56))
    c.aline([(x-40*s,y-h*0.5),(x-40*s,y+h*0.4)], (178,160,128), 160, 8*s)
    if label:
        c.rect((x-w*0.36,y-h*0.32,x+w*0.36,y+h*0.24), (216,212,198))
        c.text((x-w*0.32,y-h*0.26), "康宁药房", int(17*s), (70,80,76))
        c.text((x-w*0.32,y-h*0.02), "收件人  张强", int(21*s), (26,32,34))
        c.aline([(x-w*0.32,y+h*0.08),(x+w*0.3,y+h*0.08)], (110,110,106), 110, 2)
        for i in range(16):
            c.aline([(x-w*0.3+i*10*s,y+h*0.13),(x-w*0.3+i*10*s,y+h*0.20)], (40,40,40), 150, 2)


def keys(c, x, y, s=1.0, car=True):
    """钥匙串：金属环 + 三把垂下的门钥匙 + 一把醒目的车钥匙"""
    metal, metal_hi, dark = (146,158,160), (206,218,220), (18,22,26)
    # 金属环
    c.ell((x-30*s,y-30*s,x+30*s,y+30*s), metal)
    c.ell((x-16*s,y-16*s,x+16*s,y+16*s), dark)
    c.aline([(x-28*s,y-10*s),(x-20*s,y-22*s)], metal_hi, 180, 3*s)
    # 三把门钥匙
    for i, (dx, ang) in enumerate(((-58,0.42),(-6,0.12),(52,-0.20))):
        ax = x + dx*s
        ay = y + 18*s
        L = (112 if i!=1 else 128)*s
        tipx, tipy = ax + math.sin(ang)*L, ay + math.cos(ang)*L
        c.line([(ax+math.sin(ang)*20*s, ay+math.cos(ang)*20*s),(tipx,tipy)], metal, 8*s)
        hx = ax + math.sin(ang)*20*s
        c.rect((hx-14*s, ay-16*s, hx+14*s, ay+16*s), metal, radius=6*s)
        c.ell((hx-4*s, ay-4*s, hx+4*s, ay+4*s), dark)
        # 钥匙齿
        for j in range(3):
            bx = tipx - (j*13+2)*s*math.cos(ang)
            by = tipy - (j*13+2)*s*math.sin(ang)
            c.rect((bx-11*s,by-5*s,bx+2*s,by+5*s), metal)
        c.aline([(tipx-3*s,tipy-70*s),(tipx+1*s,tipy-8*s)], metal_hi, 110, 2*s)
    if car:
        cx, cy = x+150*s, y+30*s
        c.rect((cx-70*s,cy-42*s,cx+120*s,cy+46*s), (30,40,48), radius=16*s)
        c.rect((cx-56*s,cy-30*s,cx+40*s,cy+6*s), (74,90,98), radius=8*s)
        for k in range(3):
            c.ell((cx-44*s+k*34*s,cy-20*s,cx-28*s+k*34*s,cy-4*s), (168,188,194))
        c.ell((cx+72*s,cy-22*s,cx+100*s,cy+6*s), (152,58,50))
        c.rect((cx+112*s,cy-12*s,cx+176*s,cy+12*s), metal, radius=4*s)
        c.glow(cx+30*s, cy, 300*s, COLD, 3.0, 0.22)


def umbrella(c, x, y, s=1.0, wet=False, long=False):
    L = (330 if long else 270)*s
    c.line([(x,y),(x,y-L)], (78,86,90), 9*s)
    c.ell((x-16*s,y-L-10*s,x+16*s,y-L+14*s), (126,132,134))
    c.poly([(x,y-L+70*s),(x-88*s,y-L+70*s),(x,y-L-16*s),(x+88*s,y-L+70*s)], (52,62,70))
    c.aline([(x,y-L-16*s),(x,y-L+70*s)], (96,108,116), 100, 2*s)
    c.line([(x,y),(x-28*s,y+18*s)], (110,116,118), 6*s)
    if wet:
        rng = random.Random(9)
        for i in range(14):
            dx, dy = rng.uniform(-80,80)*s, rng.uniform(-40,60)*s
            c.aell((x+dx,y-L+60*s+dy,x+dx+4*s,y-L+64*s+dy), (150,190,204), 160)
    c.flush()


def slippers(c, x, y, s=1.0, inward=True):
    for i, dx in enumerate((0, 78*s)):
        xx = x+dx
        c.ell((xx-34*s,y-14*s,xx+46*s,y+14*s), (66,70,72))
        c.ell((xx-24*s,y-9*s,xx+34*s,y+8*s), (88,92,92))
        c.aline([(xx-20*s,y),(xx+32*s,y)], (42,46,48), 120, 2*s)


def toolbox(c, x, y, s=1.0, open_=False):
    w,h = 180*s, 110*s
    c.rect((x-w/2,y-h,x+w/2,y), (24,28,32), radius=8*s, outline=(66,72,76), width=3)
    c.line([(x-50*s,y-h),(x-50*s,y-h-26*s),(x+50*s,y-h-26*s),(x+50*s,y-h)], (92,98,100), 7*s)
    c.rect((x-16*s,y-h*0.62,x+16*s,y-h*0.42), (116,124,126), radius=3*s)
    if open_:
        c.rect((x-w/2,y-h-70*s,x+w/2,y-h-56*s), (36,40,44))
        c.line([(x-50*s,y-h-70*s),(x-10*s,y-h-18*s)], (150,158,160), 9*s)
        c.ell((x+34*s,y-h-40*s,x+74*s,y-h-14*s), (60,64,66), outline=(110,116,118), width=3)


def hand(c, x, y, s=1.0, grip=False, reach=False, pale=False):
    """手部：腕 / 掌 / 四指 / 拇指，暗光下只留边缘高光"""
    col = (132,114,100) if pale else (80,72,68)
    hi  = (178,152,130) if pale else (116,104,94)
    shadow = (34,30,28)
    # 腕
    c.poly([(x-23*s,y+34*s),(x+23*s,y+34*s),(x+25*s,y+86*s),(x-25*s,y+86*s)], col)
    c.apoly([(x-23*s,y+62*s),(x+23*s,y+62*s),(x+25*s,y+86*s),(x-25*s,y+86*s)], shadow, 90)
    # 掌
    c.poly([(x-38*s,y+36*s),(x-41*s,y-8*s),(x-33*s,y-36*s),
            (x+33*s,y-36*s),(x+41*s,y-8*s),(x+37*s,y+36*s)], col)
    # 四指
    lengths = (66, 82, 76, 58) if not grip else (30, 36, 34, 26)
    ang = 0.62 if reach else 0.0
    for i, L in enumerate(lengths):
        fx = x + (i-1.5)*20*s
        tipx = fx + L*s*math.sin(ang)
        tipy = y-32*s - L*s*math.cos(ang)*(1.0 if not grip else 0.45)
        c.line([(fx, y-28*s),(tipx,tipy)], col, 16*s)
        c.ell((tipx-8*s,tipy-8*s,tipx+8*s,tipy+8*s), col)
        c.aline([(fx-6*s, tipy+22*s),(fx+6*s, tipy+24*s)], shadow, 110, 2*s)
    # 拇指
    c.poly([(x-39*s,y+4*s),(x-48*s,y-10*s),(x-78*s,y-32*s),
            (x-70*s,y-44*s),(x-31*s,y-20*s)], col)
    # 掌背高光 / 掌心阴影
    c.aline([(x-32*s,y-33*s),(x+32*s,y-33*s)], hi, 135, 3*s)
    c.aline([(x-38*s,y+2*s),(x-70*s,y-38*s)], hi, 115, 2*s)
    c.aline([(x+39*s,y-20*s),(x+38*s,y+30*s)], hi, 95, 2*s)
    c.apoly([(x-34*s,y+8*s),(x+34*s,y+8*s),(x+34*s,y+34*s),(x-32*s,y+34*s)], shadow, 60)
    c.flush()


def person(c, x, foot, h, who, facing=1, pose='stand', tool=False, dim=1.0, alpha=255):
    """风格化人物剪影。x=中心，foot=脚底 y，h=身高，facing=1 右 / -1 左"""
    def C(v):
        return tuple(int(q*dim) for q in v)
    cloth = C((34,62,84)) if who == '陈' else C((74,78,82))
    edge  = C(BLUE_L) if who == '陈' else C(GREY_L)
    hair  = C((34,38,40)) if who == '陈' else C((26,25,27))
    skin  = C((64,58,54))
    r = h*0.082
    hy = foot-h+r*1.05                      # 头中心
    sh = foot-h*0.78                       # 肩
    wa = foot-h*0.44                       # 腰
    # 腿
    c.poly([(x-h*0.095,wa),(x-h*0.005,wa),(x-h*0.008,foot),(x-h*0.10,foot)], C((26,30,34)))
    c.poly([(x+h*0.005,wa),(x+h*0.095,wa),(x+h*0.10,foot),(x+h*0.008,foot)], C((22,26,30)))
    # 躯干
    c.poly([(x-h*0.125,sh),(x+h*0.125,sh),(x+h*0.098,wa),(x-h*0.098,wa)], cloth)
    c.aline([(x-facing*h*0.125,sh),(x-facing*h*0.098,wa)], edge, 130, 3)
    # 领口
    c.poly([(x-h*0.045,sh),(x+h*0.045,sh),(x,sh+h*0.055)], C((30,34,38)))
    # 头颈
    c.rect((x-h*0.022,sh-h*0.065,x+h*0.022,sh+h*0.01), skin)
    c.ell((x-r*0.92,hy-r*1.18,x+r*0.92,hy+r*1.28), skin)
    # 背光半张脸沉进阴影
    c.apoly([(x-facing*r*0.9,hy-r*1.1),(x-facing*r*0.9,hy+r*1.25),
             (x,hy+r*1.25),(x,hy-r*1.1)], (8,11,14), 175)
    c.poly([(x-r*0.92,hy-r*0.35),(x-r*0.85,hy-r*1.2),(x+r*0.85,hy-r*1.2),(x+r*0.92,hy-r*0.3),
            (x+r*0.5,hy-r*0.72),(x-r*0.55,hy-r*0.7)], hair)
    if who == '雅':
        c.poly([(x-r*facing,hy-r*0.2),(x-r*1.75*facing,hy+r*0.35),
                (x-r*1.5*facing,hy+r*1.55),(x-r*0.7*facing,hy+r*0.8)], hair)
        c.aline([(x-r*0.8*facing,hy-r*0.9),(x,hy-r*1.16),(x+r*0.45*facing,hy-r*0.98)],
                C((126,132,134)), 90, 2)
    else:
        c.aline([(x-r*0.5,hy-r*1.16),(x+r*0.55,hy-r*1.16)], C((104,110,112)), 120, 2)
    # 侧面轮廓（额头 → 鼻 → 唇 → 下巴），不做五官特写
    nx = x + facing*r*0.94
    c.aline([(x+facing*r*0.52,hy-r*0.72),(nx-r*0.06,hy-r*0.12),
             (x+facing*r*0.60,hy+r*0.06),(x+facing*r*0.70,hy+r*0.30),
             (x+facing*r*0.30,hy+r*0.66)], C((136,124,112)), 130, 2)
    c.aline([(x+facing*r*0.22,hy-r*0.08),(x+facing*r*0.66,hy-r*0.08)], C((20,24,26)), 190, 2)
    c.aline([(x-facing*r*0.86,hy-r*0.6),(x-facing*r*0.8,hy+r*0.5)], C(edge), 95, 2)
    # 手臂
    arm_col = cloth
    if pose == 'hold_knife':
        c.poly([(x+h*0.11*facing,sh+h*0.01),(x+h*0.16*facing,sh+h*0.03),
                (x+h*0.26*facing,wa+h*0.04),(x+h*0.23*facing,wa+h*0.09)], arm_col)
        c.ell((x+h*0.25*facing*1.0-9,wa+h*0.03,x+h*0.25*facing+9,wa+h*0.09+10), skin)
    elif pose == 'reach':
        c.poly([(x+h*0.10*facing,sh+h*0.02),(x+h*0.16*facing,sh+h*0.06),
                (x+h*0.42*facing,sh+h*0.14),(x+h*0.40*facing,sh+h*0.20)], arm_col)
        c.ell((x+h*0.41*facing-10,sh+h*0.12,x+h*0.41*facing+14,sh+h*0.22), skin)
    elif pose == 'cup':
        c.poly([(x-h*0.11*facing,sh+h*0.02),(x-h*0.16*facing,sh+h*0.05),
                (x-h*0.20*facing,wa-h*0.02),(x-h*0.15*facing,wa-h*0.05)], arm_col)
    else:
        c.poly([(x-h*0.125*facing,sh),(x-h*0.155*facing,sh+h*0.02),
                (x-h*0.16*facing,wa+h*0.04),(x-h*0.125*facing,wa+h*0.04)], arm_col)
        c.poly([(x+h*0.125*facing,sh),(x+h*0.155*facing,sh+h*0.02),
                (x+h*0.16*facing,wa+h*0.04),(x+h*0.125*facing,wa+h*0.04)], arm_col)
    # 工具箱 / 手表
    if tool:
        tx = x - h*0.20*facing
        toolbox(c, tx, foot-h*0.34, s=h/620*0.9)
    if who == '陈':
        c.aline([(x+h*0.15*facing,wa+h*0.035),(x+h*0.17*facing,wa+h*0.035)], (186,192,192), 190, 5)
    c.flush()


def oximeter_beep(c, t, cx, cy):
    pass
