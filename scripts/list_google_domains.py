#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
from typing import List, Set
import urllib.request

RAW_BASE = "https://raw.githubusercontent.com/v2fly/domain-list-community/master/"


def fetch_text(path: str) -> str:
    url = RAW_BASE + path.lstrip("/")
    req = urllib.request.Request(url, headers={"User-Agent": "github-actions"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}")


def should_ignore(line: str) -> bool:
    s = line.strip()
    return (not s) or s.startswith("#")


def parse_include_target(line: str) -> str:
    rest = line[len("include:"):].strip()
    return rest.split()[0].strip()


def normalize_domain(line: str) -> str:
    """
    Output ONLY pure domains:
      - accept "domain:example.com"  -> "example.com"
      - accept naked "example.com"   -> "example.com"
    Ignore:
      - full:..., keyword:..., regexp:..., etc.
    """
    s = line.strip()

    # typed rule
    if ":" in s:
        kind, val = s.split(":", 1)
        kind = kind.strip().lower()
        val = val.strip()

        if kind == "domain" and val:
            return val
        return ""  # drop all other kinds

    # naked domain
    return s if s else ""


def collect_domains(entry: str, visited: Set[str]) -> List[str]:
    path = entry if entry.startswith("data/") else f"data/{entry}"

    if path in visited:
        return []
    visited.add(path)

    text = fetch_text(path)
    out: List[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if should_ignore(line):
            continue

        if line.startswith("include:"):
            target = parse_include_target(line)
            out.extend(collect_domains(target, visited))
        else:
            d = normalize_domain(line)
            if d:
                out.append(d)

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", default="google", help="Entry list name under data/, e.g. google")
    ap.add_argument("--output", default="", help="Output file path; if empty, print to stdout")
    args = ap.parse_args()

    visited: Set[str] = set()
    domains = collect_domains(args.entry, visited)

    unique = sorted(set(domains))

    header = [
        f"# entry: {args.entry}",
        f"# total_unique_domains: {len(unique)}",
        f"# visited_files: {len(visited)}",
        "# ----",
    ]
    content = "\n".join(header + unique) + "\n"

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(content)
    else:
        sys.stdout.write(content)


if __name__ == "__main__":
    main()
