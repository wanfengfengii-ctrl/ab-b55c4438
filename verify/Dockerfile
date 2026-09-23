# verify：一次性验收服务。
#   阶段 1：前端依赖安装 + 单元测试 + 生产构建（失败则镜像构建失败）
#   阶段 2：后端单元测试（pytest）+ 对运行中的 backend 做 API 冒烟
# 容器跑完自行退出，退出码 0 = 全部通过，非 0 = 失败。

FROM node:20-alpine AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm test && npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install -r requirements.txt -r requirements-dev.txt

COPY backend/ ./
# 前端构建产物作为"构建成功"的凭据随镜像携带
COPY --from=frontend /fe/dist ./frontend_dist
COPY verify/smoke.py /verify/smoke.py
COPY verify/run.sh /verify/run.sh

ENV BACKEND_URL=http://backend:8000

CMD ["sh", "/verify/run.sh"]
