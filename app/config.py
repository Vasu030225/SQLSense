import os
from dotenv import load_dotenv
load_dotenv()

DB_PATH = os.getenv("DB_PATH", "data/ops.db")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 2))
MAX_ROWS = int(os.getenv("MAX_ROWS", 200))

def get_llm():
    """Local LLM served by Ollama. temperature=0 for deterministic SQL generation."""
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        num_ctx=int(os.getenv("OLLAMA_NUM_CTX", 8192)),  # schema + sample rows need a larger context
        temperature=0,
    )
