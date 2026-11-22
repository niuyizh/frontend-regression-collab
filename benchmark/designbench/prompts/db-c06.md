# DesignBench React Compile Repair 6

Primary source: `app/page.tsx`

Repair the following compilation/runtime boundary error with the smallest coherent change:

> A component imports `useState`, but it is treated as a Server Component because neither it nor a parent is marked as a Client Component.

Preserve the component behavior and layout. Do not inspect benchmark repaired targets or paths outside this workspace. Run `npm run verify:agent` after editing.
