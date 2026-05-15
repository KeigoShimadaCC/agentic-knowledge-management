# Keyboard Shortcuts

All shortcuts work in the browser UI. Press `?` anywhere outside a text field to open the shortcuts overlay.

## Global

| Key | Action |
|-----|--------|
| `⌘K` | Open search |
| `⌘\` | Collapse / expand sidebar |
| `?` | Show keyboard shortcuts |

## Search

| Key | Action |
|-----|--------|
| `↑ / ↓` | Navigate results |
| `Enter` | Open selected result |
| `Esc` | Close search |

## Editor (V2 mode — `NEXT_PUBLIC_UX_EDITOR_V2=1`)

| Key | Action |
|-----|--------|
| `/` | Open slash menu at line start |
| `⌘B` | Bold |
| `⌘I` | Italic |
| `⌘Shift+X` | Strikethrough |

## Lists

| Key | Action |
|-----|--------|
| `j / ↓` | Move highlight down |
| `k / ↑` | Move highlight up |
| `Enter` | Open highlighted item |
| `o` | Open in side pane |
| `Backspace` | Soft-delete highlighted item |
| `Esc` | Clear highlight |

## Adding Shortcuts

Add new entries to `apps/web/src/lib/shortcuts/registry.ts`. The `ShortcutOverlay` component reads from `SHORTCUTS` automatically — no other changes needed.
