# Tailwind theme extension

Tailwind v4 (`@theme` in your CSS entry):

```css
@import "tailwindcss";

@theme {
  --font-sans: "Libre Franklin", Helvetica, sans-serif;
  --font-mono: "IBM Plex Mono", ui-monospace, monospace;

  --color-accent: oklch(0.5 0.11 205);
  --color-accent-hover: oklch(0.55 0.11 205);
  --color-accent-busy: oklch(0.62 0.07 205);
  --color-accent-tint: #eef4f5;
  --color-accent-surface: #f2f8f9;
  --color-accent-border: #cfe0e3;
  --color-accent-border-strong: #bcd6da;
  --color-accent-muted: #c9d9dc;

  --color-page: #f6f5f3;
  --color-surface: #fffefc;
  --color-surface-2: #faf9f7;
  --color-surface-3: #fdfcfa;

  --color-line: #e6e3dd;
  --color-line-2: #e2ded7;
  --color-line-3: #efece7;
  --color-line-4: #f0ede8;
  --color-line-dashed: #cfcac1;

  --color-ink: #1c1a17;
  --color-ink-2: #26241f;
  --color-ink-3: #2a2723;
  --color-ink-4: #57524b;
  --color-ink-5: #6f6a62;
  --color-ink-6: #8c867d;
  --color-ink-7: #a09a91;
  --color-ink-8: #b3ada3;

  --color-brand-bar: #9DE2DA;
  --color-brand-ink: #116A72;
  --color-brand-ink-2: #316D6D;

  --color-ok: oklch(0.6 0.13 165);
  --color-ok-ink: oklch(0.42 0.07 175);

  --shadow-card: 0 1px 2px rgb(28 26 23 / 0.03);
  --shadow-btn: 0 1px 2px rgb(28 26 23 / 0.12);
  --shadow-lift: 0 1px 3px rgb(28 26 23 / 0.06);

  --animate-pulse-dot: pulseDot 2.4s ease-in-out infinite;
  --animate-shimmer: shimmer 1.3s linear infinite;
}

@keyframes pulseDot { 0%, 100% { opacity: 1 } 50% { opacity: .25 } }
@keyframes shimmer { 0% { background-position: -320px 0 } 100% { background-position: 320px 0 } }

body { @apply bg-page text-ink font-sans antialiased; }
::placeholder { color: #a8a29b; }
```

Tailwind v3 (`tailwind.config.js`): move the same values under
`theme.extend.colors` / `fontFamily` / `boxShadow` / `keyframes` / `animation`,
dropping the `--color-` prefixes.

Font link for `index.html`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
```
