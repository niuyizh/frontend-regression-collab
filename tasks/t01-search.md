# T01 — Task search with selection preservation

Add a compact search control above the task list.

Acceptance criteria:

- The input has the accessible label `Search tasks` and uses the search input role.
- Filtering is immediate and case-insensitive against task titles.
- A non-empty query shows a `Clear search` button; clearing restores every task and leaves focus on that button.
- If no task matches, show exactly `No tasks match your search.`.
- Filtering must not change the selected task merely because its row is temporarily hidden. The selected-task detail card remains stable and returns with the same selection after clearing.
- Preserve all existing behavior and keep `npm run build` and `npm run test:public` green.

Do not modify or delete existing public tests. Inspect the surrounding UI states instead of optimizing only for the obvious happy path.

Primary source files: `src/components/TaskList.tsx` and `src/App.tsx`. Read these directly; the shell already starts at the task repository root.
