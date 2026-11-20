import { useEffect, useRef, useState } from 'react';
import type { Task, TaskStatus } from '../types';

type Props = {
  task: Task;
  onCancel: () => void;
  onSave: (task: Task) => void;
};

export function TaskModal({ task, onCancel, onSave }: Props) {
  const [title, setTitle] = useState(task.title);
  const [status, setStatus] = useState<TaskStatus>(task.status);
  const titleRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const previouslyFocused = document.activeElement as HTMLElement | null;
    titleRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onCancel();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      previouslyFocused?.focus();
    };
  }, [onCancel]);

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onCancel}>
      <section
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-task-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <p className="eyebrow">Task editor</p>
        <h2 id="edit-task-title">Edit task</h2>
        <label>
          Title
          <input ref={titleRef} value={title} onChange={(event) => setTitle(event.target.value)} />
        </label>
        <label>
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value as TaskStatus)}>
            <option>Todo</option>
            <option>In progress</option>
            <option>Done</option>
          </select>
        </label>
        <p className="read-only-priority">Priority: <strong>{task.priority}</strong></p>
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onCancel}>Cancel</button>
          <button
            type="button"
            onClick={() => onSave({ ...task, title: title.trim() || task.title, status })}
          >
            Save changes
          </button>
        </div>
      </section>
    </div>
  );
}

