"""
NEXOME OSINT Terminal — FastAPI Application & Routes
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi import Query as QueryParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

from tools import check_tor_status
from llm import sherlock_agent_stream


# ══════════════════════════════════════════════════════════════════════════════
# SSE MAIN GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

async def osint_stream(query: str):
    def evt(etype: str, data: dict) -> str:
        return (
            f"data: {json.dumps({'type': etype, 'data': data, 'ts': datetime.now().strftime('%H:%M:%S')})}\n\n"
        )

    q = query.strip()
    if not q:
        yield evt("error", {"message": "Requête vide."})
        return

    yield evt("log", {"message": "Vérification du tunnel Tor..."})
    tor = await asyncio.to_thread(check_tor_status)
    yield evt("tor_status", tor)

    if not tor["tor_active"]:
        yield evt(
            "warning",
            {
                "message": (
                    "ATTENTION: Tor inactif — connexion directe utilisée. "
                    "Anonymat non garanti. Lancez 'tor' dans un terminal."
                )
            },
        )

    yield evt("log", {"message": f"[SHERLOCK] Prise en charge de la requête..."})

    async for event_type, event_data in sherlock_agent_stream(q):
        yield evt(event_type, event_data)

    yield evt("done", {"message": "— Analyse NEXOME terminée. Sherlock over & out. —"})


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="NEXOME OSINT Terminal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/", response_class=HTMLResponse)
async def index():
    tpl = Path(__file__).parent / "templates" / "index.html"
    return tpl.read_text(encoding="utf-8")


LEGAL_PAGES = {
    "mentions-legales": "mentions_legales.html",
    "confidentialite": "confidentialite.html",
    "cgu": "cgu.html",
}


@app.get("/{page}", response_class=HTMLResponse)
async def legal(page: str):
    if page not in LEGAL_PAGES:
        return HTMLResponse("Page not found", status_code=404)
    tpl = Path(__file__).parent / "templates" / LEGAL_PAGES[page]
    return tpl.read_text(encoding="utf-8")


@app.get("/api/tor-status")
async def get_tor_status():
    return await asyncio.to_thread(check_tor_status)


@app.get("/api/stream")
async def stream(q: str = QueryParam(...)):
    return StreamingResponse(
        osint_stream(q),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8080, reload=True)
