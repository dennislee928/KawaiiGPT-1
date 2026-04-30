import os
import sys
import anthropic
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from colorama import init, Fore, Style

init(autoreset=True)

SYSTEM = "You are a helpful AI assistant."
MODEL = "claude-opus-4-7"
HISTORY_FILE = os.path.join(os.path.dirname(__file__), ".chat_history")


def stream_response(client: anthropic.Anthropic, messages: list) -> str:
    print(Fore.CYAN + "Claude: " + Style.RESET_ALL, end="", flush=True)
    full_text = ""
    with client.messages.stream(
        model=MODEL,
        max_tokens=4096,
        system=[{
            "type": "text",
            "text": SYSTEM,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
            full_text += text
    print()
    return full_text


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(Fore.RED + "Error: ANTHROPIC_API_KEY is not set.")
        print("Get your key at https://console.anthropic.com")
        print("Then run: set ANTHROPIC_API_KEY=your-key-here")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    session = PromptSession(history=FileHistory(HISTORY_FILE))
    messages = []

    print(Fore.MAGENTA + "=== KawaiiGPT ===" + Style.RESET_ALL)
    print(f"Model: {MODEL}  |  Type 'exit' to quit, 'reset' to clear history\n")

    while True:
        try:
            user_input = session.prompt(Fore.GREEN + "You: " + Style.RESET_ALL).strip()
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
            print(Fore.YELLOW + "[Conversation reset]" + Style.RESET_ALL)
            continue

        messages.append({"role": "user", "content": user_input})
        try:
            response = stream_response(client, messages)
            messages.append({"role": "assistant", "content": response})
        except anthropic.AuthenticationError:
            print(Fore.RED + "Invalid API key. Check your ANTHROPIC_API_KEY.")
        except anthropic.RateLimitError:
            print(Fore.RED + "Rate limited. Wait a moment and try again.")
        except anthropic.APIConnectionError:
            print(Fore.RED + "Connection error. Check your internet connection.")
        except Exception as e:
            print(Fore.RED + f"Error: {e}")


if __name__ == "__main__":
    main()
