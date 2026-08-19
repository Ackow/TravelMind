-- TravelMind PostgreSQL 数据库初始化脚本
-- 创建主开发/生产库与自动化测试库，实现物理分库隔离

SELECT 'CREATE DATABASE travelmind_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'travelmind_db')\gexec

SELECT 'CREATE DATABASE travelmind_test_db'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'travelmind_test_db')\gexec

GRANT ALL PRIVILEGES ON DATABASE travelmind_db TO travelmind;
GRANT ALL PRIVILEGES ON DATABASE travelmind_test_db TO travelmind;
