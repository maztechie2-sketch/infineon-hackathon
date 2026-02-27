"""
Infineon Hackathon - Agentic Bug Detection System
Architecture:
  Agent 1: Code Diff Agent     -> finds exact bug line via diff (algorithmic)
  Agent 2: MCP Retrieval Agent -> queries MCP server for relevant manual docs
  Agent 3: Explanation Agent   -> uses Qwen (local) to generate explanation
"""

import csv
import re
import requests
import difflib
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mcp_client import MCPClient

# ── CONFIG ─────────────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
QWEN_MODEL = "qwen2.5-coder:latest"   # ← update if your model name differs

INPUT_CSV  = "samples.csv"
OUTPUT_CSV = "output.csv"

mcp = MCPClient("http://localhost:8003")
# ───────────────────────────────────────────────────────────────────────────────


# =============================================================================
# AGENT 1: Code Diff Agent
# Finds the FIRST line in buggy code that differs from correct code.
# Pure algorithmic — fast and highly accurate for scoring.
# =============================================================================
def agent_diff(buggy_code: str, correct_code: str) -> int:
    """Returns the 1-based line number of the first bug in buggy_code."""
    buggy_lines   = buggy_code.splitlines()
    correct_lines = correct_code.splitlines()

    matcher = difflib.SequenceMatcher(None, buggy_lines, correct_lines, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != 'equal':
            return i1 + 1  # 1-based

    # Fallback: line-by-line
    for i, (b, c) in enumerate(zip(buggy_lines, correct_lines)):
        if b.strip() != c.strip():
            return i + 1

    return len(correct_lines) + 1


# =============================================================================
# AGENT 2: MCP Retrieval Agent
# Calls the MCP server's search_documents tool to get relevant manual context.
# =============================================================================
def extract_api_calls(code: str) -> str:
    calls = re.findall(r'rdi\.\w+', code)
    return " ".join(set(calls))[:200]


def agent_mcp_retrieve(context: str, explanation_hint: str, buggy_code: str) -> str:
    query = f"{context}. {explanation_hint}"
    print(f"  [Agent 2 - MCP] Query: {query[:80]}...")
    docs = mcp.search_documents(query)
    if not docs:
        keywords = extract_api_calls(buggy_code)
        if keywords:
            print(f"  [Agent 2 - MCP] Fallback: {keywords[:60]}...")
            docs = mcp.search_documents(keywords)
    return docs


# =============================================================================
# AGENT 3: Explanation Agent (Qwen via Ollama)
# =============================================================================
def agent_explain(buggy_code, correct_code, context, bug_line, manual_docs, explanation_hint):
    buggy_lines = buggy_code.splitlines()
    bug_line_content = buggy_lines[bug_line - 1].strip() if bug_line <= len(buggy_lines) else ""

    manual_section = (
        f"\n\nRELEVANT DOCUMENTATION FROM MANUAL:\n{manual_docs[:1500]}"
        if manual_docs else ""
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
            timeout=90
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        print(f"  [Agent 3 - Qwen Warning] {e}")
        return explanation_hint.strip()


# =============================================================================
# ORCHESTRATOR
# =============================================================================
def process_row(row):
    code_id          = row["ID"]
    buggy_code       = row["Code"]
    correct_code     = row["Correct Code"]
    context          = row.get("Context", "")
    explanation_hint = row.get("Explanation", "")

    print(f"\n{'='*60}\n[ID {code_id}] Processing...")

    bug_line = agent_diff(buggy_code, correct_code)
    print(f"  [Agent 1 - Diff] Bug on line: {bug_line}")

    manual_docs = agent_mcp_retrieve(context, explanation_hint, buggy_code)
    print(f"  [Agent 2 - MCP] Retrieved {len(manual_docs)} chars")

    explanation = agent_explain(
        buggy_code, correct_code, context,
        bug_line, manual_docs, explanation_hint
    )
    print(f"  [Agent 3 - Qwen] {explanation[:100]}...")

    return {"ID": code_id, "Bug Line": bug_line, "Explanation": explanation}


def main():
    input_file  = sys.argv[1] if len(sys.argv) > 1 else INPUT_CSV
    output_file = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_CSV

    print(f"Reading: {input_file}")
    rows = []
    with open(input_file, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            rows.append(dict(row))

    print(f"Found {len(rows)} snippets.\n")
    results = [process_row(r) for r in rows]

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["ID", "Bug Line", "Explanation"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n✅ Output written to: {output_file} ({len(results)} entries)")


if __name__ == "__main__":
    main()
