#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tools/edit.py —— 编辑器↔Agent Bridge v2 的统一 CLI/daemon 入口。

手动模式用 ``--deck REL`` 打开已有 HTML，或用 ``--new [REL]`` 创建无 deck
脑暴会话；``--mcp`` 启动官方 SDK stdio 薄代理，``--stop`` 停止当前工作目录
发现的 daemon。编辑器无法连接 Bridge 时仍独立降级到 FSAA、下载或宿主
postMessage，不依赖本服务。

状态、隔离 attempt、副本发布、revision CAS、receipt、快照和 Git 专用 ref
均由 ``bridge_core.py`` 实现。所有文件访问限制在规范工作目录内，并拒绝路径
穿越、符号链接和危险硬链接；Bridge 不修改用户 HEAD 或真实暂存区。

``--convert`` 仅允许 Bridge 在 attempt 副本中触发
``skills/html-pptx/scripts/export-pptx.py --force --track both``。转换实现、门禁
和交付规则仍全部属于技能，本入口不包含转换逻辑。完整协议与使用方式见
``docs/design/editor-agent-bridge-protocol.md`` 和
``docs/howto/editor-agent-bridge.md``。

``--imagegen``（imagegen v2 G6）允许本地插画补齐通道：只落
``illustrate.requested``（slots=全部页内 placeholder 槽位），执行体仍是技能
脚本（imagegen-adapter.py + 四闸 + 色彩告警），禁止烙入。provider 由环境变量
``PPTX_HTML_IMAGEGEN_PROVIDER`` 或 ``.pptx-html/config.json`` 的
``imagegen_provider`` 键（脚本绝对路径）供给，二者皆缺则启用失败。
"""
import argparse
import json
import os
import sys
import webbrowser


def resolve_imagegen_provider(workdir):
    """--imagegen 的 provider 供给：环境变量优先，其次 .pptx-html/config.json 的
    imagegen_provider 键。返回校验过的绝对路径；未配置返回 None；配置存在但非法
    直接退出 2。路径只存内存与配置，不写 ledger/deck/文档。"""
    candidate = os.environ.get('PPTX_HTML_IMAGEGEN_PROVIDER') or None
    source = '环境变量 PPTX_HTML_IMAGEGEN_PROVIDER'
    if not candidate:
        cfg = os.path.join(workdir, '.pptx-html', 'config.json')
        if os.path.isfile(cfg):
            try:
                with open(cfg, encoding='utf-8') as f:
                    data = json.load(f)
            except (OSError, ValueError) as exc:
                print('imagegen provider 配置读取失败：%s' % exc, file=sys.stderr)
                raise SystemExit(2)
            if isinstance(data, dict) and data.get('imagegen_provider'):
                candidate = data['imagegen_provider']
                source = '.pptx-html/config.json 的 imagegen_provider'
    if not candidate:
        return None
    if not isinstance(candidate, str) or not os.path.isabs(candidate) \
            or os.path.islink(candidate) or not os.path.isfile(candidate):
        print('--imagegen provider 配置无效（来源：%s）：需要已存在的 provider 脚本绝对路径（非符号链接）' % source,
              file=sys.stderr)
        raise SystemExit(2)
    return candidate


def main():
    ap = argparse.ArgumentParser(description='editor.html 本地伴随服务 / Agent bridge v2')
    ap.add_argument('workdir', nargs='?', default='.', help='规范工作目录，默认当前目录')
    ap.add_argument('--port', type=int, default=8926)
    ap.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    ap.add_argument('--convert', action='store_true', help='允许本地完整双轨转换触发')
    ap.add_argument('--imagegen', action='store_true',
                    help='允许本地插画补齐通道（真实付费生图；需配置 provider；只补插画不烙入）')
    ap.add_argument('--mcp', action='store_true', help='运行官方 MCP SDK stdio 代理')
    ap.add_argument('--stop', action='store_true', help='停止该工作目录已发现的 daemon')
    ap.add_argument('--daemon', action='store_true', help=argparse.SUPPRESS)
    choose = ap.add_mutually_exclusive_group()
    choose.add_argument('--deck', metavar='REL', help='手动打开工作区内已有 HTML')
    choose.add_argument('--new', nargs='?', const='index.html', metavar='REL', help='手动创建 briefing 目标')
    args = ap.parse_args()

    workdir = os.path.realpath(args.workdir)
    if not os.path.isdir(workdir):
        print('工作目录不存在：%s' % workdir, file=sys.stderr)
        raise SystemExit(2)
    if args.mcp and (args.deck is not None or args.new is not None or args.daemon or args.stop):
        ap.error('--mcp 不可与 --deck/--new/--daemon/--stop 同用')

    imagegen_provider = None
    if args.imagegen and not args.stop:
        imagegen_provider = resolve_imagegen_provider(workdir)
        if not imagegen_provider:
            print('--imagegen 启用失败：未配置生图 provider。请设置环境变量 '
                  'PPTX_HTML_IMAGEGEN_PROVIDER，或在 .pptx-html/config.json 写入 '
                  'imagegen_provider 键（值为 provider 脚本绝对路径）。', file=sys.stderr)
            raise SystemExit(2)
        print('⚠ --imagegen 已启用：本地插画通道将真实调用付费生图 provider（%s），'
              '按槽位逐张计费且 adapter 不自动重试；本地通道只补插画，不做烙入。'
              % os.path.basename(imagegen_provider), file=sys.stderr)

    if args.mcp:
        try:
            from bridge_mcp import run
        except ImportError:
            from tools.bridge_mcp import run
        return run(workdir, allow_convert=args.convert, allow_imagegen=args.imagegen)

    try:
        from bridge_core import (BridgeCore, BridgeError, BridgeHTTPServer,
                                 admin_request, read_discovery, verify_discovery,
                                 write_serve)
    except ImportError:
        from tools.bridge_core import (BridgeCore, BridgeError, BridgeHTTPServer,
                                       admin_request, read_discovery,
                                       verify_discovery, write_serve)

    if args.stop:
        try:
            discovery = read_discovery(workdir)
            result = admin_request(discovery, '/api/bridge/stop', {'reason': 'cli-stop'})
            print('daemon 已停止：%s' % result['instance_id'])
            return
        except Exception as exc:
            print('停止 daemon 失败：%s' % exc, file=sys.stderr)
            raise SystemExit(1)

    if args.daemon:
        try:
            core = BridgeCore(workdir, allow_convert=args.convert, require_lock=True,
                              allow_imagegen=args.imagegen, imagegen_provider=imagegen_provider)
            server = BridgeHTTPServer(('127.0.0.1', args.port), core)
            write_serve(core, server)
            server.serve_forever(poll_interval=.2)
        except BridgeError as exc:
            print('%s: %s' % (exc.code, exc.message), file=sys.stderr)
            raise SystemExit(1)
        finally:
            if 'server' in locals(): server.server_close()
            if 'core' in locals(): core.close()
        return

    mode = 'new' if args.new is not None else 'deck'
    rel = args.new if args.new is not None else args.deck
    if rel is None:
        rel = 'index.html'
        mode = 'deck' if os.path.isfile(os.path.join(workdir, rel)) else 'new'
    try:
        discovery = read_discovery(workdir)
        if not verify_discovery(workdir, discovery):
            raise BridgeError(503, 'STORAGE_UNAVAILABLE', '发现文件身份不匹配')
        boot = admin_request(discovery, '/api/bridge/bootstrap', {'mode': mode, 'path': rel})
        print('编辑器启动链接：%s' % boot['url'])
        if not args.no_browser:
            webbrowser.open(boot['url'])
        return
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    except BridgeError as exc:
        print('%s: %s' % (exc.code, exc.message), file=sys.stderr)
        raise SystemExit(1)

    try:
        core = BridgeCore(workdir, allow_convert=args.convert, require_lock=True,
                          allow_imagegen=args.imagegen, imagegen_provider=imagegen_provider)
        server = BridgeHTTPServer(('127.0.0.1', args.port), core)
        write_serve(core, server)
        boot = core.bootstrap_issue(mode, rel)
        print('工作目录：%s' % workdir)
        print('编辑器启动链接：%s' % boot['url'])
        print('Ctrl+C 停止')
        if not args.no_browser:
            webbrowser.open(boot['url'])
        server.serve_forever(poll_interval=.2)
    except BridgeError as exc:
        print('%s: %s' % (exc.code, exc.message), file=sys.stderr)
        raise SystemExit(1)
    except KeyboardInterrupt:
        pass
    finally:
        if 'server' in locals(): server.server_close()
        if 'core' in locals(): core.close()


if __name__ == '__main__':
    main()
