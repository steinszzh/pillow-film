# -*- coding: utf-8 -*-
"""最小示例：不读时间轴，直接用底层绘制原语渲一帧。

运行：python examples/minimal.py
输出：docs/preview.png

这一步只依赖 Pillow + numpy，不需要 ffmpeg、不需要浏览器、不需要 shots.py。
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import draw as D
import scene3d as S

OUT = os.path.join(ROOT, 'docs', 'preview.png')


def build_scene():
    m = S.Mesh()
    m.box((0, -0.05, 3.0), (8, 0.1, 10), S.FLOOR)          # 地面
    m.box((-2.4, 1.3, 3.0), (0.15, 2.6, 10), S.WALL)        # 左墙
    m.box((2.4, 1.3, 3.0), (0.15, 2.6, 10), S.WALL2)        # 右墙
    m.box((0, 1.3, 6.2), (4.8, 2.6, 0.15), S.DOOR)          # 尽头
    m.box((0.9, 0.55, 3.4), (0.7, 1.1, 0.7), S.WOOD)        # 木箱
    m.box((-0.8, 0.35, 4.4), (0.5, 0.7, 0.5), S.GREY)       # 金属块
    m.light((0, 2.4, 2.2), S.C(.95, .68, .38), 1.5, 7.0)    # 暖吊灯
    m.light((0, 2.2, 5.6), S.C(.45, .72, .85), 0.8, 6.0)    # 冷灯管
    m.shadow(0.9, 3.4, 1.0)
    return m


def main():
    mesh = build_scene()
    cam = S.camera((0, 1.55, -2.4), (0, 1.15, 3.6), fov=48)
    img = S.render(mesh, cam, t=0.0)

    dr = D.ImageDraw.Draw(img)
    dr.text((28, 24), 'pillow-film / no browser, no 3D library',
            fill=D.TEXT, font=D.font(22))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    img.save(OUT, optimize=True)
    print('faces:', len(mesh.v), 'size:', img.size, '->', OUT)


if __name__ == '__main__':
    main()
