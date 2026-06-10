# Reverie Frontend

Tauri 2 + SvelteKit frontend for Reverie, an offline AI companion desktop app.

## Development

```bash
npm install
npm run tauri dev
```

Useful checks:

```bash
npm run check
npm run build
```

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
│   │   ├── components/
│   │   │   ├── Chat/           # Chat window, message list, bubbles, markdown, composer
│   │   │   └── Layout/         # App shell and future-friendly sidebar
│   │   └── types/              # Shared TypeScript types
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

The frontend is intentionally small and component-driven. `Layout` components own application chrome, while `Chat` components own conversation UI. This keeps future features such as a character panel, memory viewer, Visual Novel mode, and settings pages from requiring a rewrite of the main chat shell.
