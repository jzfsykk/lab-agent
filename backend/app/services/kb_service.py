"""实验室知识库（RAG）：ChromaDB + 本地中文向量模型"""

import os

# 国内直连 HuggingFace 常常失败，默认走镜像（可用环境变量 HF_ENDPOINT 覆盖）
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

from app.config import BASE_DIR

KB_DIR = BASE_DIR / "data" / "kb"
CHROMA_DIR = BASE_DIR / "data" / "chroma"
# 本地向量模型目录（可用 ModelScope / hf-mirror 提前下好，避免首次请求时再下载）
LOCAL_MODEL_DIR = BASE_DIR / "data" / "models" / "bge-small-zh-v1.5"
MODEL_NAME = str(LOCAL_MODEL_DIR) if LOCAL_MODEL_DIR.exists() else "BAAI/bge-small-zh-v1.5"

_collection: Collection | None = None
_embedding_fn = None


def get_embedding_fn():
    """懒加载向量模型：只加载一次，之后复用同一个实例"""
    global _embedding_fn
    if _embedding_fn is None:
        _embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=MODEL_NAME
        )
    return _embedding_fn


def get_collection() -> Collection:
    """向量库初始化：集合为空时，把 data/kb 下的 md 全部导入"""
    global _collection
    if _collection is not None:
        return _collection

    KB_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    col = client.get_or_create_collection(
        name="lab_kb", embedding_function=get_embedding_fn()
    )

    if col.count() == 0:
        ids: list[str] = []
        docs: list[str] = []
        metas: list[dict] = []
        for path in sorted(KB_DIR.glob("*.md")):
            text = path.read_text(encoding="UTF-8").strip()
            if not text:
                continue
            docs.append(text)
            ids.append(path.stem)
            metas.append({"source": path.name})
        if docs:
            col.add(ids=ids, documents=docs, metadatas=metas)

    _collection = col
    return col


def search(query: str) -> str:
    """按问题检索最相关的两段资料，拼成给模型的上下文"""
    if not query.strip():
        return ""

    col = get_collection()
    if col.count() == 0:
        return ""

    limit = min(5, col.count())
    res = col.query(query_texts=[query], n_results=limit)
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]

    score_parts = []
    for doc, meta, dist in zip(docs, metas, distances):
        score = 1 / (1 + dist)  # 0-1，越接近 1 越相关
        if score < 0.5:
            continue
        name = (meta or {}).get("source") or ""
        score_parts.append({"score": score, "content": f"[{name}]\n{doc}"})

    score_parts.sort(key=lambda item: item["score"], reverse=True)
    final_parts = [item["content"] for item in score_parts[:2]]
    return "\n\n".join(final_parts)


def warmup() -> None:
    """预热：提前把模型和集合加载好（后台任务里调用）"""
    get_collection()


def rebuild() -> None:
    """重建集合：删掉旧集合后重新导入 data/kb 下的资料"""
    global _collection
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        client.delete_collection("lab_kb")
    except Exception:
        pass
    _collection = None
    get_collection()