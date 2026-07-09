import pytest
from pathlib import Path
import tempfile


def test_generate_illustrations_imports():
    import generate_illustrations
    assert hasattr(generate_illustrations, "create_pyramid_physics_svg")
    assert hasattr(generate_illustrations, "create_tombs_vs_temples_svg")


def test_pyramid_physics_svg_content():
    from generate_illustrations import create_pyramid_physics_svg
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "test.svg"
        create_pyramid_physics_svg(out)
        content = out.read_text(encoding="utf-8")
        assert "<svg" in content
        assert "Pyramide" in content or "pyramid" in content
        assert "Mur Vertical" in content
        assert "Gravité" in content


def test_tombs_vs_temples_svg_content():
    from generate_illustrations import create_tombs_vs_temples_svg
    with tempfile.TemporaryDirectory() as tmpdir:
        out = Path(tmpdir) / "test.svg"
        create_tombs_vs_temples_svg(out)
        content = out.read_text(encoding="utf-8")
        assert "<svg" in content
        assert "PYRAMIDE D'ÉGYPTE" in content
        assert "PYRAMIDE DE MÉSOAMÉRIQUE" in content
