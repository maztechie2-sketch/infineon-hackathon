# Infineon Hackathon - GUI Backend
# FastAPI server that wraps the existing 3-agent pipeline.
# Run from: gui/backend/ inside the infineon-hackathon folder

import csv
import re
import difflib
import sys
import os
import asyncio
import io
import concurrent.futures
from pathlib import Path
from typing import List, Dict

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import requests

# ── PATH SETUP ────────────────────────────────────────────────────────────────
# gui/backend/app.py  →  go up 2 levels to reach project root
ROOT     = Path(__file__).resolve().parent.parent.parent
CODE_DIR = ROOT / "code"
FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
sys.path.insert(0, str(CODE_DIR))

from mcp_client import MCPClient

# ── CONFIG ────────────────────────────────────────────────────────────────────
OLLAMA_URL  = "http://localhost:11434/api/generate"
QWEN_MODEL  = "qwen2.5-coder:7b"
MCP_URL     = "http://localhost:8003"
QWEN_TIMEOUT = 300   # seconds — generous for i3 CPU

app = FastAPI(title="Infineon Bug Detection API", version="1.0")

# Allow React frontend (any localhost port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── AGENT 1: Diff ─────────────────────────────────────────────────────────────
def agent_diff(buggy_code: str, correct_code: str) -> int:
    buggy_lines   = buggy_code.splitlines()
    correct_lines = correct_code.splitlines()
    matcher = difflib.SequenceMatcher(None, buggy_lines, correct_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            return i1 + 1
    for i, (b, c) in enumerate(zip(buggy_lines, correct_lines)):
        if b.strip() != c.strip():
            return i + 1
    return len(correct_lines) + 1

# ── AGENT 2: MCP Retrieval ────────────────────────────────────────────────────
def extract_api_calls(code: str) -> str:
    calls = re.findall(r'rdi\.\w+', code)
    return " ".join(set(calls))[:200]

def _mcp_call(query: str) -> str:
    """Run MCP search in a fresh thread to avoid asyncio conflict."""
    mcp = MCPClient(MCP_URL)
    return mcp.search_documents(query) or ""

def agent_mcp_retrieve(context: str, explanation_hint: str, buggy_code: str) -> str:
    try:
        query = f"{context}. {explanation_hint}"
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            docs = ex.submit(_mcp_call, query).result(timeout=30)
        if not docs:
            keywords = extract_api_calls(buggy_code)
            if keywords:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    docs = ex.submit(_mcp_call, keywords).result(timeout=30)
        return docs or ""
    except Exception as e:
        return f"[MCP unavailable: {e}]"

# ── AGENT 3: Qwen Explanation ─────────────────────────────────────────────────
def agent_explain(buggy_code, correct_code, context, bug_line, manual_docs, explanation_hint):
    buggy_lines = buggy_code.splitlines()
    bug_line_content = buggy_lines[bug_line - 1].strip() if bug_line <= len(buggy_lines) else ""
    manual_section = (
        f"\n\nRELEVANT DOCUMENTATION FROM MANUAL:\n{manual_docs[:1500]}"
        if manual_docs and not manual_docs.startswith("[MCP") else ""
    )
    prompt = f"""You are an expert C++ bug analyst for the SmartRDI API (Infineon testing framework).

TASK: Explain the bug in the code below. Be concise (1-3 sentences).

CONTEXT: {context}
BUG IS ON LINE {bug_line}: `{bug_line_content}`

BUGGY CODE:
{buggy_code}

CORRECT CODE:
{correct_code}
{manual_section}

Explain what is wrong on line {bug_line} and why. Reference the API/documentation if relevant.
Do NOT repeat the code. Just a clear explanation.

EXPLANATION:"""

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": QWEN_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 200}
            },
            timeout=QWEN_TIMEOUT
        )
        resp.raise_for_status()
        result = resp.json().get("response", "").strip()
        return result if result else explanation_hint.strip()
    except Exception:
        return explanation_hint.strip()

# ── PROCESS ONE ROW ───────────────────────────────────────────────────────────
def process_row(row: Dict) -> Dict:
    code_id          = row["ID"]
    buggy_code       = row["Code"]
    correct_code     = row["Correct Code"]
    context          = row.get("Context", "")
    explanation_hint = row.get("Explanation", "")

    bug_line    = agent_diff(buggy_code, correct_code)
    manual_docs = agent_mcp_retrieve(context, explanation_hint, buggy_code)
    explanation = agent_explain(
        buggy_code, correct_code, context,
        bug_line, manual_docs, explanation_hint
    )

    return {
        "ID": code_id,
        "Bug Line": bug_line,
        "Explanation": explanation,
        # Extra fields for the GUI display (not in output.csv)
        "Context": context,
        "Buggy Code": buggy_code,
        "Correct Code": correct_code,
    }

# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Quick check that backend is alive."""
    mcp_ok = False
    qwen_ok = False
    try:
        r = requests.get("http://localhost:8003", timeout=2)
        mcp_ok = True
    except Exception:
        pass
    try:
        r = requests.get("http://localhost:11434", timeout=2)
        qwen_ok = True
    except Exception:
        pass
    return {
        "status": "ok",
        "mcp_server": mcp_ok,
        "ollama": qwen_ok,
        "model": QWEN_MODEL
    }


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    Accept samples.csv upload.
    Run all 3 agents on each row.
    Return JSON results + downloadable output.csv.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Please upload a CSV file.")

    content = await file.read()
    text    = content.decode("utf-8")
    reader  = csv.DictReader(io.StringIO(text))
    rows    = [dict(r) for r in reader]

    if not rows:
        raise HTTPException(400, "CSV file is empty.")

    required = {"ID", "Code", "Correct Code"}
    if not required.issubset(set(rows[0].keys())):
        raise HTTPException(400, f"CSV must have columns: {required}")

    # Run pipeline (sync — acceptable for demo, 20 rows)
    results = []
    for row in rows:
        results.append(process_row(row))

    return JSONResponse({
        "total": len(results),
        "results": results
    })


@app.post("/download")
async def download(file: UploadFile = File(...)):
    """
    Same as /analyze but returns output.csv as a file download.
    """
    content = await file.read()
    text    = content.decode("utf-8")
    reader  = csv.DictReader(io.StringIO(text))
    rows    = [dict(r) for r in reader]

    results = [process_row(r) for r in rows]

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["ID", "Bug Line", "Explanation"])
    writer.writeheader()
    for r in results:
        writer.writerow({
            "ID": r["ID"],
            "Bug Line": r["Bug Line"],
            "Explanation": r["Explanation"]
        })

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=output.csv"}
    )

# ── SERVE FRONTEND ────────────────────────────────────────────────────────────
@app.get("/")
def serve_frontend():
    index = FRONTEND / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"error": "Frontend not found. Place index.html in gui/frontend/"})
