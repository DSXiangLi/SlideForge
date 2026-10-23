#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""harmony-fixture 合成资产生成器（纯 stdlib：zlib+struct 手写 PNG，不引 Pillow）。

三张 160×90（16:9）竖条带图，与 index.html 的 theme token 配套：
  tokens.png  —— 纯 token 色（--paper/--ink/--accent 三条带），预期全过；
  foreign.png —— 纯无关色（品红族三近色 #ff00ff/#dd55ff/#ff55ee——对本
                 fixture 的六个 token 全部 ΔE00>39，是网格搜索能找到的最远
                 色族），预期同时触发指标 A+B；
  mixed.png   —— 50% --accent + 50% magenta，用于烙入页：预期只触发指标 A
                 （accent 有呼应、--paper/--ink 缺席但满幅烙入页豁免）。
重新生成：python3 gen-assets.py（幂等，字节一致）。
"""
import os
import struct
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))

PAPER = (0xF2, 0xEF, 0xE8)
INK = (0x17, 0x17, 0x1C)
ACCENT = (0xB4, 0x23, 0x2A)
# 对本 fixture token 集网格搜索，距全部 token ΔE00>39 的最远色族（品红/紫）
MAG_A = (0xFF, 0x00, 0xFF)
MAG_B = (0xDD, 0x55, 0xFF)
MAG_C = (0xFF, 0x55, 0xEE)

W, H = 160, 90


def chunk(typ, data):
    return (struct.pack('>I', len(data)) + typ + data +
            struct.pack('>I', zlib.crc32(typ + data) & 0xFFFFFFFF))


def write_png(path, bands):
    """bands: [(x0, x1, (r,g,b)), ...] 竖条带，拼满 [0, W)。"""
    rows = []
    for _y in range(H):
        row = bytearray(b'\x00')  # filter type 0
        for x in range(W):
            for x0, x1, rgb in bands:
                if x0 <= x < x1:
                    row += bytes(rgb)
                    break
        rows.append(bytes(row))
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)  # 8-bit RGB
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
           chunk(b'IDAT', zlib.compress(b''.join(rows))) + chunk(b'IEND', b''))
    with open(path, 'wb') as f:
        f.write(png)


def main():
    assets = os.path.join(HERE, 'assets')
    os.makedirs(assets, exist_ok=True)
    write_png(os.path.join(assets, 'tokens.png'),
              [(0, 64, PAPER), (64, 112, INK), (112, 160, ACCENT)])
    write_png(os.path.join(assets, 'foreign.png'),
              [(0, 54, MAG_A), (54, 108, MAG_B), (108, 160, MAG_C)])
    write_png(os.path.join(assets, 'mixed.png'),
              [(0, 80, ACCENT), (80, 160, MAG_A)])
    print('written: tokens.png foreign.png mixed.png (%dx%d)' % (W, H))


if __name__ == '__main__':
    main()
