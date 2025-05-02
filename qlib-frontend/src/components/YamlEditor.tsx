import * as React from 'react';
import MonacoEditor from '@monaco-editor/react';
import * as YAML from 'yaml';
import type { editor } from 'monaco-editor';
import type { EditorProps } from '../types/monaco';

// YAML编辑器属性接口
interface YamlEditorProps {
  value: string;
  onChange: (value: string) => void;
  height?: string | number;
  readOnly?: boolean;
  /**
   * YAML校验Schema，用于动态校验
   */
  validationSchema?: any;
  /**
   * 出现错误时的回调
   */
  onError?: (error: string | null) => void;
}

/**
 * YAML编辑器组件
 * 基于Monaco Editor实现，支持语法高亮和校验
 */
const YamlEditor: React.FC<YamlEditorProps> = ({
  value,
  onChange,
  height = '500px',
  readOnly = false,
  validationSchema,
  onError
}) => {
  const editorRef = React.useRef<editor.IStandaloneCodeEditor | null>(null);
  
  // 配置Monaco编辑器
  const handleEditorDidMount = (editor: editor.IStandaloneCodeEditor, monaco: any) => {
    editorRef.current = editor;
    
    // 添加YAML语言支持
    setupYamlLanguage(monaco);
    
    // 设置自动完成提示
    setupAutocompletion(monaco);
  };
  
  // 设置YAML语言支持
  const setupYamlLanguage = (monaco: any) => {
    // 此处可以配置YAML特定的语言特性
    // 如果monaco已经支持YAML，则无需额外配置
  };
  
  // 设置自动完成提示
  const setupAutocompletion = (monaco: any) => {
    // 基本的Qlib配置关键字
    const suggestions = [
      {
        label: 'qlib_init',
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: 'qlib_init:\n  provider_uri: "${1:~/.qlib/qlib_data/cn_data}"\n  region: "${2:cn}"',
        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: 'Qlib初始化配置'
      },
      {
        label: 'market',
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: 'market: &market\n  dataset_provider: "${1:LocalProvider}"\n  dataset: "${2:csi300}"\n  start_time: "${3:2008-01-01}"\n  end_time: "${4:2020-08-01}"',
        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: '市场数据配置'
      },
      {
        label: 'task',
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: 'task:\n  model:\n    class: "${1:LGBModel}"\n    module_path: "${2:qlib.contrib.model.gbdt}"\n    kwargs:\n      ${3:}',
        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: '任务配置'
      },
      {
        label: 'dataset',
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: 'dataset:\n  class: "DatasetH"\n  module_path: "qlib.data.dataset"\n  kwargs:\n    handler:\n      class: "${1:Alpha158}"\n      module_path: "qlib.contrib.data.handler"',
        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: '数据集配置'
      },
      {
        label: 'segments',
        kind: monaco.languages.CompletionItemKind.Keyword,
        insertText: 'segments:\n  train: [${1:2008-01-01}, ${2:2014-12-31}]\n  valid: [${3:2015-01-01}, ${4:2016-12-31}]\n  test: [${5:2017-01-01}, ${6:2020-08-01}]',
        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
        documentation: '数据分段配置'
      }
    ];
    
    // 注册提供者
    monaco.languages.registerCompletionItemProvider('yaml', {
      provideCompletionItems: (model, position) => {
        const word = model.getWordUntilPosition(position);
        const range = {
          startLineNumber: position.lineNumber,
          endLineNumber: position.lineNumber,
          startColumn: word.startColumn,
          endColumn: word.endColumn
        };
        
        return {
          suggestions: suggestions.map(item => ({
            ...item,
            range
          }))
        };
      }
    });
  };
  
  // 内容变化时验证YAML格式
  React.useEffect(() => {
    if (!value) return;
    
    try {
      YAML.parse(value);
      onError && onError(null);
    } catch (e) {
      if (e instanceof Error) {
        onError && onError(e.message);
      }
    }
  }, [value, onError]);
  
  // 编辑器选项
  const editorOptions: EditorProps['options'] = {
    minimap: { enabled: true },
    fontSize: 14,
    scrollBeyondLastLine: false,
    automaticLayout: true,
    folding: true,
    readOnly,
    wordWrap: 'on',
    lineNumbers: 'on',
    glyphMargin: true,
    lineDecorationsWidth: 5,
    lineNumbersMinChars: 3,
    suggestOnTriggerCharacters: true,
    tabSize: 2
  };
  
  return (
    <div className="yaml-editor-container">
      <MonacoEditor
        height={height}
        language="yaml"
        theme="vs-light"
        value={value}
        onChange={(value) => onChange(value || '')}
        onMount={handleEditorDidMount}
        options={editorOptions}
      />
    </div>
  );
};

export default YamlEditor;
