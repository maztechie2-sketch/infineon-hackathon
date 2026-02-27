import requests

class MCPClient:
    def __init__(self, base_url="http://localhost:8003"):
        self.base_url = base_url.rstrip("/")
        self._rpc_id = 0

    def _next_id(self):
        self._rpc_id += 1
        return self._rpc_id

    def call_tool(self, tool_name, arguments):
        payload = {"jsonrpc":"2.0","id":self._next_id(),"method":"tools/call","params":{"name":tool_name,"arguments":arguments}}
        try:
            resp = requests.post(f"{self.base_url}/mcp", json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json().get("result")
        except Exception as e:
            print(f"[MCP] Error: {e}")
            return None

    def search_documents(self, query, top_k=5):
        result = self.call_tool("search_documents", {"query": query})
        if not result:
            return ""
        if isinstance(result, list):
            filtered = sorted(result, key=lambda x: x.get("score",0), reverse=True)
            filtered = [r for r in filtered if r.get("score",0) > 0.25][:top_k]
            return "\n\n---\n\n".join(r.get("text","") for r in filtered)
        return str(

result)
