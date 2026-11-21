# T05 — Due-date validation with durable draft

Add an optional due-date field to the quick-add form.

Acceptance criteria:

- Add a date input labelled `Due date`.
- An empty due date is valid.
- A date earlier than the user's current local calendar date blocks submission and shows exactly `Due date cannot be in the past.` in an accessible alert.
- A validation failure preserves both title and due date.
- Title and due date drafts both survive a page reload through local storage.
- A successful submission clears both controls and both persisted draft values while retaining the existing title-required validation.
- Preserve all existing behavior and keep `npm run build` and `npm run test:public` green.

Do not modify or delete existing public tests. Pay attention to validation, persistence, and successful cleanup as distinct states.

Primary source files: `src/components/NewTaskForm.tsx`, `src/App.tsx`, and `src/types.ts`. Read these directly; the shell already starts at the task repository root.
