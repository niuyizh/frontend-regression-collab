import { useState } from 'react';
import { AsyncPanel } from './components/AsyncPanel';
import { NewTaskForm } from './components/NewTaskForm';
import { ResponsiveNav } from './components/ResponsiveNav';
import { TaskList } from './components/TaskList';
import { TaskModal } from './components/TaskModal';
import { initialTasks } from './data';
import type { Task } from './types';

export function App() {
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [selectedId, setSelectedId] = useState<number>(initialTasks[0].id);
  const [editingId, setEditingId] = useState<number | null>(null);

  const selectedTask = tasks.find((task) => task.id === selectedId) ?? tasks[0];
  const editingTask = tasks.find((task) => task.id === editingId) ?? null;

  const updateTask = (updated: Task) => {
    setTasks((current) => current.map((task) => (task.id === updated.id ? updated : task)));
    setEditingId(null);
  };

  const addTask = (title: string) => {
    const task: Task = {
      id: Math.max(...tasks.map((item) => item.id)) + 1,
      title,
      owner: 'You',
      status: 'Todo',
      priority: 'Medium',
    };
    setTasks((current) => [...current, task]);
    setSelectedId(task.id);
  };

  return (
    <div className="app-shell">
      <ResponsiveNav />
      <main>
        <header className="hero">
          <div>
            <p className="eyebrow">Product operations</p>
            <h1>RegressionBoard</h1>
            <p>Keep routine interface changes from surprising existing users.</p>
          </div>
          <span className="task-count" aria-label={`${tasks.length} tasks`}>{tasks.length} tasks</span>
        </header>

        <div className="dashboard-grid">
          <section className="card task-card" aria-labelledby="task-list-title">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Workspace</p>
                <h2 id="task-list-title">Tasks</h2>
              </div>
            </div>
            <TaskList
              tasks={tasks}
              selectedId={selectedId}
              onSelect={setSelectedId}
              onEdit={setEditingId}
            />
          </section>

          <aside className="stack">
            <section className="card detail-card" aria-labelledby="selected-title">
              <p className="eyebrow">Selected task</p>
              <h2 id="selected-title">{selectedTask.title}</h2>
              <dl>
                <div><dt>Owner</dt><dd>{selectedTask.owner}</dd></div>
                <div><dt>Status</dt><dd>{selectedTask.status}</dd></div>
                <div><dt>Priority</dt><dd>{selectedTask.priority}</dd></div>
              </dl>
            </section>
            <AsyncPanel />
            <NewTaskForm onAdd={addTask} />
          </aside>
        </div>
      </main>

      {editingTask && (
        <TaskModal
          task={editingTask}
          onCancel={() => setEditingId(null)}
          onSave={updateTask}
        />
      )}
    </div>
  );
}

