from dataclasses import dataclass, field


@dataclass(slots=True)
class ApplicationError(Exception):
    code: str  # 业务错误码，例如 TRIP_NOT_FOUND
    message: str  # 人类可读的错误提示
    status_code: int  # 对应的 HTTP 状态码
    details: list[dict[str, object]] = field(default_factory=list)  # 附加的详细错误信息
    retryable: bool = False  # 是否允许客户端稍后重试
