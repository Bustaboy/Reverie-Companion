# Reverie Frontend

Tauri 2 + SvelteKit desktop frontend for Reverie, an offline-first AI companion experience.

## What is included

- Tauri 2 shell in `src-tauri/`
- SvelteKit static frontend configured for desktop packaging
- Warm premium dark theme
- Future-ready app shell with a sidebar and main chat surface
- Local-only chat state with simulated assistant replies
- Assistant markdown rendering with sanitization

## Development

```bash
npm install
npm run tauri dev
```

Useful checks:

```bash
npm run check
npm run build
cd src-tauri && cargo check
```

## Structure

```text
frontend/
├── src/
│   ├── lib/
│   │   ├── components/
│   │   │   ├── Chat/       # Chat window, message list, bubbles, composer
│   │   │   └── Layout/     # App shell and future navigation sidebar
│   │   ├── types/          # Shared TypeScript contracts
│   │   └── utils/          # Markdown rendering utilities
│   ├── routes/             # SvelteKit routes
│   └── styles/             # Global app theme
└── src-tauri/              # Tauri 2 Rust desktop shell
```

Backend connectivity, character management, memory browsing, settings, and Visual Novel mode are intentionally left as future additions.
