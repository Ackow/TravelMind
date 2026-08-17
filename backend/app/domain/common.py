from datetime import date, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DomainModel(BaseModel):
    """所有领域对象的共同配置。"""

    model_config = ConfigDict(
        extra="forbid",  # 禁止传入未定义字段；遇到多余字段直接抛异常
        str_strip_whitespace=True,  # 字符串自动去除首尾空格
        validate_assignment=True,  # 对象实例化之后，修改属性也会触发校验
    )


class Money(DomainModel):
    """金额领域模型
    业务约定：amount 使用最小货币单位整数，例如人民币以「分」为单位，
    100 代表 1 元；避免浮点数精度丢失。
    """

    amount: int = Field(ge=0, description="最小货币单位整数")
    currency: str = Field(pattern=r"^[A-Z]{3}$")  # 必须大写3位货币代码，例 CNY / USD / JPY


class GeoPoint(DomainModel):
    """地理坐标点
    代表经纬度，用于景点、城市定位
    """

    latitude: float = Field(ge=-90, le=90)  # 纬度
    longitude: float = Field(ge=-180, le=180)  # 经度


class DateRange(DomainModel):
    """日期区间
    用于旅行的行程起止时间
    """

    start_date: date  # 开始日期（仅年月日）
    end_date: date  # 结束日期（仅年月日）

    @model_validator(mode="after")
    # 校验日期区间：结束日期不能早于开始日期
    def validate_range(self) -> "DateRange":
        if self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        return self

    # 计算旅行天数（含首尾）
    @property
    def day_count(self) -> int:
        return (self.end_date - self.start_date).days + 1


class DataQuality(StrEnum):
    """数据质量枚举，标记外部来源数据可信度"""

    VERIFIED = "verified"  # 已核实，权威真实数据
    ESTIMATED = "estimated"  # 估算值，非精确
    INCOMPLETE = "incomplete"  # 不完整的
    STALE = "stale"  # 过时老旧数据
    MOCK = "mock"  # 模拟


class SourceRef(DomainModel):
    """外部数据源引用记录
    记录这条业务数据来自哪个第三方API，抓取时间、过期时间、数据质量。
    """

    provider: str = Field(min_length=1, max_length=50)  # 数据源服务商名称
    source_id: str | None = None  # 服务商侧的资源ID
    source_url: str | None = None  # 原始数据网页/API地址
    fetched_at: datetime  # 抓取时间戳
    expires_at: datetime | None = None  # 数据过期失效时间；长期有效或未知时为空
    data_quality: DataQuality  # 数据质量等级

    @model_validator(mode="after")
    # 校验时间戳必须带时区，且过期时间晚于抓取时间
    def validate_timestamps(self) -> "SourceRef":
        if self.fetched_at.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware")
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None:
                raise ValueError("expires_at must be timezone-aware")
            if self.expires_at <= self.fetched_at:
                raise ValueError("expires_at must be after fetched_at")
        return self
