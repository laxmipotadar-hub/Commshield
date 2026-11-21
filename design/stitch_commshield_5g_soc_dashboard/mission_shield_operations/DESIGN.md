---
name: Mission Shield Operations
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#434655'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#737686'
  outline-variant: '#c3c6d7'
  surface-tint: '#0053db'
  primary: '#004ac6'
  on-primary: '#ffffff'
  primary-container: '#2563eb'
  on-primary-container: '#eeefff'
  inverse-primary: '#b4c5ff'
  secondary: '#535f74'
  on-secondary: '#ffffff'
  secondary-container: '#d4e0f9'
  on-secondary-container: '#586378'
  tertiary: '#006243'
  on-tertiary: '#ffffff'
  tertiary-container: '#007d57'
  on-tertiary-container: '#bdffdc'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b4c5ff'
  on-primary-fixed: '#00174b'
  on-primary-fixed-variant: '#003ea8'
  secondary-fixed: '#d7e3fc'
  secondary-fixed-dim: '#bbc7df'
  on-secondary-fixed: '#101c2e'
  on-secondary-fixed-variant: '#3c475b'
  tertiary-fixed: '#85f8c4'
  tertiary-fixed-dim: '#68dba9'
  on-tertiary-fixed: '#002114'
  on-tertiary-fixed-variant: '#005137'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-xl:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  title-sm:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '500'
    lineHeight: 20px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-xs:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  label-mono:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  badge-status:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.06em
  metric-stat:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.02em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-desktop: 1.5rem
  margin: 1rem
  margin-desktop: 2rem
  space-2xs: 0.125rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
---

## Brand & Style

The design system embodies the ethos of **Mission-Critical Vigilance & Modern Telemetry Clarity**. Engineered for enterprise cybersecurity teams, 5G network architects, and SOC operators, the interface balances hyper-dense data surveillance with effortless cognitive intake.

### Visual Style: Dual-Shell Modern Operations
The visual model establishes a purposeful dual-surface environment:
- **Command Navigational Shell:** Deep, monolithic dark navy (`#0a1628`) housing system navigation, global state, topology selectors, and persistent threat telemetry.
- **Analytical Canvas:** High-efficiency, light slate surfaces (`#f8fafc` to `#f1f5f9`) housing modular analytical cards, tabular logs, data visualization nodes, and diagnostic inspectors.

The tension between the dark command chassis and the crisp analytical work surface evokes precision defense hardware translated into contemporary high-velocity software. Visual elements feature surgical contrast, sharp monospaced instrumentation, subtle translucent paneling, and micro-interactive pulse signals for real-time connection status.

## Colors

The color system delivers instantaneous semantic triage. In high-stakes incident remediation, hue is never purely ornamental—it functions as visual priority signaling.

### Semantic Triage Hierarchy
- **Primary Operational (`#2563eb` / `#3b82f6`):** Indicates active states, primary actions, selected nodes, and active filter contexts.
- **Command Shell (`#0a1628` background, `#0f172a` container, `#1e293b` border):** Frames global hierarchy, sidebar tools, and top-level infrastructure selectors.
- **Threat & Alert States:**
  - **Nominal / Secured (`#059669` / `#10b981`):** Cleared packet flows, verified cryptographic handshakes, and baseline RAN status.
  - **Warning / Policy Drift (`#d97706` / `#f59e0b`):** Metric anomalies, unverified cell handoffs, and resource throttling.
  - **Critical / Threat Vector (`#dc2626` / `#f43f5e`):** Unauthorized slice access, DDoS saturation, zero-day intrusion alerts.
- **Neutral Matrix:**
  - **Surface Canvas (`#f8fafc` to `#f1f5f9`):** Non-glare working background.
  - **Surface Card (`#ffffff`):** Foreground inspection panels.
  - **Text & Borders (`#0f172a` titles, `#334155` body, `#64748b` metadata, `#e2e8f0` borders):** Rigorous contrast adhering to WCAG AAA standards for micro-telemetry.

## Typography

Typography prioritizes rapid scanning, hierarchical clarity, and numeric precision.

### Typographic Rules
- **Inter (Primary UI):** Applied across all interface headings, navigation labels, contextual metadata, and general text. All metric reads, telemetry charts, and financial/packet totals must mandate the CSS property `font-feature-settings: "tnum" 1` (tabular figures) to eliminate jitter across real-time continuous refreshes.
- **JetBrains Mono (Technical Instrumentation):** Dedicated to packet hexes, cryptographic signature hashes, IP addresses (IPv4/IPv6), 5G IMSI/SUPI handles, and CLI debug panels.
- **Status Micro-Badges:** Strict uppercase styling, weighted at 600, with expanded letter-spacing (`0.06em`) to ensure instant legibility at 11px font sizes without crowding.

## Layout & Spacing

The layout structure optimizes data density without visual friction, employing a strict 4px/8px mathematical cadence.

### Grid Architecture
- **Command Sidebar Shell:** Fixed-width 260px navigation (collapsible to 64px icon-rail for widescreen multi-monitor SOC centers).
- **Analytical Grid:** 12-column dynamic fluid grid system inside the canvas with fixed `1.5rem` (`24px`) gutters on desktop screens, scaling down to `1rem` on compact viewports.
- **Canvas Margins:** `2rem` on viewports ≥1280px, dynamically reducing to `1rem` on mobile and tablet devices.

### Breakpoints & Adaptations
- **Desktop (≥1280px):** Multi-pane monitoring: split topology mapping, real-time threat feed, and live log inspection alongside primary metric cards.
- **Tablet (768px - 1279px):** Reflows 4-card telemetry grids into 2-column configurations; incident tables shift secondary columns to expandable details drawers.
- **Mobile (<768px):** Sidebar converts into an off-canvas drawer; metric cards stack linearly; data tables toggle to condensed list-card views.

## Elevation & Depth

Visual depth is achieved through tactile boundary contrast rather than exaggerated dropshadows, ensuring clean display rendering across SOC multi-monitor arrays.

### Elevation Levels
- **Canvas Base (`#f8fafc`):** The zero ground plane of the analytical area.
- **Surface Elevation 1 (Card & Module Layer):** Pure white (`#ffffff`) background, bounded by an explicit structural outline (`1px solid rgba(226, 232, 240, 0.8)`), accompanied by a diffused micro-shadow: `0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)`.
- **Surface Elevation 2 (Dropdowns, Popovers, & Tooltips):** Background `#ffffff`, outline `1px solid #cbd5e1`, supported by `0 4px 6px -1px rgba(15, 23, 42, 0.08), 0 2px 4px -2px rgba(15, 23, 42, 0.04)`.
- **Surface Elevation 3 (Critical Incident Modals & Drawers):** High-priority contextual overlays layered above a neutral backdrop blur (`rgba(10, 22, 40, 0.65)` backdrop with `backdrop-filter: blur(4px)`), carrying `0 20px 25px -5px rgba(15, 23, 42, 0.15)`.
- **Command Shell Inset Panels:** Nested dark utility zones inside `#0a1628` use `#0f172a` with subtle inner strokes (`#1e293b`) for zero shadow depth.

## Shapes

The design system implements a deliberate structural shape hierarchy that harmonizes human-centered UI ergonomics with technical discipline.

### Radius Assignments
- **Dashboard Modules & Analytics Cards:** Fixed `16px` border-radius (`rounded-xl` in this token model), creating soft framing for high-density, sharp tabular content inside.
- **Inputs, Buttons, & Interactive Controls:** Standard `6px` to `8px` radius (`rounded-md`), providing clear clickable boundaries without resembling consumer playfulness.
- **Telemetry Indicators & Status Badges:** Fully circular / pill-shaped (`rounded-full`), visually dissociating operational status items from interactive buttons or content panels.

## Components

### Buttons
- **Primary:** Background `#2563eb`, hover `#1d4ed8`, text `#ffffff`, height 36px, horizontal padding `14px`, radius 8px, font Inter medium 13px. Focus: `0 0 0 2px #ffffff, 0 0 0 4px #3b82f6`.
- **Secondary / Shell Action:** Background `#ffffff`, border `1px solid #cbd5e1`, text `#334155`, hover background `#f8fafc`.
- **Danger:** Background `#dc2626`, hover `#b91c1c`, text `#ffffff`.

### Status Badges (Pills)
- Rendered with `rounded-full`, horizontal padding 10px (`px-2.5`), vertical padding 2px (`py-0.5`), font Inter 11px uppercase, font-weight 600, letter-spacing `0.06em`.
- **Secured / Active:** Light green tint background (`#ecfdf5`), border `#a7f3d0`, text `#065f46`, pairing with an internal 6px pulsing green indicator dot.
- **Warning / Degraded:** Light amber tint (`#fffbeb`), border `#fde68a`, text `#92400e`.
- **Incident / Breach:** Light red tint (`#fef2f2`), border `#fecaca`, text `#991b1b`.

### Cards & Module Containers
- Solid white surface `#ffffff`, border `1px solid rgba(226, 232, 240, 0.8)`, border-radius 16px, padding `20px` to `24px`. Header features title in 15px semibold `#0f172a`, actions row, and optional micro-sparkline telemetry top-right.

### Input Fields
- Height 36px, radius 8px, background `#ffffff`, border `1px solid #cbd5e1`, font Inter 13px text `#0f172a`. Placeholder `#94a3b8`. Focus state shifts border to `#2563eb` with a ring of `3px rgba(37, 99, 235, 0.15)`.

### Hash Pill Tags & Micro-Telemetry
- **Cryptographic Hash Pill:** Background `#f1f5f9`, border `1px solid #e2e8f0`, radius 6px, padding `2px 8px`, JetBrains Mono 12px, tabular numbers, text `#475569`, incorporating a one-click clipboard action.
- **Confidence Interval Bars:** Linear micro-bars 4px tall with neutral track `#e2e8f0` and fill graded from `#3b82f6` (nominal) to `#dc2626` (high risk).
- **Pulsing Live Signal:** 8px absolute dot with an outer concentric CSS ping animation (`animate-ping`, duration 1.5s) in emerald or danger hues, signifying live ingestion stream connectivity.

### Checkboxes & Radio Controls
- Checkboxes feature an 8px radius for containers (square) and 16px circle for radio. Checked background `#2563eb` with a crisp white tick/dot. Inactive border `1.5px solid #cbd5e1`.