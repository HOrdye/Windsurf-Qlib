const WebSocket = require('ws');
const http = require('http');
const url = require('url');
const { v4: uuidv4 } = require('uuid');
const net = require('net'); // 用于检查端口占用

// 配置
const config = {
  defaultPort: 8080,
  maxPortRetries: 10,  // 最大端口重试次数
  portRetryIncrement: 1, // 端口重试增量
  taskUpdateInterval: 2000, // 任务更新间隔（毫秒）
};

// 检查端口是否可用
function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    
    server.once('error', (err) => {
      if (err.code === 'EADDRINUSE') {
        // 端口被占用
        resolve(false);
      } else {
        // 其他错误，假设端口可用
        resolve(true);
      }
    });
    
    server.once('listening', () => {
      // 端口可用，关闭服务器
      server.close();
      resolve(true);
    });
    
    server.listen(port);
  });
}

// 查找可用端口
async function findAvailablePort(startPort, maxRetries, increment) {
  let port = startPort;
  let retries = 0;
  
  while (retries < maxRetries) {
    const available = await isPortAvailable(port);
    if (available) {
      return port;
    }
    
    port += increment;
    retries++;
    
    console.log(`端口 ${port - increment} 已被占用，尝试端口 ${port}`);
  }
  
  throw new Error(`无法找到可用端口，已尝试 ${maxRetries} 次`);
}

// 启动服务器
async function startServer() {
  try {
    // 查找可用端口
    const port = await findAvailablePort(
      config.defaultPort, 
      config.maxPortRetries, 
      config.portRetryIncrement
    );
    
    // 创建HTTP服务器
    const server = http.createServer((req, res) => {
      res.writeHead(200, { 'Content-Type': 'text/plain' });
      res.end('Qlib WebSocket Server');
    });
    
    // 创建WebSocket服务器
    const wss = new WebSocket.Server({ server });
    
    // 存储所有连接的客户端
    const clients = new Set();
    
    // 存储模拟任务
    const tasks = new Map();
    
    // 生成唯一ID
    function generateId() {
      return `${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
    }

    // 发送消息给所有客户端
    function broadcast(message) {
      clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
          client.send(JSON.stringify(message));
        }
      });
    }

    // 发送消息给特定客户端
    function sendTo(client, message) {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify(message));
      }
    }

    // 模拟任务进度更新
    function simulateTaskProgress(taskId) {
      const task = tasks.get(taskId);
      if (!task || task.status !== 'running') return;

      // 增加进度
      task.progress += Math.random() * 10;
      
      // 如果进度达到100%，完成任务
      if (task.progress >= 100) {
        task.progress = 100;
        task.status = 'completed';
        task.endTime = Date.now();
        
        // 广播任务状态更新
        broadcast({
          type: 'task_status',
          payload: { ...task },
          timestamp: Date.now()
        });
        
        // 发送任务结果
        broadcast({
          type: 'task_result',
          payload: {
            taskId,
            result: {
              metrics: {
                accuracy: Math.random().toFixed(4),
                precision: Math.random().toFixed(4),
                recall: Math.random().toFixed(4),
                f1: Math.random().toFixed(4)
              },
              summary: '任务执行成功'
            }
          },
          timestamp: Date.now()
        });
        
        return;
      }
      
      // 广播任务进度更新
      broadcast({
        type: 'task_progress',
        payload: {
          taskId,
          progress: task.progress
        },
        timestamp: Date.now()
      });
      
      // 添加任务日志
      const logMessage = {
        type: 'task_log',
        payload: {
          taskId,
          timestamp: Date.now(),
          level: 'info',
          message: `任务进度: ${Math.round(task.progress)}%`
        }
      };
      broadcast(logMessage);
      
      // 继续模拟进度更新
      setTimeout(() => simulateTaskProgress(taskId), config.taskUpdateInterval);
    }

    // 处理客户端连接
    wss.on('connection', (ws, req) => {
      // 添加客户端到集合
      clients.add(ws);
      console.log(`客户端连接: ${clients.size} 个连接`);
      
      // 处理心跳消息
      const heartbeatInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.ping();
        }
      }, 30000);
      
      // 处理消息
      ws.on('message', (message) => {
        try {
          const data = JSON.parse(message);
          console.log('收到消息:', data);
          
          // 处理心跳消息
          if (data.type === 'heartbeat') {
            sendTo(ws, {
              type: 'heartbeat',
              payload: { timestamp: Date.now() },
              timestamp: Date.now(),
              id: data.id
            });
            return;
          }
          
          // 处理任务状态请求
          if (data.type === 'task_status') {
            // 列出所有任务
            if (data.payload.action === 'list') {
              const taskList = Array.from(tasks.values());
              sendTo(ws, {
                type: 'task_status',
                payload: taskList,
                timestamp: Date.now(),
                id: data.id
              });
            }
            // 提交新任务
            else if (data.payload.action === 'submit') {
              const taskConfig = data.payload.task;
              const taskId = taskConfig.taskId || generateId();
              
              console.log(`收到任务提交请求:`, {
                taskId,
                type: taskConfig.type,
                name: taskConfig.name
              });
              
              // 创建新任务
              const task = {
                taskId,
                status: 'running',
                progress: 0,
                startTime: Date.now(),
                type: taskConfig.type,
                name: taskConfig.name || `任务 ${taskId.substring(0, 8)}`,
                description: taskConfig.description
              };
              
              // 保存任务
              tasks.set(taskId, task);
              
              // 发送响应
              sendTo(ws, {
                type: 'task_status',
                payload: { success: true, taskId },
                timestamp: Date.now(),
                id: data.id
              });
              
              // 广播任务状态
              broadcast({
                type: 'task_status',
                payload: task,
                timestamp: Date.now()
              });
              
              // 模拟任务进度
              setTimeout(() => simulateTaskProgress(taskId), 1000);
            }
            // 取消任务
            else if (data.payload.action === 'cancel') {
              const taskId = data.payload.taskId;
              const task = tasks.get(taskId);
              
              if (task && task.status === 'running') {
                task.status = 'failed';
                task.message = '任务已取消';
                task.endTime = Date.now();
                
                // 发送响应
                sendTo(ws, {
                  type: 'task_status',
                  payload: { success: true },
                  timestamp: Date.now(),
                  id: data.id
                });
                
                // 广播任务状态
                broadcast({
                  type: 'task_status',
                  payload: task,
                  timestamp: Date.now()
                });
              } else {
                // 发送响应
                sendTo(ws, {
                  type: 'task_status',
                  payload: { success: false, error: '任务不存在或已完成' },
                  timestamp: Date.now(),
                  id: data.id
                });
              }
            }
          }
        } catch (error) {
          console.error('处理消息出错:', error);
        }
      });
      
      // 处理关闭连接
      ws.on('close', () => {
        clients.delete(ws);
        clearInterval(heartbeatInterval);
        console.log(`客户端断开连接: ${clients.size} 个连接`);
      });
      
      // 处理错误
      ws.on('error', (error) => {
        console.error('WebSocket错误:', error);
        clients.delete(ws);
        clearInterval(heartbeatInterval);
      });
      
      // 发送系统通知
      sendTo(ws, {
        type: 'system_notification',
        payload: {
          message: '已连接到Qlib WebSocket服务器',
          level: 'info'
        },
        timestamp: Date.now()
      });
    });

    // 启动服务器
    server.listen(port, () => {
      console.log(`Qlib WebSocket服务器运行在 http://localhost:${port}`);
      console.log(`WebSocket端点: ws://localhost:${port}/ws`);
    });

    // 错误处理
    server.on('error', (error) => {
      console.error('服务器错误:', error);
    });
    
  } catch (error) {
    console.error('启动服务器失败:', error);
    process.exit(1);
  }
}

// 启动服务器
startServer();
