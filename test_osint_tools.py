import pytest
from main import OSINT_TOOLS, SHERLOCK_SYSTEM_PROMPT, _smart_route, to_gemini_tools, to_openai_messages, _detect_fraud_keywords


def test_academic_search_tool_exists():
    tool_names = [t["name"] for t in OSINT_TOOLS]
    assert "academic_search" in tool_names
    
    academic_tool = next(t for t in OSINT_TOOLS if t["name"] == "academic_search")
    assert "query" in academic_tool["input_schema"]["properties"]


@pytest.mark.parametrize("keyword", [
    "debunk", "pseudo-science", "scientifique", "osint", "analyste"
])
def test_system_prompt_contains_keywords(keyword):
    assert keyword.lower() in SHERLOCK_SYSTEM_PROMPT.lower()


def test_system_prompt_has_debunk_instructions():
    assert "debunk" in SHERLOCK_SYSTEM_PROMPT.lower() or "pseudo-science" in SHERLOCK_SYSTEM_PROMPT.lower()
    assert "scientific consensus" in SHERLOCK_SYSTEM_PROMPT.lower() or "consensus scientifique" in SHERLOCK_SYSTEM_PROMPT.lower()


def test_academic_search_handler_routing():
    import main
    assert hasattr(main, "handle_academic_search")


class TestSmartRoute:
    def test_ip_routing(self):
        tool_name, tool_input = _smart_route("190.45.32.11")
        assert tool_name == "analyze_ip"
        assert tool_input["ip"] == "190.45.32.11"

    def test_mercadolibre_routing(self):
        tool_name, tool_input = _smart_route("https://www.mercadolibre.com.mx/producto-123")
        assert tool_name == "scrape_mercadolibre"

    def test_url_routing(self):
        tool_name, tool_input = _smart_route("https://example.com/article")
        assert tool_name == "analyze_url"

    def test_airbnb_routing(self):
        tool_name, tool_input = _smart_route("Cherche un Airbnb à Merida")
        assert tool_name == "airbnb_radar"
        assert tool_input["location"].lower() == "merida"

    def test_academic_routing(self):
        tool_name, tool_input = _smart_route("Analyse les théories de @maritarx sur l'origine commune des pyramides")
        assert tool_name == "academic_search"
        assert "pyramides" in tool_input["query"].lower()

    def test_multi_search_person_routing(self):
        tool_name, tool_input = _smart_route("trouve les infos sur Jean Dupont")
        assert tool_name == "multi_search"
        assert tool_input["target"] == "Jean Dupont"

    def test_no_multi_search_for_generic(self):
        tool_name, tool_input = _smart_route("trouve les infos sur le café")
        assert tool_name != "multi_search"

    def test_generic_osint_fallback(self):
        tool_name, tool_input = _smart_route("météo paris aujourd'hui")
        assert tool_name == "osint_search"

    def test_handle_noise_in_academic(self):
        tool_name, tool_input = _smart_route("mythe des anciens astronautes analyse critique")
        assert tool_name == "academic_search"


@pytest.mark.parametrize("text,expected", [
    ("Ce produit contient de la tirzepatida", ["tirzepatida"]),
        ("Pérdida de peso garantizada sin esfuerzo", ["pérdida de peso", "sin esfuerzo"]),
    ("Article scientifique sur les peptides", ["peptide"]),
    ("Recette de gâteau au chocolat", []),
])
def test_fraud_keyword_detection(text, expected):
    assert _detect_fraud_keywords(text) == expected


def test_gemini_tools_conversion():
    gemini_tools = to_gemini_tools(OSINT_TOOLS)
    assert len(gemini_tools) == 1
    funcs = gemini_tools[0]["function_declarations"]
    names = [f["name"] for f in funcs]
    assert "academic_search" in names
    assert "analyze_ip" in names


def test_openai_messages_conversion():
    msgs_in = [
        {"role": "user", "content": "Bonjour"},
        {"role": "assistant", "content": [{"type": "text", "text": "Analyse en cours..."}]},
        {"role": "user", "content": [{"type": "tool_result", "content": "{}"}]},
    ]
    out = to_openai_messages(msgs_in)
    assert len(out) == 3
    assert out[0]["content"] == "Bonjour"
    assert "Analyse" in out[1]["content"]


@pytest.mark.parametrize("tool_name", ["academic_search", "analyze_ip", "scrape_mercadolibre", "osint_search", "analyze_url", "airbnb_radar", "multi_search"])
def test_all_tools_registered(tool_name):
    assert tool_name in [t["name"] for t in OSINT_TOOLS]


def test_all_tools_have_descriptions():
    for tool in OSINT_TOOLS:
        assert len(tool["description"]) > 20, f"{tool['name']} description trop courte"
        assert "input_schema" in tool
        assert "properties" in tool["input_schema"]
