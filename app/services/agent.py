import base64
from typing import List, Annotated, TypedDict, Union
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage, RemoveMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from app.config import LLM_MODEL
from app.services.tools import tools
from app.utils.parser import parse_agent_output

# --- In-memory storage for chat history ---
chat_memory = {}

def get_memory(chat_id):
    return chat_memory.get(chat_id, [])

def save_memory(chat_id, messages):
    chat_memory[chat_id] = messages

# --- Custom ToolNode ---
class BasicToolNode:
    def __init__(self, tools: list):
        self.tools_by_name = {tool.name: tool for tool in tools}

    def __call__(self, state: dict):
        messages = state.get("messages", [])
        last_message = messages[-1]
        outputs = []
        for tool_call in last_message.tool_calls:
            tool = self.tools_by_name[tool_call["name"]]
            tool_output = tool.invoke(tool_call["args"])
            outputs.append(ToolMessage(
                content=str(tool_output),
                tool_call_id=tool_call["id"],
                name=tool_call["name"]
            ))
        return {"messages": outputs}

# --- State & Logic ---
class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

def limit_memory(state: State):
    """
    Membatasi jumlah pesan dalam history.
    """
    messages = state["messages"]
    if len(messages) > 10:
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:-10]]}
    return {"messages": []}

def call_model(state: State):
    system_prompt = """You are a financial recorder AI agent.
Your task is to process user input about expenses and prepare it to be stored in the database.

### Instructions:
1. Sebelum membuat data baru, gunakan **get_recent_expenses** untuk mendapatkan `id` terakhir.
   - Jika belum ada data (last_id=0), mulai dari id = 1.
   - Jika ada data, id baru = last_id + 1.
2. Gunakan **get_categories** untuk melihat kategori yang sudah pernah digunakan. 
   **PENTING:** Jika input user memiliki arti yang mirip dengan kategori yang sudah ada (misal: 'perlengkapan rumah' mirip dengan 'Peralatan Rumah Tangga'), gunakan kategori yang SUDAH ADA agar konsisten.
3. Parse input user menjadi structured items. Gunakan format **Title Case** untuk kategori.
4. Gunakan **save_expense** untuk menyimpan data.
5. Gunakan tools lain jika user bertanya tentang total, kategori, atau pengeluaran pada waktu tertentu.
6. Jawab dalam Bahasa Indonesia yang natural.
"""
    model = ChatGoogleGenerativeAI(model=LLM_MODEL).bind_tools(tools)
    messages = [SystemMessage(content=system_prompt)] + state["messages"]
    response = model.invoke(messages)
    return {"messages": [response]}

def should_continue(state: State):
    last_message = state["messages"][-1]
    return "tools" if last_message.tool_calls else END

workflow = StateGraph(State)
workflow.add_node("agent", call_model)
workflow.add_node("tools", BasicToolNode(tools))
workflow.add_node("limit", limit_memory)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "limit")
workflow.add_edge("limit", "agent")

graph_app = workflow.compile()

async def get_agent_response(
    text_or_image: Union[str, bytes],
    chat_id: int,
    is_image: bool = False
):
    if is_image:
        image_data = base64.b64encode(text_or_image).decode("utf-8")
        message = HumanMessage(
            content=[
                {"type": "text", "text": "Extract data pengeluaran dari gambar ini."},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}"
                    }
                }
            ]
        )
    else:
        message = HumanMessage(content=str(text_or_image))
    
    memory = get_memory(chat_id)
    inputs = {"messages": memory + [message]}

    final_text = ""
    last_state = inputs

    async for output in graph_app.astream(inputs):
        for node_name, node_output in output.items():
            if "messages" in node_output:
                last_state["messages"] = add_messages(last_state["messages"], node_output["messages"])
            
            if node_name == "agent":
                msg = node_output["messages"][-1]
                if msg.content and not msg.tool_calls:
                    final_text = parse_agent_output(msg.content)

    save_memory(chat_id, last_state["messages"])
    return final_text
