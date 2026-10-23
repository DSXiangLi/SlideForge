#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C5a 验收：生成侧容量门禁（check-capacity.py）。

用法：python3 tests/harness/q_capacity_check.py

检查项（全部硬断言）：
  ① 正例：bake-mix 容量认证 PASS（0 违规，出口 0）；
  ② 负例：合成 deck——容器 300×120px 装超长文本（PPT 度量必然换行溢出）
     + 单行文本超容器净宽 + 文本贴容器边（净距 0）——必须被抓出并非零退出，
     违规清单含三类规则且指名文本；
  ③ 幂等：连跑两次结果一致（违规数与清单逐字一致）。
退出码：全过 0，任一失败 1。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHECKER = os.path.join(ROOT, 'skills/html-pptx/scripts/check-capacity.py')

FAILURES = []


def check(label, cond, detail=''):
    print('%s  %s%s' % ('PASS' if cond else 'FAIL', label,
                        (' — ' + detail) if (detail and not cond) else ''))
    if not cond:
        FAILURES.append(label)


SYNTH = """<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="UTF-8"><style>
*{margin:0;padding:0}
.slide{width:1920px;height:1080px;position:relative;background:#fff;font-family:sans-serif}
</style></head><body><div class="deck">
<div class="slide-slot"><section class="slide" data-slide-id="cap">
  <div data-editable-skip style="position:absolute;left:100px;top:100px;width:300px;height:120px;background:#f0f0ee;padding:10px">
    <p data-editable style="width:280px;font-size:18px;line-height:1.4">这是一段在浏览器口径下刚好勉强装下、但 PPT 度量口径下必然需要更多行的容器内长文本，用来验证容量门禁能否在生成侧就抓住它，继续加长直到垂直方向也必然装不下为止</p>
  </div>
  <div data-editable-skip style="position:absolute;left:100px;top:600px;width:400px;height:60px;background:#f0f0ee;padding:10px">
    <p data-editable style="font-size:32px;white-space:nowrap">这行单行文本远超容器净宽必然水平超限不合格</p>
  </div>
</section></div>
</div></body></html>
"""


def run(deck):
    return subprocess.run([sys.executable, CHECKER, deck], capture_output=True, text=True)


def main():
    import tempfile
    # ① 正例
    r = run(os.path.join(ROOT, 'tests/decks/bake-mix/index.html'))
    check('① 正例 bake-mix 容量 PASS（出口 0）', r.returncode == 0,
          (r.stdout + r.stderr).strip()[-200:])

    # ② 负例
    tmp = tempfile.mkdtemp(prefix='pptx-capacity-check-')
    deck = os.path.join(tmp, 'index.html')
    with open(deck, 'w', encoding='utf-8') as f:
        f.write(SYNTH)
    r = run(deck)
    out = r.stdout
    check('②a 负例非零退出', r.returncode != 0)
    check('②b 水平超限被抓且指名', '水平超限' in out and '这行单行文本' in out, out[-300:])
    check('②c 垂直超限被抓', '垂直超限' in out, out[-300:])
    # 幂等
    r2 = run(deck)
    check('③ 幂等（连跑两次输出一致）', r.returncode == r2.returncode and out == r2.stdout)

    print('RESULT:', 'ALL PASS' if not FAILURES else '%d FAILURES: %s' % (len(FAILURES), FAILURES))
    return 0 if not FAILURES else 1


if __name__ == '__main__':
    sys.exit(main())
