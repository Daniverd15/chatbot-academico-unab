"""
Cliente MCP de prueba (Streamable HTTP). Lista las herramientas y ejecuta algunas.

    python mcp_server/test_client.py https://mcp.<ip>.sslip.io/mcp U00100001
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


async def main(url: str, codigo: str) -> None:
    headers = {"Authorization": f"Bearer {os.environ['MCP_AUTH_TOKEN']}"}
    async with streamablehttp_client(url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as s:
            info = await s.initialize()
            print(f"Conectado a {info.serverInfo.name} (MCP {info.protocolVersion})")
            tools = (await s.list_tools()).tools
            print(f"{len(tools)} herramientas:")
            for t in tools:
                print(f"  - {t.name}: {t.description.splitlines()[0]}")
            for name, args in [("consultar_estado_matricula", {"codigo": codigo}),
                               ("alertas_requisitos", {"codigo": codigo}),
                               ("proyeccion_graduacion", {"codigo": codigo, "creditos_por_semestre": 18})]:
                r = await s.call_tool(name, args)
                txt = r.content[0].text if r.content else json.dumps(r.structuredContent)
                print(f"\n>>> {name}({args})\n{txt[:600]}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "U00100001"))
