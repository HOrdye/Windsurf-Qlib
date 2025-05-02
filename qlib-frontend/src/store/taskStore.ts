import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// 任务状态类型
export type TaskStatus = 'pending' | 'running' | 'success' | 'failed';

// 任务类型
export type TaskType = 'training' | 'backtest' | 'data_init';

// 任务接口
export interface Task {
  id: string;
  name: string;
  status: TaskStatus;
  progress: number;
  startTime: Date;
  endTime?: Date;
  type: TaskType;
  log: string[];
  configId?: string;
  metrics?: any;
}

// 任务状态接口
interface TaskState {
  tasks: Task[];
  selectedTaskId: string | null;
  
  // 添加任务
  addTask: (task: Task) => void;
  
  // 更新任务
  updateTask: (id: string, updates: Partial<Task>) => void;
  
  // 删除任务
  deleteTask: (id: string) => void;
  
  // 清空所有任务
  clearTasks: () => void;
  
  // 选择当前查看的任务
  selectTask: (id: string | null) => void;
  
  // 获取选中的任务
  getSelectedTask: () => Task | null;
  
  // 通过ID获取任务
  getTaskById: (id: string) => Task | undefined;
  
  // 更新任务进度
  updateTaskProgress: (id: string, progress: number, message?: string) => void;
  
  // 添加任务日志
  addTaskLog: (id: string, logMessage: string) => void;
}

// 创建状态初始值和操作函数
const createTaskState = (set: any, get: any) => ({
  // 状态
  tasks: [],
  selectedTaskId: null,
  
  // 操作
  addTask: (task: Task) => {
    set((state: TaskState) => ({
      tasks: [...state.tasks, task],
      selectedTaskId: task.id // 自动选择新添加的任务
    }));
  },
  
  updateTask: (id: string, updates: Partial<Task>) => {
    set((state: TaskState) => ({
      tasks: state.tasks.map((task) => 
        task.id === id ? { ...task, ...updates } : task
      )
    }));
  },
  
  deleteTask: (id: string) => {
    set((state: TaskState) => ({
      tasks: state.tasks.filter((task) => task.id !== id),
      selectedTaskId: state.selectedTaskId === id ? null : state.selectedTaskId
    }));
  },
  
  clearTasks: () => {
    set({
      tasks: [],
      selectedTaskId: null
    });
  },
  
  selectTask: (id: string | null) => {
    set({ selectedTaskId: id });
  },
  
  getSelectedTask: () => {
    const { tasks, selectedTaskId } = get();
    if (!selectedTaskId) return null;
    return tasks.find((task: Task) => task.id === selectedTaskId) || null;
  },
  
  getTaskById: (id: string) => {
    return get().tasks.find((task: Task) => task.id === id);
  },
  
  updateTaskProgress: (id: string, progress: number, message?: string) => {
    const { tasks } = get();
    const task = tasks.find((t: Task) => t.id === id);
    
    if (task) {
      const updates: Partial<Task> = { 
        progress: Math.min(Math.max(0, progress), 100) 
      };
      
      // 如果进度达到100%，更新任务状态为成功
      if (progress >= 100 && task.status === 'running') {
        updates.status = 'success';
        updates.endTime = new Date();
      } 
      // 如果进度大于0且状态为等待中，则更新为运行中
      else if (progress > 0 && task.status === 'pending') {
        updates.status = 'running';
      }
      
      // 如果提供了消息，添加到日志
      if (message) {
        const timestamp = new Date().toLocaleTimeString();
        const logMessage = `[${timestamp}] ${message}`;
        updates.log = [...task.log, logMessage];
      }
      
      get().updateTask(id, updates);
    }
  },
  
  addTaskLog: (id: string, logMessage: string) => {
    const { tasks } = get();
    const task = tasks.find((t: Task) => t.id === id);
    
    if (task) {
      const timestamp = new Date().toLocaleTimeString();
      const formattedLog = `[${timestamp}] ${logMessage}`;
      
      get().updateTask(id, {
        log: [...task.log, formattedLog]
      });
    }
  }
});

// 创建任务状态管理
export const useTaskStore = create(
  persist(
    createTaskState,
    {
      name: 'qlib-task-storage',
      partialize: (state: TaskState) => ({ 
        tasks: state.tasks,
        selectedTaskId: state.selectedTaskId
      }),
    }
  )
);
