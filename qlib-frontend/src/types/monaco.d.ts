declare module '@monaco-editor/react' {
  import * as React from 'react';
  import * as Monaco from 'monaco-editor';
  
  export interface EditorProps {
    value?: string;
    language?: string;
    theme?: string;
    path?: string;
    defaultValue?: string;
    height?: string | number;
    width?: string | number;
    loading?: React.ReactNode;
    options?: Monaco.editor.IStandaloneEditorConstructionOptions;
    className?: string;
    wrapperClassName?: string;
    beforeMount?: (monaco: typeof Monaco) => void;
    onMount?: (
      editor: Monaco.editor.IStandaloneCodeEditor,
      monaco: typeof Monaco
    ) => void;
    onChange?: (
      value: string | undefined,
      event: Monaco.editor.IModelContentChangedEvent
    ) => void;
    onValidate?: (
      markers: Monaco.editor.IMarker[]
    ) => void;
  }
  
  export interface DiffEditorProps extends EditorProps {
    original?: string;
    modified?: string;
    originalLanguage?: string;
    modifiedLanguage?: string;
    originalPath?: string;
    modifiedPath?: string;
  }
  
  export function useMonaco(): typeof Monaco | null;
  
  export interface MonacoProps {
    width?: string | number;
    height?: string | number;
    className?: string;
    wrapperClassName?: string;
    beforeMount?: (monaco: typeof Monaco) => void;
    onMount?: (monaco: typeof Monaco) => void;
  }
  
  declare const Editor: React.FC<EditorProps>;
  declare const DiffEditor: React.FC<DiffEditorProps>;
  declare const MonacoEditor: React.FC<MonacoProps>;
  
  export { Editor, DiffEditor, MonacoEditor };
  export default Editor;
}

// 额外导出Monaco编辑器相关类型，以便在其他文件中使用
export interface MonacoType {
  editor: any;
  languages: any;
  Uri: any;
  KeyCode: any;
  KeyMod: any;
  MarkerSeverity: any;
  MarkerTag: any;
  Position: any;
  Range: any;
  Selection: any;
  SelectionDirection: any;
}

export interface EditorProps {
  value?: string;
  language?: string;
  theme?: string;
  path?: string;
  defaultValue?: string;
  height?: string | number;
  width?: string | number;
  loading?: React.ReactNode;
  options?: any;
  className?: string;
  wrapperClassName?: string;
  beforeMount?: (monaco: MonacoType) => void;
  onMount?: (editor: any, monaco: MonacoType) => void;
  onChange?: (value: string | undefined, event: any) => void;
  onValidate?: (markers: any[]) => void;
}
