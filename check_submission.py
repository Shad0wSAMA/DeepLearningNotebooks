#!/usr/bin/env python3
"""Check interim or final coursework artifacts in a submission folder."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


MANIFESTS = {
    "interim": (
        Path(__file__).with_name("submission")
        / "submission_requirements_interim.json"
    ),
    "final": (
        Path(__file__).with_name("submission")
        / "submission_requirements_final.json"
    ),
}
CID_FILE_RE = re.compile(r"^(.+?)_E\d+_T\d+_")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report missing, empty, or incorrectly typed submission artifacts."
    )
    parser.add_argument(
        "submission_dir",
        nargs="?",
        default="submission",
        type=Path,
        help="submission folder to check (default: ./submission)",
    )
    parser.add_argument(
        "--stage",
        choices=tuple(MANIFESTS),
        help=(
            "requirements to check: 'interim' checks notebooks 02–03; "
            "'final' checks notebooks 04–09"
        ),
    )
    parser.add_argument(
        "--cid",
        help="CID used to expand {CID}; inferred from submission names when omitted",
    )
    args = parser.parse_args()
    if args.stage is None:
        parser.error(
            "choose which requirements to check with --stage: "
            "use '--stage interim' for notebooks 02–03, or "
            "'--stage final' for notebooks 04–09"
        )
    return args


def infer_cid(submission_dir: Path) -> tuple[str | None, set[str]]:
    candidates: set[str] = set()
    if submission_dir.is_dir():
        for entry in submission_dir.iterdir():
            match = CID_FILE_RE.match(entry.name)
            if match:
                candidates.add(match.group(1))
    if len(candidates) == 1:
        return next(iter(candidates)), candidates
    return None, candidates


def directory_has_content(path: Path) -> bool:
    try:
        return next(path.iterdir(), None) is not None
    except OSError:
        return False


def main() -> int:
    args = parse_args()
    manifest_path = MANIFESTS[args.stage]

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read manifest {manifest_path}: {exc}", file=sys.stderr)
        return 2

    if not args.submission_dir.is_dir():
        print(f"ERROR: submission folder does not exist: {args.submission_dir}")
        return 2

    cid = args.cid
    if cid is None:
        cid, candidates = infer_cid(args.submission_dir)
        if cid is None:
            detail = "none found" if not candidates else ", ".join(sorted(candidates))
            print(f"ERROR: could not infer one CID ({detail}); pass --cid CID")
            return 2

    requirements = manifest.get("requirements")
    if not isinstance(requirements, list):
        print("ERROR: manifest has no valid 'requirements' list", file=sys.stderr)
        return 2

    problems: list[tuple[str, str]] = []
    satisfied = 0

    for item in requirements:
        relative = item["path"].replace("{CID}", cid)
        expected_type = item.get("type", "file")
        target = args.submission_dir / relative

        if not target.exists():
            problems.append(("MISSING", relative))
        elif expected_type == "file" and not target.is_file():
            problems.append(("WRONG TYPE (expected file)", relative))
        elif expected_type == "directory" and not target.is_dir():
            problems.append(("WRONG TYPE (expected directory)", relative))
        elif expected_type == "file" and target.stat().st_size == 0:
            problems.append(("EMPTY FILE", relative))
        elif expected_type == "directory" and not directory_has_content(target):
            problems.append(("EMPTY DIRECTORY", relative))
        else:
            satisfied += 1

    print(f"Submission: {args.submission_dir.resolve()}")
    print(f"Stage: {args.stage}")
    print(f"Manifest: {manifest_path.name}")
    print(f"CID: {cid}")
    print(f"Satisfied: {satisfied}/{len(requirements)}")

    if problems:
        print(f"Problems ({len(problems)}):")
        for label, relative in problems:
            print(f"  [{label}] {relative}")
        return 1

    print("OK: all required submission artifacts exist and are non-empty.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
