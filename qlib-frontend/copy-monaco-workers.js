/**
 * 复制 Monaco Editor 的 worker 文件到公共目录
 * 这样我们就可以本地加载它们而不是依赖 CDN
 */
const fs = require('fs');
const path = require('path');

// 源目录和目标目录
const esmDir = path.join(__dirname, 'node_modules', 'monaco-editor', 'esm', 'vs');
const targetDir = path.join(__dirname, 'public', 'monaco-editor-workers');

// 要复制的 worker 文件
const workerFiles = [
  {
    source: path.join(esmDir, 'editor', 'editor.worker.js'),
    target: 'editor.worker.js'
  },
  {
    source: path.join(esmDir, 'language', 'json', 'json.worker.js'),
    target: 'json.worker.js'
  },
  {
    source: path.join(esmDir, 'language', 'css', 'css.worker.js'),
    target: 'css.worker.js'
  },
  {
    source: path.join(esmDir, 'language', 'html', 'html.worker.js'),
    target: 'html.worker.js'
  },
  {
    source: path.join(esmDir, 'language', 'typescript', 'ts.worker.js'),
    target: 'ts.worker.js'
  }
];

// 确保目标目录存在
if (!fs.existsSync(targetDir)) {
  fs.mkdirSync(targetDir, { recursive: true });
  console.log(`创建目录: ${targetDir}`);
}

// 复制文件
let copyCount = 0;
workerFiles.forEach(file => {
  if (fs.existsSync(file.source)) {
    const targetFile = path.join(targetDir, file.target);
    
    try {
      fs.copyFileSync(file.source, targetFile);
      console.log(`复制成功: ${file.target}`);
      copyCount++;
    } catch (error) {
      console.error(`复制失败 ${file.target}: ${error.message}`);
    }
  } else {
    console.warn(`源文件不存在: ${file.source}`);
  }
});

// 如果没有找到任何文件，尝试直接创建简单的 worker 文件
if (copyCount === 0) {
  console.log('未找到任何 worker 文件，创建简单的替代文件');
  
  // 创建简单的 editor worker 文件
  const editorWorkerContent = `
// 简单的 editor worker 替代方案
self.onmessage = function(e) {
  console.log('Editor Worker 收到消息:', e.data);
  self.postMessage({
    id: e.data.id,
    result: {}
  });
};
`;

  const editorWorkerPath = path.join(targetDir, 'editor.worker.js');
  try {
    fs.writeFileSync(editorWorkerPath, editorWorkerContent);
    console.log('创建 editor worker 文件成功');
  } catch (error) {
    console.error(`创建 editor worker 文件失败: ${error.message}`);
  }
}

// 创建自定义 YAML worker 文件
const yamlWorkerContent = `
// 简单的 YAML worker 替代方案
self.onmessage = function(e) {
  console.log('YAML Worker 收到消息:', e.data);
  
  // 简单地回复一个空的诊断数组
  self.postMessage({
    id: e.data.id,
    diagnostics: []
  });
};
`;

const yamlWorkerPath = path.join(targetDir, 'yaml.worker.js');
try {
  fs.writeFileSync(yamlWorkerPath, yamlWorkerContent);
  console.log('创建 YAML worker 文件成功');
} catch (error) {
  console.error(`创建 YAML worker 文件失败: ${error.message}`);
}

console.log('Monaco Editor worker 文件处理完成');
