#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
K 期章节跳转三通道验证（skeleton v7）：Playwright 1920×1080。

用法：python3 tests/harness/k_nav_check.py tests/decks/<deck>/index.html

检查项（全部硬）：
  ① 数字键直跳——按 '3' 跳到第 3 个 data-chapter 章节页（deck.scrollTop
     收敛到目标 .slide-slot 的 offsetTop）；
  ② 锚点点击——点击封面第一个 a.nav-link，跳到其 href 指向的章节页；
  ③ End 键——跳到末页。
前置断言：deck 必须含 ≥1 个 data-chapter 章节页、封面必须含 ≥1 个
a.nav-link[href^="#"]（高密度档封面目录为默认要求）。
退出码：全过 0，任一失败 1。
"""
import os
import sys

from playwright.sync_api import sync_playwright

STATE_JS = """() => {
  const deck = document.getElementById('deck');
  const slots = Array.from(deck.querySelectorAll('.slide-slot'));
  const chapters = [];
  slots.forEach((s, i) => {
    const sl = s.querySelector('.slide[data-chapter]');
    if (sl) chapters.push({ slot: i, id: sl.id, name: sl.dataset.chapter });
  });
  const top = deck.scrollTop;
  let cur = 0;
  for (let i = 0; i < slots.length; i++) {
    if (slots[i].offsetTop <= top + 8) cur = i;
  }
  return { cur, top, total: slots.length, chapters };
}"""


def wait_slot(page, idx, timeout=6000):
    """等到 deck.scrollTop 收敛到第 idx 个 slot 的 offsetTop（容差 6px）。"""
    page.wait_for_function(
        "(i) => { const d = document.getElementById('deck');"
        " const s = d.querySelectorAll('.slide-slot')[i];"
        " return s && Math.abs(d.scrollTop - s.offsetTop) < 6; }",
        arg=idx, timeout=timeout)


def main():
    target = os.path.abspath(sys.argv[1])
    url = 'file://' + target
    failures = 0
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})
        page.goto(url)
        page.wait_for_timeout(800)
        st = page.evaluate(STATE_JS)
        print('deck: %s  pages: %d  chapters: %s'
              % (target, st['total'],
                 ['%d:%s(%s)' % (c['slot'] + 1, c['id'], c['name']) for c in st['chapters']]))

        if len(st['chapters']) < 3:
            print('FAIL 前置：data-chapter 章节页不足 3 个（实际 %d）' % len(st['chapters']))
            browser.close()
            return 1
        first_link = page.query_selector('a.nav-link[href^="#"]')
        if not first_link:
            print('FAIL 前置：封面缺少 a.nav-link 目录链接')
            browser.close()
            return 1

        # ① 数字键 3 → 第 3 章
        expect = st['chapters'][2]
        page.keyboard.press('3')
        try:
            wait_slot(page, expect['slot'])
            cur = page.evaluate(STATE_JS)['cur']
            ok = cur == expect['slot']
            print('%s  ① 数字键 3 → 第3章「%s」 slot %d（当前 %d）'
                  % ('PASS' if ok else 'FAIL', expect['name'], expect['slot'] + 1, cur + 1))
            failures += 0 if ok else 1
        except Exception as e:
            print('FAIL  ① 数字键 3 未收敛到 slot %d：%s' % (expect['slot'] + 1, e))
            failures += 1

        # ② 点击封面第一个 nav-link → 其 href 指向的章节页
        page.evaluate("document.getElementById('deck').scrollTo({top: 0, behavior: 'auto'})")
        page.wait_for_timeout(400)
        href = first_link.get_attribute('href')
        want_id = href[1:]
        hit = page.evaluate(
            """(wid) => {
              const slots = Array.from(document.querySelectorAll('.slide-slot'));
              for (let i = 0; i < slots.length; i++) {
                const sl = slots[i].querySelector('.slide');
                if (sl && sl.id === wid) return i;
              }
              return -1;
            }""", want_id)
        if hit < 0:
            print('FAIL  ② nav-link href=%s 找不到对应 id 的章节页' % href)
            failures += 1
        else:
            page.click('a.nav-link[href="%s"]' % href)
            try:
                wait_slot(page, hit)
                cur = page.evaluate(STATE_JS)['cur']
                ok = cur == hit
                print('%s  ② 点击封面第一个 nav-link（%s）→ slot %d（当前 %d）'
                      % ('PASS' if ok else 'FAIL', href, hit + 1, cur + 1))
                failures += 0 if ok else 1
            except Exception as e:
                print('FAIL  ② 点击 %s 未收敛到 slot %d：%s' % (href, hit + 1, e))
                failures += 1

        # ③ End → 末页
        page.keyboard.press('End')
        last = st['total'] - 1
        try:
            wait_slot(page, last)
            cur = page.evaluate(STATE_JS)['cur']
            ok = cur == last
            print('%s  ③ End → 末页 slot %d（当前 %d）'
                  % ('PASS' if ok else 'FAIL', last + 1, cur + 1))
            failures += 0 if ok else 1
        except Exception as e:
            print('FAIL  ③ End 未收敛到末页 slot %d：%s' % (last + 1, e))
            failures += 1

        browser.close()
    print('RESULT:', 'ALL PASS' if failures == 0 else '%d FAILURES' % failures)
    return 0 if failures == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
