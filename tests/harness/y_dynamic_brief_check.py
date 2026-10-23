#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
T35 动态脑暴（briefing v2 / docs/design/brief-dynamic-brainstorming.md §11）。

用法：python3 tests/harness/y_dynamic_brief_check.py

覆盖（全部操作临时工作区，不写用户仓库）：
  T35a 注入全链路：open_editor(brief_options=...) → 会话状态携带 → 浏览器
       brief 视图动态渲染（DOM 选项文本来自 options、画像卡、★ 推荐徽标、
       prefilled 折叠行、skipped 折叠区、theme_pick 推荐卡 + 浏览全部入口）；
  T35b schema 拒收：非法 options → /api/bridge/open 400 且会话原值不变
       （并入 T35a 子断言，bridge_core 层另有 test_bridge_core.py 覆盖）；
  T35c 无 options 回落：不带参数打开 → 静态问卷渲染断言；
  T35d 覆盖语义：二次带参整体替换 → 页面重进 brief 视图取到新值；
       不带参 → 原值保持；
  T35e 嵌入态：入站 pptx-html:brief-options 注入 → 动态渲染；非法注入 →
       回落静态；
  T35f 下游零回归：动态选项作答提交 → design-brief JSON 键结构与静态提交
       diff 为空（仅多可选 extras）；prefilled 未修改按接受推断计入
       （defaulted=false）、「由 AI 决定」按缺省语义标注（defaulted=true）。
既有 k_brief 脑暴三态由 T31 在同一 run_e2e 批次覆盖。
退出码：全过 0，任一失败 1。
"""
import contextlib
import copy
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.bridge_core import BridgeCore, BridgeHTTPServer, write_serve  # noqa: E402

from playwright.sync_api import sync_playwright  # noqa: E402

PORT = 8932
BASE = 'http://127.0.0.1:%d' % PORT

FAILURES = []


def check(label, cond, detail=''):
    print('%s  %s%s' % ('PASS' if cond else 'FAIL', label,
                        (' — ' + detail) if (detail and not cond) else ''))
    if not cond:
        FAILURES.append(label)


def one_request(origin, path, body=None, bearer=None):
    headers = {}
    data = None
    if bearer:
        headers['Authorization'] = 'Bearer ' + bearer
    if body is not None:
        data = json.dumps(body, ensure_ascii=False, separators=(',', ':')).encode()
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(origin + path, data=data, headers=headers,
                                 method='POST' if body is not None else 'GET')
    try:
        response = urllib.request.urlopen(req, timeout=15)
        return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())


@contextlib.contextmanager
def live_daemon(workdir):
    core = BridgeCore(workdir, require_lock=True)
    server = BridgeHTTPServer(('127.0.0.1', 0), core)
    write_serve(core, server)
    thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .05}, daemon=True)
    thread.start()
    try:
        yield core, core.origin, core.management_token
    finally:
        server.shutdown(); thread.join(timeout=5); server.server_close(); core.close()


def open_editor(origin, management, options='__absent__'):
    body = {'consumer_id': 't35-consumer', 'deck_path': None, 'output_path': 'index.html',
            'view': 'brief', 'open_browser': False}
    if options != '__absent__':
        body['brief_options'] = options
    return one_request(origin, '/api/bridge/open', body, management)


def options_v1():
    return {
        'version': 2,
        'kind': 'brief-options',
        'context_summary': 'T35 验收·季度经营述职，数据密集，含品牌红 VI',
        'profile': {'signals': ['data-heavy', 'brand-color', 't35-marker']},
        'groups': [
            {'id': 'scene', 'title': '使用场景', 'impact': '决定密度与动效锚点',
             'state': 'ask', 'multi': False,
             'options': [
                 {'id': 'present', 'label': '动态场景·登台述职', 'desc': '限时讲完，结论先行',
                  'recommended': True, 'reason': '素材为季度经营数据'},
                 {'id': 'asyncread', 'label': '动态场景·会后自读', 'desc': '阅读分发形态', 'default': True},
             ]},
            {'id': 'audience', 'title': '受众', 'impact': '影响语言深度与隐喻选型',
             'state': 'prefilled', 'prefill_reason': '素材明确写给管理层',
             'multi': False,
             'options': [
                 {'id': 'exec', 'label': '动态受众·投委会', 'desc': '结论先行', 'recommended': True,
                  'reason': '素材抬头为投委会'},
                 {'id': 'ops', 'label': '动态受众·一线运营', 'desc': '执行细节', 'default': True},
             ]},
            {'id': 'x-data', 'title': '数据呈现偏好', 'impact': '影响图表密度',
             'state': 'ask', 'multi': False,
             'options': [
                 {'id': 'hero', 'label': '数据英雄页', 'desc': '大数字单页聚焦', 'recommended': True,
                  'reason': '素材含 12 张经营报表'},
                 {'id': 'compact', 'label': '紧凑图表', 'desc': '多图并列', 'default': True},
             ]},
            {'id': 'pages', 'title': '页数预算', 'impact': '与密度档联动校验',
             'state': 'skipped', 'prefill_reason': '对话未提页数限制',
             'multi': False,
             'options': [
                 {'id': 'p15', 'label': '8–15 页', 'desc': '缺省档', 'default': True},
                 {'id': 'p25', 'label': '15–25 页', 'desc': '长报告'},
             ]},
        ],
        'theme_pick': {'recommended': ['b1/b1-v1'], 'reason': '经营述职 + 品牌红 → 瑞士网格变体',
                       'library_open': True},
    }


def options_v2():
    opts = options_v1()
    opts['context_summary'] = 'T35 验收·覆盖语义第二版'
    opts['groups'][0]['options'][0]['label'] = '动态场景·重构汇报'
    return opts


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        # ---------- T35a + T35b + T35d + T35f：Bridge 态（in-process daemon，临时目录） ----------
        with tempfile.TemporaryDirectory(prefix='t35-bridge-') as tmp:
            with live_daemon(Path(tmp)) as (core, origin, management):
                code, opened = open_editor(origin, management, options_v1())
                check('T35a-0 open_editor 返回 200 且回显 brief_options',
                      code == 200 and (opened.get('brief_options') or {}).get('context_summary')
                      == options_v1()['context_summary'], '%s %r' % (code, opened))

                # T35b：非法 options → 400 拒收且会话原值不变
                bad = options_v1()
                bad['groups'][0]['id'] = 'unknown-dim'
                code_bad, body_bad = open_editor(origin, management, bad)
                code_keep, opened_keep = open_editor(origin, management)
                check('T35b 非法 options 400 拒收且原值不变',
                      code_bad == 400 and code_keep == 200
                      and (opened_keep.get('brief_options') or {}).get('context_summary')
                      == options_v1()['context_summary'],
                      'bad=%s %r keep=%s %r' % (code_bad, body_bad, code_keep, opened_keep))

                ctx = browser.new_context(viewport={'width': 1280, 'height': 900})
                page = ctx.new_page()
                page.on('pageerror', lambda e: print('[pageerror]', e))
                page.goto(opened['url'])
                page.wait_for_function(
                    "() => window.bridge && bridge.bound && "
                    "document.getElementById('briefOverlay').classList.contains('show')",
                    timeout=10000)
                page.wait_for_timeout(300)

                body_text = page.inner_text('#briefBody')
                check('T35a-1 动态选项文本来自 options（非静态字面量）',
                      '动态场景·登台述职' in body_text and '现场演讲' not in body_text)
                profile = page.evaluate("""() => {
                  const p = document.querySelector('#briefBody .brief-profile');
                  return p ? p.innerText : null; }""")
                check('T35a-2 画像卡：徽标 + context_summary + signals 胶囊 + 素材提示',
                      bool(profile) and '根据你的需求定制' in profile
                      and 'T35 验收·季度经营述职' in profile and 't35-marker' in profile
                      and '回到对话告知 AI' in profile, repr(profile))
                check('T35a-3 ask 组推荐项带 ★ 徽标 + reason 一行',
                      page.evaluate("""document.querySelector(
                        '[data-dyn-group="scene"] .rec-tag') !== null""")
                      and '素材为季度经营数据' in body_text)
                check('T35a-4 ask 组缺省项带「缺省」小标 + 「由 AI 决定」快捷项',
                      page.evaluate("""document.querySelector(
                        '[data-dyn-group="scene"] .def-tag') !== null""")
                      and page.evaluate("""document.querySelector(
                        '[data-dyn-group="scene"] .opt[data-id="__ai__"]') !== null"""))
                pre = page.evaluate("""() => {
                  const s = document.querySelector('[data-dyn-group="audience"]');
                  return s ? { cls: s.className, text: s.innerText,
                               bodyHidden: s.querySelector('.brief-prefilled-row + div').style.display } : null; }""")
                check('T35a-5 prefilled 折叠行「组名：推断值（依据）· 修改」+ 顶部计数',
                      bool(pre) and 'brief-prefilled' in pre['cls'] and '投委会' in pre['text']
                      and '素材明确写给管理层' in pre['text'] and '修改' in pre['text']
                      and pre['bodyHidden'] == 'none'
                      and '已按你的需求预填 1 项' in body_text, repr(pre))
                skipped_sec = page.evaluate("""() => {
                  const secs = [...document.querySelectorAll('#briefBody .brief-group')];
                  const s = secs.find(x => x.querySelector('h3') &&
                    x.querySelector('h3').textContent.includes('未提及的维度'));
                  return s ? { title: s.querySelector('h3').textContent,
                               hidden: s.querySelector('.brief-skipped-list').style.display } : null; }""")
                check('T35a-6 skipped 收进页尾「未提及的维度」折叠区',
                      bool(skipped_sec) and '1' in skipped_sec['title']
                      and skipped_sec['hidden'] == 'none', repr(skipped_sec))
                check('T35a-7 条件组带「因你的素材而问」徽标',
                      page.evaluate("""document.querySelector(
                        '[data-dyn-group="x-data"] .cond-tag') !== null"""))
                theme_rec = page.evaluate("""() => {
                  const wrap = document.getElementById('briefThemeGrid');
                  const card = wrap && wrap.querySelector('.theme-card[data-id="b1"] .rec-tag');
                  const toggle = [...document.querySelectorAll('#briefBody button')]
                    .find(b => b.textContent === '浏览全部主题');
                  return { rec: !!card, toggle: !!toggle,
                           reason: document.querySelector('#briefBody').innerText.includes('AI 推荐：') }; }""")
                check('T35a-8 theme_pick 推荐卡置顶 ★ + reason + 「浏览全部」次级入口',
                      theme_rec['rec'] and theme_rec['toggle'] and theme_rec['reason'], repr(theme_rec))
                # 推荐到变体粒度：点击推荐卡落定 theme + variant
                page.click('#briefThemeGrid .theme-card[data-id="b1"]')
                sel = page.evaluate('({t: briefAnswers.theme, v: briefAnswers.themeVariant})')
                check('T35a-9 推荐卡点击落定主题+变体', sel == {'t': 'b1', 'v': 'b1-v1'}, repr(sel))

                # ---------- T35d 覆盖语义 ----------
                code_d, opened_d = open_editor(origin, management, options_v2())
                check('T35d-0 二次带参整体替换（响应回显新值）',
                      code_d == 200 and (opened_d.get('brief_options') or {}).get('context_summary')
                      == 'T35 验收·覆盖语义第二版', '%s' % code_d)
                page.keyboard.press('Escape')
                page.wait_for_timeout(200)
                page.click('#btnBrief')
                page.wait_for_timeout(600)
                body_text2 = page.inner_text('#briefBody')
                check('T35d-1 页面重进 brief 视图取到新值',
                      '动态场景·重构汇报' in body_text2 and '动态场景·登台述职' not in body_text2)
                code_k, opened_k = open_editor(origin, management)
                check('T35d-2 不带参保持原值',
                      code_k == 200 and (opened_k.get('brief_options') or {}).get('context_summary')
                      == 'T35 验收·覆盖语义第二版', '%s' % code_k)
                page.keyboard.press('Escape')
                page.wait_for_timeout(200)
                page.click('#btnBrief')
                page.wait_for_timeout(600)
                check('T35d-3 不带参后页面仍为新值',
                      '动态场景·重构汇报' in page.inner_text('#briefBody'))

                # ---------- T35f 动态作答 → design-brief JSON 格式 diff ----------
                page.click('[data-dyn-group="scene"] .opt[data-id="present"]')
                page.click('[data-dyn-group="x-data"] .opt[data-id="__ai__"]')
                # prefilled audience 不展开不修改 = 接受推断值
                page.click('#btnBriefGen')
                page.wait_for_selector('#briefResult:not([hidden])')
                j = page.evaluate('window.briefLast.json')
                ans = j.get('answers') or {}
                expect_keys = {'topic', 'scene', 'audience', 'source', 'pages', 'theme', 'font',
                               'motion', 'brightness', 'cover', 'illustration', 'density_derived'}
                check('T35f-0 顶层与 answers 键结构（仅多可选 extras）',
                      j.get('kind') == 'design-brief' and j.get('version') == 1
                      and set(ans.keys()) == expect_keys | {'extras'}, repr(sorted(ans.keys())))
                check('T35f-1 动态组选择映射回既有 answers 键（scene 键不变）',
                      ans.get('scene', {}).get('choice') == 'present'
                      and ans['scene'].get('label') == '动态场景·重构汇报'
                      and ans['scene'].get('defaulted') is False, repr(ans.get('scene')))
                check('T35f-2 prefilled 未修改按接受推断计入（不标缺省）',
                      ans.get('audience', {}).get('choice') == 'exec'
                      and ans['audience'].get('defaulted') is False, repr(ans.get('audience')))
                check('T35f-3 x-* 条件组进 extras；「由 AI 决定」按缺省语义标注',
                      (ans.get('extras') or {}).get('x-data', {}).get('choice') == 'hero'
                      and ans['extras']['x-data'].get('defaulted') is True
                      and ans['extras']['x-data'].get('label') == '数据英雄页',
                      repr(ans.get('extras')))
                check('T35f-4 skipped 维度按缺省进简报（defaulted=true，不进 extras）',
                      ans.get('pages', {}).get('defaulted') is True
                      and 'x-data' in (ans.get('extras') or {})
                      and 'pages' not in (ans.get('extras') or {}), repr(ans.get('pages')))
                text = page.inner_text('#briefPreview')
                check('T35f-5 文本简报模板不变',
                      '需求简报 ·' in text and '请按以下需求简报制作 HTML 幻灯片' in text
                      and '动态场景·重构汇报' in text and '（缺省）' in text)
                ctx.close()

        # ---------- T35c 无 options 回落静态问卷（Bridge 态不带参） ----------
        with tempfile.TemporaryDirectory(prefix='t35-static-') as tmp:
            with live_daemon(Path(tmp)) as (core, origin, management):
                code, opened = open_editor(origin, management)
                check('T35c-0 不带参 open_editor → brief_options 为 null',
                      code == 200 and opened.get('brief_options') is None, '%s %r' % (code, opened))
                ctx = browser.new_context(viewport={'width': 1280, 'height': 900})
                page = ctx.new_page()
                page.on('pageerror', lambda e: print('[pageerror]', e))
                page.goto(opened['url'])
                page.wait_for_function(
                    "() => window.bridge && bridge.bound && "
                    "document.getElementById('briefOverlay').classList.contains('show')",
                    timeout=10000)
                page.wait_for_timeout(300)
                body_text = page.inner_text('#briefBody')
                n_def = page.evaluate("document.querySelectorAll('#briefOverlay .def-tag').length")
                check('T35c-1 静态问卷渲染（关键 DOM 与现版一致）',
                      '现场演讲' in body_text and '技术同行' in body_text
                      and page.evaluate("document.querySelector('#briefBody .brief-profile') === null")
                      and n_def >= 6, body_text[:120])
                ctx.close()

        # ---------- T35e 嵌入态 + T35f 静态参照（静态 http.server 服务仓库根） ----------
        srv = subprocess.Popen([sys.executable, '-m', 'http.server', str(PORT),
                                '--bind', '127.0.0.1', '-d', str(ROOT)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(50):
                try:
                    urllib.request.urlopen(BASE + '/editor.html', timeout=1)
                    break
                except Exception:
                    time.sleep(0.2)

            ctx = browser.new_context(viewport={'width': 1280, 'height': 900})
            page = ctx.new_page()
            page.on('pageerror', lambda e: print('[pageerror]', e))
            page.goto(BASE + '/tests/harness/harness.html')
            page.wait_for_function("""() => {
              const w = document.getElementById('ed').contentWindow;
              return w && w.state !== undefined && w.document.getElementById('btnBrief'); }""",
                                   timeout=8000)

            def ed_eval(expr):
                return page.evaluate(
                    "(() => { const w = document.getElementById('ed').contentWindow; return (%s); })()" % expr)

            def ed_click(selector):
                page.evaluate("""(sel) => {
                  const w = document.getElementById('ed').contentWindow;
                  w.document.querySelector(sel).click(); }""", selector)

            def post_options(options):
                page.evaluate("""(opts) => {
                  document.getElementById('ed').contentWindow.postMessage(
                    { type: 'pptx-html:brief-options', options: opts }, '*'); }""", options)

            # 未注入 → 静态问卷
            ed_click('#btnBrief')
            page.wait_for_timeout(300)
            check('T35e-0 未注入时嵌入态渲染静态问卷',
                  '现场演讲' in ed_eval("w.document.getElementById('briefBody').innerText"))
            ed_click('#btnBriefClose')
            page.wait_for_timeout(200)

            # 合法注入 → 动态渲染
            post_options(options_v1())
            page.wait_for_timeout(200)
            ed_click('#btnBrief')
            page.wait_for_timeout(300)
            dyn_text = ed_eval("w.document.getElementById('briefBody').innerText")
            check('T35e-1 入站 pptx-html:brief-options → 动态渲染',
                  '动态场景·登台述职' in dyn_text and '现场演讲' not in dyn_text
                  and bool(ed_eval("!!w.document.querySelector('#briefBody .brief-profile')")))
            ed_click('#btnBriefClose')
            page.wait_for_timeout(200)

            # 非法注入 → 忽略并回落静态
            post_options({'kind': 'brief', 'version': 1, 'groups': 'nope'})
            page.wait_for_timeout(200)
            ed_click('#btnBrief')
            page.wait_for_timeout(300)
            back = ed_eval("w.document.getElementById('briefBody').innerText")
            check('T35e-2 非法注入忽略并回落静态问卷',
                  '现场演讲' in back
                  and not bool(ed_eval("!!w.document.querySelector('#briefBody .brief-profile')")))
            ed_click('#btnBriefClose')
            page.wait_for_timeout(200)
            ctx.close()

            # T35f 静态参照：裸静态态提交一份未作答简报，与动态 JSON 逐键比对形状
            ctx = browser.new_context(viewport={'width': 1280, 'height': 900})
            page = ctx.new_page()
            page.on('pageerror', lambda e: print('[pageerror]', e))
            page.goto(BASE + '/editor.html')
            page.wait_for_function('() => window.state !== undefined', timeout=8000)
            page.click('#btnBrief')
            page.wait_for_timeout(300)
            page.click('#btnBriefGen')
            static_json = page.evaluate('window.briefLast.json')
            static_keys = set((static_json.get('answers') or {}).keys())
            expect_keys = {'topic', 'scene', 'audience', 'source', 'pages', 'theme', 'font',
                           'motion', 'brightness', 'cover', 'illustration', 'density_derived'}
            check('T35f-6 静态提交键结构（回归基线）', static_keys == expect_keys,
                  repr(sorted(static_keys)))
            # 与 T35f-0 动态结果同形状：动态 = 静态键 ∪ {extras}（T35f-0 已断言）
            ctx.close()
        finally:
            srv.terminate()

        browser.close()

    print('RESULT:', 'ALL PASS' if not FAILURES else '%d FAILURES: %s' % (len(FAILURES), FAILURES))
    return 0 if not FAILURES else 1


if __name__ == '__main__':
    sys.exit(main())
