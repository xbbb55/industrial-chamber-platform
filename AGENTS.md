# Frontend UI Constraints

These rules apply to all frontend work in `frontend-vue/`. Treat the current Vue desktop dashboard as the product design system, not as a one-off page reference. New UI and revisions must fit the existing interface unless the user explicitly asks for a visual redesign.

## Visual Baseline

- Preserve the rounded Electron workspace shell: a restrained cool light-gray surface, an approximately 20px outer shell radius, and a consistent 72px brand/header row across views.
- Keep the brand/logo centered and visually integrated into the shell. Do not add a white logo tile, page-specific logo sizing, or decorative rules beneath the logo.
- Keep the sidebar, brand area, top status/header bar, and sidebar footer geometrically and visually stable while switching navigation items. Shared shell elements must not change because a page adds a class or layout subtree.
- Use charcoal (`#202326` or the existing system token) for primary actions and selected navigation, white text on charcoal, and high-contrast dark-gray text for unselected navigation. Use cool gray/white surfaces, subtle borders, and restrained shadows for secondary controls.
- Keep the established rounded control language: navigation and primary buttons are generally about 12px radius; ordinary cards use the existing `--system-radius` or nearby 8-14px radii. Avoid sharp industrial/hexagonal clipping, ornamental corner marks, glows, heavy gradients, and decorative separator lines in the shared shell.
- Use color beyond the neutral shell for meaningful status/data semantics (for example temperature, humidity, alarms, or online state), not as arbitrary decoration.
- Keep the data-monitor dashboard/HMI content intact when a request only concerns shared navigation or shell styling. Change dashboard internals only when explicitly requested.

## Components And Interaction

- Reuse existing Vue components and CSS patterns before creating new ones. Use the existing `AppIcon`/Lucide icon path for interface icons; do not draw substitute icons manually.
- New buttons must match the established button height, radius, typography, spacing, and hover/focus/disabled states. Icon-only buttons need an accessible name and a tooltip/title where the icon is not self-evident.
- Use semantic controls for the job: buttons for actions, tabs for view selection, checkboxes/toggles for binary settings, and sliders only for values with meaningful finite bounds. Keep unrestricted numeric values directly editable. Keep units beside the corresponding value/input, following existing field patterns.
- Keep cards and controls aligned to a consistent grid. Avoid nested decorative cards, unexplained copy beneath buttons, and one-off spacing that makes layouts shift when navigating between views.
- Preserve keyboard access, visible focus, readable contrast, and labels for inputs. Text and controls must fit without overlap at supported widths, including collapsed sidebar and narrow layouts.

## Styling Ownership

- `styles.css` is the base layer; `enterprise.css` contains legacy/shared component styling; `motion.css` owns selection motion; `system-theme.css` and `parameter-theme.css` contain page/component theme details; `shell-theme.css` is imported last and owns shared application-shell geometry and cross-view visual invariants.
- Put cross-view header, logo, sidebar, and footer rules in `shell-theme.css`. Do not create separate monitor/non-monitor copies of shared shell rules. Prefer a shared `.app-shell:has(.sidebar)` rule; use page-specific selectors only for genuinely page-specific content.
- Keep dashboard-specific styling scoped to dashboard components. Do not let a dashboard selector override shared header/sidebar/footer styles.
- Reuse existing design tokens such as `--system-bg`, `--system-surface`, `--system-line`, `--system-ink`, `--system-ink-soft`, `--system-ink-muted`, `--system-radius`, and `--system-shadow` when applicable. Avoid introducing a second competing palette or arbitrary per-page values.
- Avoid escalating CSS specificity or adding `!important` to resolve cascade issues. First remove or consolidate the conflicting source rule where it is safe; add a narrowly scoped override only when legacy constraints require it.
- Do not alter unrelated user changes while making UI updates.

## Verification

- For frontend changes, run `npm run build` from `frontend-vue/`.
- For shell or shared-control changes, inspect the result in data monitoring, operation settings, system parameters, history, and fault query, including collapsed-sidebar and narrow-width states. Confirm the header height, logo placement, sidebar surfaces, separators, and footer controls remain consistent.
- For visual layout changes, use the available running app/browser to inspect representative desktop and narrow layouts; a successful build alone does not establish visual consistency.
