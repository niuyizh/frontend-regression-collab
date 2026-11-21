# T02 — Editable priority in the task modal

Allow a task's priority to be edited in the existing modal.

Acceptance criteria:

- Replace the read-only priority text with a form control labelled `Priority`.
- The choices are `Low`, `Medium`, and `High`, initialized from the task being edited.
- `Save changes` persists title, status, and priority together and the selected-task detail reflects the new priority.
- `Cancel`, clicking the backdrop, and pressing Escape discard every unsaved field, including priority.
- Preserve the current initial focus and focus-restoration behavior when the modal closes.
- Preserve all existing behavior and keep `npm run build` and `npm run test:public` green.

Do not modify or delete existing public tests. Check keyboard and cancellation paths, not only saving.

Primary source files: `src/components/TaskModal.tsx`, `src/App.tsx`, and `src/types.ts`. Read these directly; the shell already starts at the task repository root.
