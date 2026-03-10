import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from parser.parser import parse_text


def main() -> int:
    if len(sys.argv) > 2:
        print("Usage: python scripts/demo_parse.py [path-to-report.txt]", file=sys.stderr)
        return 2

    if len(sys.argv) == 2:
        raw = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        print("No input provided.", file=sys.stderr)
        return 1

    parsed = parse_text(raw)
    print(json.dumps(parsed, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
