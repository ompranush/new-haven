"""Headless reproducible runs and paired experiments."""
import argparse
import json
from .sim import Simulation
from .experiments import compare


def main():
    parser = argparse.ArgumentParser(description="New Haven: reproducible artificial societies")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--population", type=int, default=100)
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--compare", choices=["storm", "education", "automation", "festival", "tax"])
    parser.add_argument("--seeds", type=int, default=3)
    args = parser.parse_args()
    if args.compare:
        result = compare(args.seed, args.population, args.seeds, args.days, args.compare)
    else:
        if not 0 <= args.days <= 36500:
            parser.error("days must be between 0 and 36500")
        sim = Simulation(args.seed, args.population)
        remaining = args.days
        while remaining:
            batch = min(remaining, 365)
            sim.step(batch)
            remaining -= batch
        result = sim.summary()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
