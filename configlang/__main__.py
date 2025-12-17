from __future__ import annotations

import argparse
from pathlib import Path
import sys

from .translator import ConfigLangError, parse_and_eval, to_xml


_EXAMPLE_TEXT = "(define defaultport 8e+1) {service={workers=4e+0,port=.[defaultport].,},}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="configlang")
    parser.add_argument(
        "--generate-examples",
        action="store_true",
    )
    parser.add_argument(
        "--output-dir",
        default=".",
    )
    args = parser.parse_args(argv)

    try:
        if args.generate_examples:
            out_dir = Path(args.output_dir)
            out_dir.mkdir(parents=True, exist_ok=True)
            value = parse_and_eval(_EXAMPLE_TEXT)

            (out_dir / "example.json").unlink(missing_ok=True)
            (out_dir / "example.xml").write_text(to_xml(value) + "\n", encoding="utf-8")
            return 0

        text = sys.stdin.read()
        value = parse_and_eval(text)
        sys.stdout.write(to_xml(value))
        if not text.endswith("\n"):
            sys.stdout.write("\n")
        return 0
    except ConfigLangError as e:
        sys.stderr.write(str(e) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
