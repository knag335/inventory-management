# Sidebar App Shell Template

A reference implementation for the root layout (usually `App.vue`). Adapt the names to the project. Keep its existing components (filter bar, profile menu, language switcher, modals) and their event handlers. Move them; don't rewrite them.

## Structure

```
+--------------+-------------------------------------------+
| Brand        | Top bar: [=] Page title     [controls]    |
|              +-------------------------------------------+
| SECTION      |                                           |
|  > Overview  |  <router-view />                          |
|    Inventory |  (scrolls independently)                  |
|    Orders    |                                           |
| SECTION      |                                           |
|    Reports   |                                           |
|              |                                           |
| ------------ |                                           |
| Lang / User  |                                           |
+--------------+-------------------------------------------+
```

## Nav config

Keep navigation data-driven, so adding a route means adding one line:

```js
// Each item: route path, i18n key, icon name, and optional section grouping.
const navItems = [
  { to: '/',          labelKey: 'nav.overview',  icon: 'home',    section: 'main' },
  { to: '/inventory', labelKey: 'nav.inventory', icon: 'box',     section: 'main' },
  { to: '/orders',    labelKey: 'nav.orders',    icon: 'cart',    section: 'main' },
  { to: '/reports',   labelKey: 'nav.reports',   icon: 'chart',   section: 'insights' },
]

// Group items by section for rendering headings, keeping config order.
const navSections = computed(() => {
  const groups = new Map()
  for (const item of navItems) {
    if (!groups.has(item.section)) groups.set(item.section, [])
    groups.get(item.section).push(item)
  }
  return [...groups].map(([id, items]) => ({ id, items }))
})

// '/' is a prefix of every path, so it must match exactly;
// other items stay active on nested routes (for example /orders/123).
const isActive = (to) => to === '/' ? route.path === '/' : route.path.startsWith(to)

const pageTitle = computed(() => {
  const item = navItems.find(i => isActive(i.to))
  return item ? t(item.labelKey) : ''
})
```

## Template

```vue
<template>
  <div :class="['app-shell', { 'sidebar-open': mobileNavOpen }]">
    <aside class="sidebar" :aria-label="t('nav.mainNavigation')">
      <div class="sidebar-brand">
        <span class="brand-mark" aria-hidden="true"><!-- small SVG logo --></span>
        <span class="brand-name">{{ t('nav.companyName') }}</span>
      </div>

      <nav class="sidebar-nav">
        <div v-for="section in navSections" :key="section.id" class="nav-section">
          <p v-if="section.id !== 'main'" class="nav-section-label">
            {{ t(`nav.sections.${section.id}`) }}
          </p>
          <router-link
            v-for="item in section.items"
            :key="item.to"
            :to="item.to"
            :class="['nav-item', { active: isActive(item.to) }]"
            :aria-current="isActive(item.to) ? 'page' : undefined"
            :title="t(item.labelKey)"
          >
            <NavIcon :name="item.icon" />
            <span class="nav-label">{{ t(item.labelKey) }}</span>
          </router-link>
        </div>
      </nav>

      <div class="sidebar-footer">
        <LanguageSwitcher />
        <ProfileMenu @show-profile-details="..." @show-tasks="..." />
      </div>
    </aside>

    <!-- Backdrop only renders on mobile when the drawer is open -->
    <div v-if="mobileNavOpen" class="sidebar-backdrop" @click="mobileNavOpen = false" />

    <div class="content">
      <header class="topbar">
        <button class="menu-toggle" :aria-label="t('nav.openMenu')" @click="mobileNavOpen = true">
          <NavIcon name="menu" />
        </button>
        <h1 class="topbar-title">{{ pageTitle }}</h1>
        <div class="topbar-actions"><!-- page-level controls --></div>
      </header>
      <FilterBar />  <!-- if the app has global filters -->
      <main class="main-content"><router-view /></main>
    </div>

    <!-- existing modals stay here, unchanged -->
  </div>
</template>
```

Close the mobile drawer on navigation and on Escape:

```js
const mobileNavOpen = ref(false)
// The drawer overlays content on mobile; leaving it open after a nav click would hide the new page.
watch(() => route.path, () => { mobileNavOpen.value = false })
const onKey = (e) => { if (e.key === 'Escape') mobileNavOpen.value = false }
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
```

## Icons

A tiny local component keeps icons dependency-free. Use 24x24 outline paths with `stroke="currentColor"`:

```vue
<template>
  <svg class="nav-icon" width="18" height="18" viewBox="0 0 24 24" fill="none"
       stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"
       aria-hidden="true">
    <path v-for="d in paths" :key="d" :d="d" />
  </svg>
</template>
<script>
import { computed } from 'vue'

const ICONS = {
  home:  ['M3 10.5 12 3l9 7.5', 'M5 9.5V21h14V9.5'],
  box:   ['M21 8 12 3 3 8v8l9 5 9-5V8Z', 'M3 8l9 5 9-5', 'M12 13v8'],
  cart:  ['M3 4h2l2.4 11h11L21 7H6.2', 'M9 20h.01', 'M18 20h.01'],
  chart: ['M4 20V10', 'M10 20V4', 'M16 20v-7', 'M22 20H2'],
  menu:  ['M4 6h16', 'M4 12h16', 'M4 18h16'],
}
export default {
  name: 'NavIcon',
  props: { name: { type: String, required: true } },
  setup(props) {
    return { paths: computed(() => ICONS[props.name] || []) }
  }
}
</script>
```

Add icons as needed, such as truck, dollar, trending-up, refresh and file, in the same stroke style.

## Shell CSS

```css
.app-shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  min-height: 100vh;
  background: var(--color-bg);
}

/* Sticky + full height keeps the sidebar fixed while only the content column scrolls. */
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--sidebar-bg);
  color: var(--sidebar-text);
  padding: var(--space-4) var(--space-3);
  overflow-y: auto;
}
.sidebar-brand { display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-3) var(--space-6); color: var(--sidebar-item-active-text);
  font-weight: 600; font-size: var(--text-base); }
.sidebar-nav { flex: 1; display: flex; flex-direction: column; gap: var(--space-4); }
.nav-section { display: flex; flex-direction: column; gap: 2px; }
.nav-section-label { margin: 0; padding: 0 var(--space-3) var(--space-2);
  font-size: var(--text-xs); text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--sidebar-text-muted); }
.nav-item { display: flex; align-items: center; gap: var(--space-3);
  height: 36px; padding: 0 var(--space-3); border-radius: var(--radius-md);
  color: var(--sidebar-text); text-decoration: none; font-size: var(--text-sm); font-weight: 500;
  transition: background var(--transition), color var(--transition); }
.nav-item:hover { background: var(--sidebar-item-hover); color: var(--sidebar-item-active-text); }
.nav-item.active { background: var(--sidebar-item-active-bg); color: var(--sidebar-item-active-text); }
.nav-item:focus-visible { outline: none; box-shadow: var(--focus-ring); }
.sidebar-footer { border-top: 1px solid rgb(255 255 255 / 0.08);
  padding-top: var(--space-4); display: flex; flex-direction: column; gap: var(--space-3); }

/* min-width: 0 lets wide tables scroll inside their container instead of stretching the grid column. */
.content { min-width: 0; display: flex; flex-direction: column; }
.topbar { position: sticky; top: 0; z-index: 20; height: var(--topbar-height);
  display: flex; align-items: center; gap: var(--space-4); padding: 0 var(--space-8);
  background: var(--color-surface); border-bottom: 1px solid var(--color-border); }
.topbar-title { margin: 0; font-size: var(--text-lg); font-weight: 600; color: var(--color-text); }
.topbar-actions { margin-left: auto; display: flex; align-items: center; gap: var(--space-3); }
.menu-toggle { display: none; }
.main-content { padding: var(--space-8); width: 100%; max-width: 1440px; margin: 0 auto; }

/* Tablet: icon rail. Labels are hidden; the title attribute provides a tooltip. */
@media (max-width: 1024px) {
  .app-shell { grid-template-columns: var(--sidebar-width-collapsed) 1fr; }
  .nav-label, .brand-name, .nav-section-label { display: none; }
  .nav-item { justify-content: center; padding: 0; }
}

/* Mobile: off-canvas drawer, toggled from the top bar. */
@media (max-width: 768px) {
  .app-shell { grid-template-columns: 1fr; }
  .sidebar { position: fixed; inset: 0 auto 0 0; width: var(--sidebar-width); z-index: 40;
    transform: translateX(-100%); transition: transform 200ms ease; }
  .sidebar-open .sidebar { transform: translateX(0); }
  .sidebar-open .nav-label, .sidebar-open .brand-name, .sidebar-open .nav-section-label { display: revert; }
  .sidebar-open .nav-item { justify-content: flex-start; padding: 0 var(--space-3); }
  .sidebar-backdrop { position: fixed; inset: 0; z-index: 30; background: rgb(15 23 42 / 0.4); }
  .menu-toggle { display: inline-flex; align-items: center; justify-content: center;
    width: var(--control-height); height: var(--control-height); border: 1px solid var(--color-border);
    border-radius: var(--radius-md); background: var(--color-surface); color: var(--color-text); cursor: pointer; }
  .topbar { padding: 0 var(--space-4); }
  .main-content { padding: var(--space-4); }
}
```

## Checklist for the shell

- [ ] Every route in the router has a nav item (or a noted reason not to)
- [ ] `/` is active only on `/`
- [ ] Old top nav markup and CSS removed
- [ ] Profile menu, language switcher and filter bar still work, and their events reach the same handlers
- [ ] Drawer closes on route change, backdrop click and Escape
- [ ] No horizontal page scroll at 390px
