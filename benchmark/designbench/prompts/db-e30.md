# DesignBench React Edit 30

Primary source: `app/page.tsx`

Relevant source window: lines 63-90. Read it with `file_read` using
`offset=63, limit=28`; do not read the SVG icon definitions below the component
or inspect the shared Button implementation unless the bounded edit fails to
render. This keeps the task context within the fixed token budget.

This task uses DesignBench's text-and-code (`code`) mode. Implement this
requirement while preserving everything else in the UI:

> In the rightmost column, make the top toolbar sticky. Remove button borders
> and place the buttons directly next to each other without margins, similar
> to an Apple Mac toolbar. Keep the same toolbar options. Nothing else about
> the UI should change.

Do not inspect benchmark target files or paths outside this workspace. Run
`npm run verify:agent` after editing.
