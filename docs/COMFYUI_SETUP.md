# ComfyUI Setup for Reverie Moment Capture

Reverie uses ComfyUI as an optional local image backend. Chat, memory, journal,
growth, and character runtime must still work when ComfyUI is absent.

The default Reverie image model is:

```text
Comfy-Org/flux1-schnell
file: flux1-schnell-fp8.safetensors
license: Apache-2.0
ComfyUI folder: C:\Comfy-UI\models\checkpoints
workflow: config/comfyui/reverie-flux-schnell-fp8.api.json
```

This is the only image model required for the current default workflow. The
workflow uses `CheckpointLoaderSimple`, so Flux text encoders and GGUF custom
nodes are not required unless you intentionally switch to an experimental split
Flux workflow. The full cross-project model list is in
[Tech Stack and Model Inventory](TECH_STACK_MODELS.md).

Do not use Flux.1 Dev as the default for this project. Flux.1 Dev and its GGUF
conversions are non-commercial/source-available unless you have a separate
license. Flux.1 Schnell is the commercial-friendlier default.

## What You Need

- Windows 11 or Linux.
- NVIDIA GPU recommended. The target project machine is an RTX 4070 laptop GPU
  with 8GB VRAM.
- ComfyUI listening at `http://127.0.0.1:8188`.
- One image job at a time.
- Batch size 1.
- `--lowvram`.
- Preview-first defaults: 512x512, 4 steps, CFG 1.0.

## Folder Layout Used By This Project

This workstation uses a ComfyUI desktop-style layout:

```text
C:\ComfyUI\resources\ComfyUI        # ComfyUI source/app code
C:\Comfy-UI                         # ComfyUI base directory
C:\Comfy-UI\.venv                   # ComfyUI Python environment
C:\Comfy-UI\custom_nodes            # Custom nodes
C:\Comfy-UI\models                  # Model files
C:\Reverie-Companion                # Reverie repo
```

Keep large model files out of the Reverie repo. They belong under
`C:\Comfy-UI\models`.

## Step 1: Install Or Repair ComfyUI

If ComfyUI already opens at `http://127.0.0.1:8188`, keep your existing install.

If this workstation's ComfyUI venv is missing packages, repair it:

```powershell
C:\Comfy-UI\.venv\Scripts\python.exe -m pip install -r C:\ComfyUI\resources\ComfyUI\requirements.txt
C:\Comfy-UI\.venv\Scripts\python.exe -m pip install comfyui-frontend-package
```

Expected success:

```text
Successfully installed ...
```

## Step 2: Install The Flux Schnell Model

Create the model folder:

```powershell
New-Item -ItemType Directory -Path C:\Comfy-UI\models\checkpoints -Force
```

Download the Apache-2.0 Flux Schnell FP8 checkpoint:

```powershell
Invoke-WebRequest `
  -Uri "https://huggingface.co/Comfy-Org/flux1-schnell/resolve/main/flux1-schnell-fp8.safetensors" `
  -OutFile C:\Comfy-UI\models\checkpoints\flux1-schnell-fp8.safetensors
```

Verify the file exists and is the expected size:

```powershell
Get-Item C:\Comfy-UI\models\checkpoints\flux1-schnell-fp8.safetensors |
  Select-Object FullName,Length
```

Expected:

```text
Length: 17236328572
```

## Step 3: Optional GGUF Files

These are installed on this workstation for experimentation, but they are not
the default because split Flux workflows still need a Flux VAE file and the
original BFL VAE endpoint can be gated.

Skip this step for the standard Reverie setup. The active default remains
`flux1-schnell-fp8.safetensors`.

```powershell
New-Item -ItemType Directory -Path C:\Comfy-UI\models\unet,C:\Comfy-UI\models\text_encoders -Force

Invoke-WebRequest `
  -Uri "https://huggingface.co/city96/FLUX.1-schnell-gguf/resolve/main/flux1-schnell-Q4_0.gguf" `
  -OutFile C:\Comfy-UI\models\unet\flux1-schnell-Q4_0.gguf

Invoke-WebRequest `
  -Uri "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors" `
  -OutFile C:\Comfy-UI\models\text_encoders\clip_l.safetensors

Invoke-WebRequest `
  -Uri "https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors" `
  -OutFile C:\Comfy-UI\models\text_encoders\t5xxl_fp8_e4m3fn.safetensors
```

Install ComfyUI-GGUF only if you are building a GGUF workflow:

```powershell
git clone https://github.com/city96/ComfyUI-GGUF C:\Comfy-UI\custom_nodes\ComfyUI-GGUF
C:\Comfy-UI\.venv\Scripts\python.exe -m pip install -r C:\Comfy-UI\custom_nodes\ComfyUI-GGUF\requirements.txt
```

Restart ComfyUI after installing custom nodes.

## Step 4: Start ComfyUI

Use this exact command for the project workstation:

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

Expected log line:

```text
To see the GUI go to: http://127.0.0.1:8188
```

## Step 5: Verify ComfyUI Sees The Model

```powershell
$checkpointInfo = Invoke-RestMethod http://127.0.0.1:8188/object_info/CheckpointLoaderSimple
$checkpointInfo.CheckpointLoaderSimple.input.required.ckpt_name[0]
```

Expected list includes:

```text
flux1-schnell-fp8.safetensors
```

## Step 6: Verify CUDA

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
The project starts ComfyUI with `--lowvram --reserve-vram 0.8` because Flux
Schnell FP8 is larger than the 8GB VRAM budget. That is expected: the model uses
CUDA, but low-VRAM offloading keeps the app from crashing. A cold first preview
can take 1-2 minutes; cached previews are usually faster.

## Step 7: Configure Reverie

Copy `backend/.env.example` to `backend/.env`, then keep these image settings:

```env
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

Restart the Reverie backend after changing `.env`.

With hotswap enabled, chat and image generation intentionally do not keep both
large model families resident in VRAM:

- Chat start frees ComfyUI with `/free`.
- Image start unloads Ollama chat/embedding models with `keep_alive: 0`.
- The next request may cold-load its model again. That is expected on 8GB GPUs.

## Step 8: Smoke Test Through Reverie

Start ComfyUI, then start the backend. From repo root:

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

Expected:

```text
status: queued or running
```

Poll until complete:

```powershell
do {
  Start-Sleep -Seconds 5
  $job = Invoke-RestMethod "http://127.0.0.1:8000/api/images/$($job.job_id)"
  "{0} {1}" -f $job.status, $job.phase
} until ($job.status -in @("completed", "failed", "cancelled"))

$job
```

Expected final status:

```text
completed
```

## Common Failures

| Symptom | Cause | Fix |
|---|---|---|
| `image_comfy_unreachable` | ComfyUI is not running or wrong URL | Start ComfyUI at `127.0.0.1:8188` |
| `image_comfy_workflow_unreadable` | Reverie cannot read workflow JSON | Check `REVERIE_IMAGE_GENERATION_COMFYUI_WORKFLOW_PATH` from `backend/` |
| `image_comfy_workflow_invalid` | Workflow was not API-export format or node ids are wrong | Use `config/comfyui/reverie-flux-schnell-fp8.api.json` and the node ids above |
| `image_comfy_prompt_rejected` | ComfyUI rejected the graph | Confirm `flux1-schnell-fp8.safetensors` is visible in `CheckpointLoaderSimple` |
| `image_comfy_execution_failed` | ComfyUI accepted the prompt but failed while executing it | Open the job details, check the ComfyUI log, fix the reported node/model/CUDA error, then retry |
| `image_comfy_no_outputs` or `image_no_outputs` | ComfyUI finished without a saved image | Verify the workflow save node and output directory, then retry |
| Repeated `GET /api/images/` 404 while polling | Smoke test used the wrapper response as the job | Set `$job = $response.job` before polling |
| CUDA out of memory | Too much VRAM is already used | Stop other GPU apps, use `preview_8gb`, keep batch size 1 |
| Output file missing in gallery | ComfyUI output folder differs from Reverie output folder or the job failed before writing a file | Start ComfyUI with `--output-directory C:\Reverie-Companion\backend\data\images\generated`, then check the job error |
| ComfyUI reports CUDA unknown error | CUDA context entered a bad state after a failed generation | Restart ComfyUI, then retry with `preview_8gb` |
| Chat or image cold-loads after switching modes | Hotswap freed the other model family | Expected; this protects 8GB VRAM headroom |

## Installed On This Workstation

The current workstation has:

```text
C:\Comfy-UI\models\checkpoints\flux1-schnell-fp8.safetensors
C:\Comfy-UI\models\unet\flux1-schnell-Q4_0.gguf
C:\Comfy-UI\models\text_encoders\clip_l.safetensors
C:\Comfy-UI\models\text_encoders\t5xxl_fp8_e4m3fn.safetensors
C:\Comfy-UI\custom_nodes\ComfyUI-GGUF
```

The active Reverie default is the FP8 checkpoint workflow.

The checked-in `config/comfyui/reverie-sd15-preview.api.json` workflow references
`v1-5-pruned-emaonly.safetensors` as a legacy SD 1.5 fallback. It is not
installed by the standard setup and is not the project default.
