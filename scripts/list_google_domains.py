#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
from typing import List, Set
import urllib.request

RAW_BASE = "https://raw.githubusercontent.com/v2fly/domain-list-community/master/"


def fetch_text(path: str) -> str:
    """
    Fetch file content from v2fly/domain-list-community via raw URL.
    path example: "data/google"
    """
    url = RAW_BASE + path.lstrip("/")
    req = urllib.request.Request(url, headers={"User-Agent": "github-actions"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        raise RuntimeError(f"Failed to fetch {url}: {e}")


def parse_include_target(line: str) -> str:
    """
    Parse include line like:
      include:geolocation-!cn
      include:google
    Some lists may have extra tokens; we take the first token after 'include:'.
    """
    rest = line[len("include:"):].strip()
    # take first token if there are spaces/tabs
    target = rest.split()[0].strip()
    return target


def should_ignore(line: str) -> bool:
    s = line.strip()
    return (not s) or s.startswith("#")


def normalize_rule(line: str) -> str:
    """
    Keep original rule by default.
    If you want ONLY naked domains, you can change this function
    to extract domains from patterns like:
      domain:example.com
      full:foo.example.com
      keyword:google
    Right now we output the rule line (trimmed).
    """
    return line.strip()


def collect_rules(entry: str, visited: Set[str]) -> List[str]:
    """
    Recursively load data/<entry> and its includes.
    entry examples: "google" or "data/google"
    """
    # turn "google" -> "data/google"
    path = entry
    if not path.startswith("data/"):
        path = f"data/{path}"

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
            out.extend(collect_rules(target, visited))
        else:
            out.append(normalize_rule(line))

    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entry", default="google", help="Entry list name under data/, e.g. google")
    ap.add_argument("--output", default="", help="Output file path; if empty, print to stdout")
    args = ap.parse_args()

    visited: Set[str] = set()
    rules = collect_rules(args.entry, visited)

    # de-dup + sort
    unique = sorted(set(rules))

    header = [
        f"# entry: {args.entry}",
        f"# total_unique: {len(unique)}",
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
