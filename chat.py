"""
KawaiiGPT chat — supports multiple providers via environment variables:

  Anthropic (paid):  set ANTHROPIC_API_KEY=sk-ant-...
  Groq (free tier):  set GROQ_API_KEY=gsk_...
  Ollama (local):    set OLLAMA_HOST=http://localhost:11434   (default if nothing else set)

Optional overrides:
  OLLAMA_MODEL=llama3.2          (default: llama3.2)
  GROQ_MODEL=llama-3.3-70b-versatile
"""

import os
import sys
import requests
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.formatted_text import HTML

SYSTEM = "You are a helpful AI assistant."
HISTORY_FILE = os.path.join(os.path.dirname(__file__), ".chat_history")


# ── Provider detection ────────────────────────────────────────────────────────

def detect_provider():
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    return "ollama"


# ── Anthropic (Claude) ────────────────────────────────────────────────────────

def stream_anthropic(messages: list) -> str:
    import anthropic
    client = anthropic.Anthropic()
    model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7")
    print(f"\033[36mClaude:\033[0m ", end="", flush=True)
    full_text = ""
    with client.messages.stream(
        model=model,
        max_tokens=4096,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text += text
    print()
    return full_text


# ── Groq (free OpenAI-compatible API) ────────────────────────────────────────

def stream_openai_compat(messages: list, base_url: str, api_key: str, model: str) -> str:
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key)
    label = "Groq" if "groq" in base_url else "AI"
    print(f"\033[36m{label}:\033[0m ", end="", flush=True)
    full_text = ""
    with client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": SYSTEM}] + messages,
        stream=True,
    ) as stream:
        for chunk in stream:
            text = chunk.choices[0].delta.content or ""
            print(text, end="", flush=True)
            full_text += text
    print()
    return full_text


# ── Ollama (local, completely free) ──────────────────────────────────────────

def stream_ollama(messages: list) -> str:
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    url = f"{host}/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM}] + messages,
        "stream": True,
    }
    print(f"\033[36mOllama ({model}):\033[0m ", end="", flush=True)
    full_text = ""
    with requests.post(url, json=payload, stream=True, timeout=120) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text}")
        import json
        for line in resp.iter_lines():
            if not line:
                continue
            data = json.loads(line)
            text = data.get("message", {}).get("content", "")
            print(text, end="", flush=True)
            full_text += text
            if data.get("done"):
                break
    print()
    return full_text


def ollama_pull_if_missing(model: str, host: str):
    """Pull the model if it isn't already downloaded."""
    tags_url = f"{host}/api/tags"
    try:
        tags = requests.get(tags_url, timeout=5).json()
        names = [m["name"].split(":")[0] for m in tags.get("models", [])]
        if model.split(":")[0] not in names:
            print(f"Pulling model '{model}' from Ollama (first run, may take a while)...")
            requests.post(f"{host}/api/pull", json={"name": model}, timeout=600)
            print("Done.\n")
    except requests.ConnectionError:
        print(f"\033[31mCannot reach Ollama at {host}.\033[0m")
        print("Make sure Ollama is running:  ollama serve")
        print("Or start the Docker stack:    docker-compose up\n")
        sys.exit(1)


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    provider = detect_provider()
    model_label = {
        "anthropic": os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
        "groq":      os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "ollama":    os.environ.get("OLLAMA_MODEL", "llama3.2"),
    }[provider]

    if provider == "ollama":
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
        ollama_pull_if_missing(model_label, host)

    session = PromptSession(history=FileHistory(HISTORY_FILE))
    messages = []

    print(f"=== KawaiiGPT ===  [{provider}] {model_label}")
    print("Commands: exit | reset | help\n")

    while True:
        try:
            user_input = session.prompt(HTML("<ansigreen><b>You:</b></ansigreen> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Bye!")
            break
        if user_input.lower() == "reset":
            messages.clear()
            print("[Conversation reset]\n")
            continue
        if user_input.lower() == "help":
            print("  exit / quit  — quit\n  reset        — clear history\n")
            continue

        messages.append({"role": "user", "content": user_input})
        try:
            if provider == "anthropic":
                reply = stream_anthropic(messages)
            elif provider == "groq":
                reply = stream_openai_compat(
                    messages,
                    base_url="https://api.groq.com/openai/v1",
                    api_key=os.environ["GROQ_API_KEY"],
                    model=model_label,
                )
            else:
                reply = stream_ollama(messages)
            messages.append({"role": "assistant", "content": reply})
        except KeyboardInterrupt:
            print("\n[interrupted]")
            messages.pop()
        except Exception as e:
            print(f"\033[31mError: {e}\033[0m")
            messages.pop()


if __name__ == "__main__":
    main()
