# Reverie Frontend

Tauri 2 + SvelteKit frontend for Reverie, an offline AI companion desktop app.

This package is intentionally UI-only right now. It provides the desktop shell, warm dark visual language, and local chat prototype that the Python backend can connect to later.

## Prerequisites

- Node.js 20+
- npm 10+
- Rust stable toolchain
- Tauri 2 system dependencies for your operating system

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

## Project structure

```text
frontend/
├── package.json                # npm scripts and SvelteKit/Tauri dependencies
├── svelte.config.js            # SvelteKit static adapter for Tauri builds
├── vite.config.ts              # Vite dev server on Tauri's fixed port
├── src/
│   ├── app.css                 # Premium warm dark theme and responsive layout styles
│   ├── app.html                # SvelteKit HTML shell
│   ├── lib/
│   │   ├── chat/               # Local chat prototype factories and seed messages
│   │   ├── components/
│   │   │   ├── Chat/           # Chat window, message list, bubbles, markdown, composer
│   │   │   └── Layout/         # App shell and future-friendly sidebar
│   │   ├── config/             # App navigation and future feature configuration
│   │   ├── types/              # Shared TypeScript types
│   │   └── utils/              # UI-safe formatting and markdown helpers
│   └── routes/                 # SvelteKit routes
└── src-tauri/
    ├── tauri.conf.json         # Tauri 2 desktop app configuration
    ├── Cargo.toml              # Rust crate and Tauri dependencies
    ├── capabilities/           # Tauri 2 permissions model
    └── src/                    # Minimal Tauri bootstrap
```

## Current UI foundation

- Local-only chat state; no backend connection yet.
- Warm, spacious dark theme intended to feel private and emotionally comfortable.
- Fixed desktop sidebar with placeholders for Characters, Memory, Visual Novel mode, and Settings.
- Main chat surface with scrollable messages, visually distinct user/assistant bubbles, and a bottom composer.
- Assistant messages render basic GitHub-flavored Markdown via `marked`, with raw HTML escaped before rendering.

## Architecture notes

The frontend is intentionally small and component-driven:

- `src/lib/components/Layout/` owns app chrome: sidebar, shell, and future high-level panels.
- `src/lib/components/Chat/` owns conversation UI: window, message list, bubbles, markdown, and composer.
- `src/lib/chat/` owns local prototype message factories so backend integration can replace that layer without rewriting UI components.
- `src/lib/config/` owns navigation metadata and future feature entry points.
- `src/lib/utils/` keeps formatting and rendering helpers out of Svelte component markup.

This keeps future additions such as a character panel, memory viewer, Visual Novel mode, and settings pages from requiring a rewrite of the main chat shell.

## Future extension points

- Replace `src/lib/chat/messages.ts` with a store or service that calls the local backend.
- Convert disabled sidebar destinations into routed panels when features are ready.
- Add character/session metadata beside `ChatMessage` instead of embedding it in presentational components.
- Add Visual Novel mode as a sibling layout surface under `src/lib/components/VisualNovel/`.
