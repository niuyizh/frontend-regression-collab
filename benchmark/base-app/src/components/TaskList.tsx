import type { Task } from '../types';

type Props = {
  tasks: Task[];
  selectedId: number;
  onSelect: (id: number) => void;
  onEdit: (id: number) => void;
};

export function TaskList({ tasks, selectedId, onSelect, onEdit }: Props) {
  return (
    <ul className="task-list">
      {tasks.map((task) => (
        <li key={task.id} className={task.id === selectedId ? 'selected' : ''}>
          <button className="task-main" type="button" onClick={() => onSelect(task.id)}>
            <strong>{task.title}</strong>
            <span>{task.owner} · {task.status}</span>
          </button>
          <button
            className="icon-button"
            type="button"
            aria-label={`Edit ${task.title}`}
            onClick={() => onEdit(task.id)}
          >
            Edit
          </button>
        </li>
      ))}
    </ul>
  );
}

