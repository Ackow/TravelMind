from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.errors import ApplicationError


def error_body(
    *,
    request: Request,
    code: str,
    message: str,
    details: list[dict[str, object]],
    retryable: bool,
) -> dict[str, object]:
    # 统一错误响应结构，附带 request_id 方便排查
    request_id = getattr(request.state, "request_id", str(uuid4()))
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id,
            "retryable": retryable,
        }
    }


# 处理业务层主动抛出的 ApplicationError
async def application_error_handler(
    request: Request,
    exc: ApplicationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(
            request=request,
            code=exc.code,
            message=exc.message,
            details=exc.details,
            retryable=exc.retryable,
        ),
    )


# 把 Pydantic/FastAPI 参数校验错误转换为统一错误格式
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    details = [
        {
            "field": ".".join(str(part) for part in item["loc"]),
            "reason": item["type"],
            "message": item["msg"],
        }
        for item in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=error_body(
            request=request,
            code="VALIDATION_ERROR",
            message="请求参数不合法",
            details=details,
            retryable=False,
        ),
    )


# 注册全局异常处理器，让所有接口返回结构一致的错误 JSON
def install_error_handlers(application: FastAPI) -> None:
    application.add_exception_handler(
        ApplicationError,
        application_error_handler,
    )
    application.add_exception_handler(
        RequestValidationError,
        validation_error_handler,
    )
