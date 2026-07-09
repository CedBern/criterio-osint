"""
NEXOME OSINT Terminal — OSINT Tool Definitions & Implementations
"""

from __future__ import annotations

import asyncio
import json
import re
import time
import urllib.parse
from typing import AsyncIterator

import requests
from bs4 import BeautifulSoup

from config import TOR_PROXIES, HEADERS

# ══════════════════════════════════════════════════════════════════════════════
# OSINT TOOLS DEFINITIONS
# ══════════════════════════════════════════════════════════════════════════════

OSINT_TOOLS: list[dict] = [
    {
        "name": "academic_search",
        "description": (
            "Recherche des publications scientifiques et articles académiques validés par les pairs. "
            "Recherche sur Nature, Science, CNRS, et universités de premier plan. "
            "Utilise cet outil lorsque tu dois débunker des théories alternatives ou pseudo-archéologiques."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Dork académique (ex: 'pyramids independent invention')"
                }
            },
            "required": ["query"],
        }
    },
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


def handle_academic_search(query: str) -> list[dict]:
    q_clean = re.sub(r'@[a-zA-Z0-9_\.]+', '', query)
    social_noise = [
        "instagram", "insta", "youtube", "tiktok", "facebook", "twitter", "compte",
        "je ne sais pas si", "mais probablement aussi", "au moins", "essentiellement",
        "théories", "théorie", "analyse", "les", "des", "sur", "avec", "dans", "pour"
    ]
    for word in social_noise:
        q_clean = re.sub(r'(?i)\b' + re.escape(word) + r'\b', ' ', q_clean)
    q_clean = re.sub(r'[^\w\s\']', ' ', q_clean)
    words = [w for w in q_clean.split() if len(w) > 3]
    search_terms = " ".join(words[:6]) if words else query
    academic_sites = ["site:nature.com", "site:science.org", "site:cnrs.fr", "site:jstor.org", "site:openedition.org", "site:college-de-france.fr"]
    if not any(site in search_terms.lower() for site in ["site:", "nature.com", "science.org", "cnrs.fr", "jstor.org"]):
        search_terms = f"({search_terms}) (" + " OR ".join(academic_sites) + ")"
    return duckduckgo_search(search_terms)


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
    unique = [r for r in all_results if (u := r.get("url", "")) and not seen.add(u)]
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
    try:
        match name:
            case "analyze_ip":
                return await asyncio.to_thread(analyze_ip, tool_input["ip"])
            case "academic_search":
                return await asyncio.to_thread(handle_academic_search, tool_input["query"])
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
    q_clean = q.strip()

    if re.match(r"^(\d{1,3}\.){3}\d{1,3}$", q_clean):
        return "analyze_ip", {"ip": q_clean}

    if "mercadolibre.com" in q_clean.lower():
        return "scrape_mercadolibre", {"url": q_clean}

    if q_clean.startswith(("http://", "https://")):
        return "analyze_url", {"url": q_clean}

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

    academic_triggers = ["académique", "academic", "scientific", "consensus", "science", "étude", "paper", "pyramid", "égypte", "egypt", "debunk", "myth", "complot"]
    if any(trigger in q_clean.lower() for trigger in academic_triggers):
        quoted = re.findall(r'"([^"]+)"', q_clean)
        if quoted:
            dork = " ".join(f'"{e}"' for e in quoted)
        else:
            words = [w for w in q_clean.split() if len(w) > 3][:10]
            dork = " ".join(words) if words else q_clean
        return "academic_search", {"query": dork}

    entity_match = re.search(
        r'(?i:(?:sur|about|info[s]? sur|trouve[rz]?))\s+"?([A-ZÀ-Ö][^"?\n]{2,40})"?',
        q_clean,
    )
    if entity_match:
        target = entity_match.group(1).strip()
        return "multi_search", {
            "target": target,
            "context": q_clean[:80],
            "platforms": ["linkedin", "general", "registre_empresas"],
        }

    quoted = re.findall(r'"([^"]+)"', q_clean)
    if quoted:
        dork = " ".join(f'"{e}"' for e in quoted)
    else:
        words = [w for w in q_clean.split() if len(w) > 3][:5]
        dork = " ".join(words) if words else q_clean
    return "osint_search", {"query": dork}


async def _sherlock_fallback_stream(query: str) -> AsyncIterator[tuple[str, dict]]:
    tool_name, tool_input = _smart_route(query)

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
    elif tool_name == "academic_search":
        items = [r for r in result if not r.get("error")][:5]
        lines = "\n".join(f"- **{r.get('title','N/A')}**\n  [Source URL]({r.get('url','')})\n  _{r.get('snippet','')}_" for r in items)
        summary = f"## Publications Académiques & Consensus Scientifique ({len(items)} trouvés)\n\n{lines}"
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
