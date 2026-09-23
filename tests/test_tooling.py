import hashlib
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from package import build
from validate import validate


class ToolingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "skills").mkdir()
        (self.root / "docs").mkdir()
        for name in ("LICENSE", "README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "requirements-dev.txt"):
            (self.root / name).write_text("Test fixture\n", encoding="utf-8")
        (self.root / "VERSION").write_text("0.1.0\n", encoding="utf-8")

    def add_skill(self, body="Instructions."):
        skill = self.root / "skills" / "nexusflow-fixture"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "---\nname: nexusflow-fixture\ndescription: Test fixture only.\n---\n" + body + "\n",
            encoding="utf-8",
        )
        return skill

    def test_empty_scaffold_valid_but_not_publishable(self):
        self.assertEqual(validate(self.root), [])
        with self.assertRaisesRegex(ValueError, "No skills"):
            build(self.root)

    def test_package_is_self_contained_and_checksums_match(self):
        skill = self.add_skill("Read [data](assets/data.txt).")
        (skill / "assets").mkdir()
        (skill / "assets" / "data.txt").write_text("example", encoding="utf-8")
        output = build(self.root)
        archive = output / "nexusflow-fixture-0.1.0.zip"
        with zipfile.ZipFile(archive) as zipped:
            self.assertEqual(set(zipped.namelist()), {
                "nexusflow-fixture/SKILL.md", "nexusflow-fixture/LICENSE",
                "nexusflow-fixture/assets/data.txt",
            })
            unpacked = self.root / "unpacked"
            zipped.extractall(unpacked)
        self.assertTrue((unpacked / "nexusflow-fixture/assets/data.txt").exists())
        for line in (output / "SHA256SUMS.txt").read_text().splitlines():
            digest, name = line.split("  ")
            self.assertEqual(digest, hashlib.sha256((output / name).read_bytes()).hexdigest())
        second = build(self.root, self.root / "second-build")
        self.assertEqual(archive.read_bytes(), (second / archive.name).read_bytes())
        with self.assertRaisesRegex(ValueError, "Output must be empty"):
            build(self.root)

    def test_missing_and_external_resource_rejected(self):
        skill = self.add_skill("Read [missing](missing.md).")
        with self.assertRaisesRegex(ValueError, "missing or external"):
            validate(self.root)
        entry = skill / "SKILL.md"
        entry.write_text(entry.read_text().replace("missing.md", "../../README.md"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "missing or external"):
            validate(self.root)

    def test_private_file_rejected(self):
        skill = self.add_skill()
        (skill / ".env").write_text("EXAMPLE=value", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "private/local"):
            validate(self.root)

    def test_name_must_match_directory(self):
        skill = self.add_skill()
        entry = skill / "SKILL.md"
        entry.write_text(entry.read_text().replace("nexusflow-fixture", "nexusflow-other"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "name must match"):
            validate(self.root)


if __name__ == "__main__":
    unittest.main()
