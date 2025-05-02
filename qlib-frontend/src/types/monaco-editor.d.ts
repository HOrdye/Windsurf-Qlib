declare module 'monaco-editor' {
  export namespace editor {
    export interface IStandaloneCodeEditor {
      getValue(): string;
      setValue(value: string): void;
      getModel(): any;
      updateOptions(options: any): void;
      layout(dimension?: { width: number; height: number }): void;
      focus(): void;
      onDidChangeModelContent(listener: (e: IModelContentChangedEvent) => void): any;
      onDidBlurEditorText(listener: () => void): any;
      onDidFocusEditorText(listener: () => void): any;
      [key: string]: any;
    }
    
    export interface IStandaloneEditorConstructionOptions {
      value?: string;
      language?: string;
      theme?: string;
      readOnly?: boolean;
      minimap?: { enabled?: boolean };
      fontSize?: number;
      automaticLayout?: boolean;
      scrollBeyondLastLine?: boolean;
      wordWrap?: string;
      lineNumbers?: string | Function;
      glyphMargin?: boolean;
      folding?: boolean;
      renderLineHighlight?: string;
      scrollbar?: any;
      [key: string]: any;
    }
    
    export interface IModelContentChangedEvent {
      changes: any[];
      eol: string;
      versionId: number;
      isUndoing: boolean;
      isRedoing: boolean;
      [key: string]: any;
    }
    
    export interface IMarker {
      severity: number;
      message: string;
      startLineNumber: number;
      startColumn: number;
      endLineNumber: number;
      endColumn: number;
      [key: string]: any;
    }
  }
  
  export const MarkerSeverity: {
    Hint: number;
    Info: number;
    Warning: number;
    Error: number;
  };

  export const KeyMod: {
    CtrlCmd: number;
    Shift: number;
    Alt: number;
    WinCtrl: number;
  };

  export const KeyCode: {
    KEY_H: number;
    KEY_S: number;
    KEY_F: number;
    KEY_G: number;
    Enter: number;
    Escape: number;
    [key: string]: number;
  };
  
  export namespace languages {
    export const CompletionItemKind: {
      Function: number;
      Constructor: number;
      Field: number;
      Variable: number;
      Class: number;
      Struct: number;
      Interface: number;
      Module: number;
      Property: number;
      Event: number;
      Operator: number;
      Unit: number;
      Value: number;
      Constant: number;
      Enum: number;
      EnumMember: number;
      Keyword: number;
      Text: number;
      Color: number;
      File: number;
      Reference: number;
      Customcolor: number;
      Folder: number;
      TypeParameter: number;
      Snippet: number;
    };

    export function registerCompletionItemProvider(language: string, provider: any): any;
  }
  
  export function register(language: any): void;
  export function setMonarchTokensProvider(language: string, provider: any): any;
  export function registerCompletionItemProvider(language: string, provider: any): any;
  
  export class Uri {
    static parse(value: string): Uri;
    [key: string]: any;
  }
}
