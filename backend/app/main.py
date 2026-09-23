"""FastAPI application: rebuild production-line replays from edited events."""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import ErrorItem, SolveRequest, SolveResponse, Witness
from .solver import solve
from .validation import validate_request

logger = logging.getLogger("replay")

app = FastAPI(title="停机回放工作台", version="1.0.0")

# The frontend is served from a separate origin in development and through
# an nginx container in production; allow the standard browser origins.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/solve", response_model=SolveResponse)
def api_solve(req: SolveRequest) -> SolveResponse:
    errors, by_id = validate_request(req)
    if errors:
        return SolveResponse(status="invalid_input", errors=errors)

    status, cost, witnesses, reason = solve(by_id, req.orderings)
    return SolveResponse(
        status=status,
        reason=reason,
        optimalCost=cost,
        witnesses=[Witness(timeline=t) for t in witnesses],
    )


@app.exception_handler(RuntimeError)
async def handle_runtime_error(request: Request, exc: RuntimeError):
    # Solver timeouts or other non-result states: report instead of 500.
    return JSONResponse(
        status_code=503,
        content={"status": "solver_error", "message": str(exc)},
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError):
    """Shape body-level (JSON/type) errors like semantic errors: located."""
    items = []
    for err in exc.errors():
        loc = [str(part) for part in err.get("loc", []) if part != "body"]
        items.append(
            ErrorItem(
                code=f"schema.{err.get('type', 'error')}",
                message=err.get("msg", "输入格式有误"),
                path=loc,
            ).model_dump(by_alias=True)
        )
    return JSONResponse(
        status_code=422,
        content=SolveResponse(status="invalid_input", errors=items).model_dump(by_alias=True),
    )
