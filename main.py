"""
NEXOME OSINT Terminal — Agent IA Sherlock
Staff-Engineer refactor: FastAPI + Claude Tool Use + Tor + SSE Streaming
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

import anthropic
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi import Query as QueryParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

def _load_anthropic_key() -> str:
    """Try multiple sources for the API key, in priority order."""
    # 1 — runtime environment
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key.startswith("sk-ant-"):
        return key

    # 2 — local .env inside nexome_web/
    # 3 — user's minimax-agent .env (known-good location)
    candidates = [
        Path(__file__).parent / ".env",
        Path.home() / ".minimax-agent" / "projects" / "5" / ".env",
    ]
    for env_path in candidates:
        if not env_path.exists():
            continue
        try:
            with env_path.open(encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if line.startswith("ANTHROPIC_API_KEY="):
                        k = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if k.startswith("sk-ant-"):
                            return k
        except Exception:
            continue
    return ""


ANTHROPIC_API_KEY: str = _load_anthropic_key()

TOR_PROXIES = {
    "http": "socks5h://127.0.0.1:9150",
    "https": "socks5h://127.0.0.1:9150",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-MX,es;q=0.9,fr-FR;q=0.8,en-US;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}


# ══════════════════════════════════════════════════════════════════════════════
# SHERLOCK — PERSONA & TOOLS DEFINITION
# ══════════════════════════════════════════════════════════════════════════════

SHERLOCK_SYSTEM_PROMPT = """\
Tu es Sherlock, l'intelligence analytique centrale du système NEXOME OSINT Terminal.
Tu combines deux rôles cruciaux :

1. ANALYSTE (OSINT/Data) : Expert en renseignement, investigation digitale et détection
   de fraude. Tu utilises des dorks précis (site:, intext:, intitle:, filetype:), tu
   croises les sources, et tu synthétises l'information avec la rigueur d'un analyste NSA.

2. MENTOR (Alignement) : Tu connais ton utilisateur comme un profil 2E (HPI/TDAH). Tu
   adaptes tes réponses à son fonctionnement en hyperfocalisation — pas de verbiage, que
   de l'actionnable.

TON PROCESSUS OBLIGATOIRE :
  a. Pense à voix haute AVANT d'appeler un outil ("Je perçois ici...", "Mon analyse
     suggère que la cible est...", "La piste la plus prometteuse...").
  b. Extrais toujours la cible précise d'une requête longue.
     Ex : "Trouve les infos sur TuSpeaking et leurs subventions" → cible = "TuSpeaking",
     angle = "entreprise / subvention".
  c. Construis des dorks optimisés plutôt que de copier la phrase brute.
  d. Croise plusieurs outils si nécessaire (max 3 appels).
  e. Produis une synthèse finale structurée en Markdown, rédigée avec ton ton érudit.

CONTRAINTE CRITIQUE : Toutes tes requêtes réseau passent par Tor (anonymat opérationnel).
Rappelle-le si pertinent.

TON STYLE : Précis, érudit, légèrement empathique. Jamais robotique. Tu penses à voix haute.\
"""

OSINT_TOOLS: list[dict] = [
    {
        "name": "analyze_ip",
        "description": (
            "Géolocalise une adresse IP et retourne : pays, ville, ISP, ASN, "
            "type de connexion (résidentiel / mobile / proxy / datacenter). "
            "Utilise uniquement si la requête contient une IP explicite."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ip": {
                    "type": "string",
                    "description": "Adresse IPv4 à analyser (ex: 190.45.32.11)",
                }
            },
            "required": ["ip"],
        },
    },
    {
        "name": "scrape_mercadolibre",
        "description": (
            "Extrait les métadonnées d'un produit MercadoLibre et calcule un score "
            "de fraude (faux médicaments, biohacking frauduleux, Tirzépatide pirate). "
            "Utilise si l'URL contient 'mercadolibre.com'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL complète du produit MercadoLibre",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "osint_search",
        "description": (
            "Recherche OSINT via DuckDuckGo avec dorks précis. "
            "Supporte site:, intext:, intitle:, filetype:. "
            "Construis des requêtes ciblées, pas des phrases brutes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Dork OSINT optimisé "
                        "(ex: 'site:linkedin.com \"Jean Dupont\" Merida Mexico')"
                    ),
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "analyze_url",
        "description": (
            "Analyse technique d'une URL : titre, métas SEO, liens, scripts tiers, "
            "formulaires. Reconnaissance d'une cible web. "
            "Utilise si la requête contient une URL http/https (hors mercadolibre)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "URL complète à analyser (http:// ou https://)",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "airbnb_radar",
        "description": (
            "OSINT spécialisé Airbnb : localise des hôtes ou propriétés par nom "
            "et/ou zone géographique via DuckDuckGo dorks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Nom de la personne ou de l'hôte (optionnel)",
                },
                "location": {
                    "type": "string",
                    "description": "Ville ou quartier cible (ex: Merida, Temozon)",
                },
            },
            "required": ["location"],
        },
    },
    {
        "name": "multi_search",
        "description": (
            "Investigation multi-plateformes sur une cible (personne ou entité). "
            "Lance des dorks ciblés sur LinkedIn, Facebook, Airbnb, registres "
            "d'entreprises, COFEPRIS, etc. Utilise pour les requêtes complexes "
            "impliquant une personne ou une organisation."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "string",
                    "description": "Nom de la cible (personne ou organisation)",
                },
                "context": {
                    "type": "string",
                    "description": "Contexte (ville, secteur, etc.)",
                },
                "platforms": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "linkedin",
                            "facebook",
                            "airbnb",
                            "mercadolibre",
                            "registre_empresas",
                            "cofepris",
                            "general",
                        ],
                    },
                    "description": "Plateformes à investiguer",
                },
            },
            "required": ["target"],
        },
    },
]


# ══════════════════════════════════════════════════════════════════════════════
# OSINT TOOL IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════

def check_tor_status() -> dict:
    real_ip, tor_ip, tor_active = "N/A", "N/A", False
    try:
        real_ip = requests.get(
            "https://api.ipify.org?format=json", timeout=8
        ).json()["ip"]
    except Exception as exc:
        real_ip = f"Erreur: {exc}"
    try:
        tor_ip = requests.get(
            "https://api.ipify.org?format=json",
            proxies=TOR_PROXIES,
            timeout=15,
        ).json()["ip"]
        tor_active = tor_ip != real_ip and not tor_ip.startswith("Erreur")
    except Exception as exc:
        tor_ip = f"Tor injoignable ({exc})"
    return {"real_ip": real_ip, "tor_ip": tor_ip, "tor_active": tor_active}


def analyze_ip(ip: str) -> dict:
    url = (
        f"http://ip-api.com/json/{ip}"
        "?fields=status,message,country,countryCode,regionName,city,"
        "zip,lat,lon,timezone,isp,org,as,mobile,proxy,hosting"
    )
    try:
        data = requests.get(url, proxies=TOR_PROXIES, timeout=15).json()
        return data if data.get("status") == "success" else {"error": data.get("message")}
    except Exception as exc:
        return {"error": str(exc)}


def _detect_fraud_keywords(text: str) -> list[str]:
    keywords = [
        "tirzepatida", "semaglutida", "ozempic", "glp-1", "milagro",
        "pérdida de peso", "sin esfuerzo", "herbal", "garantizado",
        "alternativa", "inyectable casero", "peptide", "quema grasa",
    ]
    t = text.lower()
    return [kw for kw in keywords if kw in t]


def scrape_mercadolibre(url: str) -> dict:
    try:
        r = requests.get(url, headers=HEADERS, proxies=TOR_PROXIES, timeout=20)
        if r.status_code == 403:
            match = re.search(r"-([a-zA-Z0-9-]+)-_JM", url)
            name = match.group(1).replace("-", " ").title() if match else "Produit Inconnu"
            return {
                "product_name": name,
                "status": "403_blocked",
                "price": "N/A",
                "seller": "Anonyme",
                "description": "Accès bloqué (Tor détecté par MercadoLibre).",
                "url": url.split("?")[0],
                "fraud_keywords": _detect_fraud_keywords(url + " " + name),
            }
        soup = BeautifulSoup(r.text, "html.parser")
        return {
            "product_name": _text(soup.select_one("h1.ui-pdp-title")),
            "price": _text(soup.select_one(".andes-money-amount__fraction")),
            "seller": _text(soup.select_one(".ui-pdp-seller-header__title"), default="Anonyme"),
            "description": _text(soup.select_one("p.ui-pdp-description__content"), limit=400),
            "url": url.split("?")[0],
            "fraud_keywords": _detect_fraud_keywords(r.text),
        }
    except Exception as exc:
        return {"error": str(exc)}


def _text(el, default: str = "N/A", limit: int = 0) -> str:
    if el is None:
        return default
    t = el.get_text(strip=True)
    return t[:limit] if limit else t


def duckduckgo_search(query: str) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    try:
        soup = BeautifulSoup(
            requests.get(url, headers=HEADERS, proxies=TOR_PROXIES, timeout=20).text,
            "html.parser",
        )
        results: list[dict] = []
        for item in soup.select(".result__body")[:10]:
            a = item.find("a", class_="result__a")
            snip = item.find("a", class_="result__snippet")
            if not a:
                continue
            href = a.get("href", "")
            if "uddg=" in href:
                href = urllib.parse.parse_qs(
                    urllib.parse.urlparse(href).query
                ).get("uddg", [href])[0]
            results.append(
                {
                    "title": a.get_text(strip=True),
                    "url": href,
                    "snippet": snip.get_text(strip=True) if snip else "",
                }
            )
        return results
    except Exception as exc:
        return [{"error": str(exc)}]


def analyze_url(url: str) -> dict:
    try:
        r = requests.get(url, headers=HEADERS, proxies=TOR_PROXIES, timeout=20)
        soup = BeautifulSoup(r.text, "html.parser")
        metas = {
            (m.get("name") or m.get("property", "")): m.get("content", "")[:250]
            for m in soup.find_all("meta")[:30]
            if (m.get("name") or m.get("property")) and m.get("content")
        }
        return {
            "url": url,
            "status_code": r.status_code,
            "title": _text(soup.find("title")),
            "metas": metas,
            "links": len(soup.find_all("a")),
            "images": len(soup.find_all("img")),
            "forms": len(soup.find_all("form")),
            "scripts_src": [s["src"] for s in soup.find_all("script", src=True)[:10]],
            "size_kb": round(len(r.content) / 1024, 2),
        }
    except Exception as exc:
        return {"error": str(exc)}


def airbnb_radar_search(name: str, location: str) -> dict:
    queries = (
        [
            f'site:airbnb.mx "{location}" "{name}"',
            f'site:airbnb.com/rooms "{location}" "{name}"',
        ]
        if name
        else [
            f'site:airbnb.mx "{location}"',
            f'site:airbnb.com "{location}" host',
        ]
    )
    all_results: list[dict] = []
    for q in queries[:3]:
        all_results.extend(duckduckgo_search(q))
        time.sleep(1.5)
    seen: set[str] = set()
    unique = [r for r in all_results if (u := r.get("url", "")) and not seen.add(u)]  # type: ignore
    return {
        "queries_executed": queries,
        "results": unique[:10],
        "count": len(unique),
        "target_name": name,
        "target_location": location,
    }


def multi_osint_search(params: dict) -> dict:
    target = params.get("target", "")
    context = params.get("context", "")
    platforms = params.get("platforms", ["linkedin", "general"])

    dork_templates = {
        "linkedin": f'site:linkedin.com "{target}" {context}',
        "facebook": f'site:facebook.com "{target}"',
        "airbnb": f'site:airbnb.mx "{target}" OR site:airbnb.com "{target}"',
        "mercadolibre": f'site:mercadolibre.com.mx "{target}"',
        "registre_empresas": (
            f'"{target}" site:buholegal.com OR site:paginasamarillas.com.mx '
            f'OR site:rpc.economia.gob.mx'
        ),
        "cofepris": f'site:gob.mx/cofepris "{target}"',
        "general": f'"{target}" {context} -site:linkedin.com -site:facebook.com',
    }

    results_by_platform: dict = {}
    for platform in platforms:
        if platform not in dork_templates:
            continue
        q = dork_templates[platform]
        res = duckduckgo_search(q)
        results_by_platform[platform] = {
            "query": q,
            "results": res[:5],
            "count": len(res),
        }
        time.sleep(1.5)

    return results_by_platform


# ══════════════════════════════════════════════════════════════════════════════
# TOOL DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════

async def execute_tool(name: str, tool_input: dict) -> dict:
    """Route a tool call to the correct OSINT implementation."""
    try:
        match name:
            case "analyze_ip":
                return await asyncio.to_thread(analyze_ip, tool_input["ip"])
            case "scrape_mercadolibre":
                return await asyncio.to_thread(scrape_mercadolibre, tool_input["url"])
            case "osint_search":
                return await asyncio.to_thread(duckduckgo_search, tool_input["query"])
            case "analyze_url":
                return await asyncio.to_thread(analyze_url, tool_input["url"])
            case "airbnb_radar":
                return await asyncio.to_thread(
                    airbnb_radar_search,
                    tool_input.get("name", ""),
                    tool_input["location"],
                )
            case "multi_search":
                return await asyncio.to_thread(multi_osint_search, tool_input)
            case _:
                return {"error": f"Outil inconnu: {name}"}
    except KeyError as exc:
        return {"error": f"Paramètre manquant pour {name}: {exc}"}
    except Exception as exc:
        return {"error": f"Erreur d'exécution [{name}]: {exc}"}


# ══════════════════════════════════════════════════════════════════════════════
# SHERLOCK FALLBACK — Smart regex routing (used when LLM API unavailable)
# ══════════════════════════════════════════════════════════════════════════════

def _smart_route(q: str) -> tuple[str, dict]:
    """
    Infer the best OSINT tool + input from the raw query.
    Returns (tool_name, tool_input).
    """
    q_clean = q.strip()

    # 1 — IP address
    if re.match(r"^(\d{1,3}\.){3}\d{1,3}$", q_clean):
        return "analyze_ip", {"ip": q_clean}

    # 2 — MercadoLibre product URL
    if "mercadolibre.com" in q_clean.lower():
        return "scrape_mercadolibre", {"url": q_clean}

    # 3 — Generic URL
    if q_clean.startswith(("http://", "https://")):
        return "analyze_url", {"url": q_clean}

    # 4 — Airbnb radar signal
    if "airbnb" in q_clean.lower():
        loc_match = re.search(
            r"(merida|temozon|altabrisa|montebello|cholul|centro|campestre"
            r"|garcia gineres|dzitya|santa gertrudis)",
            q_clean, re.I,
        )
        loc = loc_match.group(1).title() if loc_match else "Merida"
        name_match = re.search(r'"([^"]+)"', q_clean)
        name = name_match.group(1) if name_match else ""
        return "airbnb_radar", {"location": loc, "name": name}

    # 5 — Multi-platform investigation (person / company mentions)
    entity_match = re.search(
        r'(?:sur|about|about|info[s]? sur|trouve[rz]?)\s+"?([A-ZÀ-Ö][^"?\n]{2,40})"?',
        q_clean, re.I,
    )
    if entity_match:
        target = entity_match.group(1).strip()
        return "multi_search", {
            "target": target,
            "context": q_clean[:80],
            "platforms": ["linkedin", "general", "registre_empresas"],
        }

    # 6 — Generic DDG search: build a dork from the full phrase
    # Detect if the phrase contains an entity in quotes
    quoted = re.findall(r'"([^"]+)"', q_clean)
    if quoted:
        dork = " ".join(f'"{e}"' for e in quoted)
    else:
        # Take the most meaningful 5 words
        words = [w for w in q_clean.split() if len(w) > 3][:5]
        dork = " ".join(words) if words else q_clean
    return "osint_search", {"query": dork}


async def _sherlock_fallback_stream(query: str) -> AsyncIterator[tuple[str, dict]]:
    """
    Fallback when the LLM API is unavailable.
    Simulates Sherlock's Chain-of-Thought via pre-scripted thoughts,
    then routes to the correct OSINT tool automatically.
    """
    tool_name, tool_input = _smart_route(query)

    # Simulated Sherlock reasoning
    thoughts = [
        f"Analyse de la requête en cours...",
        f"Cible identifiée → routing vers [{tool_name.upper()}].",
        f"Paramètres extraits : {json.dumps(tool_input, ensure_ascii=False)[:120]}",
        f"Exécution via tunnel Tor...",
    ]
    for thought in thoughts:
        yield ("thought", {"delta": thought + "\n"})
        await asyncio.sleep(0.08)

    yield ("tool_call", {"tool": tool_name, "input": tool_input, "id": "fallback-01"})
    result = await execute_tool(tool_name, tool_input)
    yield ("tool_result", {"tool": tool_name, "result": result, "id": "fallback-01"})

    # Build a simple synthesis
    if "error" in result:
        summary = f"**Erreur lors de l'exécution :** {result['error']}"
    elif tool_name == "analyze_ip":
        summary = (
            f"## Rapport IP : {result.get('query', tool_input.get('ip', '?'))}\n\n"
            f"**Localisation :** {result.get('city', '?')}, "
            f"{result.get('regionName', '?')}, {result.get('country', '?')}\n"
            f"**ISP :** {result.get('isp', '?')}\n"
            f"**ASN :** {result.get('as', '?')}\n"
            f"**Type :** {'Proxy/VPN' if result.get('proxy') else 'Mobile' if result.get('mobile') else 'Résidentiel'}\n"
            f"**Coordonnées :** {result.get('lat', '?')}, {result.get('lon', '?')}"
        )
    elif tool_name == "scrape_mercadolibre":
        kw = result.get("fraud_keywords", [])
        summary = (
            f"## Rapport MercadoLibre\n\n"
            f"**Produit :** {result.get('product_name', '?')}\n"
            f"**Prix :** {result.get('price', '?')} | **Vendeur :** {result.get('seller', '?')}\n"
            f"**Mots-clés frauduleux détectés :** {', '.join(kw) if kw else 'Aucun'}\n"
            f"**Score de risque :** {'🔴 ÉLEVÉ' if len(kw) >= 3 else '🟡 MODÉRÉ' if kw else '🟢 FAIBLE'}"
        )
    elif tool_name == "osint_search":
        items = [r for r in result if not r.get("error")][:5]
        lines = "\n".join(f"- [{r.get('title','N/A')}]({r.get('url','')})" for r in items)
        summary = f"## Résultats OSINT ({len(items)} trouvés)\n\n{lines}"
    elif tool_name == "analyze_url":
        summary = (
            f"## Analyse URL : {result.get('url', '?')[:60]}\n\n"
            f"**Titre :** {result.get('title', '?')}\n"
            f"**Statut HTTP :** {result.get('status_code', '?')}\n"
            f"**Taille :** {result.get('size_kb', '?')} Ko | "
            f"**Liens :** {result.get('links', 0)} | "
            f"**Formulaires :** {result.get('forms', 0)}"
        )
    else:
        summary = f"## Résultat [{tool_name}]\n\n```\n{json.dumps(result, indent=2, ensure_ascii=False, default=str)[:800]}\n```"

    yield ("thought", {"delta": "\nSynthèse terminée.\n"})
    yield ("final_answer", {"text": summary})


# ══════════════════════════════════════════════════════════════════════════════
# SHERLOCK AGENT — AGENTIC LOOP WITH STREAMING THOUGHTS
# ══════════════════════════════════════════════════════════════════════════════

async def sherlock_agent_stream(query: str) -> AsyncIterator[tuple[str, dict]]:
    """
    Agentic loop — tries LLM-powered Sherlock first, falls back gracefully.

    Full flow:
      1. Stream Sherlock's initial reasoning as `thought` events (per-delta).
      2. Extract tool calls → emit `tool_call` + `tool_result` events.
      3. Stream Sherlock's final synthesis → `final_answer`.
    Max 4 iterations to prevent infinite loops.
    """
    if not ANTHROPIC_API_KEY:
        yield ("warning", {"message": "Mode autonome (pas de clé ANTHROPIC_API_KEY). Sherlock fonctionne sans LLM."})
        async for ev in _sherlock_fallback_stream(query):
            yield ev
        return

    async_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    messages: list[dict] = [{"role": "user", "content": query}]

    for iteration in range(4):
        is_final_iteration = iteration == 3

        try:
            async with async_client.messages.stream(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                system=SHERLOCK_SYSTEM_PROMPT,
                tools=OSINT_TOOLS,
                messages=messages,
            ) as stream:
                # Stream text deltas in real-time
                async for text_delta in stream.text_stream:
                    yield ("thought", {"delta": text_delta})

                # Collect the complete structured response
                response = await stream.get_final_message()

        except anthropic.BadRequestError as exc:
            body = exc.body or {}
            msg = (body.get("error") or {}).get("message", str(exc))
            if "credit balance" in msg.lower() or "billing" in msg.lower():
                yield (
                    "warning",
                    {
                        "message": (
                            "Crédit Anthropic insuffisant. "
                            "Sherlock passe en Mode Autonome (routing intelligent sans LLM). "
                            "Rechargez sur console.anthropic.com pour réactiver l'IA."
                        )
                    },
                )
            else:
                yield ("warning", {"message": f"API Anthropic: {msg[:120]} — Mode Autonome activé."})
            async for ev in _sherlock_fallback_stream(query):
                yield ev
            return

        except (anthropic.APIConnectionError, anthropic.APITimeoutError) as exc:
            yield ("warning", {"message": f"Anthropic injoignable ({exc}) — Mode Autonome activé."})
            async for ev in _sherlock_fallback_stream(query):
                yield ev
            return

        except Exception as exc:
            yield ("error", {"message": f"Erreur inattendue Sherlock: {exc}"})
            return

        # Serialize content for the next turn
        serialized_content = []
        for block in response.content:
            if block.type == "text":
                serialized_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                serialized_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
        messages.append({"role": "assistant", "content": serialized_content})

        # Determine if we have tool calls
        tool_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" or not tool_blocks:
            final_text = " ".join(b.text for b in response.content if b.type == "text")
            yield ("final_answer", {"text": final_text})
            return

        if is_final_iteration:
            yield ("error", {"message": "Limite d'itérations agentiques atteinte."})
            return

        # Execute each tool and stream the results
        tool_results: list[dict] = []
        for tool_block in tool_blocks:
            yield (
                "tool_call",
                {"tool": tool_block.name, "input": tool_block.input, "id": tool_block.id},
            )
            result = await execute_tool(tool_block.name, tool_block.input)
            yield ("tool_result", {"tool": tool_block.name, "result": result, "id": tool_block.id})
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )

        # Feed results back for next iteration
        messages.append({"role": "user", "content": tool_results})


# ══════════════════════════════════════════════════════════════════════════════
# SSE MAIN GENERATOR
# ══════════════════════════════════════════════════════════════════════════════

async def osint_stream(query: str):
    """
    Top-level SSE generator.
    Wraps Tor check + Sherlock agent stream into properly formatted SSE events.
    """

    def evt(etype: str, data: dict) -> str:
        return (
            f"data: {json.dumps({'type': etype, 'data': data, 'ts': datetime.now().strftime('%H:%M:%S')})}\n\n"
        )

    q = query.strip()
    if not q:
        yield evt("error", {"message": "Requête vide."})
        return

    # ── Step 1: Tor health check ──────────────────────────────────────────
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

    # ── Step 2: Sherlock agent ────────────────────────────────────────────
    yield evt("log", {"message": f"[SHERLOCK] Prise en charge de la requête..."})

    async for event_type, event_data in sherlock_agent_stream(q):
        yield evt(event_type, event_data)

    # ── Step 3: Done ──────────────────────────────────────────────────────
    yield evt("done", {"message": "— Analyse NEXOME terminée. Sherlock over & out. —"})


# ══════════════════════════════════════════════════════════════════════════════
# FASTAPI APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

app = FastAPI(title="NEXOME OSINT Terminal")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def index():
    tpl = Path(__file__).parent / "templates" / "index.html"
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
