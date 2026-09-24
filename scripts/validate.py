"""Validate the repository's portable skill directories (without executing them)."""

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME = re.compile(r"(?:nexusflow-[a-z0-9]+(?:-[a-z0-9]+)*|[a-z0-9]+(?:-[a-z0-9]+)*-to-nexusflow)")
FIELDS = {"name", "description", "license", "compatibility", "metadata", "allowed-tools"}
BLOCKED_DIRS = {".git", ".venv", "__pycache__", "node_modules"}


def version(root):
    value = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)", value):
        raise ValueError("VERSION must use X.Y.Z without leading zeros")
    return value


def skill_files(skill):
    """Reject links and unwanted local files before collecting distributable files."""
    files = []

    def visit(directory):
        for path in sorted(directory.iterdir()):
            if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
                raise ValueError(f"links are not distributable: {path}")
            if path.name in BLOCKED_DIRS:
                raise ValueError(f"local directory is not distributable: {path}")
            if path.is_dir():
                visit(path)
            elif path.is_file():
                name = path.name.lower()
                if ((name == ".env" or name.startswith(".env.")) and name != ".env.example"
                        or path.suffix.lower() in {".pem", ".key", ".p12", ".pyc"}
                        or name in {"id_rsa", "id_ed25519", "credentials.json"}):
                    raise ValueError(f"potential private/local file: {path}")
                if name != ".gitkeep":
                    files.append(path)

    visit(skill)
    return files


def check_links(path, skill):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"^(`{3,}|~{3,}).*?^\1[^\n]*$", "", text, flags=re.M | re.S)
    for raw in re.findall(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", text):
        target = raw.strip().split(' "', 1)[0].strip("<>")
        if target.startswith("#"):
            continue
        link = urlsplit(target)
        if link.scheme in {"http", "https", "mailto"}:
            continue
        if link.scheme or link.netloc or "\\" in target:
            raise ValueError(f"unsupported or absolute local link in {path}: {target}")
        local = (path.parent / unquote(link.path)).resolve()
        if not local.is_relative_to(skill.resolve()) or not local.exists():
            raise ValueError(f"missing or external local resource in {path}: {target}")


def validate(root=ROOT):
    version(root)
    skills = []
    for skill in sorted((root / "skills").iterdir()):
        if skill.name == ".gitkeep" and skill.is_file() and not skill.is_symlink():
            continue
        if skill.is_symlink() or getattr(skill, "is_junction", lambda: False)():
            raise ValueError(f"skill cannot be a link: {skill}")
        if not skill.is_dir() or not NAME.fullmatch(skill.name) or len(skill.name) > 64:
            raise ValueError(f"invalid skill directory: {skill}")
        files = skill_files(skill)
        entry = skill / "SKILL.md"
        if entry not in files:
            raise ValueError(f"missing SKILL.md: {skill}")
        source = entry.read_text(encoding="utf-8")
        match = re.fullmatch(r"---\r?\n(.*?)\r?\n---\r?\n(.*)", source, re.S)
        if not match or not match[2].strip():
            raise ValueError(f"SKILL.md needs YAML frontmatter and instructions: {skill}")
        meta = yaml.safe_load(match[1])
        if not isinstance(meta, dict) or set(meta) - FIELDS:
            raise ValueError(f"invalid frontmatter fields: {skill}")
        if meta.get("name") != skill.name:
            raise ValueError(f"name must match its directory: {skill}")
        for key, limit in (("description", 1024), ("compatibility", 500)):
            if key == "compatibility" and key not in meta:
                continue
            value = meta.get(key)
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"invalid {key}: {skill}")
        for key in ("license", "allowed-tools"):
            if key in meta and (not isinstance(meta[key], str) or not meta[key].strip()):
                raise ValueError(f"{key} must be a nonempty string: {skill}")
        metadata = meta.get("metadata", {})
        if not isinstance(metadata, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()
        ):
            raise ValueError(f"metadata must map strings to strings: {skill}")
        for file in files:
            if file.suffix.lower() == ".md":
                check_links(file, skill)
        skills.append(skill)
    return skills


if __name__ == "__main__":
    try:
        found = validate()
        print(f"Validated {len(found)} skill(s)." + (" Scaffold only; nothing to publish." if not found else ""))
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        sys.exit(1)
