#!/usr/bin/env python3
"""Verify the released packed base + fixed delta and emit local-only state."""
import argparse
import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
from portable_runtime import prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-path', type=Path, required=True)
    parser.add_argument('--state-dir', type=Path, required=True)
    parser.add_argument('--delta-path', type=Path)
    args = parser.parse_args()
    result = prepare(args.model_path, args.state_dir, args.delta_path)
    print(json.dumps({k: str(v) for k, v in result.items()}, indent=2))


if __name__ == '__main__':
    main()
