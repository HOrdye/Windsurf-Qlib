
// 简单的 YAML worker 替代方案
self.onmessage = function(e) {
  console.log('YAML Worker 收到消息:', e.data);
  
  // 简单地回复一个空的诊断数组
  self.postMessage({
    id: e.data.id,
    diagnostics: []
  });
};
