# -*- coding: utf-8 -*-
"""端到端测量实验室 Agent：首事件延迟、工具调用链路、总耗时。

需要一个可用的 LLM_API_KEY（backend/.env）和运行中的 MySQL。
运行：backend/.venv/Scripts/python.exe scripts/measure_agent.py
"""

import asyncio
import os
import sys
import time

BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, BASE)
os.chdir(BASE)

from app.database import SessionLocal
from app.models.user import User
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import agent_service

CASES = [
    "实验室几点开门",                       # 纯知识库检索
    "现在有哪些实验室是空的",                 # 实时查询工具
    "我想预约明天下午三点的实验室，两个小时",      # 多工具串联
]

db = SessionLocal()
user = db.query(User).first()
print(f"user = {user.id}/{user.username} role={user.role}\n")


async def run(q: str) -> None:
    data = ChatRequest(messages=[ChatMessage(role="user", content=q)])
    t0 = time.perf_counter()
    first = None
    tools = []
    kinds = {}
    text = ""

    async for ev in agent_service.stream_agent(db, user, data):
        kind = ev.get("type")
        if first is None:
            first = time.perf_counter() - t0
        kinds[kind] = kinds.get(kind, 0) + 1
        if kind == "tool_start":
            tools.append(ev.get("name"))
        if kind == "token":
            text += ev.get("content") or ""
        if kind in ("done", "error"):
            break

    total = time.perf_counter() - t0
    print(f"Q: {q}")
    print(f"   首事件 {first:.2f}s | 总耗时 {total:.2f}s | 事件 {len(kinds)} 类 {sum(kinds.values())} 条")
    print(f"   工具链路: {' -> '.join(tools) if tools else '(无，纯问答)'}")
    print(f"   回答: {text[:120].replace(chr(10), ' ')}\n")


async def main() -> None:
    for q in CASES:
        try:
            await run(q)
        except Exception as exc:
            print(f"Q: {q}\n   FAILED: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    asyncio.run(main())