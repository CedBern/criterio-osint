import pytest
from pathlib import Path
import tempfile
import json

SCRIPT_DIR = Path(__file__).parent


@pytest.fixture
def sample_markdown():
    return """# Titre de test

Introduction avec du **contenu** et des *italiques*.

## Sous-titre

> Une citation importante

- Item 1
- Item 2

[Lien vers source](https://example.com)

![Une image](images/test.png)

| Colonne 1 | Colonne 2 |
|-----------|-----------|
| Valeur 1  | Valeur 2  |"""


def test_md_to_html_import():
    from publish_dossiers import md_to_html
    assert callable(md_to_html)


def test_md_to_html_titles(sample_markdown):
    from publish_dossiers import md_to_html
    html = md_to_html(sample_markdown)
    assert "<h2>Titre de test</h2>" in html
    assert "<h3>Sous-titre</h3>" in html


def test_md_to_html_formatting(sample_markdown):
    from publish_dossiers import md_to_html
    html = md_to_html(sample_markdown)
    assert "<strong>contenu</strong>" in html
    assert "<em>italiques</em>" in html


def test_md_to_html_blockquote(sample_markdown):
    from publish_dossiers import md_to_html
    html = md_to_html(sample_markdown)
    assert "<blockquote>Une citation importante</blockquote>" in html


def test_md_to_html_list(sample_markdown):
    from publish_dossiers import md_to_html
    html = md_to_html(sample_markdown)
    assert "<ul>" in html
    assert "<li>Item 1</li>" in html


def test_md_to_html_link(sample_markdown):
    from publish_dossiers import md_to_html
    html = md_to_html(sample_markdown)
    assert 'href="https://example.com"' in html
    assert 'target="_blank"' in html


def test_md_to_html_image(sample_markdown):
    from publish_dossiers import md_to_html
    html = md_to_html(sample_markdown)
    assert '<div class="article-media">' in html
    assert 'src="images/test.png"' in html


def test_md_to_html_table():
    from publish_dossiers import md_to_html
    table_md = "| Colonne 1 | Colonne 2 |\n|-----------|-----------|\n| Valeur 1  | Valeur 2  |"
    html = md_to_html(table_md)
    assert '<table class="styled-table">' in html
    assert "<th>Colonne 1</th>" in html


def test_parse_lang_meta():
    from publish_dossiers import parse_lang_meta
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write("# Titre Principal\n\nCeci est une introduction suffisamment longue pour être capturée comme résumé par la fonction d'extraction.")
        tmp = f.name
    try:
        title, summary = parse_lang_meta(tmp)
        assert title == "Titre Principal"
        assert len(summary) > 0
    finally:
        Path(tmp).unlink(missing_ok=True)


def test_parse_lang_meta_missing_file():
    from publish_dossiers import parse_lang_meta
    title, summary = parse_lang_meta("/nonexistent/file.md")
    assert title == ""
    assert summary == ""


def test_get_cover_image_default():
    from publish_dossiers import get_cover_image
    cover = get_cover_image("unknown_slug")
    assert cover in ("images/Piramides_de_Guiza.webp", "images/Piramides_de_Guiza.jpg")


def test_get_cover_image_from_content():
    from publish_dossiers import get_cover_image
    cover = get_cover_image("test", "![Alt](images/custom.jpg)")
    assert cover == "images/custom.jpg"


def test_highlight_glossary():
    from publish_dossiers import highlight_glossary
    glossary = {"pyramide": "Monument"}
    html = highlight_glossary("<p>La pyramide est grande</p>", glossary)
    assert 'data-word="pyramide"' in html
    assert 'class="glossary-term"' in html


def test_highlight_glossary_no_match():
    from publish_dossiers import highlight_glossary
    html = highlight_glossary("<p>Les chats sont mignons</p>", {"pyramide": "Monument"})
    assert html == "<p>Les chats sont mignons</p>"


def test_generate_multilingual_html_basic():
    from publish_dossiers import generate_multilingual_html
    fr = "Paragraphe 1\n\nParagraphe 2"
    es = "Párrafo 1\n\nPárrafo 2"
    en = "Paragraph 1\n\nParagraph 2"
    html = generate_multilingual_html(fr, es, en, {})
    assert 'class="paragraph-block"' in html
    assert 'class="paragraph-fr"' in html
    assert 'class="paragraph-es"' in html
    assert 'class="paragraph-en"' in html


def test_generate_multilingual_html_media_block():
    from publish_dossiers import generate_multilingual_html
    fr = "![Image](test.png)\n\nTexte normal"
    es = "![Imagen](test.png)\n\nTexto normal"
    en = "![Image](test.png)\n\nNormal text"
    html = generate_multilingual_html(fr, es, en, {})
    assert 'class="media-block"' in html
    assert 'class="paragraph-block"' in html


def test_generate_multilingual_html_sources():
    from publish_dossiers import generate_multilingual_html
    fr = "Sources et Références\n\nAutre contenu"
    es = "Fuentes y Referencias\n\nOtro contenido"
    en = "Sources and References\n\nOther content"
    html = generate_multilingual_html(fr, es, en, {})
    assert 'class="sources-wrapper"' in html


def test_publish_dossiers_config_uses_relative_paths():
    import publish_dossiers
    d = str(publish_dossiers.dossiers_dir)
    assert d.endswith("documents_debunking")
    assert "website" in str(publish_dossiers.html_path)
    assert "website" in str(publish_dossiers.website_dir)


def test_highlight_glossary_multilingual():
    from publish_dossiers import highlight_glossary
    glossary = {
        "bâtisseurs": {
            "es": "constructores",
            "en": "builders",
            "def": "Personnes qui conçoivent et construisent."
        }
    }
    html_fr = highlight_glossary("Les bâtisseurs", glossary, "fr")
    html_es = highlight_glossary("Los constructores", glossary, "es")
    html_en = highlight_glossary("The builders", glossary, "en")
    
    assert 'data-word="bâtisseurs"' in html_fr
    assert 'data-word="bâtisseurs"' in html_es
    assert 'data-word="bâtisseurs"' in html_en
    assert 'constructores</span>' in html_es
    assert 'builders</span>' in html_en
