from __future__ import annotations

from pathlib import Path


REQUIRED_FILES = {
    "auth.py",
    "checkout.py",
    "cart.py",
    "config.py",
    "database.py",
    "utils.py",
    "models.py",
    "payments.py",
    "api.py",
    "main.py",
}


def validate_fixture(project_root: Path) -> tuple[bool, list[str]]:
    errors: list[str] = []
    files = {path.name for path in project_root.glob("*.py")}

    missing = sorted(REQUIRED_FILES - files)
    extra = sorted(files - REQUIRED_FILES)
    if missing:
        errors.append(f"missing files: {', '.join(missing)}")
    if extra:
        errors.append(f"unexpected files: {', '.join(extra)}")

    checkout_text = (project_root / "checkout.py").read_text(encoding="utf-8")
    if "validate_token(token)" not in checkout_text or "user[\"card_token\"]" not in checkout_text:
        errors.append("checkout.py does not include expected nullable-token cascade pattern")

    config_text = (project_root / "config.py").read_text(encoding="utf-8")
    if '"auth_provider"' in config_text or "'auth_provider'" in config_text:
        errors.append("config.py unexpectedly includes auth_provider key")

    database_text = (project_root / "database.py").read_text(encoding="utf-8")
    if "+ user_id" not in database_text:
        errors.append("database.py does not include expected SQL concatenation pattern")

    cart_text = (project_root / "cart.py").read_text(encoding="utf-8")
    if "total=0" not in cart_text:
        errors.append("cart.py does not include expected style-violation signature")

    return (len(errors) == 0), errors


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1] / "sample_project_canonical"
    ok, errs = validate_fixture(root)
    if ok:
        print("fixture valid")
    else:
        for item in errs:
            print(item)
        raise SystemExit(1)
