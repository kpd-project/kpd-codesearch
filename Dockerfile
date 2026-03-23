# АСТРА-М (ASTRA-M) — веб-приложение RAG по кодовой базе
FROM python:3.12-slim

WORKDIR /app

# Системные зависимости для treesitter-chunker (tree-sitter)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p logs .index_state

# Внутри контейнера репозитории монтируются в /repos
ENV REPOS_BASE_PATH=/repos
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]
