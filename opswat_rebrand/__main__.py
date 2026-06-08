import argparse, sys
from .pipeline import run

def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="opswat-rebrand",
        description="Rebrand a web codebase to the OPSWAT product-UI design system.")
    ap.add_argument("src", help="path to the source codebase")
    ap.add_argument("-o", "--out", help="output path (default: <src>-opswat)")
    ap.add_argument("--depth", choices=["tokens", "theme", "full"], default="full",
                    help="tokens: colours+fonts only; theme: +baseline override; "
                         "full: +emit LLM restyle work order")
    ap.add_argument("--target-theme", choices=["auto", "light", "dark"], default="auto",
                    help="auto: preserve detected source polarity; or force light/dark")
    ap.add_argument("-q", "--quiet", action="store_true")
    args = ap.parse_args(argv)
    out = args.out or (args.src.rstrip("/\\") + "-opswat")
    run(args.src, out, depth=args.depth, target_theme=args.target_theme, verbose=not args.quiet)

if __name__ == "__main__":
    sys.exit(main())
