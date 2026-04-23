import re
import argparse
import difflib
from pathlib import Path
from core.rules import load_rules
from core.pipeline import run_pipeline
from core.tokenizer import count_tokens

DEFAULT_RULES = Path(__file__).parent.parent / "rules" / "default.toml"


def main():
    parser = argparse.ArgumentParser(prog="caveman")
    parser.add_argument("-file", dest="input", type=Path, required=True)
    parser.add_argument("-o", dest="output", type=Path)
    parser.add_argument("-rules", dest="rules", type=Path, default=None)
    parser.add_argument(
        "-tokenizer",
        dest="tokenizer",
        default="approx",
        choices=["approx", "cl100k_base", "o200k_base"],
    )
    parser.add_argument("-diff", action="store_true")
    args = parser.parse_args()

    rules_path = args.rules or DEFAULT_RULES
    original = args.input.read_text(encoding="utf-8")
    rules = load_rules(str(rules_path))
    result = run_pipeline(original, rules)
    out_path = args.output or args.input.with_suffix(".txt")

    out_path.write_text(result["output"], encoding="utf-8")

    orig_tokens = count_tokens(original, args.tokenizer)
    out_tokens = count_tokens(result["output"], args.tokenizer)

    print(f"  Input:   {result['original_chars']:>6} chars  {orig_tokens:>5} tokens")
    print(f"  Output:  {result['output_chars']:>6} chars  {out_tokens:>5} tokens")
    print(f"  Saved:   {result['reduction_pct']}% reduction")
    print(f"  Written: {out_path}")

    if args.diff:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            result["output"].splitlines(keepends=True),
            fromfile="original",
            tofile="compressed",
        )
        print("\n--- diff ---")
        print("".join(diff))


if __name__ == "__main__":
    main()
