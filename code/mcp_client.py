"""
MCP Client using fastmcp's native async Client.
Connects to the SSE server at http://localhost:8003/sse
"""
import asyncio
from fastmcp import Client


async def _search(query: str, top_k: int = 5) -> str:
    async with Client("http://localhost:8003/sse") as client:
        result = await client.call_tool("search_documents", {"query": query})
        nodes = result.data if hasattr(result, 'data') else result
        if isinstance(nodes, list):
            filtered = sorted(nodes, key=lambda x: x.get("score", 0) if isinstance(x, dict) else 0, reverse=True)
            filtered = [r for r in filtered if isinstance(r, dict) and r.get("score", 0) > 0.25][:top_k]
            return "\n\n---\n\n".join(r.get("text", "") for r in filtered)
        return str(nodes)


class MCPClient:
    def __init__(self, base_url="http://localhost:8003"):
        self.base_url = base_url.rstrip("/")

    def search_documents(self, query: str, top_k: int = 5) -> str:
        """Search the vector store for relevant manual documentation."""
        try:
            return asyncio.run(_search(query, top_k))
        except Exception as e:
            print(f"[MCP] Error: {e}")
            return ""
