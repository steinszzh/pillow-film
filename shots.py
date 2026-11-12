# -*- coding: utf-8 -*-
"""示例时间轴：30 镜 / 330 秒 / 24fps。

这里只保留结构演示数据。画面全部由 render.py / render3d.py 的代码绘制，
镜头描述为中性占位文字，台词留空。本文件不含任何第三方剧本内容。

换成自己的片子时：保持 id / t0 / t1 / kind / size / desc / lines 字段，
kind 需与 render.py 的场景分支对应，并同步调整 render.py 的 CAM 相机表。
"""

W, H = 1280, 720
FPS = 24
DURATION = 330

ACTS = [
    ("第1段", 0, 55),
    ("第2段", 55, 120),
    ("第3段", 120, 165),
    ("第4段", 165, 225),
    ("第5段", 225, 280),
    ("第6段", 280, 330),
]

# (镜号, 起, 止, 景别/机位, 画面描述, 台词, 画面类型)
SHOTS = [
    dict(id=1, t0=0, t1=5, size='黑屏', desc='黑屏 · 程序化绘制（black）',
         kind='black', lines=[]),
    dict(id=2, t0=5, t1=12, size='低机位特写', desc='低机位特写 · 程序化绘制（mat_hand）',
         kind='mat_hand', lines=[]),
    dict(id=3, t0=12, t1=18, size='中景背影', desc='中景背影 · 程序化绘制（corridor_back）',
         kind='corridor_back', lines=[]),
    dict(id=4, t0=18, t1=22, size='手机特写', desc='手机特写 · 程序化绘制（phone_car）',
         kind='phone_car', lines=[]),
    dict(id=5, t0=22, t1=28, size='中景', desc='中景 · 程序化绘制（elevator）',
         kind='elevator', lines=[]),
    dict(id=6, t0=28, t1=45, size='正反打', desc='正反打 · 程序化绘制（twoshot）',
         kind='twoshot', lines=[]),
    dict(id=7, t0=45, t1=55, size='过肩', desc='过肩 · 程序化绘制（entry_parcel）',
         kind='entry_parcel', lines=[]),
    dict(id=8, t0=55, t1=70, size='中景', desc='中景 · 程序化绘制（sink）',
         kind='sink', lines=[]),
    dict(id=9, t0=70, t1=85, size='手部特写', desc='手部特写 · 程序化绘制（phone_group）',
         kind='phone_group', lines=[]),
    dict(id=10, t0=85, t1=95, size='厨房玻璃反光', desc='厨房玻璃反光 · 程序化绘制（glass_reflection）',
         kind='glass_reflection', lines=[]),
    dict(id=11, t0=95, t1=108, size='中近景', desc='中近景 · 程序化绘制（two_glasses）',
         kind='two_glasses', lines=[]),
    dict(id=12, t0=108, t1=120, size='鞋底特写 → 正反打', desc='鞋底特写 → 正反打 · 程序化绘制（shoes）',
         kind='shoes', lines=[]),
    dict(id=13, t0=120, t1=138, size='手部特写 → 中景', desc='手部特写 → 中景 · 程序化绘制（hand_knife）',
         kind='hand_knife', lines=[]),
    dict(id=14, t0=138, t1=150, size='中景，桌面特写', desc='中景，桌面特写 · 程序化绘制（badge）',
         kind='badge', lines=[]),
    dict(id=15, t0=150, t1=165, size='正反打', desc='正反打 · 程序化绘制（reverse_bedroom）',
         kind='reverse_bedroom', lines=[]),
    dict(id=16, t0=165, t1=180, size='中景', desc='中景 · 程序化绘制（table_still）',
         kind='table_still', lines=[]),
    dict(id=17, t0=180, t1=192, size='缓推', desc='缓推 · 程序化绘制（umbrella）',
         kind='umbrella', lines=[]),
    dict(id=18, t0=192, t1=208, size='地垫特写', desc='地垫特写 · 程序化绘制（keys）',
         kind='keys', lines=[]),
    dict(id=19, t0=208, t1=225, size='手机屏特写 → 手部', desc='手机屏特写 → 手部 · 程序化绘制（chat）',
         kind='chat', lines=[]),
    dict(id=20, t0=225, t1=238, size='近景', desc='近景 · 程序化绘制（knife_tremble）',
         kind='knife_tremble', lines=[]),
    dict(id=21, t0=238, t1=250, size='中景', desc='中景 · 程序化绘制（block_door）',
         kind='block_door', lines=[]),
    dict(id=22, t0=250, t1=268, size='近景，手部特写', desc='近景，手部特写 · 程序化绘制（tears）',
         kind='tears', lines=[]),
    dict(id=23, t0=268, t1=280, size='正反打', desc='正反打 · 程序化绘制（lower_knife）',
         kind='lower_knife', lines=[]),
    dict(id=24, t0=280, t1=288, size='门缝侧脸', desc='门缝侧脸 · 程序化绘制（door_side）',
         kind='door_side', lines=[]),
    dict(id=25, t0=288, t1=295, size='门缝静物，一个长镜', desc='门缝静物，一个长镜 · 程序化绘制（nightstand）',
         kind='nightstand', lines=[]),
    dict(id=26, t0=295, t1=305, size='中景', desc='中景 · 程序化绘制（call120）',
         kind='call120', lines=[]),
    dict(id=27, t0=305, t1=312, size='低机位', desc='低机位 · 程序化绘制（slide_down）',
         kind='slide_down', lines=[]),
    dict(id=28, t0=312, t1=320, size='近景，老陈回头', desc='近景，老陈回头 · 程序化绘制（look_back）',
         kind='look_back', lines=[]),
    dict(id=29, t0=320, t1=327, size='门缝 → 小雅手部', desc='门缝 → 小雅手部 · 程序化绘制（reach_water）',
         kind='reach_water', lines=[]),
    dict(id=30, t0=327, t1=330, size='黑屏', desc='黑屏 · 程序化绘制（black）',
         kind='black', lines=[]),
]

# 音效事件：(时间点, 类型, 强度)。environment audio 由 audio.py 用 numpy 合成。
SFX = [
    (2.6, 'key', 0.9),
    (19.2, 'beep', 0.35),
    (22.4, 'ding', 0.55),
    (38.6, 'flicker', 0.8),
    (82.0, 'tap', 0.45),
    (97.5, 'pour', 0.5),
    (307.2, 'knife', 1.0),
    (325.0, 'siren', 0.75),
]


def shot_at(t):
    for s in SHOTS:
        if s["t0"] <= t < s["t1"]:
            return s
    return SHOTS[-1]


def layout_lines(shot):
    """按字数加权把镜内时间分配给台词，返回 [(speaker, text, start, dur)]。
    示例时间轴台词为空，直接返回 []。"""
    lines = shot["lines"]
    if not lines:
        return []
    a = shot["t0"] + 0.45
    b = shot["t1"] - 0.35
    span = max(1.0, b - a)
    weights = [3.0 if sp == "." else max(6.0, float(len(tx))) for sp, tx in lines]
    total = sum(weights)
    out, cur = [], a
    for (sp, tx), w in zip(lines, weights):
        d = span * w / total
        out.append((sp, tx, cur, d))
        cur += d
    return out


def act_of(t):
    for name, a, b in ACTS:
        if a <= t < b:
            return name
    return ACTS[-1][0]
