import requests, sys

def test_mcp():
    print("Testing MCP Server...")
    try:
        payload = {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"add","arguments":{"a":2,"b":3}}}
        resp = requests.post("http://localhost:8003/mcp", json=payload, timeout=10)
        result = resp.json().get("result")
        print(f"  OK MCP Server (add(2,3)={result})")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

def test_qwen(model="qwen2.5-coder:7b"):
    print(f"Testing Qwen ({model})...")
    try:
        resp = requests.post("http://localhost:11434/api/generate",
            json={"model":model,"prompt":"Say OK","stream":False,"options":{"num_predict":5}}, timeout=30)
        text = resp.json().get("response","").strip()
        print(f"  OK Qwen (response: '{text}')")
        return True
    except Exception as e:
        print(f"  FAILED: {e}")
        return False

def test_mcp_search():
    print("Testing MCP search_documents...")
    try:
        payload = {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_documents","arguments":{"query":"vForce range"}}}
        resp = requests.post("http://localhost:8003/mcp", json=payload, timeout=20)
        result = resp.json().get("result",[])
        print(f"  OK search returned {len(result)} docs")
    except Exception as e:
        print(f"  FAILED: {e}")

if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5-coder:7b"
    if test_mcp(): test_mcp_search()
    test_qwen(model)
