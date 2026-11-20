import { FormEvent, useState } from 'react';

const DRAFT_KEY = 'regression-board-draft';

type Props = { onAdd: (title: string) => void };

export function NewTaskForm({ onAdd }: Props) {
  const [title, setTitle] = useState(() => window.localStorage.getItem(DRAFT_KEY) ?? '');
  const [error, setError] = useState('');

  const updateTitle = (value: string) => {
    setTitle(value);
    window.localStorage.setItem(DRAFT_KEY, value);
    if (value.trim()) setError('');
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!title.trim()) {
      setError('Enter a task title.');
      return;
    }
    onAdd(title.trim());
    setTitle('');
    setError('');
    window.localStorage.removeItem(DRAFT_KEY);
  };

  return (
    <section className="card form-card">
      <p className="eyebrow">Quick add</p>
      <h2>New task</h2>
      <form onSubmit={submit} noValidate>
        <label>
          Title
          <input
            name="title"
            value={title}
            aria-describedby={error ? 'title-error' : undefined}
            onChange={(event) => updateTitle(event.target.value)}
          />
        </label>
        {error && <p id="title-error" className="field-error" role="alert">{error}</p>}
        <button type="submit">Add task</button>
      </form>
    </section>
  );
}

