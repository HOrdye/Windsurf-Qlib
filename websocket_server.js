const WebSocket = require('ws');
const http = require('http');

// 创建HTTP服务器
const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Qlib WebSocket Server');
});

// 创建WebSocket服务器
const wss = new WebSocket.Server({ server });

// 客户端连接集合
const clients = new Set();

// 任务状态存储
const tasks = new Map();
const workflows = new Map();

// 处理WebSocket连接
wss.on('connection', (ws) => {
  console.log('客户端已连接');
  clients.add(ws);

  // 发送欢迎消息
  ws.send(JSON.stringify({
    type: 'system_notification',
    payload: {
      message: '已连接到Qlib服务器',
      level: 'success'
    },
    timestamp: Date.now()
  }));

  // 处理消息
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      console.log('收到消息:', data);

      // 处理心跳消息
      if (data.type === 'heartbeat') {
        ws.send(JSON.stringify({
          type: 'heartbeat',
          payload: { timestamp: Date.now() },
          timestamp: Date.now(),
          id: data.id
        }));
        return;
      }

      // 处理任务提交
      if (data.type === 'task_submit') {
        const taskId = `task_${Date.now()}`;
        const task = {
          id: taskId,
          name: data.payload.name || `任务 ${taskId}`,
          type: data.payload.type || 'train',
          status: 'pending',
          progress: 0,
          startTime: new Date().toISOString(),
          config: data.payload.config || {}
        };

        tasks.set(taskId, task);

        // 发送任务ID响应
        ws.send(JSON.stringify({
          type: 'task_submit_response',
          payload: { taskId },
          timestamp: Date.now(),
          id: data.id
        }));

        // 模拟任务执行
        setTimeout(() => {
          task.status = 'running';
          broadcastTaskUpdate(task);

          // 模拟任务进度更新
          const progressInterval = setInterval(() => {
            task.progress += 10;
            
            if (task.progress >= 100) {
              clearInterval(progressInterval);
              task.progress = 100;
              task.status = 'success';
              task.endTime = new Date().toISOString();
              
              // 为训练任务添加模拟指标
              if (task.type === 'train') {
                task.metrics = {
                  accuracy: Math.random() * 0.2 + 0.7,
                  precision: Math.random() * 0.2 + 0.7,
                  recall: Math.random() * 0.2 + 0.7,
                  f1_score: Math.random() * 0.2 + 0.7,
                  returns: Array.from({ length: 30 }, () => Math.random() * 10 - 2),
                  performance: {
                    IC: Math.random() * 0.5,
                    ICIR: Math.random() * 2,
                    Rank_IC: Math.random() * 0.5,
                    Rank_ICIR: Math.random() * 2
                  },
                  allocation: {
                    '股票': Math.random() * 60 + 20,
                    '债券': Math.random() * 30 + 10,
                    '现金': Math.random() * 20 + 5,
                    '其他': Math.random() * 10
                  }
                };
              }
              
              // 为回测任务添加模拟指标
              if (task.type === 'backtest') {
                task.metrics = {
                  annualized_return: Math.random() * 0.3 + 0.05,
                  max_drawdown: Math.random() * 0.2 + 0.1,
                  sharpe: Math.random() * 2 + 0.5,
                  information_ratio: Math.random() * 1.5 + 0.3,
                  returns: Array.from({ length: 50 }, (_, i) => Math.sin(i / 5) * 5 + Math.random() * 2 - 1),
                  performance: {
                    win_rate: Math.random() * 0.3 + 0.5,
                    avg_win: Math.random() * 0.05 + 0.02,
                    avg_loss: Math.random() * 0.03 + 0.01,
                    profit_factor: Math.random() * 2 + 1
                  },
                  allocation: {
                    '大盘股': Math.random() * 40 + 20,
                    '中盘股': Math.random() * 30 + 15,
                    '小盘股': Math.random() * 20 + 10,
                    '现金': Math.random() * 15 + 5
                  }
                };
              }
            }
            
            broadcastTaskUpdate(task);
          }, 2000);
        }, 1000);

        return;
      }

      // 处理工作流提交
      if (data.type === 'workflow_submit') {
        const workflowId = `workflow_${Date.now()}`;
        const workflow = {
          id: workflowId,
          name: data.payload.name || `工作流 ${workflowId}`,
          type: data.payload.type || 'full',
          status: 'pending',
          steps: data.payload.steps || [],
          configId: data.payload.configId,
          startTime: new Date().toISOString()
        };

        workflows.set(workflowId, workflow);

        // 发送工作流ID响应
        ws.send(JSON.stringify({
          type: 'workflow_submit_response',
          payload: { workflowId },
          timestamp: Date.now(),
          id: data.id
        }));

        // 模拟工作流执行
        setTimeout(() => {
          workflow.status = 'running';
          broadcastWorkflowUpdate(workflow);

          // 为工作流中的每个步骤创建任务
          let currentStepIndex = 0;
          
          const executeNextStep = () => {
            if (currentStepIndex >= workflow.steps.length) {
              workflow.status = 'success';
              workflow.endTime = new Date().toISOString();
              broadcastWorkflowUpdate(workflow);
              return;
            }

            const step = workflow.steps[currentStepIndex];
            step.status = 'running';
            broadcastWorkflowUpdate(workflow);

            // 创建任务
            const taskId = `task_${Date.now()}_${currentStepIndex}`;
            const task = {
              id: taskId,
              name: step.name || `步骤 ${currentStepIndex + 1}`,
              type: step.type || 'train',
              status: 'running',
              progress: 0,
              startTime: new Date().toISOString(),
              workflowId: workflowId,
              stepId: currentStepIndex
            };

            tasks.set(taskId, task);
            step.taskId = taskId;
            broadcastTaskUpdate(task);

            // 模拟任务进度更新
            const progressInterval = setInterval(() => {
              task.progress += 10;
              
              if (task.progress >= 100) {
                clearInterval(progressInterval);
                task.progress = 100;
                task.status = 'success';
                task.endTime = new Date().toISOString();
                
                // 为训练任务添加模拟指标
                if (task.type === 'train') {
                  task.metrics = {
                    accuracy: Math.random() * 0.2 + 0.7,
                    precision: Math.random() * 0.2 + 0.7,
                    recall: Math.random() * 0.2 + 0.7,
                    f1_score: Math.random() * 0.2 + 0.7,
                    returns: Array.from({ length: 30 }, () => Math.random() * 10 - 2),
                    performance: {
                      IC: Math.random() * 0.5,
                      ICIR: Math.random() * 2,
                      Rank_IC: Math.random() * 0.5,
                      Rank_ICIR: Math.random() * 2
                    }
                  };
                }
                
                // 为回测任务添加模拟指标
                if (task.type === 'backtest') {
                  task.metrics = {
                    annualized_return: Math.random() * 0.3 + 0.05,
                    max_drawdown: Math.random() * 0.2 + 0.1,
                    sharpe: Math.random() * 2 + 0.5,
                    information_ratio: Math.random() * 1.5 + 0.3,
                    returns: Array.from({ length: 50 }, (_, i) => Math.sin(i / 5) * 5 + Math.random() * 2 - 1)
                  };
                }
                
                broadcastTaskUpdate(task);
                
                // 更新工作流步骤状态
                step.status = 'success';
                broadcastWorkflowUpdate(workflow);
                
                // 执行下一个步骤
                currentStepIndex++;
                setTimeout(executeNextStep, 1000);
              }
              
              broadcastTaskUpdate(task);
            }, 2000);
          };
          
          // 开始执行第一个步骤
          executeNextStep();
        }, 1000);

        return;
      }

      // 处理获取任务列表请求
      if (data.type === 'get_tasks') {
        const taskList = Array.from(tasks.values());
        ws.send(JSON.stringify({
          type: 'task_list',
          payload: taskList,
          timestamp: Date.now(),
          id: data.id
        }));
        return;
      }

      // 处理获取工作流列表请求
      if (data.type === 'get_workflows') {
        const workflowList = Array.from(workflows.values());
        ws.send(JSON.stringify({
          type: 'workflow_list',
          payload: workflowList,
          timestamp: Date.now(),
          id: data.id
        }));
        return;
      }

      // 处理获取任务详情请求
      if (data.type === 'get_task') {
        const taskId = data.payload.taskId;
        const task = tasks.get(taskId);
        
        if (task) {
          ws.send(JSON.stringify({
            type: 'task_detail',
            payload: task,
            timestamp: Date.now(),
            id: data.id
          }));
        } else {
          ws.send(JSON.stringify({
            type: 'error',
            payload: { message: `任务 ${taskId} 不存在` },
            timestamp: Date.now(),
            id: data.id
          }));
        }
        return;
      }

      // 处理获取工作流详情请求
      if (data.type === 'get_workflow') {
        const workflowId = data.payload.workflowId;
        const workflow = workflows.get(workflowId);
        
        if (workflow) {
          ws.send(JSON.stringify({
            type: 'workflow_detail',
            payload: workflow,
            timestamp: Date.now(),
            id: data.id
          }));
        } else {
          ws.send(JSON.stringify({
            type: 'error',
            payload: { message: `工作流 ${workflowId} 不存在` },
            timestamp: Date.now(),
            id: data.id
          }));
        }
        return;
      }

      // 处理未知消息类型
      ws.send(JSON.stringify({
        type: 'error',
        payload: { message: `未知消息类型: ${data.type}` },
        timestamp: Date.now(),
        id: data.id
      }));

    } catch (error) {
      console.error('处理消息错误:', error);
      ws.send(JSON.stringify({
        type: 'error',
        payload: { message: '消息格式错误' },
        timestamp: Date.now()
      }));
    }
  });

  // 处理连接关闭
  ws.on('close', () => {
    console.log('客户端已断开连接');
    clients.delete(ws);
  });

  // 处理错误
  ws.on('error', (error) => {
    console.error('WebSocket错误:', error);
    clients.delete(ws);
  });
});

// 广播任务更新
function broadcastTaskUpdate(task) {
  const message = JSON.stringify({
    type: 'task_status',
    payload: task,
    timestamp: Date.now()
  });

  clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
}

// 广播工作流更新
function broadcastWorkflowUpdate(workflow) {
  const message = JSON.stringify({
    type: 'workflow_status',
    payload: workflow,
    timestamp: Date.now()
  });

  clients.forEach(client => {
    if (client.readyState === WebSocket.OPEN) {
      client.send(message);
    }
  });
}

// 强制使用8080端口，与前端配置一致
const PORT = 8080;

// 启动服务器
server.listen(PORT, () => {
  console.log(`Qlib WebSocket服务器运行在端口 ${PORT}`);
  console.log(`HTTP服务器运行在 http://localhost:${PORT}`);
});
