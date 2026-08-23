"""Dynamic Execution Manifest (agent_manifest.json) loading & validation."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

MANIFEST_SCHEMA = {
    "required": ["manifest_version", "project_name", "runtime", "commands", "contracts"],
    "runtime_required": ["language", "version", "package_manager", "ui_type"],
    "commands_required": ["install", "build", "lint", "test_unit", "dev_server"],
    "contracts_required": ["entry_point", "specs_dir", "source_dir", "test_dir", "port_variable"],
    "ui_types": ["cli", "web", "desktop", "library", "service"],
}


class ManifestError(Exception):
    pass


@dataclass
class Manifest:
    raw: dict
    path: Path

    # -- convenience accessors -------------------------------------------------
    @property
    def project_name(self) -> str:
        return self.raw["project_name"]

    @property
    def ui_type(self) -> str:
        return self.raw["runtime"]["ui_type"]

    def cmd(self, name: str) -> Optional[str]:
        return self.raw["commands"].get(name)

    def contract(self, name: str) -> str:
        return self.raw["contracts"][name]

    def needs_visual_qa(self) -> bool:
        return self.ui_type in ("web", "desktop")

    def to_json(self) -> str:
        return json.dumps(self.raw, indent=2)


def validate(raw: dict) -> None:
    """Validate a manifest dict against the required schema shape."""
    for key in MANIFEST_SCHEMA["required"]:
        if key not in raw:
            raise ManifestError(f"manifest missing required key: {key}")
    for section, req_key in (("runtime", "runtime_required"),
                             ("commands", "commands_required"),
                             ("contracts", "contracts_required")):
        sec = raw.get(section, {})
        missing = [k for k in MANIFEST_SCHEMA[req_key] if k not in sec]
        if missing:
            raise ManifestError(f"manifest.{section} missing: {', '.join(missing)}")
    ui = raw["runtime"].get("ui_type")
    if ui not in MANIFEST_SCHEMA["ui_types"]:
        raise ManifestError(f"ui_type '{ui}' not in {MANIFEST_SCHEMA['ui_types']}")


def load(root: Path) -> Manifest:
    path = root / "agent_manifest.json"
    if not path.exists():
        raise ManifestError(f"no agent_manifest.json at {root}")
    raw = json.loads(path.read_text())
    validate(raw)
    return Manifest(raw=raw, path=path)
