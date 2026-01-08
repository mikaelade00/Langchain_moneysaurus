import json
from typing import List
from langchain_core.tools import tool
from psycopg2.extras import RealDictCursor
from app.db.database import get_db_connection

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
            category = item.get("category", "Lain-lain")
            if category:
                category = category.strip().title()
            
            # Use provided date or CURRENT_TIMESTAMP
            date_val = item.get("date") # Expected format: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
            
            if date_val:
                cursor.execute(
                    "INSERT INTO pengeluaran (id, description, category, expenses, created_at) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET description = EXCLUDED.description, category = EXCLUDED.category, expenses = EXCLUDED.expenses, created_at = EXCLUDED.created_at",
                    (item.get("id"), item.get("description"), category, item.get("expenses"), date_val)
                )
            else:
                cursor.execute(
                    "INSERT INTO pengeluaran (id, description, category, expenses) VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO UPDATE SET description = EXCLUDED.description, category = EXCLUDED.category, expenses = EXCLUDED.expenses",
                    (item.get("id"), item.get("description"), category, item.get("expenses"))
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
    cursor.execute("SELECT INITCAP(category) as cat, SUM(expenses) as total FROM pengeluaran GROUP BY cat ORDER BY total DESC")
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

@tool
def get_categories():
    """ Mengambil daftar unik semua kategori yang sudah ada di database. """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT category FROM pengeluaran")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return [row[0] for row in rows] if rows else []

@tool
def get_expense_by_period(period: str):
    """ 
    Mengambil rincian pengeluaran berdasarkan periode.
    Input period bisa berupa: 'hari ini', 'minggu ini', 'bulan ini', atau tahun (misal: '2024').
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT description, category, expenses, created_at::date FROM pengeluaran WHERE "
    if period == "hari ini":
        query += "created_at::date = CURRENT_DATE"
    elif period == "minggu ini":
        query += "created_at >= CURRENT_DATE - INTERVAL '7 days'"
    elif period == "bulan ini":
        query += "EXTRACT(MONTH FROM created_at) = EXTRACT(MONTH FROM CURRENT_DATE) AND EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM CURRENT_DATE)"
    else:
        # Asumsikan input tahun atau format spesifik lainnya bisa dikembangkan
        query += "TRUE"
        
    query += " ORDER BY created_at DESC"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not rows:
        return f"Tidak ada data pengeluaran untuk periode {period}."
    
    res = [f"Rincian pengeluaran {period}:"]
    for row in rows:
        res.append(f"- [{row[3]}] {row[0]} ({row[1]}): Rp {row[2]:,.0f}")
    return "\n".join(res)

tools = [
    save_expense, 
    get_total_expense, 
    get_expense_by_category, 
    get_recent_expenses, 
    get_categories, 
    get_expense_by_period
]
