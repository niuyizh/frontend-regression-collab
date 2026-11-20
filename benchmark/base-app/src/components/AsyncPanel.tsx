import { useEffect, useState } from 'react';

type State = 'loading' | 'success' | 'error';

export function AsyncPanel() {
  const [state, setState] = useState<State>('loading');

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const requested = new URLSearchParams(window.location.search).get('sync');
      setState(requested === 'error' ? 'error' : 'success');
    }, 120);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <section className="card sync-card" aria-live="polite">
      <p className="eyebrow">Remote sync</p>
      {state === 'loading' && <p className="sync-state">Checking service…</p>}
      {state === 'success' && <p className="sync-state success">All changes are synced.</p>}
      {state === 'error' && (
        <div className="sync-state error" role="alert">
          <strong>Sync failed</strong>
          <span>Check your connection and try again later.</span>
        </div>
      )}
    </section>
  );
}

