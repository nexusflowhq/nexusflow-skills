"""Build single-skill and collection ZIPs with checksums."""

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

import yaml

from validate import ROOT, skill_files, validate, version


def write_zip(path, entries):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, content)


def build(root=ROOT, output=None):
    skills = validate(root)
    if not skills:
        raise ValueError("No skills available. Refusing to package an empty collection.")
    release = version(root)
    output = Path(output) if output else root / "dist" / release
    if output.exists() and any(output.iterdir()):
        raise ValueError(f"Output must be empty: {output}")
    license_data = (root / "LICENSE").read_bytes()
    bundle_root = f"nexusflow-skills-{release}"
    collection = {
        f"{bundle_root}/{name}": (root / name).read_bytes()
        for name in ("LICENSE", "README.md", "VERSION", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "requirements-dev.txt")
    }
    for file in sorted((root / "docs").rglob("*.md")):
        collection[f"{bundle_root}/{file.relative_to(root).as_posix()}"] = file.read_bytes()
    for directory in ("scripts", "tests"):
        for file in sorted((root / directory).rglob("*")):
            if file.is_file() and file.suffix in {".py", ".md"}:
                collection[f"{bundle_root}/{file.relative_to(root).as_posix()}"] = file.read_bytes()
    output.mkdir(parents=True, exist_ok=True)
    archives = []
    for skill in skills:
        entries = {f"{skill.name}/{file.relative_to(skill).as_posix()}": file.read_bytes()
                   for file in skill_files(skill)}
        # Preserve an explicit skill license; otherwise include the repository license.
        entries.setdefault(f"{skill.name}/LICENSE", license_data)
        path = output / f"{skill.name}-{release}.zip"
        write_zip(path, entries)
        archives.append(path)
        collection.update({f"{bundle_root}/skills/{name}": data for name, data in entries.items()})
    path = output / f"{bundle_root}.zip"
    write_zip(path, collection)
    archives.append(path)
    checksums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in archives)
    (output / "SHA256SUMS.txt").write_text(checksums, encoding="utf-8", newline="\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, help="An empty output directory")
    args = parser.parse_args()
    try:
        print(f"Packages created: {build(output=args.output)}")
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(f"Packaging failed: {exc}", file=sys.stderr)
        sys.exit(1)
