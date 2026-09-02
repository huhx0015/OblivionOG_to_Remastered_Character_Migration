"""CLI for Oblivion OG to Remastered Character Migration (PC only)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .console_export import emit_console_script
from .ess_parser import EssError, parse_ess
from .formid_map import load_plugins_txt
from .sav_inspect import inspect_sav


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("ess", type=Path, help="Original Oblivion PC .ess save")
    p.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Write migrate.txt here (default: stdout)",
    )
    p.add_argument(
        "--json",
        type=Path,
        help="Also write the parsed character dump as JSON",
    )
    p.add_argument(
        "--plugins",
        type=Path,
        help="Remastered plugins.txt (default: bundled data/remastered_plugins.txt)",
    )
    p.add_argument(
        "--no-quests",
        action="store_true",
        help="Do not emit setstage commands",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="migrate.py",
        description=(
            "Oblivion OG to Remastered Character Migration. "
            "PC only: original Oblivion .ess and Oblivion Remastered on PC. "
            "Xbox and other consoles are not supported."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    migrate = sub.add_parser("migrate", help="Parse .ess and write migrate.txt")
    _add_common(migrate)

    dump = sub.add_parser("dump", help="Print parsed character JSON only")
    dump.add_argument("ess", type=Path)

    inspect = sub.add_parser("inspect-sav", help="Describe a Remastered .sav")
    inspect.add_argument("sav", type=Path)
    return parser


def cmd_migrate(args: argparse.Namespace) -> int:
    try:
        character = parse_ess(args.ess)
    except (OSError, EssError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    plugins = load_plugins_txt(args.plugins) if args.plugins else None
    text = emit_console_script(
        character,
        plugins,
        include_quests=not args.no_quests,
    )
    if args.json:
        args.json.write_text(json.dumps(character.to_dict(), indent=2), encoding="utf-8")
        print(f"wrote dump {args.json}", file=sys.stderr)
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


def cmd_dump(args: argparse.Namespace) -> int:
    try:
        character = parse_ess(args.ess)
    except (OSError, EssError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    json.dump(character.to_dict(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    try:
        sys.stdout.write(inspect_sav(args.sav))
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd == "migrate":
        return cmd_migrate(args)
    if args.cmd == "dump":
        return cmd_dump(args)
    if args.cmd == "inspect-sav":
        return cmd_inspect(args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
