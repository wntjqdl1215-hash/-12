#!/usr/bin/env python3
"""룸엘이스케이프 캐러셀 파이프라인 v2 CLI.

사용법:
  python pipeline.py list
  python pipeline.py render content/episodes/ep001_cctv.yaml [--no-comfy]
"""

import argparse
from pathlib import Path

import yaml

from renderer import FORMATS, render_episode

ROOT = Path(__file__).parent
EPISODES_DIR = ROOT / "content" / "episodes"


def cmd_list(_args) -> None:
    print("지원 포맷:", ", ".join(FORMATS))
    print()
    files = sorted(EPISODES_DIR.glob("*.yaml"))
    if not files:
        print("에피소드 없음 (content/episodes/*.yaml)")
        return
    for f in files:
        ep = yaml.safe_load(f.read_text(encoding="utf-8"))
        print(f"  {f.relative_to(ROOT)}  [{ep.get('format')}]  {ep.get('title')}")


def cmd_render(args) -> None:
    render_episode(args.episode, use_comfy=not args.no_comfy)


def main() -> None:
    parser = argparse.ArgumentParser(description="룸엘이스케이프 캐러셀 파이프라인 v2")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="에피소드 목록").set_defaults(func=cmd_list)

    p = sub.add_parser("render", help="에피소드 렌더링")
    p.add_argument("episode", help="에피소드 YAML 경로")
    p.add_argument("--no-comfy", action="store_true",
                   help="ComfyUI 배경 생성 없이 렌더링")
    p.set_defaults(func=cmd_render)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
