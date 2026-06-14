# Reverie QA Bug Reports - 2026-06-15

Environment:
- Windows 11, RTX 4070 Laptop GPU, 8 GB VRAM target.
- Backend: `http://127.0.0.1:8000`.
- Frontend: `http://localhost:1420`.
- ComfyUI: `http://127.0.0.1:8188`, launched with `--lowvram --reserve-vram 0.8`.
- Ollama: `llama3.1:8b`, `nomic-embed-text`.
- TTS: Orpheus-CPP primary on CPU, Piper fallback.

## Verification Summary

Passed:
- Backend full suite: `190 passed`.
- Frontend check: `svelte-check found 0 errors and 0 warnings`.
- Frontend tests: `5 passed`, `12 passed`.
- Tauri compile check: `cargo check` passed.
- Frontend production build: passed.
- Live API smoke: 45 public route checks passed before fixes.
- Live TTS after fixes: Orpheus returned WAV, `duration_seconds=1.536`, backend working set about `3.91 GB`.
- Live image output: `img_aff36ba30bc84154873a2b044c0e062a` served `image/png`, `332811` bytes.
- Live chat after image/TTS checks: returned a non-streaming `llama3.1:8b` response.
- Hotswap checks: image mode unloaded Ollama; chat mode freed ComfyUI cache and reloaded Ollama.

Blocked:
- In-app Browser DOM/screenshot inspection of `http://localhost:1420/#images` was blocked by the Browser plugin URL policy. Automated frontend checks passed, but visual click-through coverage could not be completed through that tool.

## Bugs

### QA-2026-06-15-001 - Image jobs could report completed with no output

Severity: P1
Status: Fixed
Area: Backend image generation / ComfyUI adapter

Evidence:
- Job `img_871ea3528cef4067b2a2d65d738a7143` returned `status=completed` with `output_paths=[]`.
- `GET /api/images/img_871ea3528cef4067b2a2d65d738a7143/outputs/0` returned `image_output_not_found`.
- ComfyUI history for the prompt had `status_str=error`, `completed=false`, `outputs={}`, and `exception_type=torch.AcceleratorError`.

Fix:
- `ComfyUIFluxAdapter.generate()` now raises `image_comfy_execution_failed` for ComfyUI error histories.
- Empty ComfyUI histories now raise `image_comfy_no_outputs`.
- The service now fails any adapter result with an empty output list instead of marking it complete.

Verification:
- Added regression tests for ComfyUI error histories, empty histories, and empty adapter outputs.
- `tests/test_image_generation_service.py`: `23 passed`.
- Full backend suite: `190 passed`.
- Clean image rerun produced and served `reverie_img_aff36ba30bc84154873a2b044c0e062a_00001_.png`.

### QA-2026-06-15-002 - TTS `duration_seconds` reported generation time

Severity: P2
Status: Fixed
Area: Backend TTS API metadata

Evidence:
- Before fix, `POST /api/tts/generate` for `Ready.` returned about `98k` base64 chars but reported `duration_seconds` around `11-14s`.
- The actual WAV payload size is about `1.536s` of 24 kHz mono PCM.

Fix:
- Orpheus and Piper WAV backends now report parsed WAV duration via `estimate_wav_duration()` instead of wall-clock synthesis time.

Verification:
- Added regression test for Orpheus-CPP audio duration.
- Live check after backend restart: elapsed synthesis `18.75s`, returned `duration_seconds=1.536`.

### QA-2026-06-15-003 - Orpheus-CPP CPU model consumed most system RAM

Severity: P1
Status: Fixed
Area: TTS runtime resource usage

Evidence:
- Before fix, one short Orpheus TTS call left the backend Python worker around `14.48 GB` working set.
- ComfyUI reported system `ram_free` under `1 GB`.
- Cause: `orpheus-cpp` constructs llama.cpp with `n_ctx=0`, which allocates a maximum context KV cache.

Fix:
- Added `REVERIE_TTS_ORPHEUS_CPP_N_CTX=4096`.
- Reverie now bounds Orpheus-CPP llama.cpp context during wrapper initialization.

Verification:
- Added config and constructor-bounding tests.
- After fix, one short Orpheus TTS call left backend worker around `3.91-3.97 GB`.
- ComfyUI later reported about `9.7-11.3 GB` system RAM free.

### QA-2026-06-15-004 - ComfyUI CUDA context can enter an error state after failed generation

Severity: P2
Status: Mitigated, still monitor
Area: ComfyUI runtime / CUDA

Evidence:
- After the failed job in QA-2026-06-15-001, `GET /system_stats` returned HTTP 500.
- ComfyUI log showed `torch.AcceleratorError: CUDA error: unknown error`.
- Restarting ComfyUI restored `system_stats` and subsequent generation succeeded.

Mitigation:
- Restarted ComfyUI with documented low-VRAM flags.
- Fixed Reverie so this ComfyUI failure is surfaced as a failed image job instead of a false success.
- Reduced Orpheus CPU RAM pressure, which should lower system-level stress during local AI hotswapping.

Remaining risk:
- If ComfyUI itself hits a CUDA unknown error, its process may still need restart. Reverie now reports image failure correctly.

### QA-2026-06-15-005 - ComfyUI startup logs database/frontend package warnings

Severity: P3
Status: Open environment warning
Area: ComfyUI setup

Evidence:
- ComfyUI log repeatedly prints `comfyui-frontend-package not found in requirements.txt`.
- Startup also logs `Failed to initialize database ... sqlite3.OperationalError unable to open database file`.
- ComfyUI still serves the API and generated an image successfully.

Impact:
- Current Reverie image generation works.
- Future ComfyUI versions may require the database path to be valid.

Recommendation:
- Keep this in setup troubleshooting and revisit the ComfyUI user/database directory permissions.

### QA-2026-06-15-006 - Browser screenshot capture unavailable

Severity: P3
Status: Blocked by tooling
Area: QA tooling

Evidence:
- The in-app Browser loaded `http://127.0.0.1:1420/#images` with title `Reverie`.
- A read-only page evaluation confirmed the Svelte app shell rendered navigation and page text.
- Browser console logs reported no warning/error entries for the loaded tab.
- DOM snapshot returned an empty string for this Svelte route, and screenshot capture timed out/reset the browser automation kernel.

Impact:
- I could not capture a final visual screenshot or complete a full visual click-through through the in-app Browser.
- Frontend static, type, unit, build, and live API contracts were still verified.

Recommendation:
- Re-run manual visual testing or browser-plugin screenshot testing when the browser automation surface can capture this local route reliably.

### QA-2026-06-15-007 - Frontend dev server was not running during final readiness check

Severity: P3
Status: Resolved operationally
Area: Local dev operations

Evidence:
- Final `Invoke-WebRequest http://127.0.0.1:1420` initially failed with connection refused.
- Running `npm run dev -- --host 127.0.0.1 --port 1420` in the foreground started Vite cleanly.
- Starting Vite through an escalated hidden PowerShell host kept the frontend available.

Impact:
- The application UI is inaccessible until the frontend dev server is running, even when backend, Ollama, and ComfyUI are healthy.

Recommendation:
- For normal development, run the documented frontend command in a terminal and leave that terminal open.
- For Codex-managed background runs on this workstation, start Vite outside the managed sandbox so the background process is not torn down.
