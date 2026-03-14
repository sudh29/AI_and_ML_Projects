# 🚀 RAG Project

A simple Retrieval-Augmented Generation (RAG) pipeline using LangChain, Ollama, and FAISS for document-based question answering.

## Setup Instructions

### 1. Install `uv` (Python package manager)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Create and initialize a virtual environment
```bash
uv venv
uv init
```

### 3. Activate the virtual environment
```bash
source .venv/bin/activate
```

### 4. Install project dependencies
```bash
uv pip install -r requirements.txt
```
Or, to sync with `pyproject.toml`:
```bash
uv sync
```

### 5. (Optional) Freeze current dependencies
```bash
uv pip freeze > requirements.txt
```

### 6. Install Ollama (for local LLM inference)
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### 7. Download the Qwen3 model
```bash
ollama run qwen3:0.6b
```

## Usage

1. Place your PDF (e.g., `DOCKER.pdf`) in the project directory.
2. Run the main script:
```bash
python main.py
```
3. Enter your question when prompted.

## Project Structure
- `main.py` — Main RAG pipeline script
- `requirements.txt` — Python dependencies
- `DOCKER.pdf` — Example document (replace with your own)

## Notes
- Make sure Ollama is running before starting the script.
- The script will remove any `<think>...</think>` blocks and newlines from the model's output.
