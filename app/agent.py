"""Custom LangGraph SQL agent running on a local Ollama model:
   load_schema -> generate_sql -> validate+execute -> (error: retry <= MAX_RETRIES) -> answer
"""
import time
from typing import TypedDict, Optional, List
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from .config import get_llm, MAX_RETRIES
from .db import get_schema, run_query
from .guardrails import validate_sql, extract_sql, UnsafeSQLError

class AgentState(TypedDict, total=False):
    question: str
    schema: str
    sql: str
    error: Optional[str]
    attempts: int
    sql_history: List[str]
    columns: list
    rows: list
    answer: str
    blocked: bool

# Explicit, short rules work better for small local models than long instructions.
GEN_PROMPT = ChatPromptTemplate.from_messages([
 ("system", "You are an expert SQLite analyst. Write ONE read-only SELECT query that answers the question.\n"
  "Rules:\n- Use only tables and columns from the schema.\n- Relative dates: datetime('now','-7 days'); 'last week' = last 7 days.\n"
  "- sla_breached is 1 (breached) or 0.\n- Add LIMIT 200 unless aggregating.\n"
  "- Output ONLY the SQL. No explanation, no markdown.\n\nSchema:\n{schema}"),
 ("human", "Question: {question}\n{feedback}")])

ANS_PROMPT = ChatPromptTemplate.from_messages([
 ("system", "Answer the question concisely using ONLY the SQL result. If there are no rows, say no matching data was found. "
  "Never invent values."),
 ("human", "Question: {question}\nSQL: {sql}\nColumns: {columns}\nRows: {rows}")])

llm = None
def _llm():
    global llm
    llm = llm or get_llm()
    return llm

def load_schema(s: AgentState):
    return {"schema": get_schema(), "attempts": 0, "sql_history": [], "blocked": False, "error": None}

def generate_sql(s: AgentState):
    fb = f"Previous SQL:\n{s['sql']}\nfailed with error: {s['error']}\nReturn a corrected query." if s.get("error") else ""
    raw = (GEN_PROMPT | _llm()).invoke({"schema": s["schema"], "question": s["question"], "feedback": fb}).content
    sql = extract_sql(raw)
    return {"sql": sql, "attempts": s["attempts"] + 1, "sql_history": s["sql_history"] + [sql]}

def validate_and_execute(s: AgentState):
    try:
        sql = validate_sql(s["sql"])
    except UnsafeSQLError as e:
        return {"error": str(e), "blocked": True}
    except ValueError as e:
        return {"error": str(e)}
    try:
        cols, rows = run_query(sql)
        return {"sql": sql, "columns": cols, "rows": rows, "error": None}
    except Exception as e:           # SQLite errors feed the self-correction loop
        return {"error": f"{type(e).__name__}: {e}"}

def route(s: AgentState):
    if s.get("blocked"):
        return "refuse"
    if s.get("error"):
        return "retry" if s["attempts"] <= MAX_RETRIES else "fail"
    return "answer"

def answer(s: AgentState):
    a = (ANS_PROMPT | _llm()).invoke({"question": s["question"], "sql": s["sql"],
                                     "columns": s["columns"], "rows": s["rows"][:50]}).content
    return {"answer": a}

def refuse(s: AgentState):
    return {"answer": f"Request refused by safety guardrail: {s['error']}"}

def fail(s: AgentState):
    return {"answer": f"Could not produce a valid query after {s['attempts']} attempts. Last error: {s['error']}"}

def build_graph():
    g = StateGraph(AgentState)
    for name, fn in [("load_schema", load_schema), ("generate_sql", generate_sql), ("execute", validate_and_execute),
                     ("answer", answer), ("refuse", refuse), ("fail", fail)]:
        g.add_node(name, fn)
    g.set_entry_point("load_schema")
    g.add_edge("load_schema", "generate_sql")
    g.add_edge("generate_sql", "execute")
    g.add_conditional_edges("execute", route, {"retry": "generate_sql", "answer": "answer", "refuse": "refuse", "fail": "fail"})
    for n in ("answer", "refuse", "fail"):
        g.add_edge(n, END)
    return g.compile()

graph = build_graph()

def ask(question: str) -> dict:
    t0 = time.time()
    s = graph.invoke({"question": question})
    return {"question": question, "answer": s.get("answer"), "sql": s.get("sql"),
            "sql_history": s.get("sql_history", []), "retries": max(s.get("attempts", 1) - 1, 0),
            "blocked": s.get("blocked", False), "row_count": len(s.get("rows") or []),
            "latency_s": round(time.time() - t0, 2)}
