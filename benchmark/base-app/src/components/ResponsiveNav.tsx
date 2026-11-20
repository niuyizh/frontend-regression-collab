import { useState } from 'react';

export function ResponsiveNav() {
  const [open, setOpen] = useState(false);
  return (
    <nav className="top-nav" aria-label="Primary navigation">
      <a className="brand" href="#top">RB</a>
      <button
        className="menu-button"
        type="button"
        aria-expanded={open}
        aria-controls="nav-links"
        onClick={() => setOpen((value) => !value)}
      >
        Menu
      </button>
      <div id="nav-links" className={`nav-links ${open ? 'open' : ''}`}>
        <a href="#board">Board</a>
        <a href="#activity">Activity</a>
      </div>
    </nav>
  );
}

