import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Workflow, WorkflowStatus } from '../services/workflowManager';

// 工作流存储状态接口
interface WorkflowState {
  workflows: Workflow[];
  selectedWorkflowId: string | null;
  
  // 添加工作流
  addWorkflow: (workflow: Workflow) => void;
  
  // 更新工作流
  updateWorkflow: (id: string, updates: Partial<Workflow>) => void;
  
  // 删除工作流
  deleteWorkflow: (id: string) => void;
  
  // 清空所有工作流
  clearWorkflows: () => void;
  
  // 选择当前查看的工作流
  selectWorkflow: (id: string | null) => void;
  
  // 获取选中的工作流
  getSelectedWorkflow: () => Workflow | null;
  
  // 通过ID获取工作流
  getWorkflowById: (id: string) => Workflow | undefined;
  
  // 更新工作流步骤状态
  updateWorkflowStepStatus: (workflowId: string, stepId: string, status: 'pending' | 'running' | 'success' | 'failed') => void;
  
  // 更新工作流状态
  updateWorkflowStatus: (id: string, status: WorkflowStatus) => void;
}

// 创建状态初始值和操作函数
const createWorkflowState = (set: any, get: any) => ({
  // 状态
  workflows: [],
  selectedWorkflowId: null,
  
  // 操作
  addWorkflow: (workflow: Workflow) => {
    set((state: WorkflowState) => ({
      workflows: [...state.workflows, workflow],
      selectedWorkflowId: workflow.id // 自动选择新添加的工作流
    }));
  },
  
  updateWorkflow: (id: string, updates: Partial<Workflow>) => {
    set((state: WorkflowState) => ({
      workflows: state.workflows.map((workflow) => 
        workflow.id === id ? { ...workflow, ...updates } : workflow
      )
    }));
  },
  
  deleteWorkflow: (id: string) => {
    set((state: WorkflowState) => ({
      workflows: state.workflows.filter((workflow) => workflow.id !== id),
      selectedWorkflowId: state.selectedWorkflowId === id ? null : state.selectedWorkflowId
    }));
  },
  
  clearWorkflows: () => {
    set({
      workflows: [],
      selectedWorkflowId: null
    });
  },
  
  selectWorkflow: (id: string | null) => {
    set({ selectedWorkflowId: id });
  },
  
  getSelectedWorkflow: () => {
    const { workflows, selectedWorkflowId } = get();
    if (!selectedWorkflowId) return null;
    return workflows.find((workflow: Workflow) => workflow.id === selectedWorkflowId) || null;
  },
  
  getWorkflowById: (id: string) => {
    return get().workflows.find((workflow: Workflow) => workflow.id === id);
  },
  
  updateWorkflowStepStatus: (workflowId: string, stepId: string, status: 'pending' | 'running' | 'success' | 'failed') => {
    set((state: WorkflowState) => ({
      workflows: state.workflows.map((workflow) => {
        if (workflow.id === workflowId) {
          return {
            ...workflow,
            steps: workflow.steps.map((step) => 
              step.id === stepId ? { ...step, status } : step
            )
          };
        }
        return workflow;
      })
    }));
    
    // 检查是否需要更新工作流状态
    const workflow = get().getWorkflowById(workflowId);
    if (workflow) {
      const allStepsCompleted = workflow.steps.every(step => 
        step.status === 'success' || step.status === 'failed'
      );
      
      const anyStepFailed = workflow.steps.some(step => step.status === 'failed');
      
      if (allStepsCompleted) {
        get().updateWorkflowStatus(
          workflowId, 
          anyStepFailed ? WorkflowStatus.FAILED : WorkflowStatus.COMPLETED
        );
      }
    }
  },
  
  updateWorkflowStatus: (id: string, status: WorkflowStatus) => {
    set((state: WorkflowState) => ({
      workflows: state.workflows.map((workflow) => {
        if (workflow.id === id) {
          return {
            ...workflow,
            status,
            // 如果工作流完成或失败，设置结束时间
            endTime: (status === WorkflowStatus.COMPLETED || 
                     status === WorkflowStatus.FAILED || 
                     status === WorkflowStatus.CANCELED) 
                     ? new Date() 
                     : workflow.endTime
          };
        }
        return workflow;
      })
    }));
  }
});

// 创建工作流状态管理
export const useWorkflowStore = create(
  persist(
    createWorkflowState,
    {
      name: 'qlib-workflow-storage',
      partialize: (state: WorkflowState) => ({ 
        workflows: state.workflows,
        selectedWorkflowId: state.selectedWorkflowId
      }),
    }
  )
);
