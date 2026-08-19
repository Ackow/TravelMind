from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from psycopg import Connection

from app.core.config import get_settings


def create_agent_checkpointer() -> BaseCheckpointSaver:
    """根据环境配置构建持久化 Checkpointer。

    当配置了 PostgreSQL 时，接入企业级集中式 PostgresSaver；
    本地/测试环境回退为独立 SQLite Saver。
    """
    settings = get_settings()

    if "postgresql" in settings.DATABASE_URL or "postgres" in settings.DATABASE_URL:
        conn_str = settings.DATABASE_URL.replace("+psycopg", "")
        conn = Connection.connect(conn_str, autocommit=True)
        saver = PostgresSaver(conn)
        saver.setup()
        return saver

    import sqlite3

    conn = sqlite3.connect(settings.AGENT_CHECKPOINT_DB_PATH, check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return saver
