#!/usr/bin/env bash
# 一键启动编辑器 WebUI：伴随服务（git 版本 + 转换能力）+ 自动开浏览器 +
# 启动即后台跑导出管线（工作目录有 index.html 时）。
#
# 用法：
#   tools/start-webui.sh [deck目录] [--deck REL|--new [REL]] [--no-browser]
#   tools/start-webui.sh tests/decks/cmb-retail-v2 --deck index.html
#
# 等价命令：python3 tools/edit.py <deck目录> --convert [其余参数]
cd "$(dirname "$0")/.." || exit 1
if [[ $# -eq 0 ]]; then
  set -- .
fi
exec python3 tools/edit.py "$@" --convert
