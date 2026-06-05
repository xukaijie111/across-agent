#!/usr/bin/env python3
"""
Single entry-point: protocol static check + optional TypeScript build.

Usage:
    python3 scripts/run_pipeline.py
    python3 scripts/run_pipeline.py --repo-root /path/to/python-less
    python3 scripts/run_pipeline.py --skip-tsc
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from check_graph_protocol import run_checks


def run_tsc(repo_root: Path) -> int:
    server_dir = repo_root / "apps/server"
    pkg = server_dir / "package.json"
    if not pkg.is_file():
        print("SKIP: apps/server/package.json not found — tsc skipped")
        return 0

    print(f"Running npm run build in {server_dir} ...")
    proc = subprocess.run(
        ["npm", "run", "build"],
        cwd=server_dir,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        print("FAIL: TypeScript build failed", file=sys.stderr)
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        return proc.returncode
    print("OK: TypeScript build passed")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Graph chat protocol pipeline")
    parser.add_argument("--repo-root", type=Path, default=None)
    parser.add_argument(
        "--skip-tsc",
        action="store_true",
        help="Skip apps/server npm run build",
    )
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    repo_root = args.repo_root
    if repo_root is None:
        candidate = skill_dir.parent.parent.parent
        if (candidate / "docs/chat-protocol.md").is_file():
            repo_root = candidate
        else:
            repo_root = Path.cwd()
    repo_root = repo_root.resolve()

    print(f"Repo root: {repo_root}\n--- Protocol check ---")
    try:
        violations = run_checks(repo_root)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if violations:
        print(f"FAIL: {len(violations)} chat-protocol violation(s)\n")
        for v in violations:
            print(f"  [{v.rule_id}] {v.file}")
            print(f"    {v.message}")
            print(f"    See docs/chat-protocol.md {v.doc_section}\n")
        return 1
    print(f"OK: graph layer matches docs/chat-protocol.md ({repo_root})")

    if args.skip_tsc:
        return 0

    print("\n--- TypeScript build ---")
    return run_tsc(repo_root)


if __name__ == "__main__":
    sys.exit(main())
