"""
NEXOME OSINT Terminal — LLM Adapters & Agentic Loop
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import AsyncIterator

import anthropic
import requests

from config import ANTHROPIC_API_KEY, GEMINI_API_KEY, LOCAL_LLM_URL, LOCAL_LLM_MODEL, SHERLOCK_SYSTEM_PROMPT
from tools import OSINT_TOOLS, execute_tool, _sherlock_fallback_stream


def to_gemini_tools(osint_tools: list[dict]) -> list[dict]:
    gemini_tools = []
    for tool in osint_tools:
        gemini_tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"]
        })
    return [{"function_declarations": gemini_tools}]


def to_gemini_messages(anthropic_messages: list[dict]) -> list[dict]:
    gemini_msgs = []
    for msg in anthropic_messages:
        role = "model" if msg["role"] == "assistant" else "user"
        parts = []
        content = msg["content"]

        if isinstance(content, str):
            parts.append({"text": content})
        elif isinstance(content, list):
            for block in content:
                if block.get("type") == "text":
                    parts.append({"text": block["text"]})
                elif block.get("type") == "tool_use":
                    parts.append({
                        "functionCall": {
                            "name": block["name"],
                            "args": block["input"]
                        }
                    })
                elif block.get("type") == "tool_result":
                    try:
                        res_obj = json.loads(block["content"])
                    except Exception:
                        res_obj = {"result": block["content"]}
                    parts.append({
                        "functionResponse": {
                            "name": block.get("tool_use_id", ""),
                            "response": {"result": res_obj}
                        }
                    })
        gemini_msgs.append({"role": role, "parts": parts})
    return gemini_msgs


async def run_anthropic_loop(model_name: str, query: str) -> AsyncIterator[tuple[str, dict]]:
    async_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    messages: list[dict] = [{"role": "user", "content": query}]

    for iteration in range(4):
        is_final_iteration = iteration == 3
        async with async_client.messages.stream(
            model=model_name,
            max_tokens=4096,
            system=SHERLOCK_SYSTEM_PROMPT,
            tools=OSINT_TOOLS,
            messages=messages,
        ) as stream:
            async for text_delta in stream.text_stream:
                yield ("thought", {"delta": text_delta})
            response = await stream.get_final_message()

        serialized_content = []
        for block in response.content:
            if block.type == "text":
                serialized_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                serialized_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        messages.append({"role": "assistant", "content": serialized_content})

        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        if response.stop_reason == "end_turn" or not tool_blocks:
            final_text = " ".join(b.text for b in response.content if b.type == "text")
            yield ("final_answer", {"text": final_text})
            return

        if is_final_iteration:
            yield ("error", {"message": "Limite d'itérations agentiques atteinte."})
            return

        tool_results = []
        for tool_block in tool_blocks:
            yield ("tool_call", {"tool": tool_block.name, "input": tool_block.input, "id": tool_block.id})
            result = await execute_tool(tool_block.name, tool_block.input)
            yield ("tool_result", {"tool": tool_block.name, "result": result, "id": tool_block.id})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })
        messages.append({"role": "user", "content": tool_results})


async def run_gemini_loop(model_name: str, query: str) -> AsyncIterator[tuple[str, dict]]:
    messages: list[dict] = [{"role": "user", "content": [{"type": "text", "text": query}]}]
    gemini_tools = to_gemini_tools(OSINT_TOOLS)

    for iteration in range(4):
        is_final_iteration = iteration == 3
        payload = {
            "contents": to_gemini_messages(messages),
            "tools": gemini_tools,
            "systemInstruction": {
                "parts": [{"text": SHERLOCK_SYSTEM_PROMPT}]
            }
        }
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent?alt=sse"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
        }

        def do_post():
            return requests.post(url, headers=headers, json=payload, stream=True, timeout=30)

        max_retries = 3
        for attempt in range(max_retries):
            r = await asyncio.to_thread(do_post)
            if r.status_code == 200:
                break
            elif r.status_code in [429, 503] and attempt < max_retries - 1:
                wait_time = 1.5 * (attempt + 1)
                await asyncio.sleep(wait_time)
                continue
            else:
                raise Exception(f"Gemini HTTP {r.status_code}: {r.text}")

        complete_text = ""
        tool_calls = []

        def read_lines():
            return list(r.iter_lines())

        lines = await asyncio.to_thread(read_lines)
        for line in lines:
            if not line:
                continue
            decoded = line.decode("utf-8").strip()
            if decoded.startswith("data: "):
                try:
                    data = json.loads(decoded[6:])
                    candidate = data.get("candidates", [{}])[0]
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])
                    for part in parts:
                        if "text" in part:
                            txt = part["text"]
                            complete_text += txt
                            yield ("thought", {"delta": txt})
                        if "functionCall" in part:
                            fc = part["functionCall"]
                            fc_id = fc.get("id") or f"gemini-call-{iteration}-{len(tool_calls)}"
                            tool_calls.append({
                                "type": "tool_use",
                                "id": fc_id,
                                "name": fc["name"],
                                "input": fc.get("args", {})
                            })
                except Exception:
                    continue

        if not tool_calls:
            yield ("final_answer", {"text": complete_text})
            return

        if is_final_iteration:
            yield ("error", {"message": "Limite d'itérations agentiques atteinte."})
            return

        assistant_content = []
        if complete_text:
            assistant_content.append({"type": "text", "text": complete_text})
        for tc in tool_calls:
            assistant_content.append(tc)
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for tc in tool_calls:
            yield ("tool_call", {"tool": tc["name"], "input": tc["input"], "id": tc["id"]})
            result = await execute_tool(tc["name"], tc["input"])
            yield ("tool_result", {"tool": tc["name"], "result": result, "id": tc["id"]})
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })
        messages.append({"role": "user", "content": tool_results})


def _detect_local_llm() -> dict | None:
    if LOCAL_LLM_URL and LOCAL_LLM_MODEL:
        prov = "ollama" if "ollama" in LOCAL_LLM_URL.lower() else "openai_local"
        return {"url": LOCAL_LLM_URL, "model": LOCAL_LLM_MODEL, "provider": prov}

    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=0.2)
        if r.status_code == 200:
            models = r.json().get("models", [])
            if models:
                ds_model = next((m["name"] for m in models if "deepseek" in m["name"].lower()), models[0]["name"])
                return {"url": "http://127.0.0.1:11434/api/chat", "model": ds_model, "provider": "ollama"}
    except Exception:
        pass

    try:
        r = requests.get("http://127.0.0.1:1234/v1/models", timeout=0.2)
        if r.status_code == 200:
            models = r.json().get("data", [])
            if models:
                ds_model = next((m["id"] for m in models if "deepseek" in m["id"].lower()), models[0]["id"])
                return {"url": "http://127.0.0.1:1234/v1/chat/completions", "model": ds_model, "provider": "openai_local"}
    except Exception:
        pass

    return None


def to_openai_messages(anthropic_messages: list[dict]) -> list[dict]:
    openai_msgs = []
    for msg in anthropic_messages:
        role = msg["role"]
        content = msg["content"]
        if isinstance(content, str):
            openai_msgs.append({"role": role, "content": content})
        elif isinstance(content, list):
            txt = ""
            for block in content:
                if block.get("type") == "text":
                    txt += block["text"] + "\n"
                elif block.get("type") == "tool_use":
                    txt += f"[Recherche OSINT requise : {block['name']} ({block['input']})]\n"
                elif block.get("type") == "tool_result":
                    txt += f"[Résultat de recherche : {block['content']}]\n"
            openai_msgs.append({"role": role, "content": txt.strip()})
    return openai_msgs


async def run_local_llm_loop(url: str, provider: str, model_name: str, query: str) -> AsyncIterator[tuple[str, dict]]:
    messages: list[dict] = [{"role": "user", "content": query}]
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": SHERLOCK_SYSTEM_PROMPT},
            *to_openai_messages(messages)
        ],
        "stream": True
    }

    def do_post():
        return requests.post(url, json=payload, stream=True, timeout=20)

    r = await asyncio.to_thread(do_post)
    if r.status_code != 200:
        raise Exception(f"Local LLM {r.status_code}: {r.text}")

    complete_text = ""
    def read_lines():
        return list(r.iter_lines())

    lines = await asyncio.to_thread(read_lines)
    for line in lines:
        if not line:
            continue
        decoded = line.decode("utf-8").strip()

        if provider == "ollama":
            try:
                data = json.loads(decoded)
                txt = data.get("message", {}).get("content", "")
                if txt:
                    complete_text += txt
                    yield ("thought", {"delta": txt})
            except Exception:
                continue
        else:
            if decoded.startswith("data: "):
                try:
                    data = json.loads(decoded[6:])
                    txt = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if txt:
                        complete_text += txt
                        yield ("thought", {"delta": txt})
                except Exception:
                    continue

    yield ("final_answer", {"text": complete_text})


async def run_agent_loop(provider: str, model_name: str, query: str) -> AsyncIterator[tuple[str, dict]]:
    if provider == "anthropic":
        async for ev in run_anthropic_loop(model_name, query):
            yield ev
    elif provider == "google":
        async for ev in run_gemini_loop(model_name, query):
            yield ev
    elif provider in ["ollama", "openai_local"]:
        url = "http://127.0.0.1:11434/api/chat" if provider == "ollama" else "http://127.0.0.1:1234/v1/chat/completions"
        if LOCAL_LLM_URL:
            url = LOCAL_LLM_URL
        async for ev in run_local_llm_loop(url, provider, model_name, query):
            yield ev
    else:
        raise ValueError(f"Provider inconnu: {provider}")


async def sherlock_agent_stream(query: str) -> AsyncIterator[tuple[str, dict]]:
    models_chain = []

    if ANTHROPIC_API_KEY:
        models_chain.append(
            {"provider": "anthropic", "model": "claude-sonnet-4-20250514"}
        )

    if GEMINI_API_KEY:
        models_chain.extend([
            {"provider": "google", "model": "gemini-2.5-flash"},
            {"provider": "google", "model": "gemini-1.5-flash"},
        ])

    local_info = _detect_local_llm()
    if local_info:
        models_chain.append(
            {"provider": local_info["provider"], "model": local_info["model"]}
        )

    if not models_chain:
        yield ("warning", {"message": "Aucun modèle configuré (API ou Local). Mode Autonome activé."})
        async for ev in _sherlock_fallback_stream(query):
            yield ev
        return

    for config in models_chain:
        provider = config["provider"]
        model_name = config["model"]

        yield ("thought", {"delta": f"[Système : Tentative de connexion avec {model_name} ({provider.upper()})...]\n"})

        try:
            async for event_type, event_data in run_agent_loop(provider, model_name, query):
                yield event_type, event_data
            return
        except Exception as exc:
            yield ("warning", {"message": f"Échec avec {model_name} : {str(exc)[:120]}. Passage au modèle suivant..."})
            continue

    yield ("warning", {"message": "Tous les modèles de la chaîne ont échoué. Mode Autonome activé."})
    async for ev in _sherlock_fallback_stream(query):
        yield ev
