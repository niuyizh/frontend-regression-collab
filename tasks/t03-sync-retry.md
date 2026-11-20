# T03 — Recoverable asynchronous error state

Add a recovery action to the remote-sync error state.

Acceptance criteria:

- The existing success path at `/` remains unchanged and never shows a retry action.
- At `/?sync=error`, the error state includes a button named `Retry sync`.
- Activating it immediately returns the panel to `Checking service…`, then completes as `All changes are synced.` after the same simulated delay.
- The retry action disappears after success and cannot create overlapping timers from repeated activation.
- Retrying must not reload the page or reset the currently selected task.
- Preserve all existing behavior and keep `npm run build` and `npm run test:public` green.

Do not modify or delete existing public tests. Treat loading, error, success, cleanup, and unrelated page state as separate regression surfaces.

