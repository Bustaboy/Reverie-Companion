# Reverie Tech Stack and Model Inventory

Last updated: June 14, 2026.

This is the canonical list of local runtimes and model artifacts referenced by
the current Reverie codebase and setup docs. If a model changes, update this
file, `backend/.env.example`, and the relevant setup guide in the same change.

## Runtime Stack

| Layer | Current choice | Notes |
|---|---|---|
| Desktop shell | Tauri 2 + Rust | Packaged desktop runtime. |
| Frontend | SvelteKit 2, Svelte 5, Vite 6, TypeScript | Local UI served on `http://localhost:1420` in dev. |
| Backend | FastAPI, Python 3.11, Uvicorn | Local API on `http://127.0.0.1:8000`. |
| Chat runtime | Ollama local API | Required for chat. Default host: `http://localhost:11434`. |
| Memory store | LanceDB with optional mem0 write-through | Data stays under `backend/data` by default. |
| TTS runtime | Orpheus-CPP CPU primary, Piper CPU fallback | Orpheus is the emotional voice target. The default local runtime uses CPU `llama.cpp` layers so TTS does not consume VRAM. |
| Image runtime | ComfyUI | Optional for chat, required for rendered Moment Capture images. |
| Target hardware | RTX 4070 laptop GPU, 8GB VRAM | Heavy model families are hotswapped instead of kept resident together. |

## Active Model Defaults

| Area | Model or artifact | Runtime | Required for | Local setting/path | License/commercial note |
|---|---|---|---|---|---|
| Chat LLM | `llama3.1:8b` | Ollama | Chat and default local LLM calls | `REVERIE_OLLAMA_MODEL="llama3.1:8b"` | Meta Llama license via Ollama. Check upstream terms before redistribution. |
| Memory embeddings | `nomic-embed-text` | Ollama | Memory write/search when memory is enabled | `REVERIE_MEMORY_EMBEDDING_MODEL="nomic-embed-text"` and `REVERIE_MEMORY_EMBEDDING_DIMENSIONS=768` | Nomic Embed is documented as open weights/code/data under Apache-2.0 in its technical report; still check the packaged model terms before redistribution. |
| Memory extraction / reflection LLM | Reuses `llama3.1:8b` unless overridden | Ollama | mem0 extraction/reflection support | Leave `REVERIE_MEMORY_LLM_MODEL=` empty to reuse chat model | No separate model is required by the standard setup. |
| Primary TTS | `isaiahbjork/orpheus-3b-0.1-ft-Q4_K_M-GGUF`, file `orpheus-3b-0.1-ft-q4_k_m.gguf` | `orpheus-cpp` + `llama-cpp-python` CPU wheel | Emotional local voice playback | Hugging Face cache, configured by `REVERIE_TTS_ORPHEUS_CPP_MODEL_ID` | Apache-2.0 model repo. Keep downloaded GGUF files local; do not commit them. |
| Orpheus audio decoder | `onnx-community/snac_24khz-ONNX`, file `decoder_model.onnx` | ONNX Runtime through `orpheus-cpp` | Decoding Orpheus audio tokens | Hugging Face cache | MIT model repo. Downloaded automatically by Orpheus-CPP. |
| Orpheus source model | `canopylabs/orpheus-3b-0.1-ft` | Upstream Orpheus reference | Quality target and source lineage | `REVERIE_TTS_ORPHEUS_MODEL_ID="canopylabs/orpheus-3b-0.1-ft"` | Apache-2.0 on Hugging Face; access can require accepting model conditions. |
| TTS fallback voice | Piper `en_US-lessac-medium.onnx`, saved locally as `reverie_default.onnx` plus `.onnx.json` | `piper-tts` subprocess | Fallback local voice playback | `backend/models/piper/reverie_default.onnx` | `rhasspy/piper-voices` is MIT licensed. Voice files are local-only and are not committed. |
| Default image model | `Comfy-Org/flux1-schnell`, file `flux1-schnell-fp8.safetensors` | ComfyUI `CheckpointLoaderSimple` | Moment Capture/image generation | `C:\Comfy-UI\models\checkpoints\flux1-schnell-fp8.safetensors` and `config/comfyui/reverie-flux-schnell-fp8.api.json` | Apache-2.0. This replaced Flux.1 Dev as the project default. |

## Optional or Experimental Model References

These are referenced by code or docs but are not required for the standard
fresh setup.

| Area | Model or artifact | Runtime | Status | Notes |
|---|---|---|---|---|
| Alternate Orpheus runtime | `canopylabs/orpheus-3b-0.1-ft` via `orpheus-speech`/vLLM | Optional GPU-backed Orpheus adapter | Not the Windows default | Apache-2.0 on Hugging Face, but access can require accepting model conditions. Use only if native vLLM support is practical for the target machine. |
| Flux GGUF experiment | `city96/FLUX.1-schnell-gguf`, file `flux1-schnell-Q4_0.gguf` | ComfyUI-GGUF custom node | Optional experiment | Apache-2.0. Requires a split Flux workflow and custom node support. |
| Flux split text encoders | `comfyanonymous/flux_text_encoders`, files `clip_l.safetensors` and `t5xxl_fp8_e4m3fn.safetensors` | ComfyUI DualCLIPLoader-style workflows | Optional experiment | Apache-2.0. Not used by the default FP8 checkpoint workflow. |
| Legacy SD 1.5 preview workflow | `v1-5-pruned-emaonly.safetensors` | ComfyUI `CheckpointLoaderSimple` | Legacy fallback workflow only | Referenced by `config/comfyui/reverie-sd15-preview.api.json`. Not installed by the standard setup and not the default. Verify the exact upstream checkpoint license before use or redistribution. |
| Personal LoRA base model | None selected yet | Future training pipeline | Not active | Current Personal LoRA work stores reviewable examples and manifests only; it does not ship a training base model. |
| Reranker | None | Not used | Not active | The memory stack intentionally has no resident reranker. |
| STT / ASR | None | Not used | Not active | Voice input is not part of the current model stack. |
| Vision evaluator / CLIP | None | Not used | Not active | Visual consistency evals are deterministic contract tests, not CLIP/cloud scoring. |

## 8GB Residency Rules

- Keep Ollama chat/embedding models and ComfyUI image models from staying
  resident at the same time on 8GB GPUs.
- Before chat, Reverie can call ComfyUI `/free`.
- Before image generation, Reverie can ask Ollama to unload loaded models with
  `keep_alive: 0`.
- Orpheus-CPP runs on CPU by default with `REVERIE_TTS_ORPHEUS_CPP_N_GPU_LAYERS=0`.
- Orpheus-CPP context is bounded with `REVERIE_TTS_ORPHEUS_CPP_N_CTX=4096`;
  do not use an unbounded `n_ctx=0` smoke test on this workstation.
- Piper runs on CPU as the fallback backend when Orpheus is unavailable or too
  slow for a request.
- If CPU Orpheus is degraded, a CUDA `llama-cpp-python` wheel plus
  `REVERIE_TTS_ORPHEUS_CPP_N_GPU_LAYERS` can be benchmarked, but it is not the
  default because the current Windows probe was slower and ComfyUI needs VRAM
  headroom.
- Image generation stays queued with batch size 1 and preview-first defaults.

## Models Not To Treat As Current Defaults

- Do not document Flux.1 Dev or Flux.1 Dev GGUF conversions as Reverie's default
  image model. They are not safe to assume for commercial use without a separate
  license.
- Do not document SDXL Turbo, hosted image APIs, cloud LLMs, CLIP scoring, or a
  resident reranker as current Reverie defaults. They are not part of the active
  setup.

## Upstream References

- `Comfy-Org/flux1-schnell`: https://huggingface.co/Comfy-Org/flux1-schnell
- `rhasspy/piper-voices`: https://huggingface.co/rhasspy/piper-voices
- `canopylabs/orpheus-3b-0.1-ft`: https://huggingface.co/canopylabs/orpheus-3b-0.1-ft
- `isaiahbjork/orpheus-3b-0.1-ft-Q4_K_M-GGUF`: https://huggingface.co/isaiahbjork/orpheus-3b-0.1-ft-Q4_K_M-GGUF
- `onnx-community/snac_24khz-ONNX`: https://huggingface.co/onnx-community/snac_24khz-ONNX
- `orpheus-cpp`: https://pypi.org/project/orpheus-cpp/
- `llama-cpp-python`: https://github.com/abetlen/llama-cpp-python
- `city96/FLUX.1-schnell-gguf`: https://huggingface.co/city96/FLUX.1-schnell-gguf
- `comfyanonymous/flux_text_encoders`: https://huggingface.co/comfyanonymous/flux_text_encoders
- `llama3.1` in Ollama: https://ollama.com/library/llama3.1
- `nomic-embed-text` in Ollama: https://ollama.com/library/nomic-embed-text
- Nomic Embed technical report: https://arxiv.org/abs/2402.01613
