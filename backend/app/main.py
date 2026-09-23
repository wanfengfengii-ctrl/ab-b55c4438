"""FastAPI 入口：健康检查 + 回放求解。"""
from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .solver import solve_replay
from .validation import to_event_specs, validate_payload

app = FastAPI(title="产线回放工作台", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/solve")
async def solve(request: Request) -> JSONResponse:
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=422,
            content={"detail": [{"loc": "body", "msg": "请求体须为合法 JSON"}]},
        )

    errors = validate_payload(data)
    if errors:
        return JSONResponse(status_code=422, content={"detail": errors})

    specs = to_event_specs(data["events"])
    precedences = [(p["before"], p["after"]) for p in data.get("precedences", [])]
    # 求解为 CPU 密集操作，放到线程池以免阻塞事件循环
    result = await run_in_threadpool(solve_replay, specs, precedences)
    return JSONResponse(content=result)
