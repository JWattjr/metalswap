---
name: MetalSwap
description: A graphite market terminal for exact, finality-gated metal relative returns.
colors:
  canvas: "#0c1112"
  canvas-deep: "#080c0d"
  surface: "#11191b"
  surface-raised: "#172124"
  surface-soft: "#141d1f"
  rule: "#2a3739"
  rule-soft: "#202b2d"
  paper: "#eef0ea"
  text: "#d9dfd9"
  muted: "#8c9998"
  quiet: "#637170"
  gold: "#d4a354"
  gold-bright: "#f2ca78"
  silver: "#aebec1"
  silver-bright: "#e3eef0"
  cyan: "#71d8cf"
  amber: "#e7b76d"
  error: "#ff9a8e"
typography:
  display:
    fontFamily: "Arial, ui-sans-serif, system-ui, sans-serif"
    fontSize: "clamp(36px, 5vw, 58px)"
    fontWeight: 500
    lineHeight: 0.98
    letterSpacing: "-0.055em"
  title:
    fontFamily: "Arial, ui-sans-serif, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Arial, ui-sans-serif, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "SFMono-Regular, Consolas, Liberation Mono, monospace"
    fontSize: "10px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "0.1em"
  mono:
    fontFamily: "SFMono-Regular, Consolas, Liberation Mono, monospace"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.4
rounded:
  sm: "7px"
  md: "10px"
  lg: "14px"
spacing:
  xs: "6px"
  sm: "12px"
  md: "18px"
  lg: "24px"
  xl: "34px"
components:
  button-primary:
    backgroundColor: "{colors.cyan}"
    textColor: "{colors.canvas-deep}"
    rounded: "{rounded.sm}"
    padding: "0 15px"
    height: "48px"
  button-secondary:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.paper}"
    rounded: "{rounded.sm}"
    padding: "0 14px"
    height: "40px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.lg}"
    padding: "24px"
  input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.paper}"
    rounded: "{rounded.sm}"
    padding: "0 14px"
    height: "48px"
---

# Design System: MetalSwap

## Overview

**Creative North Star: "The Assay Console"**

MetalSwap is styled as a quiet instrument panel for making one time-bounded decision. Graphite surfaces keep the screen analytical and low-noise; the two metals get their own material voice so the choice can be read before it is clicked. The density is deliberate: a live working surface first, supporting evidence below.

The visual language is flat, bordered, and precise. Cyan belongs to evidence, protocol, and focus states; it is not a general-purpose decoration. The screen avoids gradients, glass, crypto-neon spectacle, fabricated market activity, and ornamental imagery. Synthetic data is always named where it appears.

**Key Characteristics:**

- Instrument-like graphite canvas with thin structural rules.
- Warm brass for gold, cool silver for silver, cyan for evidence and finality.
- Tabular numbers and monospace protocol labels for quick scanning.
- One dominant entry bench, with history and settlement detail kept subordinate.

## Colors

The palette is a dark graphite field with restrained warm/cool material accents and a rare verification cyan.

### Primary

- **Evidence Cyan**: Used for finality, evidence, focus, and the primary action.

### Secondary

- **Warm Brass**: Used for gold selection, gold chart strokes, and gold pool weight.
- **Cool Silver**: Used for silver selection, silver chart strokes, and silver pool weight.

### Neutral

- **Graphite Canvas**: The page field and deepest instrument background.
- **Instrument Surface**: Panel fill and raised panel fill.
- **Paper / Text**: High-contrast headings and standard reading text.
- **Muted / Quiet**: Supporting copy, labels, and low-priority metadata.
- **Structural Rules**: Thin borders and dividers that define grouping without cards-within-cards noise.

### Named Rules

**The Rare Cyan Rule.** Cyan signals a protocol or interaction state; it should not become a general decorative accent.

## Typography

**Display Font:** Arial with ui-sans-serif and system fallbacks  
**Body Font:** Arial with ui-sans-serif and system fallbacks  
**Label/Mono Font:** SFMono-Regular, Consolas, or Liberation Mono

**Character:** A plain grotesk keeps the product legible and tool-like. Monospace is reserved for timestamps, amounts, hashes, and compact protocol labels so exact values feel inspectable.

### Hierarchy

- **Display** (500, clamp 36px–58px, 0.98 line-height): The Gold vs Silver market promise.
- **Title** (600, 17px, 1.2 line-height): Panel headings and evidence sections.
- **Body** (400, 14px, 1.5 line-height): Explanatory copy and reading text.
- **Label** (700, 10px, uppercase, 0.1em tracking): Section labels, status, and protocol metadata.
- **Mono** (500, 10px–20px, tabular figures): Time, pool, stake, and exact rule display.

### Named Rules

**The Instrument Numbers Rule.** Display amounts and timestamps with tabular numerals; never make exact market state look ornamental.

## Layout

The page uses a centered surface capped at 1440px with 34px side gutters on wide screens. The first working region is a two-column bench: relative performance and live reading occupy the broad left field; the entry panel is a fixed narrow rail. The interval bar spans the surface and anchors the current UTC window before the decision area.

Below the bench, positions and settlement history share a quieter two-column row, followed by a single protocol strip and the settlement detail. At 900px the workbench becomes one column with the entry panel first, so the decision remains immediately actionable on mobile. At 600px gutters tighten, metadata collapses, and evidence tables become compact without horizontal page overflow.

## Elevation & Depth

Depth comes from tonal layering and structural borders rather than floating glass. The interval bar carries a restrained ambient shadow to separate the live window from the canvas; ordinary panels remain flat. Hover movement is limited to a one-pixel lift on actionable controls, and focus is a clear cyan outline.

### Shadow Vocabulary

- **Ambient interval**: `0 14px 34px rgba(0, 0, 0, 0.22)` for the current interval bar only.
- **Flat panel**: no shadow; use surface contrast and a thin rule.

### Named Rules

**The Flat Instrument Rule.** If a surface can be understood through tonal contrast and a rule, do not add elevation.

## Shapes

Panels use gently rounded 14px corners, controls use 7px corners, and compact outcome blocks use 10px corners. Borders are thin and slightly softened against graphite. Pills are reserved for network, evidence, and state labels; the main market choice uses a rectangular selection block so it reads like a control surface rather than a badge.

## Components

### Buttons

- **Shape:** Tactile, compact rectangles with 7px corners.
- **Primary:** Cyan fill, deep graphite text, 48px height, and a deliberate full-width action in the entry rail.
- **Hover / Focus:** A one-pixel lift and color shift on hover; a 2px cyan outline on keyboard focus.
- **Secondary / Ghost:** Graphite fill or transparent fill with a structural rule; use for side selection, quick stakes, and copy/refresh actions.

### Chips

- **Style:** Small uppercase labels with a thin border, tight padding, and no filled gradient.
- **State:** Cyan marks synthetic/evidence or selected protocol states; amber marks provisional timing; metal colors mark instrument identity.

### Cards / Containers

- **Corner Style:** 14px for major panels, 10px for nested outcome blocks.
- **Background:** Graphite surface layers, never translucent glass.
- **Shadow Strategy:** Flat by default; only the interval bar uses ambient depth.
- **Border:** One thin structural rule around a working surface.
- **Internal Padding:** 22px–24px on desktop, 16px on narrow screens.

### Inputs / Fields

- **Style:** Dark inset field with a 1px rule, 7px corners, and a tabular numeric face.
- **Focus:** Border shifts to evidence cyan with the global 2px focus outline.
- **Error / Disabled:** Quiet rule and quiet text; preserve the shape and explain the state in plain language.

### Navigation

- **Style:** A compact 68px top bar with wordmark, network/data mode, and wallet/replay action.
- **Mobile:** Keep the wordmark and primary action; hide secondary network context to protect the working width.

### Relative-performance chart

The chart is runtime SVG, not a raster asset. It is rebased to 100.00 for directional context only, uses brass and silver strokes, and carries an explicit synthetic replay label. It must never be presented as settlement evidence or historical volume.

## Do's and Don'ts

### Do:

- **Do** make GOLD and SILVER the clearest competing controls on the first working surface.
- **Do** use cyan for evidence, finality, focus, and verified protocol steps.
- **Do** keep timestamps, pool amounts, and rule versions tabular and exact-looking.
- **Do** label synthetic or illustrative values at the point of use.
- **Do** preserve the mobile order: entry decision first, context second, settlement proof below.

### Don't:

- **Don't** use gradients, glassmorphism, default crypto neon, or decorative coin imagery.
- **Don't** imply live liquidity, volume, history, addresses, or finality without a readback.
- **Don't** turn every section into a repeated rounded card; use the terminal's structural hierarchy.
- **Don't** let chart movement or a provisional leader masquerade as the settlement result.
