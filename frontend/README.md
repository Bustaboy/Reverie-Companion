# Reverie Frontend

Tauri 2 + SvelteKit frontend for Reverie, an offline AI companion desktop app with warm chat, selected-character runtime, Moment Capture, private journal review, memory/reflection settings, growth notifications, visual review controls, and Personal LoRA training controls.

## Prerequisites

- Node.js 20+
- npm 10+
- Rust stable toolchain
- Tauri 2 system dependencies for your operating system
- Reverie backend running at `http://localhost:8000` unless `VITE_REVERIE_API_BASE_URL` is configured

## Setup

```bash
cd frontend
npm install
```

## Available scripts

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the SvelteKit/Vite dev server on Tauri's fixed port (`1420`). |
| `npm run tauri dev` | Launch the full Tauri desktop app in development mode. |
| `npm run build` | Build the SvelteKit static frontend into `build/`. |
| `npm run preview` | Preview the built frontend in a browser. |
| `npm run check` | Run SvelteKit sync and TypeScript/Svelte diagnostics. |

## Current UI Capabilities

- **Chat**: local backend chat integration, streaming response state, Markdown rendering, connection errors, and rare growth-notification cards.
- **Characters**: selected-character store, selector, quick creation flow, and chat request integration.
- **Moment Capture / Images**: capture-aware image generation controls, queued job cards, retry/cancel flows, gallery history, character/source/capture metadata, and resource-status copy for waiting, TTS pause, downgrade, failure, and completion states.
- **Visual feedback and review**: quick actions (`Looks Right`, `Wrong Appearance`, `Make Canon`, `Use Outfit Again`, `Just This Scene`, `Reject Style Trait`), detailed trait feedback, pending visual change review cards, and approve/reject/rollback actions.
- **Visual Novel**: lightweight VN stage, expression/pose state, immersive presentation, and image/capture hooks that share the same resource-aware image queue.
- **Journal**: private self-reflection entries with confidence, emotional intensity, promotion status, themes, insights, privacy tags, and training eligibility.
- **Settings**: local controls for long-term memory, self-reflection, reflection frequency/sensitivity, growth notifications, and 8GB-aware context budget presets.
- **Training**: Personal LoRA review panel with collection opt-in, training opt-in, pending candidate approval/rejection/deletion, job status, and safe start controls.
- **Layout**: warm premium dark shell, fixed sidebar navigation, responsive panels, and local-first trust copy.

## Project Structure

```text
frontend/
├── package.json                # npm scripts and SvelteKit/Tauri dependencies
├── svelte.config.js            # SvelteKit static adapter for Tauri builds
├── vite.config.ts              # Vite dev server on Tauri's fixed port
├── src/
│   ├── app.css                 # Premium warm dark theme and responsive panel styles
│   ├── app.html                # SvelteKit HTML shell
│   ├── lib/
│   │   ├── api/                # Chat, character, journal, growth, image, and capture API clients
│   │   ├── chat/               # Local seed/fallback message helpers
│   │   ├── components/
│   │   │   ├── Chat/           # Chat window, messages, markdown, composer, notices
│   │   │   ├── Growth/         # Personal LoRA review/training panel
│   │   │   ├── Journal/        # Reflection journal browser
│   │   │   ├── Layout/         # App shell and sidebar
│   │   │   └── Settings/       # Memory/reflection controls
│   │   ├── config/             # App navigation metadata
│   │   ├── stores/             # Chat, character, image/capture, resource, journal, settings, and growth stores
│   │   ├── types/              # Shared TypeScript types
│   │   └── utils/              # UI-safe formatting and markdown helpers
│   └── routes/                 # SvelteKit routes
└── src-tauri/
    ├── tauri.conf.json         # Tauri 2 desktop app configuration
    ├── Cargo.toml              # Rust crate and Tauri dependencies
    ├── capabilities/           # Tauri 2 permissions model
    └── src/                    # Minimal Tauri bootstrap
```

## Architecture Notes

The frontend is intentionally component-driven and trust-oriented:

- `src/lib/api/` isolates backend shape, timeouts, and user-friendly local-service errors.
- `src/lib/stores/` keeps async loading state, selected character, image/capture jobs, visual change review, selected journal entries, growth actions, and local settings out of markup.
- `src/lib/components/Chat/` owns the active companion surface and keeps chat responsive while media jobs run through the image/capture store.
- `src/lib/components/ImageGeneration/` owns gallery history, Moment Capture metadata display, feedback actions, review cards, and retry/cancel controls.
- `src/lib/components/Journal/` makes reflection artifacts inspectable without turning them into automatic canon.
- `src/lib/components/Growth/` keeps Personal LoRA collection and training separate: examples must be collected, reviewed, approved, and training-opted-in before any job can use them.
- `src/lib/components/Settings/` exposes calm controls; backend synchronization remains M8 scope.

## Environment

Set `VITE_REVERIE_API_BASE_URL` if the backend is not on `http://localhost:8000`:

```bash
VITE_REVERIE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Future Extension Points

- Add full character gallery and character-card import/edit/export flows in M6/M8.
- Add memory browser edit/delete controls using the same local-first panel pattern.
- Synchronize Settings UI with backend `.env`/runtime controls once the settings API is introduced.
- Run packaged target-hardware smoke on RTX 4070 8GB mobile or equivalent with TTS and ComfyUI available in M8-P09.
