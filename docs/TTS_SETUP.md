# TTS Setup for Reverie Voice

Reverie uses Orpheus as the primary emotional TTS backend and Piper as the
fallback. The default Orpheus path is `orpheus-cpp` with `llama.cpp` CPU layers
set to `0` and context bounded to `4096`, so voice generation does not fight
ComfyUI for RTX 4070 8GB VRAM or consume most system RAM.

Model summary:

| Role | Model/artifact | Runtime | Required |
|---|---|---|---|
| Primary TTS | `isaiahbjork/orpheus-3b-0.1-ft-Q4_K_M-GGUF` | `orpheus-cpp` + `llama-cpp-python` CPU wheel | Yes for full voice |
| Orpheus source model | `canopylabs/orpheus-3b-0.1-ft` | Upstream Orpheus model reference | Documented source/quality target |
| Audio decoder | `onnx-community/snac_24khz-ONNX` | ONNX Runtime | Downloaded by Orpheus-CPP |
| Fallback TTS | Piper `en_US-lessac-medium.onnx`, saved as `reverie_default.onnx` | `piper-tts` subprocess | Yes as fallback |

See [Tech Stack and Model Inventory](TECH_STACK_MODELS.md) for the complete
model list and license notes.

## Install Packages

From `backend/` with the virtualenv active:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip check
```

Expected:

```text
No broken requirements found.
```

`requirements.txt` installs:

- `orpheus-cpp`
- `llama-cpp-python` from the CPU wheel index
- `piper-tts`

## Download Orpheus Models

The Orpheus model files are large and must stay local. Download them into the
Hugging Face cache by running this from `backend/`:

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

- One printed path ending in `orpheus-3b-0.1-ft-q4_k_m.gguf`.
- One printed path ending in `decoder_model.onnx`.

Do not copy either file into the repo. The root `.gitignore` excludes local AI
weights and cache folders.

## Download Piper Fallback Voice

From `backend/`:

```powershell
New-Item -ItemType Directory -Path .\models\piper -Force
$voiceBase = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
Invoke-WebRequest -Uri $voiceBase -OutFile .\models\piper\reverie_default.onnx
Invoke-WebRequest -Uri "$voiceBase.json" -OutFile .\models\piper\reverie_default.onnx.json
```

Expected files:

```text
backend/models/piper/reverie_default.onnx
backend/models/piper/reverie_default.onnx.json
```

## Configure `.env`

Use these defaults in `backend/.env`:

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

REVERIE_TTS_PIPER_BINARY_PATH=
REVERIE_TTS_PIPER_VOICE_DIR="./models/piper"
REVERIE_TTS_PIPER_MODEL_PATH="./models/piper/reverie_default.onnx"
REVERIE_TTS_PIPER_TIMEOUT_SECONDS=20
```

Leave `REVERIE_TTS_PIPER_BINARY_PATH` empty when Uvicorn is launched from an
activated backend venv. If Uvicorn starts without the venv active, set:

```env
REVERIE_TTS_PIPER_BINARY_PATH="C:/Reverie-Companion/backend/.venv/Scripts/piper.exe"
```

## CPU vs GPU

Default TTS is CPU:

```env
REVERIE_TTS_DEVICE="cpu"
REVERIE_TTS_ORPHEUS_CPP_N_GPU_LAYERS=0
REVERIE_TTS_ORPHEUS_CPP_N_CTX=4096
```

Keep it that way unless Orpheus CPU synthesis is too slow on the target machine.
This protects the 8GB GPU for ComfyUI image generation, avoids loading chat,
image, and voice models into VRAM at the same time, and prevents the Orpheus-CPP
`n_ctx=0` path from allocating the full model context.

If CPU Orpheus is degraded, GPU offload can be benchmarked, but do not keep it
unless it is faster on the target machine. On the project RTX 4070 laptop test,
the CPU wheel was the stable path; CUDA offload required extra DLL path setup
and partial offload was slower before Reverie bounded the context.

To benchmark CUDA, reinstall `llama-cpp-python` with the CUDA wheel that matches
the installed CUDA runtime:

```powershell
.\.venv\Scripts\python.exe -m pip install --force-reinstall llama-cpp-python==0.3.29 `
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu132
```

Then set either a measured layer count, or `-1` for full offload:

```env
REVERIE_TTS_DEVICE="cuda"
REVERIE_TTS_ORPHEUS_CPP_N_GPU_LAYERS=-1
```

If Windows cannot load `llama.dll` after installing the CUDA wheel, add the
directory containing CUDA runtime DLLs to `PATH` before launching the backend.
On this workstation, ComfyUI provides those DLLs here:

```powershell
$env:PATH = "C:\Comfy-UI\.venv\Lib\site-packages\torch\lib;$env:PATH"
```

Only keep GPU TTS if smoke testing shows it is materially faster than CPU and
does not cause ComfyUI/Ollama VRAM pressure. Otherwise reinstall the CPU wheel:

```powershell
.\.venv\Scripts\python.exe -m pip install --force-reinstall llama-cpp-python==0.3.29 `
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

## Smoke Test

Start the backend, then run:

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

- HTTP 200.
- `backend` is `orpheus`.
- `voice_id` is `reverie_default`.
- `audio_base64` is present.

If Orpheus fails and Piper files are installed, Reverie should retry with Piper.
That fallback response reports `backend: piper`.

## Common Failures

| Symptom | Cause | Fix |
|---|---|---|
| `tts_orpheus_cpp_dependency_missing` | Orpheus-CPP or llama.cpp Python package is missing | Run `python -m pip install -r requirements.txt` |
| First Orpheus request is slow | Cold model load or first Hugging Face download | Predownload with the command above and retry |
| `tts_orpheus_generation_failed` | Orpheus runtime failed mid-generation | Check logs, then verify the direct Orpheus smoke below |
| Backend RAM jumps above 10 GB after TTS | Orpheus-CPP context is unbounded | Keep `REVERIE_TTS_ORPHEUS_CPP_N_CTX=4096` and restart the backend |
| Orpheus CPU is too slow | CPU-only `llama.cpp` is not fast enough on the machine | Try the CUDA wheel and `REVERIE_TTS_ORPHEUS_CPP_N_GPU_LAYERS` only after confirming CPU degradation |
| `tts_piper_binary_missing` | Piper is not installed or not on PATH | Run `python -m pip install -r requirements.txt` or set `REVERIE_TTS_PIPER_BINARY_PATH` |
| `tts_piper_model_missing` | The `.onnx` Piper voice file is missing | Download both Piper voice files to `backend/models/piper` |

## Direct Orpheus Smoke

This bypasses the API and confirms the local Orpheus runtime can synthesize:

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

The file is local test output under `backend/data` and is ignored by git.
