# T04 — Responsive navigation destination and active state

Extend the primary navigation with a `Reports` destination and active-state semantics.

Acceptance criteria:

- Add a `Reports` link targeting `#reports`; preserve `Board` and `Activity`.
- Clicking a navigation link marks only that link with `aria-current="page"` and updates the URL hash.
- On mobile, selecting any link closes the expanded menu and updates the Menu button's `aria-expanded` state.
- On desktop, all navigation links remain visible without opening the menu.
- Resizing from mobile to desktop must not leave links hidden because the mobile menu was closed.
- Preserve all existing behavior and keep `npm run build` and `npm run test:public` green.

Do not modify or delete existing public tests. Check both sides of the responsive breakpoint.

