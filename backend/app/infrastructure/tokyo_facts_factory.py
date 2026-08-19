# 向后兼容模块：重定向至 NanjingFactsFactory
from app.infrastructure.nanjing_facts_factory import (
    DefaultFactsFactory,
    NanjingFactsFactory,
    TokyoFactsFactory,
)

__all__ = ["TokyoFactsFactory", "NanjingFactsFactory", "DefaultFactsFactory"]
