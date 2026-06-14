# Reverie Installation Guide

This guide is for a fresh local Windows setup. It is intentionally explicit:
copy commands in order, check the expected result, then move to the next step.

Reverie is a local-first development app, not a packaged installer yet.

## What Gets Installed

Required for the main app:

1. Ollama for chat and embeddings.
2. Python backend on `http://127.0.0.1:8000`.
3. Svelte frontend on `http://localhost:1420`.

Required for the full local media experience:

4. Orpheus-CPP TTS model files plus Piper fallback voice files.
5. ComfyUI on `http://127.0.0.1:8188`.
6. Flux Schnell FP8 checkpoint for local image generation.

Default model choices:

| Purpose | Model/artifact | Runtime | Required for first full local setup |
|---|---|---|---|
| Chat | `llama3.1:8b` | Ollama | Yes |
| Embeddings | `nomic-embed-text` | Ollama | Yes |
| Memory extraction/reflection LLM | Reuses `llama3.1:8b` unless `REVERIE_MEMORY_LLM_MODEL` is set | Ollama | No separate model |
| TTS | Orpheus `orpheus-3b-0.1-ft-q4_k_m.gguf` plus SNAC `decoder_model.onnx` | `orpheus-cpp` CPU backend | Yes for voice |
| TTS fallback | Piper `en_US-lessac-medium.onnx`, stored as `reverie_default.onnx` | `piper-tts` CPU backend | Yes as fallback |
| Images | `Comfy-Org/flux1-schnell`, file `flux1-schnell-fp8.safetensors` | ComfyUI | Yes for image generation |
| Orpheus source model | `canopylabs/orpheus-3b-0.1-ft` | Upstream model reference | No separate download for the default GGUF path |
| Optional Flux GGUF experiment | `flux1-schnell-Q4_0.gguf` plus `clip_l.safetensors` and `t5xxl_fp8_e4m3fn.safetensors` | ComfyUI-GGUF | No |
| Legacy SD 1.5 preview workflow | `v1-5-pruned-emaonly.safetensors` | ComfyUI | No |

See [Tech Stack and Model Inventory](TECH_STACK_MODELS.md) for the complete
model stack, local paths, and license notes.

Do not use Flux.1 Dev as the default image model for this project. Flux.1 Dev
and its GGUF conversions are not safe to assume for commercial use.

## 1. Prerequisites

Install these first:

- Git for Windows
- Python 3.11 from python.org
- Node.js 20+ with npm
- Rust stable, only needed for Tauri desktop mode
- Ollama
- NVIDIA driver, recommended for ComfyUI

Verify PowerShell can see the basics:

```powershell
git --version
py -3.11 --version
node --version
npm --version
rustc --version
```

If `rustc` is missing, Tauri will not work yet. Backend plus browser frontend can
still run.

## 2. Clone The Repo

```powershell
cd C:\
git clone https://github.com/Bustaboy/Reverie-Companion.git
cd C:\Reverie-Companion
git status
```

Expected:

```text
On branch ...
```

## 3. Install Ollama Models

Open Ollama once from the Start Menu, or run the Ollama installer if it is not
installed.

PowerShell sometimes cannot find `ollama` on PATH immediately after install. Use
this helper so both cases work:

```powershell
$Ollama = "ollama"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  $Ollama = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
}
if (-not (Test-Path $Ollama) -and $Ollama -ne "ollama") {
  throw "Ollama is not installed. Install it from https://ollama.com, then rerun this step."
}
```

Pull the required models:

```powershell
& $Ollama pull llama3.1:8b
& $Ollama pull nomic-embed-text
& $Ollama list
```

Expected list includes:

```text
llama3.1:8b
nomic-embed-text
```

Verify the Ollama HTTP API:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags | ConvertTo-Json -Depth 5
```

Expected JSON includes both model names.

## 4. Backend Setup

From repo root:

```powershell
cd C:\Reverie-Companion\backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
copy .env.example .env
python -m pip check
```

Expected:

```text
No broken requirements found.
```

Important Python rule: create and use the venv with Python 3.11 only. Do not use
MSYS2 Python or Python 3.14 for this backend.

If you see:

```text
ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'
```

repair the venv from `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pip install --force-reinstall -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

## 5. Backend `.env`

Keep these values in `backend\.env`:

```env
REVERIE_OLLAMA_HOST="http://localhost:11434"
REVERIE_OLLAMA_MODEL="llama3.1:8b"
REVERIE_MEMORY_EMBEDDING_MODEL="nomic-embed-text"
REVERIE_CORS_ORIGINS='["http://localhost:1420","http://localhost:5173"]'
```

For TTS and image generation, keep these values:

```env
REVERIE_TTS_ENABLED=true
REVERIE_TTS_PRIMARY_BACKEND="orpheus"
REVERIE_TTS_ORPHEUS_RUNTIME="cpp"
REVERIE_TTS_ORPHEUS_MODEL_ID="canopylabs/orpheus-3b-0.1-ft"
REVERIE_TTS_ORPHEUS_CPP_MODEL_ID="isaiahbjork/orpheus-3b-0.1-ft-Q4_K_M-GGUF"
REVERIE_TTS_ORPHEUS_TIMEOUT_SECONDS=120
REVERIE_TTS_ORPHEUS_DEFAULT_VOICE_ID="tara"
REVERIE_TTS_ORPHEUS_CPP_LANGUAGE="en"
REVERIE_TTS_ORPHEUS_CPP_N_GPU_LAYERS=0
REVERIE_TTS_ORPHEUS_CPP_N_THREADS=0
REVERIE_TTS_ORPHEUS_CPP_N_CTX=4096
REVERIE_TTS_ORPHEUS_CPP_PRE_BUFFER_SECONDS=1.0
REVERIE_TTS_DEVICE="cpu"
REVERIE_TTS_PIPER_VOICE_DIR="./models/piper"
REVERIE_TTS_PIPER_MODEL_PATH="./models/piper/reverie_default.onnx"
REVERIE_TTS_PIPER_TIMEOUT_SECONDS=20

REVERIE_LOCAL_AI_HOTSWAP_ENABLED=true
REVERIE_LOCAL_AI_HOTSWAP_TIMEOUT_SECONDS=3
REVERIE_LOCAL_AI_UNLOAD_OLLAMA_BEFORE_IMAGES=true
REVERIE_LOCAL_AI_UNLOAD_COMFYUI_BEFORE_CHAT=true
REVERIE_IMAGE_GENERATION_ENABLED=true
REVERIE_IMAGE_GENERATION_COMFYUI_URL="http://127.0.0.1:8188"
REVERIE_IMAGE_GENERATION_DEFAULT_PRESET="preview_8gb"
REVERIE_IMAGE_GENERATION_COMFYUI_WORKFLOW_PATH="../config/comfyui/reverie-flux-schnell-fp8.api.json"
REVERIE_IMAGE_GENERATION_COMFYUI_POSITIVE_NODE_ID="3"
REVERIE_IMAGE_GENERATION_COMFYUI_POSITIVE_INPUT="text"
REVERIE_IMAGE_GENERATION_COMFYUI_NEGATIVE_NODE_ID="4"
REVERIE_IMAGE_GENERATION_COMFYUI_NEGATIVE_INPUT="text"
REVERIE_IMAGE_GENERATION_COMFYUI_WIDTH_NODE_ID="5"
REVERIE_IMAGE_GENERATION_COMFYUI_WIDTH_INPUT="width"
REVERIE_IMAGE_GENERATION_COMFYUI_HEIGHT_NODE_ID="5"
REVERIE_IMAGE_GENERATION_COMFYUI_HEIGHT_INPUT="height"
REVERIE_IMAGE_GENERATION_COMFYUI_STEPS_NODE_ID="6"
REVERIE_IMAGE_GENERATION_COMFYUI_STEPS_INPUT="steps"
REVERIE_IMAGE_GENERATION_COMFYUI_GUIDANCE_NODE_ID="6"
REVERIE_IMAGE_GENERATION_COMFYUI_GUIDANCE_INPUT="cfg"
REVERIE_IMAGE_GENERATION_COMFYUI_SEED_NODE_ID="6"
REVERIE_IMAGE_GENERATION_COMFYUI_SEED_INPUT="seed"
REVERIE_IMAGE_GENERATION_COMFYUI_SAVE_NODE_ID="8"
REVERIE_IMAGE_GENERATION_COMFYUI_SAVE_INPUT="filename_prefix"
```

## 6. Run Backend

From `backend/` with the venv active:

```powershell
uvicorn app.main:app --reload
```

Open a second PowerShell and check:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health | ConvertTo-Json -Depth 8
```

Expected:

```text
"status": "ok"
"model_available": true
```

If status is `degraded`, Ollama is missing, stopped, or does not have
`llama3.1:8b`.

## 7. Frontend Setup

Open a new terminal:

```powershell
cd C:\Reverie-Companion\frontend
npm install
npm run check
npm run test
npm run dev
```

Open:

```text
http://localhost:1420
```

Expected:

- The UI loads.
- The status shows the local backend is ready.
- Chat can send a message and receive a response.

## 8. Tauri Desktop Mode

Only do this after backend plus browser frontend work:

```powershell
cd C:\Reverie-Companion\frontend
rustup update stable
npm run tauri dev
```

If Tauri fails before the app opens, fix Rust/WebView2/C++ Build Tools first.

## 9. Install TTS Models

The Python packages are installed through `backend/requirements.txt`, but the
Orpheus GGUF model, SNAC decoder, and Piper fallback voice are local model files
and are not committed.

From `backend/` with the venv active, first predownload the Orpheus files:

```powershell
@'
from huggingface_hub import hf_hub_download

files = [
    (
        "isaiahbjork/orpheus-3b-0.1-ft-Q4_K_M-GGUF",
        "orpheus-3b-0.1-ft-q4_k_m.gguf",
        None,
    ),
    (
        "onnx-community/snac_24khz-ONNX",
        "decoder_model.onnx",
        "onnx",
    ),
]

for repo_id, filename, subfolder in files:
    path = hf_hub_download(repo_id=repo_id, filename=filename, subfolder=subfolder)
    print(path)
'@ | .\.venv\Scripts\python.exe -
```

Expected:

```text
orpheus-3b-0.1-ft-q4_k_m.gguf
decoder_model.onnx
```

Then download the Piper fallback voice:

```powershell
New-Item -ItemType Directory -Path .\models\piper -Force
$voiceBase = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
Invoke-WebRequest -Uri $voiceBase -OutFile .\models\piper\reverie_default.onnx
Invoke-WebRequest -Uri "$voiceBase.json" -OutFile .\models\piper\reverie_default.onnx.json
```

Expected local files:

```text
backend\models\piper\reverie_default.onnx
backend\models\piper\reverie_default.onnx.json
```

Keep Orpheus on CPU unless smoke testing proves it is too slow or degraded:

```env
REVERIE_TTS_PRIMARY_BACKEND="orpheus"
REVERIE_TTS_ORPHEUS_RUNTIME="cpp"
REVERIE_TTS_ORPHEUS_CPP_N_GPU_LAYERS=0
REVERIE_TTS_ORPHEUS_CPP_N_CTX=4096
REVERIE_TTS_DEVICE="cpu"
```

Keep `REVERIE_TTS_ORPHEUS_CPP_N_CTX=4096`. The Orpheus-CPP wrapper can pass
`n_ctx=0` to llama.cpp, which means "use the full model context" and can push
the backend worker above 14 GB RAM on this workstation. Reverie bounds that
context during backend startup, and direct Orpheus smoke tests should do the
same.

If Uvicorn is not launched from an activated venv, also set:

```env
REVERIE_TTS_PIPER_BINARY_PATH="C:/Reverie-Companion/backend/.venv/Scripts/piper.exe"
```

Direct Orpheus smoke test:

```powershell
@'
import wave
from pathlib import Path

import llama_cpp
from orpheus_cpp import OrpheusCpp

original_llama = llama_cpp.Llama

def bounded_llama(*args, **kwargs):
    if int(kwargs.get("n_ctx") or 0) <= 0:
        kwargs["n_ctx"] = 4096
    return original_llama(*args, **kwargs)

llama_cpp.Llama = bounded_llama
try:
    model = OrpheusCpp(n_gpu_layers=0, n_threads=0, verbose=False, lang="en")
    sample_rate, samples = model.tts(
        "Ready.",
        options={"voice_id": "tara", "pre_buffer_size": 0.25, "max_tokens": 256},
    )
finally:
    llama_cpp.Llama = original_llama

out = Path("data/tts_smoke_orpheus.wav")
out.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(out), "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(sample_rate)
    wav_file.writeframes(samples.squeeze().astype("int16").tobytes())
print(out)
'@ | .\.venv\Scripts\python.exe -
```

Expected:

```text
data\tts_smoke_orpheus.wav
```

Backend TTS API smoke test:

```powershell
$body = @{
  text = "Ready."
  voice_id = "reverie_default"
  stream = $false
  audio_format = "wav"
}

Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/tts/generate" `
  -Method Post `
  -Body (ConvertTo-Json $body) `
  -ContentType "application/json"
```

Expected:

```text
backend: orpheus
audio_base64: present
```

If Orpheus fails and the Piper files are present, Reverie should retry with
Piper and return `backend: piper`.

Only if CPU Orpheus is too slow, benchmark a CUDA `llama-cpp-python` wheel and
`REVERIE_TTS_ORPHEUS_CPP_N_GPU_LAYERS`. Do not leave GPU TTS enabled unless the
benchmark is faster on that machine. The current project workstation keeps the
CPU wheel because CUDA offload was slower and needed extra DLL path setup. See
[TTS Setup](TTS_SETUP.md) for the exact GPU-offload command and rollback command.

## 10. Install ComfyUI

If ComfyUI already exists on this workstation, use the project layout:

```text
C:\ComfyUI\resources\ComfyUI
C:\Comfy-UI
```

Repair dependencies if needed:

```powershell
C:\Comfy-UI\.venv\Scripts\python.exe -m pip install -r C:\ComfyUI\resources\ComfyUI\requirements.txt
C:\Comfy-UI\.venv\Scripts\python.exe -m pip install comfyui-frontend-package
```

If you are installing ComfyUI from scratch, follow the official ComfyUI install
instructions, then adapt the paths in this guide so:

```text
ComfyUI code path = C:\ComfyUI\resources\ComfyUI
ComfyUI base path = C:\Comfy-UI
```

## 11. Install The ComfyUI Image Model

Create the checkpoint folder:

```powershell
New-Item -ItemType Directory -Path C:\Comfy-UI\models\checkpoints -Force
```

Download the default image model:

```powershell
Invoke-WebRequest `
  -Uri "https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors" `
  -OutFile C:\Comfy-UI\models\checkpoints\flux1-schnell-fp8.safetensors
```

Verify it:

```powershell
Get-Item C:\Comfy-UI\models\checkpoints\flux1-schnell-fp8.safetensors |
  Select-Object FullName,Length
```

Expected:

```text
Length: 17236328572
```

Optional advanced GGUF files are documented in [ComfyUI Setup](COMFYUI_SETUP.md),
but they are not the default because the split VAE path can require gated access.

## 12. Start ComfyUI

Use this exact command:

```powershell
C:\Comfy-UI\.venv\Scripts\python.exe C:\ComfyUI\resources\ComfyUI\main.py `
  --listen 127.0.0.1 `
  --port 8188 `
  --base-directory C:\Comfy-UI `
  --user-directory C:\Comfy-UI\user `
  --output-directory C:\Reverie-Companion\backend\data\images\generated `
  --input-directory C:\Comfy-UI\input `
  --lowvram `
  --reserve-vram 0.8 `
  --disable-api-nodes `
  --disable-auto-launch
```

Expected:

```text
To see the GUI go to: http://127.0.0.1:8188
```

Verify ComfyUI sees the model:

```powershell
$checkpointInfo = Invoke-RestMethod http://127.0.0.1:8188/object_info/CheckpointLoaderSimple
$checkpointInfo.CheckpointLoaderSimple.input.required.ckpt_name[0]
```

Expected list includes:

```text
flux1-schnell-fp8.safetensors
```

Verify ComfyUI is using the NVIDIA GPU:

```powershell
$stats = Invoke-RestMethod http://127.0.0.1:8188/system_stats
$stats.system.pytorch_version
$stats.devices | Select-Object name,type,vram_total,vram_free
nvidia-smi
```

Expected:

```text
pytorch_version includes +cu
device name starts with cuda:0 NVIDIA GeForce RTX 4070
nvidia-smi shows a python.exe process on the GPU after the model loads
```

`GPU-Util` can be `0%` while ComfyUI is idle. During generation it should rise.
Flux Schnell FP8 is a large checkpoint, so on an 8GB GPU it uses CUDA plus
low-VRAM offloading. A cold first image can take 1-2 minutes; cached preview
runs are usually faster. If a smoke test appears to run for 10+ minutes, check
that the polling command is using `$response.job`, not `$response.job_id`.

Reverie hotswaps local model memory by default:

- Before chat, the backend calls ComfyUI `/free` so the image model does not
  stay resident while Ollama is answering.
- Before image generation, the backend asks Ollama to unload loaded chat and
  embedding models with `keep_alive: 0`.
- This is a latency tradeoff on 8GB GPUs: the next model may need a cold load,
  but the app avoids holding chat and image models in VRAM at the same time.

## 13. Image Smoke Test

Start backend and ComfyUI first, then run:

```powershell
$body = @{
  conversation_id = "setup-smoke"
  prompt = "a warm portrait of a friendly AI companion in soft window light"
  negative_prompt = "low quality, blurry, distorted"
  quality_preset = "preview_8gb"
}

$response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/images/generate" `
  -Method Post `
  -Body (ConvertTo-Json $body) `
  -ContentType "application/json"

$job = $response.job
$job
```

Poll it:

```powershell
do {
  Start-Sleep -Seconds 5
  $job = Invoke-RestMethod "http://127.0.0.1:8000/api/images/$($job.job_id)"
  "{0} {1}" -f $job.status, $job.phase
} until ($job.status -in @("completed", "failed", "cancelled"))

$job
```

Expected:

```text
status: completed
output_paths: contains one PNG
```

## 14. Full Verification Commands

Backend:

```powershell
cd C:\Reverie-Companion\backend
.\.venv\Scripts\Activate.ps1
python -m pip check
python -m pytest
```

Frontend:

```powershell
cd C:\Reverie-Companion\frontend
npm run check
npm run test
npm run build
```

Tauri:

```powershell
cd C:\Reverie-Companion\frontend\src-tauri
cargo check
```

## 15. Common Failures

| Symptom | Likely cause | Fix |
|---|---|---|
| `ollama` is not recognized | Ollama is not on PATH | Use `$env:LOCALAPPDATA\Programs\Ollama\ollama.exe` |
| `/health` is degraded | Ollama stopped or models missing | Start Ollama, pull `llama3.1:8b` and `nomic-embed-text` |
| `pydantic_core._pydantic_core` missing | Python/venv ABI mismatch | Reinstall requirements with Python 3.11 venv |
| `npm` cannot find `npm-cli.js` | Broken PowerShell npm shim or user npm prefix | Use `npm.cmd run check`, `npm.cmd run test`, and `npm.cmd run dev`, or repair the local Node/NVM install |
| Frontend cannot reach backend | Backend down or CORS missing `1420` | Run backend and keep default CORS |
| `tts_orpheus_cpp_dependency_missing` | Orpheus packages missing from the venv | Run `python -m pip install -r requirements.txt` |
| First TTS request is very slow | Orpheus model files are cold-downloading or cold-loading | Predownload in step 9 and retry |
| Backend RAM jumps above 10 GB after TTS | Orpheus-CPP context is unbounded | Keep `REVERIE_TTS_ORPHEUS_CPP_N_CTX=4096` and restart the backend |
| TTS says Piper model missing | Piper fallback voice files missing | Download `reverie_default.onnx` and `.onnx.json` |
| `image_comfy_unreachable` | ComfyUI down or wrong URL | Start ComfyUI at `127.0.0.1:8188` |
| `image_comfy_prompt_rejected` | ComfyUI cannot load workflow/model | Verify `flux1-schnell-fp8.safetensors` appears in `CheckpointLoaderSimple` |
| `image_comfy_execution_failed` | ComfyUI accepted the prompt but failed while executing it | Open the job details, check the ComfyUI log, fix the reported node/model/CUDA error, then retry |
| `image_comfy_no_outputs` or `image_no_outputs` | ComfyUI finished without a saved image | Verify the workflow save node and output directory, then retry |
| Repeated `GET /api/images/` 404 while polling | Smoke test used the wrapper response as the job | Set `$job = $response.job` before polling |
| Gallery says output missing | ComfyUI output folder is wrong or the job failed before writing a file | Start ComfyUI with the `--output-directory` shown above, then check the job error |
| CUDA out of memory | Too much VRAM is already used | Close GPU apps, use `preview_8gb`, batch size 1 |
| ComfyUI reports CUDA unknown error | CUDA context entered a bad state after a failed generation | Restart ComfyUI, then retry with `preview_8gb` |
| Chat is slow right after an image | Hotswap unloaded Ollama to free VRAM | Expected on 8GB; the model is cold-loading again |
| Image is slow right after chat | Hotswap unloaded Ollama and ComfyUI must load Flux | Expected on 8GB; this avoids CUDA OOM |

## 16. Clean Reset

Stop backend and frontend first.

Delete local runtime data only if you are okay losing local memories, images,
characters, drafts, journal entries, and test artifacts:

```powershell
Remove-Item -Recurse -Force C:\Reverie-Companion\backend\data
```

Do not delete `C:\Comfy-UI\models` unless you want to redownload large model
files.

## 17. Minimal First Run Order

1. Install Ollama.
2. Pull `llama3.1:8b`.
3. Pull `nomic-embed-text`.
4. Set up backend venv.
5. Start backend and verify `/health`.
6. Set up frontend and open `http://localhost:1420`.
7. Download Orpheus TTS files plus Piper fallback voice and test TTS.
8. Install/start ComfyUI.
9. Download `flux1-schnell-fp8.safetensors`.
10. Run the image smoke test.
