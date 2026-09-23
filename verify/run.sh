#!/bin/sh
# verify 入口：依次执行后端测试、前端产物检查、API 冒烟；任一步失败即非零退出。
set -e

echo "== [1/3] 后端单元测试 (pytest) =="
cd /app
pytest -q

echo "== [2/3] 前端构建产物检查 =="
test -f /app/frontend_dist/index.html
echo "frontend_dist/index.html 存在（前端测试与构建已在镜像构建阶段完成）"

echo "== [3/3] API 冒烟 =="
python /verify/smoke.py

echo "VERIFY OK"
