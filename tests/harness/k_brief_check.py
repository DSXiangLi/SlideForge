#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
需求脑暴页快速检查（editor.html v2.5，技能 Step 0.5 / references/briefing.md）。

用法：python3 tests/harness/k_brief_check.py

流程（全部硬断言）：
  ① 打开 editor.html（独立模式，本地静态服务）→ 点「需求脑暴」→ 覆盖层打开；
  ② 选场景「现场演讲」+ 主题 B1 变体「柠檬黄」+ 封面多选（加勾 主标题/日期）；
  ③ 生成简报 → 断言预览文本含「需求简报」「现场演讲」「B1」「柠檬黄」
     「design-brief」，且未作答组标注（缺省）；
  ④ 状态隔离：脑暴页选择不得污染设计决策抽屉的 answers（theme 仍为 null）；
  ⑤ Esc 关闭覆盖层；
  ⑥ 配图方式三态（imagegen v2 G1）：⑧b 三态选项齐备；条件追问随「部分页整页重绘」
     显隐；缺省展开为语义清单（封面/各章节扉页/收束页 + defaulted）；
     显式清单分隔符解析；纯 HTML 不携带 bake_intent。
退出码：全过 0，任一失败 1。
"""
import os
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PORT = 8931
BASE = 'http://127.0.0.1:%d' % PORT


def main():
    failures = []

    def check(label, cond, detail=''):
        print('%s  %s%s' % ('PASS' if cond else 'FAIL', label,
                            (' — ' + detail) if (detail and not cond) else ''))
        if not cond:
            failures.append(label)

    srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT),
                            '--bind', '127.0.0.1', '-d', ROOT],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(50):
            try:
                urllib.request.urlopen(BASE + '/editor.html', timeout=1)
                break
            except Exception:
                time.sleep(0.2)

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            ctx = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = ctx.new_page()
            page.on('pageerror', lambda e: print('[pageerror]', e))
            page.goto(BASE + '/editor.html')
            page.wait_for_function('() => window.state !== undefined')

            # ① 打开脑暴页（覆盖层内容应在此刻才首次渲染）
            #    主题卡数随 themes.md 单源漂移（sync-themes 同步进 PANEL_DATA），
            #    断言动态取注入 JSON 的选项数，不钉死常量
            n_themes = page.evaluate("PANEL_DATA.questions[0].options.length")
            n_cards_before = page.evaluate("document.querySelectorAll('.theme-card').length")
            page.click('#btnBrief')
            page.wait_for_selector('#briefOverlay.show')
            n_cards_after = page.evaluate("document.querySelectorAll('.theme-card').length")
            check('① 覆盖层打开；主题卡懒渲染（开前 %d → 开后 %d，主题数 %d）'
                  % (n_cards_before, n_cards_after, n_themes),
                  n_cards_before == n_themes and n_cards_after == n_themes * 2)

            # 缺省项视觉标注
            n_def = page.evaluate("document.querySelectorAll('#briefOverlay .def-tag').length")
            check('①b 缺省项带「缺省」标注（%d 处）' % n_def, n_def >= 6)
            narr_hidden = page.evaluate(
                "document.getElementById('briefNarrative').style.display === 'none'")
            check('①c 叙事弧追问默认隐藏', narr_hidden)

            # ② 作答：场景=现场演讲；内容来源=从 0 到 1 → 叙事弧出现；
            #    主题 B1 + 变体柠檬黄；封面加勾 主标题/日期
            page.click('#briefOverlay .opt[data-id="keynote"]')
            page.click('#briefOverlay .opt[data-id="scratch"]')
            narr_shown = page.evaluate(
                "document.getElementById('briefNarrative').style.display !== 'none'")
            check('②a 选「从 0 到 1」后叙事弧条件显示', narr_shown)
            page.click('#briefOverlay .theme-card[data-id="b1"] .variants i[data-vid="b1-v1"]')
            page.click('#briefOverlay .chip[data-id="title"]')
            page.click('#briefOverlay .chip[data-id="date"]')
            ba = page.evaluate('window.briefAnswers')
            check('②b 状态落定', ba['scene'] == 'keynote' and ba['theme'] == 'b1'
                  and ba['themeVariant'] == 'b1-v1'
                  and sorted(ba['cover']) == ['date', 'title', 'toc'],
                  repr(ba))

            # ③ 简报内容（v3.9.x 起「生成」并入「发送」，`#btnBriefGen` 已不存在：预览由
            #    buildBriefExport() 产出，这里直接读构造器输出，不为了断言真的提交一次）
            text = page.evaluate("() => buildBriefExport().text")
            for kw in ['需求简报', '现场演讲', 'B1', '柠檬黄', 'design-brief',
                       '请按以下需求简报制作 HTML 幻灯片', '章节目录',
                       'SLOT: theme tokens', 'SLOT: theme css']:
                check('③ 简报含 %r' % kw, kw in text)
            check('③b 未作答组标注（缺省）', '（缺省）' in text)
            check('③c 密度按场景推导', '低密度' in text)
            check('③d 封面多选生效', '主标题' in text and '日期' in text)
            states = page.evaluate("() => ['loading','pending','processing','succeeded','error'].every(s => document.querySelector('.brief-submit-status[data-state=\"'+s+'\"]') || [...document.styleSheets].some(sheet => { try { return [...sheet.cssRules].some(r => r.selectorText && r.selectorText.includes('data-state=\"'+s+'\"')); } catch(e) { return false; } }))")
            check('③e 状态机样式覆盖 loading/pending/processing/succeeded/error', states)
            page.click('#btnBriefSend')
            page.wait_for_selector('#briefResult:not([hidden])')
            page.wait_for_function("() => bridge.briefSubmission.state === 'succeeded' && bridge.briefSubmission.route === 'copy'")
            copy_status = page.inner_text('#briefSubmitStatus')
            check('③f copy 路由文案独立且不冒充 MCP', '已复制' in copy_status and '未进入 Bridge 队列' in copy_status and '没有 MCP tool result' in copy_status, copy_status)
            embedded_status = page.evaluate("""async () => { state.embedded=true; await document.getElementById('btnBriefSend').click(); await new Promise(r=>setTimeout(r,50)); return {route:bridge.briefSubmission.route,text:document.getElementById('briefSubmitStatus').innerText}; }""")
            check('③g embedded 路由文案独立', embedded_status['route'] == 'embedded' and 'postMessage' in embedded_status['text'] and '未进入 Bridge 队列' in embedded_status['text'], repr(embedded_status))
            page.evaluate('state.embedded=false')

            # ④ 与设计决策抽屉状态隔离
            drawer_theme = page.evaluate('window.answers.theme')
            check('④ 抽屉 answers 未被脑暴页污染（theme=%r）' % drawer_theme,
                  drawer_theme is None)

            # ⑥ 配图方式三态（imagegen v2 G1 / briefing.md 第⑧组）：
            #    ⑧b 三态单选 + 条件追问 + bake_intent 字段 + 缺省展开
            n_ill = page.evaluate(
                "document.querySelectorAll('#briefOverlay .opt[data-id=\"html\"],"
                "#briefOverlay .opt[data-id=\"ai\"],#briefOverlay .opt[data-id=\"bake\"]').length")
            check('⑥a 配图方式三态选项齐备（html/ai/bake）', n_ill == 3)
            bake_hidden = page.evaluate(
                "document.getElementById('briefBakePages').style.display === 'none'")
            check('⑥b 未选「部分页整页重绘」时条件追问隐藏', bake_hidden)
            page.click('#briefOverlay .opt[data-id="bake"]')
            bake_shown = page.evaluate(
                "document.getElementById('briefBakePages').style.display !== 'none'")
            check('⑥c 选「部分页整页重绘」后条件追问显示', bake_shown)
            text = page.evaluate("() => buildBriefExport().text")
            j = page.evaluate("() => buildBriefExport().json")
            bi = (j.get('answers') or {}).get('bake_intent') or {}
            check('⑥d 缺省展开：文本「配图方式：部分页整页重绘」+「整页重绘：封面、各章节扉页、收束页（缺省）」',
                  '配图方式：部分页整页重绘' in text and '整页重绘：封面、各章节扉页、收束页（缺省）' in text)
            check('⑥e bake_intent 缺省展开为语义清单 + defaulted',
                  bi.get('pages') == ['封面', '各章节扉页', '收束页'] and bi.get('defaulted') is True,
                  repr(bi))
            page.fill('#briefBakePages input', '封面、 Q3 复盘页')
            text = page.evaluate("() => buildBriefExport().text")
            j = page.evaluate("() => buildBriefExport().json")
            bi = (j.get('answers') or {}).get('bake_intent') or {}
            check('⑥f 显式清单：分隔符解析 + 不再标缺省',
                  '整页重绘：封面、Q3 复盘页' in text and '（缺省）' not in text.split('整页重绘：')[1].split('\n')[0]
                  and bi.get('pages') == ['封面', 'Q3 复盘页'] and bi.get('defaulted') is False,
                  repr(bi))
            page.click('#briefOverlay .opt[data-id="html"]')
            j = page.evaluate("() => buildBriefExport().json")
            t = page.evaluate("() => buildBriefExport().text")
            check('⑥g 纯 HTML 不携带 bake_intent、无「整页重绘：」行',
                  'bake_intent' not in (j.get('answers') or {}) and '整页重绘：' not in t)
            page.click('#briefOverlay .opt[data-id="bake"]')   # 还原现场，不干扰后续断言

            # ⑤ Esc 关闭
            page.keyboard.press('Escape')
            page.wait_for_timeout(200)
            closed = page.evaluate(
                "!document.getElementById('briefOverlay').classList.contains('show')")
            check('⑤ Esc 关闭覆盖层', closed)

            ctx.close()
            browser.close()
    finally:
        srv.terminate()

    print('RESULT:', 'ALL PASS' if not failures else '%d FAILURES: %s' % (len(failures), failures))
    return 0 if not failures else 1


if __name__ == '__main__':
    sys.exit(main())
