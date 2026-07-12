# 룸엘이스케이프 캐러셀 파이프라인 v2

인스타그램(@roomlescape) 콘텐츠 제작 파이프라인.
콘텐츠 YAML 한 장 → 업로드 가능한 슬라이드 PNG + 캡션까지 자동 생성합니다.

## v1에서 바뀐 것

- **퍼즐 작가(관찰력 테스트) 단계 제거.** `puzzle` / `observation_test` 포맷은 더 이상 지원하지 않습니다.
- 포맷 3종으로 교체:

| 포맷 | 용도 | 비율 | 빈도 |
|---|---|---|---|
| `cctv_moments` | 직원 CCTV 관찰형 캐러셀 (도달 주력) | 4:5 | 주 1–2회 |
| `guest_types` | 손님 유형 캐러셀 (친구 태그 유도) | 4:5 | 월 1–2회 |
| `trailer` | AI 예고편 릴스 스토리보드 (테마당 1개, 고정용) | 9:16 | 8개 한도 내 |

- **배경 이미지는 ComfyUI로 생성.** 슬라이드 YAML에 `bg.prompt`만 적으면
  로컬 ComfyUI API로 배경을 뽑아 슬라이드 뒤에 깔아줍니다.
  ComfyUI가 꺼져 있으면 CSS 그라디언트 폴백으로 렌더링됩니다 (실패하지 않음).

## 설치

```bash
pip install -r requirements.txt
playwright install chromium   # 로컬 최초 1회
```

ComfyUI를 쓰려면 로컬에서 ComfyUI를 띄워두세요 (기본 `http://127.0.0.1:8188`,
`config.yaml`의 `comfyui.base_url`에서 변경).

## 사용법

```bash
# 에피소드 목록
python pipeline.py list

# 렌더링 (ComfyUI 배경 포함)
python pipeline.py render content/episodes/ep001_cctv.yaml

# ComfyUI 없이 (CSS 배경만)
python pipeline.py render content/episodes/ep001_cctv.yaml --no-comfy
```

결과물은 `out/<에피소드 id>/`에 생성됩니다:

```
out/ep001/
  slide_01.png … slide_NN.png   # 그대로 업로드
  caption.txt                   # 캡션 + 해시태그
  slides.html                   # 렌더 소스 (브라우저에서 미리보기 가능)
  assets/                       # ComfyUI 생성 배경
```

## 새 에피소드 만들기

`content/episodes/`의 기존 YAML을 복사해서 문구만 바꾸면 됩니다.
슬라이드 종류(`kind`): `hook`(표지) / `rank`(TOP N) / `type`(유형) / `cta`(마지막) / `scene`(예고편 장면).

배경이 필요한 슬라이드에는:

```yaml
bg:
  prompt: "dark laundromat at night, single washing machine glowing, cinematic, moody"
```

## ComfyUI 워크플로 교체

`comfyui/workflows/bg_txt2img.json`은 표준 SDXL txt2img (API 포맷)입니다.
자기 워크플로를 쓰려면 ComfyUI에서 **Save (API Format)** 로 내보낸 뒤,
노드 `_meta.title`을 다음으로 지정하면 파이프라인이 값을 주입합니다:
`positive_prompt` / `negative_prompt` / `latent` / `sampler` / `checkpoint`
