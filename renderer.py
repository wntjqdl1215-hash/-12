"""에피소드 YAML → 슬라이드 PNG + 캡션 렌더러."""

import sys
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader

from comfyui_client import ComfyUIClient, ComfyUIError

ROOT = Path(__file__).parent

# 지원 포맷: (테마, 기본 비율). 퍼즐 작가(관찰력 테스트)는 v2에서 제거됨.
FORMATS = {
    "cctv_moments": ("cctv", "4:5"),
    "guest_types": ("cctv", "4:5"),
    "trailer": ("film", "9:16"),
}
REMOVED_FORMATS = {"puzzle", "observation_test", "관찰력테스트"}

SIZES = {"4:5": (1080, 1350), "9:16": (1080, 1920)}


def load_config() -> dict:
    return yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))


def _generate_backgrounds(ep: dict, aspect: str, outdir: Path, config: dict) -> None:
    """bg.prompt가 있는 슬라이드의 배경을 ComfyUI로 생성. 실패해도 렌더링은 계속."""
    cfg = config["comfyui"]
    wants_bg = [s for s in ep["slides"] if (s.get("bg") or {}).get("prompt")]
    if not wants_bg:
        return

    client = ComfyUIClient(
        base_url=cfg["base_url"],
        workflow_path=ROOT / cfg["workflow"],
        checkpoint=cfg.get("checkpoint"),
        timeout_sec=cfg.get("timeout_sec", 300),
    )
    if not client.is_up():
        print(f"  ! ComfyUI({cfg['base_url']}) 응답 없음 — CSS 배경 폴백으로 진행")
        return

    width, height = cfg["bg_size"][aspect]
    suffix = cfg.get("style_suffix", {}).get(ep["format"], "")
    assets = outdir / "assets"
    assets.mkdir(parents=True, exist_ok=True)

    for i, s in enumerate(ep["slides"], start=1):
        bg = s.get("bg") or {}
        if not bg.get("prompt"):
            continue
        prompt = bg["prompt"] + (", " + suffix if suffix else "")
        try:
            print(f"  · ComfyUI 배경 생성 중 (slide {i}) …")
            png = client.generate(
                prompt=prompt,
                negative=bg.get("negative", cfg.get("negative_prompt", "")),
                width=width, height=height,
                seed=bg.get("seed"),
            )
            path = assets / f"bg_{i:02d}.png"
            path.write_bytes(png)
            s["bg_file"] = f"assets/bg_{i:02d}.png"
        except ComfyUIError as e:
            print(f"  ! slide {i} 배경 생성 실패({e}) — CSS 배경 폴백")


def _screenshot_slides(html_path: Path, outdir: Path, n_slides: int,
                       width: int, height: int) -> None:
    import os

    from playwright.sync_api import sync_playwright

    # Playwright 기본 브라우저가 없으면 CHROMIUM_PATH로 시스템 크로뮴 지정 가능
    launch_opts = {}
    if os.environ.get("CHROMIUM_PATH"):
        launch_opts["executable_path"] = os.environ["CHROMIUM_PATH"]

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_opts)
        page = browser.new_page(viewport={"width": width, "height": height},
                                device_scale_factor=1)
        page.goto(html_path.resolve().as_uri())
        page.wait_for_load_state("networkidle")
        for i in range(1, n_slides + 1):
            page.locator(f"#slide-{i}").screenshot(
                path=str(outdir / f"slide_{i:02d}.png"))
        browser.close()


def render_episode(episode_path: str | Path, use_comfy: bool = True) -> Path:
    config = load_config()
    ep = yaml.safe_load(Path(episode_path).read_text(encoding="utf-8"))

    fmt = ep.get("format")
    if fmt in REMOVED_FORMATS:
        sys.exit(f"오류: '{fmt}' 포맷(퍼즐 작가)은 v2에서 제거되었습니다. "
                 f"사용 가능: {', '.join(FORMATS)}")
    if fmt not in FORMATS:
        sys.exit(f"오류: 알 수 없는 포맷 '{fmt}'. 사용 가능: {', '.join(FORMATS)}")

    theme, default_aspect = FORMATS[fmt]
    aspect = ep.get("aspect", default_aspect)
    width, height = SIZES[aspect]

    outdir = ROOT / config["render"]["out_dir"] / ep["id"]
    outdir.mkdir(parents=True, exist_ok=True)
    print(f"▶ {ep['id']} · {ep['title']} ({fmt}, {aspect}, 슬라이드 {len(ep['slides'])}장)")

    if use_comfy:
        _generate_backgrounds(ep, aspect, outdir, config)
    else:
        print("  · --no-comfy: 배경 생성 건너뜀")

    env = Environment(loader=FileSystemLoader(ROOT / "templates"))
    html = env.get_template("slides.html.j2").render(
        ep=ep, slides=ep["slides"], theme=theme, width=width, height=height)
    html_path = outdir / "slides.html"
    html_path.write_text(html, encoding="utf-8")

    _screenshot_slides(html_path, outdir, len(ep["slides"]), width, height)

    caption = ep.get("caption", "").strip()
    tags = " ".join(f"#{t.lstrip('#')}" for t in ep.get("hashtags", []))
    (outdir / "caption.txt").write_text(
        caption + ("\n\n" + tags if tags else "") + "\n", encoding="utf-8")

    print(f"✔ 완료 → {outdir}")
    return outdir
