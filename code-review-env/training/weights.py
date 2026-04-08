from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass(frozen=True)
class WeightManifest:
    model_name: str
    source_path: str
    sha256: str
    size_bytes: int
    created_at: str


class WeightSafetyManager:
    """Store and load model weight artifacts with hash verification and atomic manifests."""

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir.resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def checksum(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()

    def register_existing(self, model_name: str, weight_path: Path) -> WeightManifest:
        resolved = weight_path.resolve()
        if not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError(f"Model weights not found: {resolved}")

        sha = self.checksum(resolved)
        manifest = WeightManifest(
            model_name=model_name,
            source_path=str(resolved),
            sha256=sha,
            size_bytes=resolved.stat().st_size,
            created_at=datetime.now(UTC).isoformat(),
        )
        self._write_manifest(model_name, manifest)
        return manifest

    def load_verified(self, model_name: str) -> Path:
        manifest = self._read_manifest(model_name)
        source = Path(manifest.source_path)
        if not source.exists() or not source.is_file():
            raise FileNotFoundError(f"Weight file missing for model {model_name}: {source}")

        sha = self.checksum(source)
        if sha != manifest.sha256:
            raise ValueError(
                f"Checksum mismatch for model {model_name}: expected {manifest.sha256}, got {sha}"
            )
        return source

    def _manifest_path(self, model_name: str) -> Path:
        safe_name = "".join(ch for ch in model_name if ch.isalnum() or ch in {"-", "_", "."})
        return self.root_dir / f"{safe_name}.manifest.json"

    def _write_manifest(self, model_name: str, manifest: WeightManifest) -> None:
        path = self._manifest_path(model_name)
        temp_path = path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(manifest.__dict__, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)

    def _read_manifest(self, model_name: str) -> WeightManifest:
        path = self._manifest_path(model_name)
        if not path.exists():
            raise FileNotFoundError(f"Weight manifest not found for {model_name}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return WeightManifest(**payload)
