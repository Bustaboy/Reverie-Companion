# Reverie Frontend

Tauri 2 + SvelteKit frontend for Reverie, an offline AI companion desktop app with warm chat, private journal review, memory/reflection settings, growth notifications, and Personal LoRA training controls.

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
│   │   ├── api/                # Chat, journal, and growth API clients
│   │   ├── chat/               # Local seed/fallback message helpers
│   │   ├── components/
│   │   │   ├── Chat/           # Chat window, messages, markdown, composer, notices
│   │   │   ├── Growth/         # Personal LoRA review/training panel
│   │   │   ├── Journal/        # Reflection journal browser
│   │   │   ├── Layout/         # App shell and sidebar
│   │   │   └── Settings/       # Memory/reflection controls
│   │   ├── config/             # App navigation metadata
│   │   ├── stores/             # Chat, journal, settings, and growth stores
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
- `src/lib/stores/` keeps async loading state, selected journal entries, growth actions, and local settings out of markup.
- `src/lib/components/Chat/` owns the active companion surface and only displays growth notifications provided by the backend/store.
- `src/lib/components/Journal/` makes reflection artifacts inspectable without turning them into automatic canon.
- `src/lib/components/Growth/` keeps Personal LoRA collection and training separate: examples must be collected, reviewed, approved, and training-opted-in before any job can use them.
- `src/lib/components/Settings/` exposes calm MVP controls; advanced scheduler and backend synchronization can be added without changing the visual model.

## Environment

Set `VITE_REVERIE_API_BASE_URL` if the backend is not on `http://localhost:8000`:

```bash
VITE_REVERIE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Future Extension Points

- Add full character gallery and character-card import/edit flows.
- Add memory browser edit/delete controls using the same local-first panel pattern.
- Synchronize Settings UI with backend `.env`/runtime controls once the settings API is introduced.
- Add Visual Novel mode as a sibling layout surface under `src/lib/components/VisualNovel/`.
