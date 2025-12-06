#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sys
from typing import List, Set, Tuple
import urllib.request

RAW_BASE = "https://raw.githubusercontent.com/v2fly/domain-list-community/master/"


def fetch_text(path: str) -> str:
    url = RAW_BASE + path.lstrip("/")
    req = urllib.request.Request(url, headers={"User-Agent": "github-actions"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def should_ignore(line: str) -> bool:
    s = line.strip()
    return (not s) or s.startswith("#")


def parse_include_target(line: str) -> str:
    rest = line[len("include:"):].strip()
    return rest.split()[0].strip()


def split_rule_and_tags(line: str) -> Tuple[str, Set[str]]:
    """
    Split "domain:example.com @ads @cn" into:
      rule="domain:example.com"
      tags={"@ads","@cn"}
    """
    parts = line.strip().split()
    if not parts:
        return "", set()
    rule = parts[0].strip()
    tags = {p.strip().lower() for p in parts[1:] if p.strip().startswith("@")}
    return rule, tags


def normalize_domain(rule: str) -> str:
    """
    Output ONLY pure domains:
      - "domain:example.com" -> "example.com"
      - naked "example.com"  -> "example.com"
    Ignore:
      - full:..., keyword:..., regexp:..., etc.
    """
    s = rule.strip()
    if not s:
        return ""

    if ":" in s:
        kind, val = s.split(":", 1)
        kind = kind.strip().lower()
        val = val.strip()
        if kind == "domain" and val:
            return val
        return ""
    return s


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
            continue

        rule, tags = split_rule_and_tags(line)

        # ✅ 只过滤带 @ads 标签的
        if "@ads" in tags:
            continue

        d = normalize_domain(rule)
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
        "# filtered: rules tagged with @ads",
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
