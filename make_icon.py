# -*- coding: utf-8 -*-
"""
生成 Git命令速查 app 图标（.ico 多尺寸 + .png 预览）
风格：深色圆角底 + 绿色 git 分支，与 app 主题一致
用法：python make_icon.py
"""
import math
import os

from PIL import Image, ImageDraw

# 主题色（与 main.py COLORS 一致）
BG_TOP = (35, 35, 69)      # #232345
BG_BOTTOM = (20, 20, 31)   # #14141f
GREEN = (78, 204, 163)     # #4ecca3
GREEN_DIM = (47, 143, 114)  # #2f8f72
BORDER = (60, 60, 100)     # #3c3c64

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
ICO = os.path.join(OUT_DIR, "icon.ico")
PNG = os.path.join(OUT_DIR, "icon.png")


def draw_icon(size: int) -> Image.Image:
    """在 size x size 上绘制图标（已抗锯齿）"""
    S = size * 4  # 4x 超采样再缩小
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # ---- 圆角背景 + 垂直渐变 ----
    pad = S * 0.04
    radius = S * 0.22
    # 用逐行渐变填满圆角矩形：先画整矩形渐变，再圆角遮罩
    grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(S):
        t = y / S
        r = int(BG_TOP[0] + (BG_BOTTOM[0] - BG_TOP[0]) * t)
        g = int(BG_TOP[1] + (BG_BOTTOM[1] - BG_TOP[1]) * t)
        b = int(BG_TOP[2] + (BG_BOTTOM[2] - BG_TOP[2]) * t)
        gd.line([(0, y), (S, y)], fill=(r, g, b, 255))
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([pad, pad, S - pad, S - pad], radius=radius, fill=255)
    img.paste(grad, (0, 0), mask)

    # 圆角边框（描边）
    d.rounded_rectangle([pad, pad, S - pad, S - pad], radius=radius,
                        outline=BORDER, width=max(2, S // 220))

    # ---- git 分支图形 ----
    W, H = S, S
    # 三个节点：顶部圆 / 左下圆 / 右下大圆
    top = (W * 0.50, H * 0.21)
    left = (W * 0.30, H * 0.78)
    right = (W * 0.72, H * 0.78)
    junction = (W * 0.50, H * 0.42)  # 分叉点

    line_w = max(4, int(S * 0.052))
    # 主干：top -> junction
    d.line([top, junction], fill=GREEN, width=line_w)
    # 分叉：junction -> left / junction -> right
    d.line([junction, left], fill=GREEN, width=line_w)
    d.line([junction, right], fill=GREEN, width=line_w)

    # 节点圆点（盖住线头，圆润收尾）
    def node(c, r):
        x, y = c
        d.ellipse([x - r, y - r, x + r, y + r], fill=GREEN)

    node(top, line_w * 0.62)
    node(left, line_w * 0.62)
    node(right, line_w * 0.95)  # 右下大圆

    # 大圆加一圈深色描边，更有层次
    x, y = right
    r = line_w * 0.95
    d.ellipse([x - r - line_w * 0.28, y - r - line_w * 0.28,
               x + r + line_w * 0.28, y + r + line_w * 0.28],
              outline=BG_BOTTOM, width=int(line_w * 0.3))

    # 缩小到目标尺寸（抗锯齿）
    return img.resize((size, size), Image.LANCZOS)


def main():
    # 生成多尺寸 ico（Windows 常用尺寸齐全）
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
             (128, 128), (256, 256)]
    imgs = [draw_icon(s) for s, _ in sizes]
    imgs[-1].save(ICO, format="ICO", sizes=sizes, append_images=imgs[:-1])
    print(f"ICO written: {ICO}")

    # 高分辨率 PNG 预览
    preview = draw_icon(512)
    preview.save(PNG, format="PNG")
    print(f"PNG written: {PNG}")


if __name__ == "__main__":
    main()
