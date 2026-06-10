# Reverie Frontend

Tauri 2 + SvelteKit desktop frontend for Reverie.

This milestone provides a clean, warm, local-first chat shell. It intentionally does **not** connect to the backend yet; all chat state is simulated in the browser process so the UI foundation can be refined independently.

## Project Structure

```text
frontend/
├── package.json              # npm scripts and SvelteKit/Tauri dependencies
├── svelte.config.js          # Static SvelteKit adapter for Tauri bundling
├── vite.config.ts            # Vite dev server pinned to Tauri's dev URL
├── src/
│   ├── app.css               # Global premium dark theme
│   ├── app.html              # SvelteKit document shell
│   ├── lib/
│   │   ├── components/
│   │   │   ├── Chat/         # Chat window, message list, bubbles, composer
│   │   │   └── Layout/       # App shell and sidebar foundation
│   │   └── types/            # Shared TypeScript types
│   └── routes/               # SvelteKit page and static/Tauri layout config
└── src-tauri/
    ├── Cargo.toml            # Tauri 2 Rust crate
    ├── tauri.conf.json       # Desktop window and build configuration
    ├── capabilities/         # Tauri 2 permission capability baseline
    └── src/main.rs           # Minimal Tauri application entry point
```

## Key Decisions

- **Static SvelteKit output**: `@sveltejs/adapter-static` produces a Tauri-friendly bundle with `fallback: 'index.html'`.
- **Local-only chat state**: the chat loop is useful and testable without coupling to the backend before API contracts are ready.
- **Component boundaries**: chat and layout code live separately under `src/lib/components/`, leaving room for Visual Novel mode, settings, memory tools, and character panels.
- **Warm dark theme**: soft rose/violet gradients, spacious message bubbles, and muted surfaces create a premium companion-app feel without heavy animation.
- **Markdown-ready assistant bubbles**: assistant messages render basic GitHub-flavored markdown via `marked`; user messages are rendered as plain text.

## Development

Install dependencies:

```bash
npm install
```

Run the SvelteKit dev server only:

```bash
npm run dev
```

Run the Tauri desktop app:

```bash
npm run tauri dev
```

Run checks:

```bash
npm run check
npm run build
```
