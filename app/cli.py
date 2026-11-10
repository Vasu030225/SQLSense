from .agent import ask

if __name__ == "__main__":
    print("SQL Agent POC (Ollama) - type 'exit' to quit")
    while (q := input("\n> ").strip()) != "exit":
        r = ask(q)
        print(f"\nSQL ({r['retries']} retries, {r['latency_s']}s):\n{r['sql']}\n\nAnswer: {r['answer']}")
