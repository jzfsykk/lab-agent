import json
import traceback

from openai import OpenAI
from sqlalchemy.orm import Session

from app.common.exceptions import BusinessException
from app.config import settings
from app.schemas.ai import ChatMessage, ChatRequest
from app.services import equipment_service, kb_service, lab_service

SYSTEM_PROMPT = """你是智能实验室预约系统的助手，回答要简洁。
如果下面提供了实验室资料，请依据资料回答规则、安全、文档里的开放时间说明。
查询当前有哪些开放实验室、某实验室有哪些设备时，必须调用工具，不要编造。
你不能替用户提交预约，也不能直接改数据库。
如果用户要预约，请说明去「实验室列表」选择后提交，等待管理员审核。
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_open_labs",
            "description": "查询当前开放中的实验室列表，可以按名称关键字来筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "keywords": {
                        "type": "string",
                        "description": "实验室的名称关键字，可以为空",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_lab_equipments",
            "description": "查询某个实验室下的设备列表",
            "parameters": {
                "type": "object",
                "properties": {
                    "lab_id": {
                        "type": "integer",
                        "description": "实验室 ID",
                    },
                    "keywords": {
                        "type": "string",
                        "description": "设备名称的关键字，可以为空",
                    },
                },
            }
        },
    },
]

MAX_TOOL_ROUNDS = 3


def get_client() -> OpenAI:
    """创建 OpenAI 兼容客户端（本课对接 Agnes）"""
    if not settings.LLM_API_KEY:
        raise BusinessException(message="未获取到大模型的API Key")
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)


def build_history(data: ChatRequest) -> list[dict]:
    """过滤掉空内容和非法 role，得到可以发给模型的历史消息"""
    history = []
    for message in data.messages:
        if message.role in ("user", "assistant") and message.content.strip():
            history.append(message.model_dump())
    return history


def build_system_prompt(question: str) -> str:
    """把检索到的资料拼进 system 提示词"""
    knowledge = kb_service.search(question)
    if knowledge:
        return SYSTEM_PROMPT + "\n\n以下是检索到的实验室的资料：\n" + knowledge
    return SYSTEM_PROMPT


def run_tool(db: Session, name: str, arguments: str) -> str:
    """执行模型请求的工具，结果以 JSON 字符串返回（异常也返回 JSON，不打断对话）"""
    try:
        args = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return json.dumps({"error": "参数不是合法的json"}, ensure_ascii=False)

    try:
        if name == "list_open_labs":
            keywords = (args.get("keywords") or "").strip() or None
            page = lab_service.get_lab_page_list(
                db, page=1, page_size=10, keywords=keywords, status=1
            )
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "location": item.location,
                    "capacity": item.capacity,
                    "open_time": item.open_time,
                    "close_time": item.close_time,
                }
                for item in page.list
            ]
            return json.dumps({"total": page.total, "labs": rows}, ensure_ascii=False)

        if name == "list_lab_equipments":
            lab_id = args.get("lab_id")
            if not lab_id:
                return json.dumps({"error": "参数缺少实验室 lab_id"}, ensure_ascii=False)
            keywords = (args.get("keywords") or "").strip() or None
            page = equipment_service.get_equipment_page_list(
                db, page=1, page_size=10, lab_id=int(lab_id), keywords=keywords
            )
            rows = [
                {
                    "id": item.id,
                    "name": item.name,
                    "lab_id": item.lab_id,
                    "lab_name": item.lab_name,
                    "spec": item.spec,
                    "quantity": item.quantity,
                    "status": item.status,
                }
                for item in page.list
            ]
            return json.dumps({"total": page.total, "equipments": rows}, ensure_ascii=False)

        return json.dumps({"error": f"未找到工具：{name}"}, ensure_ascii=False)
    except BusinessException as exc:
        return json.dumps({"error": exc.message}, ensure_ascii=False)
    except Exception as exc:  # 工具内部异常不影响整轮对话
        return json.dumps({"error": str(exc)}, ensure_ascii=False)


def chat(db: Session, data: ChatRequest) -> str:
    """大模型对话：RAG 资料 + Tool Calling 查库"""
    if not data.messages:
        raise BusinessException(message="对话内容为空")

    history = build_history(data)
    if not history:
        raise BusinessException(message="请输入您要对话的内容")

    # 用最后一句用户提问去检索资料
    question = next(
        (item["content"] for item in reversed(history) if item["role"] == "user"), ""
    )

    client = get_client()  # 先确认有 Key，再加载向量模型
    system_prompt = build_system_prompt(question)
    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        *history,
    ]

    try:
        for _ in range(MAX_TOOL_ROUNDS):
            res = client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
            )
            msg = res.choices[0].message
            tool_calls = msg.tool_calls or []
            if not tool_calls:  # 没有工具调用，直接返回模型输出
                content = msg.content
                if not content or not content.strip():
                    raise BusinessException(message="大模型没有返回内容")
                return content

            # 把模型的工具调用请求写回上下文
            messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.function.name,
                                "arguments": call.function.arguments,
                            },
                        }
                        for call in tool_calls
                    ],
                }
            )
            # 逐个执行工具，把结果以 role=tool 塞回去
            for call in tool_calls:
                result = run_tool(db, call.function.name, call.function.arguments)
                messages.append(
                    {"role": "tool", "content": result, "tool_call_id": call.id}
                )
    except BusinessException:
        raise
    except Exception as exc:
        traceback.print_exc()
        raise BusinessException(message=f"大模型调用失败，请稍后重试：{exc}")

    # 工具轮数用尽仍未给出文本
    raise BusinessException(message="工具调用次数过多，请把问题问得更具体一些")