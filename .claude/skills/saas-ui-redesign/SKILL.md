---
name: saas-ui-redesign
description: Redesign a Vue 3 application's UI into a modern SaaS-style interface - a fixed vertical navigation sidebar on the left (replacing a top nav bar), a design-token system with a consistent spacing scale, and polished cards, tables, badges, buttons and forms. Use when the user asks to modernize, restyle, or "make professional" a Vue 3 app's UI, move navigation to a sidebar, or unify spacing and visual consistency. Changes presentation only, never behavior.
---

# SaaS UI Redesign for Vue 3

Turn an existing Vue 3 app into a clean, modern SaaS-style interface. The result has:

- A **fixed left sidebar** with brand, grouped navigation, and the user/account area at the bottom
- A **slim top bar** in the content area with the page title and page-level controls (filters, language, actions)
- A **token-based design system** (CSS custom properties) for color, spacing, radius, shadow and type
- **Consistent spacing** on a 4px scale, applied to every view
- **Polished components**: cards, stat tiles, tables, badges, buttons, inputs, modals

This is a **presentation-only** change. Routes, data loading, API calls, state, i18n keys and emitted events must behave exactly as before.

## Reference files

- `references/design-tokens.css` - the token set to install (light theme, plus an optional dark theme)
- `references/sidebar-shell.md` - the app shell template (sidebar, top bar, content area) and nav config pattern

Read both before starting phase 2.

## Before you start

1. **Read the project's instructions.** Check `CLAUDE.md` files (root and `client/`) for design-system rules (palette, "no emojis", chart conventions), delegation rules (for example "all .vue edits go through a specific subagent"), and browser-testing tools. Project rules take precedence over this skill. If the project names a palette, map it onto the tokens instead of using the defaults.
2. **Confirm scope with the user** if it's unclear: the whole app or the shell only, light only or light and dark, and whether a collapsible sidebar is wanted. Default: whole app, light theme with the dark theme wired up through `prefers-color-scheme`, collapsible below 1024px.
3. **Don't add dependencies** (UI kits, icon packages, Tailwind) unless the user asks. Use plain CSS and inline SVG icons.

## Workflow

### Phase 1 - Audit (read-only)

Build a short inventory before changing anything:

- **Shell**: find the root layout (usually `App.vue`) and how navigation is rendered (hard-coded `router-link`s, a nav array, and so on).
- **Routes**: list every route from the router config. Each needs a sidebar entry or a deliberate reason not to have one.
- **Global styles**: find where shared classes live (`App.vue` unscoped `<style>`, `main.css`, `style.css`). List the shared class names views rely on (`.card`, `.stat-card`, `.badge.*`, `.table-container`, `.page-header`, and so on). **These names are a contract.** Restyle them; don't rename or delete them.
- **Hard-coded values**: grep views and components for raw hex colors, `px` paddings and margins, and `box-shadow`/`border-radius` literals. These get replaced with tokens in phase 4.
- **Baseline screenshots**: with the dev server running, screenshot every route at 1440px wide using the project's browser tool (for example Playwright MCP). Note any console errors that already exist, so you don't blame them on the redesign later.

Give the user a 5-10 line summary of the plan and the files you'll touch before editing.

### Phase 2 - Install design tokens

- Copy the tokens from `references/design-tokens.css` into the global stylesheet, at the top under `:root`.
- If the project defines a palette, override the color tokens to match it (for example slate `#0f172a`, `#64748b` and `#e2e8f0` map to `--color-text`, `--color-text-muted` and `--color-border`).
- Set base typography on `body`: `font-family: var(--font-sans)`, `font-size: var(--text-sm)`, `color: var(--color-text)`, `background: var(--color-bg)`, and `-webkit-font-smoothing: antialiased`.

### Phase 3 - Build the sidebar shell

Follow `references/sidebar-shell.md`. Key requirements:

- **Layout**: CSS Grid on the app root, `grid-template-columns: var(--sidebar-width) 1fr`. The sidebar is `position: sticky; top: 0; height: 100vh`, and the content area scrolls.
- **Nav config**: replace the hard-coded links with a `navItems` array (`{ to, labelKey, icon, section? }`) rendered with `v-for` and keyed by `to`. Keep the existing i18n keys. If a label was hard-coded, add a key for it in every locale.
- **Active state**: use `router-link`'s `active-class` / `exact-active-class`, or compare `$route.path`. `/` must match exactly so it isn't always active. Set `aria-current="page"` on the active item.
- **Icons**: 18-20px inline SVG, `stroke="currentColor"` and `fill="none"`, so they inherit the item color. One simple, consistent outline style.
- **Bottom area**: move the profile/account menu (and the language switcher, if there is one) into the sidebar footer. Keep their emitted events wired to the same handlers.
- **Top bar**: a sticky bar above `<router-view>` with the current page title (derived from the active nav item), plus any global controls that were in the old header or directly under it (for example a filter bar). Don't drop components; relocate them.
- **Responsive**: at 1024px and below, collapse to an icon rail (`--sidebar-width-collapsed`) with labels hidden and tooltips via `title`. At 768px and below, hide the sidebar off-canvas behind a hamburger button in the top bar, with a backdrop. Close it on route change and on `Escape`.
- **Delete the old top nav** markup and its now-unused CSS. Don't leave dead styles behind.

### Phase 4 - Spacing and component polish

Apply the tokens to shared classes first (the biggest effect for the least change), then sweep each view.

**Spacing rules (4px scale):**
- Page padding: `--space-8` (desktop), `--space-4` (mobile)
- Gap between sections and cards: `--space-6`
- Card padding: `--space-6`; card header to body: `--space-4`
- Stat grid: `repeat(auto-fit, minmax(220px, 1fr))` with a `--space-4` gap
- Table cells: `--space-3` vertical and `--space-4` horizontal
- Form controls and buttons: 36px height (`--control-height`), `--space-3` horizontal padding
- Use only token values. No `13px`, `18px` or `22px` one-offs.

**Component specs:**
- **Page header**: title `--text-2xl` at weight 600, description `--text-sm` muted, `--space-6` below.
- **Card**: `--color-surface`, 1px `--color-border`, `--radius-lg`, `--shadow-sm`. No heavy shadows. Use hover elevation only on clickable cards.
- **Stat tile**: label `--text-xs` uppercase, letter-spacing 0.04em, muted; value `--text-2xl` at weight 600 with tabular numbers. Status variants tint the value, not the whole card.
- **Table**: sticky header row on `--color-surface-muted`, header text `--text-xs` uppercase muted, row dividers only (no vertical borders), row hover `--color-surface-muted`, numbers right-aligned with `font-variant-numeric: tabular-nums`. Wrap the table in an `overflow-x: auto` container.
- **Badge**: pill (`--radius-full`), `--text-xs` at weight 500, a soft tinted background with a darker text color for each status (success, info, warning, danger, neutral).
- **Buttons**: primary (solid `--color-primary`), secondary (surface with a border), ghost (text only). All have `--radius-md` and a visible `:focus-visible` ring (`--focus-ring`). Disabled buttons use 50% opacity and `cursor: not-allowed`.
- **Inputs, selects, range sliders**: `--control-height`, a 1px border, `--radius-md`, and the focus ring. Color range sliders with `accent-color: var(--color-primary)`.
- **Modals**: `--radius-xl`, `--shadow-lg`, backdrop `rgb(15 23 42 / 0.4)`, max-width 560px, `--space-6` padding.
- **Empty, loading and error states**: centered in the card, muted text, `--space-10` vertical padding. Errors use the danger tint, not plain red text.

**Sweep each view:** replace raw colors, spacing, radii and shadows with tokens. Keep the edits to `<style>` blocks and class attributes. Only touch `<script>` when a layout change truly needs it, such as a computed page title.

### Phase 5 - Verify

For every route, at 1440px, 1024px and 390px wide:

1. Screenshot it and compare with the baseline. The layout should be new, but every piece of content and every control should still be present.
2. Check that the sidebar active state is correct and that keyboard Tab order reaches the nav, the top bar controls and the content, with visible focus.
3. Exercise the core interactions: filters, modals, forms, any submit buttons. Confirm the data still loads and updates.
4. Check that the browser console has no **new** errors compared with the phase 1 baseline.
5. Check that the page body never scrolls horizontally at 390px. Only tables may scroll, inside their container.
6. Spot-check text contrast (at least 4.5:1 for body text, 3:1 for large text and icons).

Run the project's existing test suite if there is one.

## Rules

- **Behavior is frozen.** Don't change data flow, API calls, route paths, i18n keys, props or emitted events. If a fix seems necessary, report it instead of making it.
- **Shared class names are a contract.** Restyle them; only rename them if you update every usage in the same change.
- **Tokens only.** Every color, space, radius, shadow and font size in new or edited CSS comes from a token.
- **Use v-for keys from stable values** (`to`, `id`, `sku`), never the index.
- **Comment non-obvious layout logic**, such as the sticky and grid interplay, the exact-match rule for `/`, and the off-canvas close-on-route-change watcher. Don't comment obvious CSS.
- **Follow the project's delegation rules.** If `CLAUDE.md` says `.vue` work must go through a specific subagent, delegate the phases 3-4 edits to it with this skill's specs in the prompt.
- **Report honestly**: which routes and breakpoints you verified, which you didn't, and any existing issues you saw but left alone.
