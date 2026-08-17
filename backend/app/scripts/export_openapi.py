import json
from pathlib import Path

from app.main import create_app


def main() -> None:
    """导出 OpenAPI 文档到 backend/openapi.json。"""
    output = Path(__file__).resolve().parents[2] / "openapi.json"
    output.write_text(
        json.dumps(create_app().openapi(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"wrote {output}")


if __name__ == "__main__":
    main()
