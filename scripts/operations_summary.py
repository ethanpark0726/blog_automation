#!/usr/bin/env python3
"""Render pipeline telemetry as a GitHub Actions job summary."""

from __future__ import annotations

import json
import os
from pathlib import Path


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError):
        return {}


def build_summary(pipeline: dict, pages: dict) -> str:
    usage = pipeline.get("usage") or {}
    source = (pipeline.get("metrics") or {}).get("source_quality") or {}
    lines = [
        "## Blog Automation Operations",
        "",
        f"- Pipeline: **{pipeline.get('status', 'unknown')}**",
        f"- Pages: **{pages.get('status', 'not checked')}**",
        f"- Gemini calls: **{usage.get('successful_calls', 0)} successful / {usage.get('api_attempts', 0)} attempts**",
        f"- Tokens: **{usage.get('total_tokens', 0):,} total** ({usage.get('prompt_tokens', 0):,} input / {usage.get('output_tokens', 0):,} output)",
    ]
    if source:
        lines.append(
            f"- Source quality: **{source.get('score', 0)}/100 ({source.get('grade', 'unknown')})** — "
            f"{source.get('reference_count', 0)} references, {source.get('domain_count', 0)} domains"
        )

    by_stage = usage.get("by_stage") or {}
    if by_stage:
        lines.extend(
            [
                "",
                "| Gemini stage | Attempts | Input tokens | Output tokens | Total |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for stage, stage_usage in by_stage.items():
            lines.append(
                f"| `{stage}` | {stage_usage.get('attempts', 0)} | "
                f"{stage_usage.get('prompt_tokens', 0):,} | "
                f"{stage_usage.get('output_tokens', 0):,} | "
                f"{stage_usage.get('total_tokens', 0):,} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    pipeline = load_json(Path(".pipeline_result.json"))
    pages = load_json(Path(".pages_result.json"))
    summary = build_summary(pipeline, pages)
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with Path(target).open("a", encoding="utf-8") as output:
            output.write(summary)
    else:
        print(summary)


if __name__ == "__main__":
    main()
