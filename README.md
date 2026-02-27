# Agentic Bug Detection System — Infineon Hackathon

## Architecture
```
Input CSV (buggy C++ code)
        ↓
Agent 1: Code Diff Agent      → finds exact bug line (algorithmic diff)
        ↓
Agent 2: MCP Retrieval Agent  → queries MCP server for manual docs
        ↓
Agent 3: Explanation Agent    → Qwen (local LLM) generates explanation
        ↓
output.csv  (ID, Bug Line, Explanation)
```

---

## Prerequisites

### 1. Install Ollama + Qwen model
```bash
# Windows — download installer from:
# https://ollama.com/download

# After installing Ollama, pull the model:
ollama pull qwen2.5-coder:7b
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. MCP Server setup
The MCP server requires:
- `server/embedding_model/` folder (BAAI/bge-base-en-v1.5)
- `server/storage/` folder (vector store JSON files)

**These folders are NOT in this repo** (too large for GitHub).  
Download them from the shared drive link provided by the organizers,  
and place them at:
```
repo/
├── server/
│   ├── embedding_model/   ← paste here
│   ├── storage/           ← paste here
│   └── mcp_server.py
```

### 4. Start the MCP Server (in a separate terminal)
```bash
cd server
python mcp_server.py
```
Server runs on `http://localhost:8003`

---

## Running the Pipeline

```bash
# Step 1 — verify connections
python code/test_connections.py

# Step 2 — run bug detection
python code/main.py samples.csv output.csv

# Step 3 — open GUI in browser
# Just open code/gui.html in any browser
# Drag and drop output.csv (and optionally samples.csv) into the GUI
```

---

## Configuration

Edit the top of `code/main.py` to change model or ports:

```python
OLLAMA_URL = "http://localhost:11434/api/generate"
QWEN_MODEL = "qwen2.5-coder:7b"   # change if you pulled a different model
INPUT_CSV  = "samples.csv"
OUTPUT_CSV = "output.csv"
```

If you pulled a smaller model use:
- `qwen2.5-coder:1.5b`  (low RAM machines)
- `qwen2.5-coder:7b`    (recommended, needs ~8GB RAM)

---

## Output Format

`output.csv` contains:

| ID | Bug Line | Explanation |
|----|----------|-------------|
| 3  | 4        | vForce set to 31V exceeds vForceRange of 30V... |
| 16 | 1        | vecEditMode set to TA::VECD instead of TA::VTT... |

---

## Submission Structure
```
TeamName_Submission.zip
├── output.csv
├── requirements.txt
├── code/
│   ├── main.py
│   ├── mcp_client.py
│   ├── test_connections.py
│   └── gui.html
└── server/
    └── mcp_server.py
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `MCP Server FAILED` | Run `python server/mcp_server.py` first |
| `Qwen FAILED` | Run `ollama serve` then `ollama list` to verify model name |
| `embedding_model not found` | Copy the folder from organizer's shared drive |
| Low RAM machine | Use `qwen2.5-coder:1.5b` instead |
