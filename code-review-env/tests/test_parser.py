from pathlib import Path

from parser.ast_parser import parse_python_file


def test_parse_python_file_extracts_core_elements() -> None:
    root = Path("sample_codebase")
    path = root / "cart.py"
    parsed = parse_python_file(path=path, root_dir=root)

    assert parsed.module_id == "cart"
    assert any(sig.startswith("calculate_total(") for sig in parsed.function_signatures)
    assert "config" in " ".join(parsed.dependencies)
