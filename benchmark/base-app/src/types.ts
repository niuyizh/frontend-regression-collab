export type TaskStatus = 'Todo' | 'In progress' | 'Done';

export type Task = {
  id: number;
  title: string;
  owner: string;
  status: TaskStatus;
  priority: 'Low' | 'Medium' | 'High';
};

