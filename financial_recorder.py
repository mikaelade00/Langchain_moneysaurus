import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import base64
from typing import List, Annotated, TypedDict, Union
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, SystemMessage, RemoveMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState, add_messages
import operator
from dotenv import load_dotenv

llm = "gemini-2.5-flash"

# --- In-memory storage for chat history ---
chat_memory = {}

def get_memory(chat_id):
    return chat_memory.get(chat_id, [])

def save_memory(chat_id, messages):
    chat_memory[chat_id] = messages


load_dotenv()
# --- Database Setup (Postgres) ---
def get_db_connection(dbname=None):
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=dbname or os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=os.getenv("POSTGRES_PORT")
    )

def init_db():
    target_db = os.getenv("POSTGRES_DB")
    
    # Connect to default 'postgres' db to check/create target db
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{target_db}'")
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {target_db}")
            print(f"Database {target_db} created.")
    finally:
        cursor.close()
        conn.close()

    # Now connect to target db to create table
    conn = get_db_connection(target_db)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pengeluaran (
            id INTEGER PRIMARY KEY,
            description TEXT,
            category TEXT,
            expenses NUMERIC
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

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

# --- Tools ---

@tool
def save_expense(items: List[dict]):
    """
    Menyimpan data pengeluaran baru ke database.
    Input items harus berupa list of dictionaries dengan key: id, description, category, expenses.
    """
    if isinstance(items, str):
        items = json.loads(items)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        for item in items:
            cursor.execute(
                "INSERT INTO pengeluaran (id, description, category, expenses) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET description = EXCLUDED.description, category = EXCLUDED.category, expenses = EXCLUDED.expenses",
                (item.get("id"), item.get("description"), item.get("category"), item.get("expenses"))
            )
        conn.commit()
        return "Berhasil menyimpan pengeluaran."
    except Exception as e:
        return f"Gagal menyimpan: {str(e)}"
    finally:
        cursor.close()
        conn.close()

@tool
def get_total_expense():
    """ Mengambil total semua pengeluaran dari database. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(SUM(expenses), 0) AS total FROM pengeluaran")
    total = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    return f"Total pengeluaran saat ini: {total}"

@tool
def get_expense_by_category():
    """ Mengambil ringkasan pengeluaran per kategori. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT category, SUM(expenses) as total FROM pengeluaran GROUP BY category ORDER BY total DESC")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    if not rows:
        return "Belum ada data pengeluaran."
    return "\n".join([f"- {row[0]}: {row[1]}" for row in rows])

@tool
def get_recent_expenses():
    """ Mengambil data pengeluaran terakhir untuk menentukan ID berikutnya. """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, description, category, expenses FROM pengeluaran ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if not row:
        return json.dumps({"status": "empty", "last_id": 0})
    return json.dumps({"status": "exists", "id": row["id"], "description": row["description"], "category": row["category"], "expenses": float(row["expenses"])})

tools = [save_expense, get_total_expense, get_expense_by_category, get_recent_expenses]

# --- State & Logic ---

class State(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

def limit_memory(state: State):
    """
    Membatasi jumlah pesan dalam history.
    Menggunakan RemoveMessage untuk menghapus pesan lama agar state tidak membengkak.
    """
    messages = state["messages"]
    if len(messages) > 10:
        # Hapus pesan-pesan tertua kecuali yang terakhir (sisakan 10)
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:-10]]}
    return {"messages": []}


def call_model(state: State):
    system_prompt = """You are a financial recorder AI agent.
Your task is to process user input about expenses and prepare it to be stored in the database.

### Instructions:
1. Sebelum membuat data baru, gunakan **get_recent_expenses** untuk mendapatkan `id` terakhir.
   - Jika belum ada data (last_id=0), mulai dari id = 1.
   - Jika ada data, id baru = last_id + 1.
2. Parse input user menjadi structured items.
3. Gunakan **save_expense** untuk menyimpan data.
4. Gunakan tools lain jika user bertanya tentang total atau kategori.
5. Jawab dalam Bahasa Indonesia yang natural.
"""
    model = ChatGoogleGenerativeAI(model=llm).bind_tools(tools)
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

app = workflow.compile()

def parse_agent_output(content) -> str:
    """
    Normalize LangChain agent output into plain text for Telegram.
    Mengabaikan blok 'thought' dan memastikan newline (\n) dirender dengan benar.
    """
    if not content:
        return ""
        
    res = ""
    if isinstance(content, str):
        res = content
    elif isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                # Jangan ambil 'thought' karena itu internal
                val = item.get("text") or item.get("content")
                if val and isinstance(val, str):
                    texts.append(val)
        res = "\n".join(texts)
    else:
        res = str(content)

    # Memperbaiki masalah \n literal dan merapikan spasi
    if res:
        # Ganti literal \n (backslash + n) dengan karakter newline asli jika ada
        res = res.replace("\\n", "\n")
        # Hapus spasi di awal/akhir dan rapikan baris kosong berlebih
        res = res.strip()
        
    return res




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
    # Combine memory with the new message
    inputs = {"messages": memory + [message]}

    final_text = ""
    last_state = inputs

    async for output in app.astream(inputs):
        for node_name, node_output in output.items():
            if "messages" in node_output:
                # Accumulate messages for manual persistence
                last_state["messages"] = add_messages(last_state["messages"], node_output["messages"])
            
            if node_name == "agent":
                msg = node_output["messages"][-1]
                # Jika ada tool_calls, teksnya biasanya cuma "internal thinking/rencana"
                # Jadi kita hanya tampilkan teks jika TIDAK ada tool_calls (yaitu jawaban akhir)
                if msg.content and not msg.tool_calls:
                    final_text = parse_agent_output(msg.content)

    # Save the updated messages back to memory
    save_memory(chat_id, last_state["messages"])

    return final_text




if __name__ == "__main__":
    import asyncio
    init_db()
    print("Financial Recorder LangGraph (Postgres) Active.")
    async def cli():
        while True:
            raw = input("User: ")
            if raw.lower() == "exit": break
            if raw.endswith((".jpg", ".png", ".jpeg")) and os.path.exists(raw):
                with open(raw, "rb") as f:
                    print(f"Agent: {await get_agent_response(f.read(), chat_id=0, is_image=True)}")
            else:
                print(f"Agent: {await get_agent_response(raw, chat_id=0)}")
    asyncio.run(cli())
