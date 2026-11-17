import logging, os
import httpx
from fastapi import FastAPI
from pydantic import BaseModel
from .agent import ask

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sql-agent")
app = FastAPI(title="LangChain SQL Agent POC (Ollama)")

class Q(BaseModel):
    question: str

@app.post("/ask")
def ask_endpoint(q: Q):
    r = ask(q.question)
    log.info("q=%r retries=%s blocked=%s sql=%r latency=%s", q.question, r["retries"], r["blocked"], r["sql"], r["latency_s"])
    return r

@app.get("/health")
def health():
    """Also checks that the local Ollama server is reachable and the model is pulled."""
    base, model = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"), os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    try:
        tags = [m["name"] for m in httpx.get(f"{base}/api/tags", timeout=3).json().get("models", [])]
        return {"status": "ok", "ollama": "up", "model_available": any(t.startswith(model) for t in tags)}
    except Exception as e:
        return {"status": "degraded", "ollama": f"unreachable: {e}"}
