# UX Guide

Design system and UX conventions for KnowledgeOS (PHASE-ENHANCE-03).

## Design Tokens

Tokens are defined in `apps/web/src/styles/tokens.css` as CSS custom properties and bridged into Tailwind via `tailwind.config.ts`.

### Usage

Always use token-backed Tailwind classes rather than raw Tailwind color names:

```tsx
// ✅ Correct — uses design token
<div className="bg-surface-1 text-fg">…</div>

// ❌ Avoid — hardcoded gray scale
<div className="bg-gray-900 text-gray-100">…</div>
```

### Token Groups

| Group | CSS vars | Tailwind classes |
|-------|----------|-----------------|
| Surfaces | `--surface-0/1/2/3` | `bg-surface-0/1/2/3` |
| Text | `--text-primary/secondary/tertiary/disabled` | `text-fg`, `text-fg-muted`, `text-fg-subtle`, `text-fg-disabled` |
| Brand | `--brand`, `--brand-fg` | `bg-brand`, `text-brand-fg` |
| Semantic | `--success/warning/danger/info` | `bg-success`, `text-danger`, etc. |
| Ring | `--ring` | `ring-ring` |
| Radius | `--radius-sm/md/lg/xl` | `rounded-sm/md/lg/xl` |
| Duration | `--duration-fast/base/slow` | `duration-fast/base/slow` |

## Theming

- Default: **dark** (`data-theme="dark"` on `<html>`).
- Light theme opt-in via `ThemeToggle` in the sidebar footer.
- `ThemeProvider` is configured with `defaultTheme="dark"` and `enableSystem=false`.
- Never conditionally render based on theme — use CSS tokens that update automatically.

## Fonts

- Sans: Inter (`--font-sans`) — loaded via `next/font/google` at build time.
- Mono: JetBrains Mono (`--font-mono`) — loaded via `next/font/google` at build time.
- No Google Fonts network call at page load. For offline builds, swap to `next/font/local`.

## Component Primitives

All UI primitives live in `apps/web/src/components/ui/`. Import from the barrel:

```ts
import { Button, Input, Dialog, Badge } from "@/components/ui";
```

### Button Variants

| Variant | Use |
|---------|-----|
| `primary` | Primary action, one per screen |
| `secondary` | Default — secondary actions |
| `ghost` | Toolbar and icon buttons |
| `destructive` | Delete / irreversible actions |
| `link` | Inline text actions |

### Badge Variants

| Variant | Use |
|---------|-----|
| `default` | Neutral label |
| `success` | Completed / live |
| `warning` | Needs attention |
| `danger` | Error / critical |
| `info` | Informational |

## Feature Flags

| Flag | Controls |
|------|---------|
| `NEXT_PUBLIC_UX_SEARCH_V2=1` | New `SearchCommand` palette (cmdk) instead of `SearchModal` |
| `NEXT_PUBLIC_UX_EDITOR_V2=1` | Slash menu + bubble menu in `PageView` |

Both flags default to off. Set in `.env.local` or in `infra/.env`.

## List Pages

All list pages use the `<ListPage>` layout component:
- Skeleton loading rows via `skeletonRows` prop
- `<EmptyState>` when no items
- `<ErrorState>` with retry when fetch fails
- `<BulkActionBar>` for multi-select operations
- `<ListToolbar>` for search + sort + optional view-mode

## Toast Notifications

Use `toast` from `@/components/ui/Toast` (re-exports sonner):

```ts
import { toast } from "@/components/ui/Toast";

toast.success("Saved");
toast.error("Failed to save", { description: err.message });
```

`<Toaster position="bottom-right" richColors />` is mounted once in `(app)/layout.tsx`.
