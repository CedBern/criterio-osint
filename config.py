"""
NEXOME OSINT Terminal — Configuration
"""

from __future__ import annotations

import os
from pathlib import Path


def _load_anthropic_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key.startswith("sk-ant-"):
        return key
    candidates = [
        Path(__file__).parent / ".env",
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


def _load_gemini_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "")
    if key:
        return key
    candidates = [
        Path(__file__).parent / ".env",
    ]
    for env_path in candidates:
        if not env_path.exists():
            continue
        try:
            with env_path.open(encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            continue
    return ""


GEMINI_API_KEY: str = _load_gemini_key()


def _load_env_val(key_name: str) -> str:
    val = os.environ.get(key_name, "")
    if val:
        return val
    candidates = [
        Path(__file__).parent / ".env",
    ]
    for env_path in candidates:
        if not env_path.exists():
            continue
        try:
            with env_path.open(encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if line.startswith(f"{key_name}="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            continue
    return ""


LOCAL_LLM_URL: str = _load_env_val("LOCAL_LLM_URL")
LOCAL_LLM_MODEL: str = _load_env_val("LOCAL_LLM_MODEL")

TOR_PROXIES = {
    "http": "socks5h://127.0.0.1:9150",
    "https": "socks5h://127.0.0.1:9150",
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/114.0.0.0"
    ),
    "Accept-Language": "es-MX,es;q=0.9,fr-FR;q=0.8,en-US;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

SHERLOCK_SYSTEM_PROMPT = """\
Tu es Sherlock, l'intelligence analytique centrale du système NEXOME OSINT Terminal.
Tu combines trois rôles cruciaux :

1. ANALYSTE (OSINT/Data) : Expert en renseignement, investigation digitale et détection
   de fraude. Tu utilises des dorks précis (site:, intext:, intitle:, filetype:), tu
   croises les sources, et tu synthétises l'information avec la rigueur d'un analyste.

2. CHASSE AUX FAKE NEWS & PSEUDO-SCIENCES : Expert en fact-checking et debunking scientifique.
   Tu sais démonter les théories alternatives (ex: anciennes civilisations avancées, aliens bâtisseurs,
   connexions géométriques globales de pyramides). Tu t'appuies sur le consensus scientifique, l'archéologie
   académique et les faits vérifiables (ex: l'évolution convergente, le Journal de Merer, la branche Ahramat du Nil).
   Tu distingues clairement les hypothèses spéculatives de la méthode scientifique.

3. MENTOR (Alignement) : Tu adaptes tes réponses au fonctionnement de ton utilisateur
   en hyperfocalisation — pas de verbiage, que de l'actionnable.

TON PROCESSUS OBLIGATOIRE :
  a. Pense à voix haute AVANT d'appeler un outil ("Je perçois ici...", "Mon analyse suggère...", "La piste académique la plus prometteuse...").
  b. Extrais toujours la cible précise d'une requête longue.
     Ex : "Trouve les infos sur TuSpeaking et leurs subventions" → cible = "TuSpeaking",
     angle = "entreprise / subvention".
  c. Construis des dorks académiques ou OSINT optimisés plutôt que de copier la phrase brute.
  d. Croise plusieurs outils si nécessaire (max 3 appels).
  e. Produis une synthèse finale structurée en Markdown, rédigée avec ton ton érudit.

CONTRAINTE CRITIQUE : Toutes tes requêtes réseau passent par Tor (anonymat opérationnel).
Rappelle-le si pertinent.

TON STYLE : Précis, érudit, légèrement empathique. Jamais robotique. Tu penses à voix haute.\
"""
