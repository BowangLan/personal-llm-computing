# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a monorepo containing:
- `apps/web`: Next.js web application using shadcn/ui components
- `apps/bot`: Python Telegram bot with LLM integration and command execution
- `packages/ui`: Shared UI component library using shadcn/ui, Radix UI, and Tailwind CSS
- `packages/eslint-config`: Shared ESLint configuration
- `packages/typescript-config`: Shared TypeScript configuration

## Technology Stack

- **Package Manager**: pnpm (version 10.4.1)
- **Build System**: Turbo (monorepo orchestration)
- **Node Version**: >=20
- **Web Framework**: Next.js 16 with React 19, Tailwind CSS 4
- **Python Bot**: Python 3.13+, uses `uv` for dependency management

## Development Commands

### Monorepo-wide Commands (run from root)

```bash
# Install dependencies
pnpm install

# Run all apps in dev mode
pnpm dev

# Build all apps and packages
pnpm build

# Lint all packages
pnpm lint

# Format all TypeScript/TSX/MD files
pnpm format
```

### Web App (`apps/web`)

```bash
cd apps/web

# Development server with Turbopack
pnpm dev

# Production build
pnpm build

# Start production server
pnpm start

# Lint
pnpm lint

# Auto-fix lint issues
pnpm lint:fix

# Type checking only
pnpm typecheck
```

### Telegram Bot (`apps/bot`)

The bot requires environment variables managed via Doppler. Required variables:
- `BOT_TOKEN`: Telegram bot token
- `OPENAI_API_KEY`: OpenAI API key
- `LLM_MODEL` (optional): defaults to `gpt-5-nano`
- `LOG_LEVEL` (optional): defaults to `INFO`

```bash
# Install bot dependencies (uses uv)
pnpm install:bot
# Or directly:
cd apps/bot && uv sync

# Start bot (uses Doppler for env vars)
pnpm start:bot
# Or directly:
cd apps/bot && doppler run -- uv run bot.py
```

Bot capabilities:
- Replies to normal text messages with LLM responses
- Executes shell commands when messages are prefixed with `run:` or `cmd:`
- Commands: `/start`, `/help`, `/bg <command>` (background execution), `/status`

### UI Package (`packages/ui`)

```bash
cd packages/ui

# Lint
pnpm lint
```

## Architecture Notes

### Monorepo Structure

This is a pnpm workspace using Turbo for task orchestration. Workspaces are defined in `package.json`:
```json
"workspaces": ["apps/*", "packages/*"]
```

Turbo configuration in `turbo.json` defines task dependencies:
- `build` tasks depend on dependencies being built first (`^build`)
- `dev` tasks run persistently without caching
- Build outputs are cached except `.next/cache`

### UI Component Library Pattern

The `@workspace/ui` package is a shared component library:
- Components live in `packages/ui/src/components/`
- Exports are defined in `packages/ui/package.json` using the `exports` field
- Import components from apps using: `import { Button } from "@workspace/ui/components/button"`

### Adding shadcn/ui Components

Run from repository root:
```bash
pnpm dlx shadcn@latest add button -c apps/web
```

This places UI components in `packages/ui/src/components/` directory, making them available to all apps in the workspace.

### Tailwind Configuration

Global styles are in `packages/ui/src/styles/globals.css`. The web app's `tailwind.config.ts` is configured to use components from the ui package. VS Code settings point to this configuration file.

### Python Bot Architecture

The bot uses:
- `claude-agent-sdk` (>=0.1.18) for Claude integration
- `python-telegram-bot` for Telegram API
- `rich` for console formatting
- Dependency management via `uv` (modern Python package manager)
- Environment secrets managed via Doppler CLI

## Key Files

- `/package.json`: Root package.json with monorepo scripts
- `/turbo.json`: Turbo build system configuration
- `/pnpm-workspace.yaml`: pnpm workspace definition
- `/packages/ui/package.json`: UI package exports configuration
- `/apps/bot/pyproject.toml`: Python dependencies
- `/apps/web/package.json`: Next.js app configuration
