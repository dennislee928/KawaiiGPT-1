FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    anthropic \
    openai \
    requests \
    prompt_toolkit \
    colorama

COPY chat.py .

CMD ["python", "chat.py"]
