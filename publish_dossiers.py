import os
import re
import json
import datetime
from pathlib import Path

_BASE = Path(__file__).parent

# Config — chemins relatifs portables
dossiers_dir = _BASE / "documents_debunking"
html_path = _BASE / "website" / "index.html"
website_dir = _BASE / "website"

# Optionnel : synchronisation cache Open Design (variable d'environnement)
_OD_CACHE = os.environ.get("NEXOME_OD_CACHE", "")

def md_to_html(md_text):
    # Check if the block is a markdown table
    if md_text.strip().startswith('|'):
        lines = [line.strip() for line in md_text.strip().split('\n') if line.strip()]
        html_rows = []
        has_header = False
        has_separator = len(lines) > 1 and all(c in '|:- ' for c in lines[1])
        for idx, line in enumerate(lines):
            if idx == 1 and has_separator:
                continue
            cells = [c.strip() for c in line.split('|')]
            if line.startswith('|'):
                cells = cells[1:]
            if line.endswith('|') and cells:
                cells = cells[:-1]
            if idx == 0:
                formatted_cells = []
                for cell in cells:
                    cell = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', cell)
                    cell = re.sub(r'\*(.*?)\*', r'<em>\1</em>', cell)
                    formatted_cells.append(f'<th>{cell}</th>')
                html_rows.append(f'<thead><tr>{"".join(formatted_cells)}</tr></thead><tbody>')
                has_header = True
            else:
                formatted_cells = []
                for cell in cells:
                    cell = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', cell)
                    cell = re.sub(r'\*(.*?)\*', r'<em>\1</em>', cell)
                    formatted_cells.append(f'<td>{cell}</td>')
                html_rows.append(f'<tr>{"".join(formatted_cells)}</tr>')
        if has_header:
            html_rows.append('</tbody>')
        return f'<div class="table-responsive"><table class="styled-table">{"".join(html_rows)}</table></div>'

    # Remplacer les titres
    html = re.sub(r'^###\s+(.+)$', r'<h4>\1</h4>', md_text, flags=re.MULTILINE)
    html = re.sub(r'^##\s+(.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    html = re.sub(r'^#\s+(.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    
    # Images (ex: ![alt](src))
    html = re.sub(r'!\[(.*?)\]\((.*?)\)', r'<div class="article-media"><img src="\2" alt="\1"><span class="media-caption">\1</span></div>', html)
    
    # Liens: [text](url) -> <a href="url" target="_blank" rel="noopener noreferrer">text</a>
    html = re.sub(r'(?<!\!)\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', html)
    
    # Blockquotes
    html = re.sub(r'^>\s+(.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
    
    # Listes à puces (AVANT le gras et l'italique pour éviter les conflits d'astérisques !)
    html = re.sub(r'^\*\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'^-\s+(.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    
    # Encadrer les listes
    html = re.sub(r'(<li>.*?</li>\s*)+', lambda m: f'<ul>{m.group(0)}</ul>', html, flags=re.DOTALL)
    
    # Gras et Italique
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    
    # Formater les paragraphes
    paragraphs = []
    for block in html.split('\n\n'):
        block = block.strip()
        if not block:
            continue
        if block == '---':
            paragraphs.append('<hr>')
        elif block.startswith('<h') or block.startswith('<ul') or block.startswith('<blockquote') or block.startswith('<div') or block.startswith('<hr'):
            paragraphs.append(block)
        else:
            block = block.replace('\n', '<br>')
            block = re.sub(r'<br>\s*(<ul>|</ul>|<li>|</li>|<div|</div>|<blockquote>|</blockquote>|<ol>|</ol>|<hr>|<table>|</table>|<tr>|</tr>|<th>|</th>|<td>|</td>)', r'\1', block)
            block = re.sub(r'(<ul>|</ul>|<li>|</li>|<div|</div>|<blockquote>|</blockquote>|<ol>|</ol>|<hr>|<table>|</table>|<tr>|</tr>|<th>|</th>|<td>|</td>)\s*<br>', r'\1', block)
            
            if any(tag in block for tag in ['<ul>', '<blockquote>', '<div', '<ol>', '<table']):
                block_formatted = f'<p>{block}</p>'
                block_formatted = block_formatted.replace('<ul>', '</p><ul>').replace('</ul>', '</ul><p>')
                block_formatted = block_formatted.replace('<ol>', '</p><ol>').replace('</ol>', '</ol><p>')
                block_formatted = block_formatted.replace('<blockquote>', '</p><blockquote>').replace('</blockquote>', '</blockquote><p>')
                block_formatted = block_formatted.replace('<div', '</p><div').replace('</div>', '</div><p>')
                block_formatted = block_formatted.replace('<table', '</p><table').replace('</table>', '</table><p>')
                block_formatted = re.sub(r'<p>\s*</p>', '', block_formatted)
                paragraphs.append(block_formatted)
            else:
                paragraphs.append(f'<p>{block}</p>')
            
    return '\n'.join(paragraphs)

def highlight_glossary(html_text, glossary, lang="fr"):
    parts = re.split(r'(<[^>]+>)', html_text)
    
    for i in range(len(parts)):
        if not parts[i].startswith('<'):
            for word, word_data in glossary.items():
                search_word = word
                if isinstance(word_data, dict):
                    if lang == "es" and "es" in word_data:
                        search_word = word_data["es"]
                    elif lang == "en" and "en" in word_data:
                        search_word = word_data["en"]
                else:
                    if lang != "fr":
                        continue
                
                options = [o.strip() for o in search_word.split("/") if o.strip()]
                for opt in options:
                    pattern = r'\b(' + re.escape(opt) + r')\b'
                    parts[i] = re.sub(pattern, rf'<span class="glossary-term" data-word="{word}">\1</span>', parts[i], flags=re.IGNORECASE)
                
    return "".join(parts)

def generate_multilingual_html(content_fr, content_es, content_en, glossary):
    blocks_fr = content_fr.split("\n\n")
    blocks_es = content_es.split("\n\n") if content_es else []
    blocks_en = content_en.split("\n\n") if content_en else []
    
    max_len = max(len(blocks_fr), len(blocks_es), len(blocks_en))
    html_blocks = []
    
    for i in range(max_len):
        b_fr = blocks_fr[i].strip() if i < len(blocks_fr) else ""
        b_es = blocks_es[i].strip() if i < len(blocks_es) else ""
        b_en = blocks_en[i].strip() if i < len(blocks_en) else ""
        
        if not b_fr:
            continue
            
        html_fr = md_to_html(b_fr)
        html_es = md_to_html(b_es) if b_es else ""
        html_en = md_to_html(b_en) if b_en else ""
        
        is_sources = "Sources" in b_fr and ("Référence" in b_fr or "Reference" in b_fr or "Referencia" in b_fr)
        
        if b_fr.startswith("![") or b_fr.startswith("<div class=\"article-media\""):
            html_blocks.append(f'<div class="media-block">{html_fr}</div>')
        elif is_sources:
            html_blocks.append(f"""
            <div class="sources-wrapper">
              <div class="sources-fr">{html_fr}</div>
              <div class="sources-es" style="display:none;">{html_es}</div>
              <div class="sources-en" style="display:none;">{html_en}</div>
            </div>""")
        else:
            if glossary:
                html_fr = highlight_glossary(html_fr, glossary, 'fr')
                html_es = highlight_glossary(html_es, glossary, 'es') if html_es else ""
                html_en = highlight_glossary(html_en, glossary, 'en') if html_en else ""
                
            html_blocks.append(f"""
            <div class="paragraph-block">
              <div class="paragraph-fr">{html_fr}</div>
              <div class="paragraph-es" style="display:none;">{html_es}</div>
              <div class="paragraph-en" style="display:none;">{html_en}</div>
              <div class="paragraph-actions" style="display:none;">
                <button class="btn-translate-es" title="Traducción al español">🇲🇽</button>
                <button class="btn-translate-en" title="English translation">🇬🇧</button>
              </div>
            </div>""")
            
    return "\n".join(html_blocks)

def get_cover_image(base_name: str, content_fr: str = "") -> str:
    images_dir = _BASE / "website" / "images"
    slug_image = images_dir / f"{base_name}.webp"
    if slug_image.exists():
        return f"images/{base_name}.webp"
    if content_fr:
        m = re.search(r'!\[.*?\]\((.*?)\)', content_fr)
        if m:
            return m.group(1)
    return "images/Piramides_de_Guiza.jpg"

def parse_lang_meta(filepath):
    if not os.path.exists(filepath):
        return "", ""
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else ""
    
    paragraphs = [p.strip() for p in content.split("\n") if p.strip() and not p.startswith("#") and not p.lower().startswith(("tags:", "etiquetas:"))]
    summary = ""
    for p in paragraphs:
        if len(p) > 40 and not p.startswith("Source:") and not p.startswith("*") and not p.startswith("!"):
            summary = p[:180] + "..." if len(p) > 180 else p
            break
    return title, summary

def extract_tags_from_file(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    tags_match = re.search(r"^(?:Tags|Etiquetas):\s+(.+)$", content, re.MULTILINE | re.IGNORECASE)
    return [t.strip() for t in tags_match.group(1).split(",")] if tags_match else []

def main():
    print("=== NEXOME MAGAZINE PUBLISHER ===")
    
    if not os.path.exists(dossiers_dir):
        print(f"Directory {dossiers_dir} does not exist.")
        return
        
    files = os.listdir(dossiers_dir)
    dossiers_map = {}
    
    for f in files:
        if f.endswith(".fr.md"):
            base = f[:-6]
            dossiers_map[base] = {
                "type": "multilingual",
                "fr": os.path.join(dossiers_dir, f),
                "es": os.path.join(dossiers_dir, base + ".es.md"),
                "en": os.path.join(dossiers_dir, base + ".en.md"),
                "json": os.path.join(dossiers_dir, base + ".didactic.json")
            }
        elif f.endswith(".md") and not f.endswith(".es.md") and not f.endswith(".en.md") and not f.endswith(".fr.md"):
            base = f[:-3]
            dossiers_map[base] = {
                "type": "monolingual",
                "fr": os.path.join(dossiers_dir, f)
            }
            
    if not dossiers_map:
        print("No dossiers found to publish.")
        return
        
    ORDER = {
        "dater_l_impossible_comment_la_science_determine_l_age_des_pyramides": 4,
        "les_pyramides_de_gizeh_bloc_de_pierre_ou_beton_antique": 3,
        "le_mirage_de_la_connexion_globale": 2,
        "le_secret_des_batisseurs": 1
    }
    sorted_bases = sorted(
        dossiers_map.keys(),
        key=lambda b: ORDER.get(b, 0),
        reverse=True
    )
    
    print(f"Found {len(sorted_bases)} dossiers to publish.")
    
    dossiers_data = []
    for idx, base in enumerate(sorted_bases):
        info = dossiers_map[base]
        
        title_fr, summary_fr = parse_lang_meta(info["fr"])
        tags_fr = extract_tags_from_file(info["fr"])
        
        title_es, summary_es = parse_lang_meta(info["es"]) if "es" in info else ("", "")
        tags_es = extract_tags_from_file(info["es"]) if "es" in info else []
        
        title_en, summary_en = parse_lang_meta(info["en"]) if "en" in info else ("", "")
        tags_en = extract_tags_from_file(info["en"]) if "en" in info else []
        
        if not title_fr:
            title_fr = base.replace("_", " ")
        if not title_es:
            title_es = title_fr
        if not title_en:
            title_en = title_fr
        if not summary_fr:
            summary_fr = "Analyse scientifique et contexte historique."
        if not summary_es:
            summary_es = "Análisis científico y contexto histórico."
        if not summary_en:
            summary_en = "Scientific analysis and historical context."
            
        with open(info["fr"], "r", encoding="utf-8", errors="ignore") as f:
            content_fr = f.read()
            
        cover = get_cover_image(base, content_fr)
        year = datetime.datetime.now().year
            
        content_es = ""
        content_en = ""
        didactic_config = {}
        
        if info["type"] == "multilingual":
            if os.path.exists(info["es"]):
                with open(info["es"], "r", encoding="utf-8", errors="ignore") as f:
                    content_es = f.read()
            if os.path.exists(info["en"]):
                with open(info["en"], "r", encoding="utf-8", errors="ignore") as f:
                    content_en = f.read()
            if os.path.exists(info["json"]):
                try:
                    with open(info["json"], "r", encoding="utf-8") as f:
                        didactic_config = json.load(f)
                    if "glossary" not in didactic_config:
                        print(f"Warning: {info['json']} missing 'glossary' - no clickable terms")
                    if not any(k in didactic_config for k in ["quiz", "quiz_a2", "quiz_b1", "quiz_b2"]):
                        print(f"Warning: {info['json']} missing 'quiz' - no FLE questionnaire")
                except Exception as exc:
                    print(f"Error reading {info['json']}: {exc}")
                    
        level = didactic_config.get("level", "Lectura General")
        LEVEL_LABELS = {
            "B1/B2 (Intermedio)": {"fr": "B1/B2 (Interm\u00e9diaire)", "es": "B1/B2 (Intermedio)", "en": "B1/B2 (Intermediate)"},
            "Lectura General": {"fr": "Lecture G\u00e9n\u00e9rale", "es": "Lectura General", "en": "General Reading"},
        }
        level_fr = LEVEL_LABELS.get(level, {}).get("fr", level)
        level_es = LEVEL_LABELS.get(level, {}).get("es", level)
        level_en = LEVEL_LABELS.get(level, {}).get("en", level)
        glossary = didactic_config.get("glossary", {})
        quiz_a2 = didactic_config.get("quiz_a2", [])
        quiz_a2_es = didactic_config.get("quiz_a2_es", [])
        quiz_a2_en = didactic_config.get("quiz_a2_en", [])
        
        quiz_b1 = didactic_config.get("quiz_b1", [])
        quiz_b1_es = didactic_config.get("quiz_b1_es", [])
        quiz_b1_en = didactic_config.get("quiz_b1_en", [])
        
        quiz_b2 = didactic_config.get("quiz_b2", [])
        quiz_b2_es = didactic_config.get("quiz_b2_es", [])
        quiz_b2_en = didactic_config.get("quiz_b2_en", [])
        
        if info["type"] == "multilingual":
            full_html = generate_multilingual_html(content_fr, content_es, content_en, glossary)
        else:
            full_html = md_to_html(content_fr)
            
        glossary_attr = json.dumps(glossary, ensure_ascii=False).replace("'", "&apos;")
        quiz_a2_attr = json.dumps(quiz_a2, ensure_ascii=False).replace("'", "&apos;")
        quiz_a2_es_attr = json.dumps(quiz_a2_es, ensure_ascii=False).replace("'", "&apos;")
        quiz_a2_en_attr = json.dumps(quiz_a2_en, ensure_ascii=False).replace("'", "&apos;")
        
        quiz_b1_attr = json.dumps(quiz_b1, ensure_ascii=False).replace("'", "&apos;")
        quiz_b1_es_attr = json.dumps(quiz_b1_es, ensure_ascii=False).replace("'", "&apos;")
        quiz_b1_en_attr = json.dumps(quiz_b1_en, ensure_ascii=False).replace("'", "&apos;")
        
        quiz_b2_attr = json.dumps(quiz_b2, ensure_ascii=False).replace("'", "&apos;")
        quiz_b2_es_attr = json.dumps(quiz_b2_es, ensure_ascii=False).replace("'", "&apos;")
        quiz_b2_en_attr = json.dumps(quiz_b2_en, ensure_ascii=False).replace("'", "&apos;")
        
        title_fr_esc = title_fr.replace('"', '&quot;')
        title_es_esc = title_es.replace('"', '&quot;')
        title_en_esc = title_en.replace('"', '&quot;')
        summary_fr_esc = summary_fr.replace('"', '&quot;')
        summary_es_esc = summary_es.replace('"', '&quot;')
        summary_en_esc = summary_en.replace('"', '&quot;')
        
        dossiers_data.append({
            "title_fr": title_fr_esc,
            "title_es": title_es_esc,
            "title_en": title_en_esc,
            "summary_fr": summary_fr_esc,
            "summary_es": summary_es_esc,
            "summary_en": summary_en_esc,
            "cover": cover,
            "year": year,
            "level": level,
            "level_fr": level_fr,
            "level_es": level_es,
            "level_en": level_en,
            "glossary_attr": glossary_attr,
            "quiz_a2_attr": quiz_a2_attr,
            "quiz_a2_es_attr": quiz_a2_es_attr,
            "quiz_a2_en_attr": quiz_a2_en_attr,
            "quiz_b1_attr": quiz_b1_attr,
            "quiz_b1_es_attr": quiz_b1_es_attr,
            "quiz_b1_en_attr": quiz_b1_en_attr,
            "quiz_b2_attr": quiz_b2_attr,
            "quiz_b2_es_attr": quiz_b2_es_attr,
            "quiz_b2_en_attr": quiz_b2_en_attr,
            "tags_fr": tags_fr,
            "tags_es": tags_es,
            "tags_en": tags_en,
            "full_html": full_html
        })
        
    # 1. Générer le Featured Article
    feat = dossiers_data[0]
    feat_tags_fr_attr = ",".join(feat['tags_fr'])
    feat_tags_es_attr = ",".join(feat['tags_es'])
    feat_tags_en_attr = ",".join(feat['tags_en'])
    feat_tags_badges = "".join([f'<span class="tag-badge">{t}</span>' for t in feat['tags_fr']])
    
    featured_html = f"""
      <article class="featured-story" tabindex="0" 
               data-title-fr="{feat['title_fr']}" data-title-es="{feat['title_es']}" data-title-en="{feat['title_en']}"
               data-summary-fr="{feat['summary_fr']}" data-summary-es="{feat['summary_es']}" data-summary-en="{feat['summary_en']}"
               data-level-fr="{feat['level_fr']}" data-level-es="{feat['level_es']}" data-level-en="{feat['level_en']}"
               data-tags-fr="{feat_tags_fr_attr}" data-tags-es="{feat_tags_es_attr}" data-tags-en="{feat_tags_en_attr}">
        <div class="featured-img-container">
          <img src="{feat['cover']}" alt="{feat['title_fr']}" class="featured-img">
        </div>
        <div class="featured-body">
          <div class="story-meta">
            <span class="story-category-label" data-category="featured">Investigaci&oacute;n Principal</span>
            <span class="story-level"> &mdash; {feat['level_es']}</span>
            <span class="story-date">Julio 2026</span>
          </div>
          <h2 class="story-title">{feat['title_fr']}</h2>
          <p class="story-excerpt">{feat['summary_fr']}</p>
          <div class="card-tags">{feat_tags_badges}</div>
          <div class="story-footer">
            <span class="read-more-btn" data-readmore="featured">Leer investigaci&oacute;n completa &rarr;</span>
          </div>
          <div class="dcell-content" style="display:none;" 
               data-level="{feat['level']}"
               data-glossary='{feat['glossary_attr']}'
               data-quiz-a2-fr='{feat['quiz_a2_attr']}'
               data-quiz-a2-es='{feat['quiz_a2_es_attr']}'
               data-quiz-a2-en='{feat['quiz_a2_en_attr']}'
               data-quiz-b1-fr='{feat['quiz_b1_attr']}'
               data-quiz-b1-es='{feat['quiz_b1_es_attr']}'
               data-quiz-b1-en='{feat['quiz_b1_en_attr']}'
               data-quiz-b2-fr='{feat['quiz_b2_attr']}'
               data-quiz-b2-es='{feat['quiz_b2_es_attr']}'
               data-quiz-b2-en='{feat['quiz_b2_en_attr']}'>
            {feat['full_html']}
          </div>
        </div>
      </article>"""
      
    cards_html_list = []
    for card in dossiers_data[1:]:
        card_tags_fr_attr = ",".join(card['tags_fr'])
        card_tags_es_attr = ",".join(card['tags_es'])
        card_tags_en_attr = ",".join(card['tags_en'])
        card_tags_badges = "".join([f'<span class="tag-badge">{t}</span>' for t in card['tags_fr']])
        
        card_html = f"""
        <article class="magazine-card reveal" tabindex="0"
                 data-title-fr="{card['title_fr']}" data-title-es="{card['title_es']}" data-title-en="{card['title_en']}"
                 data-summary-fr="{card['summary_fr']}" data-summary-es="{card['summary_es']}" data-summary-en="{card['summary_en']}"
                 data-level-fr="{card['level_fr']}" data-level-es="{card['level_es']}" data-level-en="{card['level_en']}"
                 data-tags-fr="{card_tags_fr_attr}" data-tags-es="{card_tags_es_attr}" data-tags-en="{card_tags_en_attr}">
          <div class="card-img-container">
            <img src="{card['cover']}" alt="{card['title_fr']}" class="card-img">
          </div>
          <div class="card-body">
            <div class="card-meta">
              <span class="card-category-label" data-category="doc">Documento</span>
              <span class="card-level"> &mdash; {card['level_es']}</span>
              <span class="card-date">{card['year']}</span>
            </div>
            <h3 class="card-title">{card['title_fr']}</h3>
            <p class="card-excerpt">{card['summary_fr']}</p>
            <div class="card-tags">{card_tags_badges}</div>
            <div class="card-footer">
              <span class="read-more-link" data-readmore="card">Leer artículo &rarr;</span>
            </div>
            <div class="dcell-content" style="display:none;" 
                 data-level="{card['level']}"
                 data-glossary='{card['glossary_attr']}'
                 data-quiz-a2-fr='{card['quiz_a2_attr']}'
                 data-quiz-a2-es='{card['quiz_a2_es_attr']}'
                 data-quiz-a2-en='{card['quiz_a2_en_attr']}'
                 data-quiz-b1-fr='{card['quiz_b1_attr']}'
                 data-quiz-b1-es='{card['quiz_b1_es_attr']}'
                 data-quiz-b1-en='{card['quiz_b1_en_attr']}'
                 data-quiz-b2-fr='{card['quiz_b2_attr']}'
                 data-quiz-b2-es='{card['quiz_b2_es_attr']}'
                 data-quiz-b2-en='{card['quiz_b2_en_attr']}'>
              {card['full_html']}
            </div>
          </div>
        </article>"""
        cards_html_list.append(card_html)
        
    cards_html = "\n".join(cards_html_list)

    if not os.path.exists(html_path):
        print(f"HTML file {html_path} not found.")
        return
        
    with open(html_path, "r", encoding="utf-8") as f:
        html_code = f.read()

    try:
        parts = html_code.split("<!-- FEATURED_START -->")
        if len(parts) < 2:
            raise ValueError("Placeholder <!-- FEATURED_START --> introuvable.")
        subparts = parts[1].split("<!-- FEATURED_END -->")
        if len(subparts) < 2:
            raise ValueError("Placeholder <!-- FEATURED_END --> introuvable.")
        html_code = parts[0] + "<!-- FEATURED_START -->" + featured_html + "\n      <!-- FEATURED_END -->" + subparts[1]
    except Exception as e:
        print(f"Warning Featured Replace: {e}")

    try:
        parts = html_code.split("<!-- DOSSIERS_START -->")
        if len(parts) < 2:
            raise ValueError("Placeholder <!-- DOSSIERS_START --> introuvable.")
        subparts = parts[1].split("<!-- DOSSIERS_END -->")
        if len(subparts) < 2:
            raise ValueError("Placeholder <!-- DOSSIERS_END --> introuvable.")
        html_code = parts[0] + "<!-- DOSSIERS_START -->" + cards_html + "\n      <!-- DOSSIERS_END -->" + subparts[1]
    except Exception as e:
        print(f"Error Dossiers Replace: {e}")
        return
        
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_code)
        
    print("OK: index.html successfully updated with your multilingual magazine layout!")

    # Copier dans le cache Open Design (optionnel, via NEXOME_OD_CACHE)
    if _OD_CACHE:
        od_path = Path(_OD_CACHE)
        try:
            od_path.parent.mkdir(parents=True, exist_ok=True)
            od_path.write_text(html_code, encoding="utf-8")
            print(f"OK: Open Design cache synced → {_OD_CACHE}")
        except Exception as e:
            print(f"Warning Open Design cache sync failed: {e}")

    # Git commit (optionnel, seulement si le répo existe)
    git_dir = website_dir / ".git"
    if git_dir.exists():
        print("\nGit commit disponible — exécuter manuellement :")
        print(f"  cd {website_dir} && git add index.html && git commit -m \"Mise à jour publication {datetime.date.today()}\"")
    else:
        print("(Pas de repo git dans website/ — commit ignoré)")

if __name__ == "__main__":
    main()
