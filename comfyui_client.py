"""ComfyUI API 클라이언트 — 슬라이드 배경 이미지 생성.

표준 ComfyUI HTTP API 사용:
  POST /prompt          워크플로 큐잉
  GET  /history/{id}    완료 확인
  GET  /view            결과 이미지 다운로드

워크플로 JSON(API 포맷)의 노드 `_meta.title`로 값을 주입한다:
  positive_prompt / negative_prompt / latent / sampler / checkpoint
"""

import json
import random
import time
import uuid
from pathlib import Path

import requests


class ComfyUIError(RuntimeError):
    pass


def _round8(n: int) -> int:
    return max(64, int(round(n / 8)) * 8)


class ComfyUIClient:
    def __init__(self, base_url: str, workflow_path: str,
                 checkpoint: str | None = None, timeout_sec: int = 300):
        self.base_url = base_url.rstrip("/")
        self.workflow_path = Path(workflow_path)
        self.checkpoint = checkpoint
        self.timeout_sec = timeout_sec
        self.client_id = uuid.uuid4().hex

    def is_up(self) -> bool:
        try:
            requests.get(f"{self.base_url}/system_stats", timeout=3)
            return True
        except requests.RequestException:
            return False

    def _build_workflow(self, prompt: str, negative: str,
                        width: int, height: int, seed: int | None) -> dict:
        wf = json.loads(self.workflow_path.read_text(encoding="utf-8"))
        if seed is None:
            seed = random.randint(0, 2**48)
        for node in wf.values():
            title = node.get("_meta", {}).get("title", "")
            inputs = node.get("inputs", {})
            if title == "positive_prompt":
                inputs["text"] = prompt
            elif title == "negative_prompt":
                inputs["text"] = negative
            elif title == "latent":
                inputs["width"] = _round8(width)
                inputs["height"] = _round8(height)
            elif title == "sampler":
                inputs["seed"] = seed
            elif title == "checkpoint" and self.checkpoint:
                inputs["ckpt_name"] = self.checkpoint
        return wf

    def generate(self, prompt: str, negative: str = "",
                 width: int = 832, height: int = 1216,
                 seed: int | None = None) -> bytes:
        """이미지 1장을 생성해 PNG 바이트로 반환."""
        wf = self._build_workflow(prompt, negative, width, height, seed)
        try:
            r = requests.post(f"{self.base_url}/prompt",
                              json={"prompt": wf, "client_id": self.client_id},
                              timeout=30)
            r.raise_for_status()
        except requests.RequestException as e:
            raise ComfyUIError(f"ComfyUI 큐잉 실패: {e}") from e
        prompt_id = r.json().get("prompt_id")
        if not prompt_id:
            raise ComfyUIError(f"ComfyUI 응답에 prompt_id 없음: {r.text[:200]}")

        deadline = time.time() + self.timeout_sec
        while time.time() < deadline:
            time.sleep(1.5)
            h = requests.get(f"{self.base_url}/history/{prompt_id}", timeout=30)
            h.raise_for_status()
            entry = h.json().get(prompt_id)
            if not entry:
                continue
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise ComfyUIError(f"ComfyUI 실행 오류: {json.dumps(status)[:300]}")
            for output in entry.get("outputs", {}).values():
                for img in output.get("images", []):
                    if img.get("type") != "output":
                        continue
                    v = requests.get(
                        f"{self.base_url}/view",
                        params={"filename": img["filename"],
                                "subfolder": img.get("subfolder", ""),
                                "type": img["type"]},
                        timeout=60)
                    v.raise_for_status()
                    return v.content
        raise ComfyUIError(f"ComfyUI 생성 타임아웃 ({self.timeout_sec}s)")
