# -*- coding: utf-8 -*-
"""离线测量实验室知识库的检索表现：Top-K 命中率、阈值过滤情况、上下文 token 估算。

用途：为检索质量提供可复现的量化基线，改动知识库内容或分块策略后直接对比。
运行：backend/.venv/Scripts/python.exe scripts/measure_retrieval.py
"""

import os
import sys
import time

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
BASE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
sys.path.insert(0, BASE)
os.chdir(BASE)

import chromadb
from chromadb.utils import embedding_functions

MODEL = os.path.abspath("data/models/bge-small-zh-v1.5")
THRESHOLD = 0.5          # kb_service.search 里的实际阈值
TOP_N = 2                # kb_service.search 里实际拼接的条数

# (问题, 期望命中的文档；None 表示知识库中确实没有答案，用于观察误召回)
CASES = [
    ("实验室几点开门", "开放时间.md"),
    ("平时最晚能待到什么时候", "开放时间.md"),
    ("周末开放吗", "开放时间.md"),
    ("中午休息时间能进实验室吗", "开放时间.md"),
    ("进实验室要穿实验服吗", "安全规范.md"),
    ("能不能带吃的进去", "安全规范.md"),
    ("着火了怎么处理", "安全规范.md"),
    ("设备坏了找谁报修", "设备使用.md"),
    ("仪器用完要归位吗", "设备使用.md"),
    ("设备可以借出去用吗", "设备使用.md"),
    ("一个人最多能预约几个小时", "预约规则.md"),
    ("预约了没去会怎么样", "预约规则.md"),
    ("可以帮室友预约吗", "预约规则.md"),
    ("最多能提前几天预约", "预约规则.md"),
    ("实验楼在几层楼", None),
    ("学校食堂几点关门", None),
]

ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=MODEL)
client = chromadb.PersistentClient(path="data/chroma")
col = client.get_or_create_collection(name="lab_kb", embedding_function=ef)

print(f"collection count = {col.count()}")
t0 = time.perf_counter()
col.query(query_texts=["预热"], n_results=1)
warm = time.perf_counter() - t0
print(f"首次查询(含模型加载) = {warm:.2f}s")

hit = 0
asked = 0
empty_after_filter = 0
lat = []
ctx_chars = []

print("\n%-26s %-12s %-6s %-6s %s" % ("question", "gold", "hit", "keep", "top3(score,source)"))
for q, gold in CASES:
    t = time.perf_counter()
    res = col.query(query_texts=[q], n_results=min(5, col.count()))
    lat.append((time.perf_counter() - t) * 1000)

    docs = res["documents"][0]
    metas = res["metadatas"][0]
    dists = res["distances"][0]
    scored = sorted(
        ((1.0 / (1.0 + d), (m or {}).get("source"), doc) for d, m, doc in zip(dists, metas, docs)),
        key=lambda x: x[0],
        reverse=True,
    )
    kept = [s for s in scored if s[0] >= THRESHOLD]
    if not kept:
        empty_after_filter += 1
    top2 = kept[:TOP_N]
    ok = any(s[1] == gold for s in top2) if gold else None
    if gold:
        asked += 1
        if ok:
            hit += 1
    if top2:
        ctx_chars.append(sum(len(s[2]) for s in top2))

    top3 = ", ".join(f"{s[0]:.3f}/{s[1]}" for s in scored[:3])
    print("%-26s %-12s %-6s %-6d %s" % (q, gold or "-", str(ok), len(kept), top3))

lat.sort()
print(f"\nTop-{TOP_N} 命中率: {hit}/{asked} = {hit / asked:.1%}")
print(f"阈值 {THRESHOLD} 过滤后为空的问题数: {empty_after_filter}/{len(CASES)}")
print(f"拼接上下文平均字符数: {sum(ctx_chars) / len(ctx_chars):.0f} (n={len(ctx_chars)})")
print(f"单次检索延迟 P50/P95: {lat[len(lat) // 2]:.1f}ms / {lat[int(len(lat) * 0.95) - 1]:.1f}ms")