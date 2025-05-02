declare module 'yaml' {
  interface ParseOptions {
    version?: string;
    schema?: any;
    customTags?: any[];
    mapAsMap?: boolean;
    keepBlobsInJSON?: boolean;
    keepCstNodes?: boolean;
    prettyErrors?: boolean;
    merge?: boolean;
    maxAliasCount?: number;
    logLevel?: string;
    lineCounter?: any;
  }

  interface DocumentOptions {
    version?: string;
    schema?: any;
    tagPrefixes?: { [prefix: string]: string };
    customTags?: any[];
    merge?: boolean;
    directives?: boolean | null;
    mapAsMap?: boolean;
  }

  interface StringifyOptions {
    anchorPrefix?: string;
    indentSeq?: boolean;
    lineWidth?: number;
    minContentWidth?: number;
    simpleKeys?: boolean;
    indent?: number;
    stringifyComment?: (comment: any) => string;
    condenseFlow?: boolean;
    doubleQuotedMinMultiLineLength?: number;
    doubleQuotedAsJSON?: boolean;
    singleQuote?: boolean;
    nullStr?: string;
    commentString?: string;
    sortMapEntries?: boolean | ((a: any, b: any) => number);
  }

  export class Document {
    constructor(value?: any, options?: DocumentOptions);
    contents: any;
    errors: Error[];
    warnings: Error[];
    toString(): string;
    setSchema(version: string | number, options?: any): void;
  }

  export function parse(src: string, options?: ParseOptions): any;
  export function parseDocument(src: string, options?: ParseOptions): Document;
  export function parseAllDocuments(src: string, options?: ParseOptions): Document[];
  export function stringify(value: any, options?: StringifyOptions): string;
  export function createNode(value: any, wrapScalars?: boolean): any;
  export function isMap(value: any): boolean;
  export function isSeq(value: any): boolean;
  export function isPair(value: any): boolean;
  export function isScalar(value: any): boolean;
}
