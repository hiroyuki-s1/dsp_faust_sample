#!/usr/bin/env python3
"""Print parameter config in human-readable form."""
import json
import sys

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "params/default.json"
    with open(path) as f:
        cfg = json.load(f)

    print(f"\nSample Rate : {cfg.get('sample_rate', 48000)} Hz")
    print(f"Block Size  : {cfg.get('block_size', 48)} samples")
    print()
    print(f"{'Parameter':<20} {'Default':>8}  {'Min':>8}  {'Max':>8}  {'Unit':<6}  {'Hardware'}")
    print("-" * 72)
    for key, p in cfg["parameters"].items():
        unit = p.get("unit", "")
        hw   = p.get("daisy_hardware", "-")
        print(f"{p['label']:<20} {p['default']:>8}  {p['min']:>8}  {p['max']:>8}  {unit:<6}  {hw}")
    print()

if __name__ == "__main__":
    main()
