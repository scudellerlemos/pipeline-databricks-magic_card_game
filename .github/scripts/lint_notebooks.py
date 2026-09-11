#!/usr/bin/env python3
"""AUD-10: statically lints the real Python code inside notebooks (undefined
names, syntax errors) instead of only validating YAML/JSON structure.
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_PREFIXES = ("%sql", "%scala", "%md", "%sh", "%fs", "%r", "%%")
RUN_RE = re.compile(r"^%run\s+(\S+)")
DATABRICKS_STUB = "spark = dbutils = display = displayHTML = sqlContext = table = None\n"


def resolve_run_target(notebook_path, ref):
    ref = ref.strip("\"'")
    candidate = (notebook_path.parent / ref).with_suffix(".py")
    return candidate if candidate.exists() else None


def extract_python(notebook_path, visited):
    nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    chunks = []
    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        first_line = next((l for l in source.splitlines() if l.strip()), "")
        if first_line.lstrip().startswith(SKIP_PREFIXES):
            continue  # whole cell is non-Python (%sql, %md, ...)

        kept = []
        for line in source.splitlines():
            stripped = line.lstrip()
            run_match = RUN_RE.match(stripped)
            if run_match:
                # %run inlines another notebook/source-linked .py into this
                # namespace at runtime (Databricks Repos) - mirror that here
                # so names it defines (e.g. get_secret) aren't flagged undefined.
                target = resolve_run_target(notebook_path, run_match.group(1))
                if target and target not in visited:
                    visited.add(target)
                    chunks.append(target.read_text(encoding="utf-8"))
                continue
            if stripped.startswith("%"):
                continue  # drop other inline magics
            kept.append(line)
        chunks.append("\n".join(kept))
    return "\n\n".join(chunks)


def main():
    notebooks = sorted(REPO_ROOT.glob("src/**/*.ipynb"))
    failed = False
    with tempfile.TemporaryDirectory() as tmp:
        for nb_path in notebooks:
            code = DATABRICKS_STUB + extract_python(nb_path, {nb_path})
            tmp_file = Path(tmp) / (nb_path.stem + ".py")
            tmp_file.write_text(code, encoding="utf-8")
            result = subprocess.run(
                ["ruff", "check", "--select=F821,F822,F823", "--quiet", str(tmp_file)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if result.stdout.strip():
                print(f"FAIL {nb_path.relative_to(REPO_ROOT)}")
                print(result.stdout)
                failed = True
    if failed:
        sys.exit(1)
    print(f"OK: {len(notebooks)} notebooks passed static lint (ruff F821/F822/F823)")


if __name__ == "__main__":
    main()
