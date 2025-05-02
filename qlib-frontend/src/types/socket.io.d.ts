declare module 'socket.io-client' {
  interface SocketOptions {
    forceNew?: boolean;
    multiplex?: boolean;
    transports?: string[];
    reconnection?: boolean;
    reconnectionAttempts?: number;
    reconnectionDelay?: number;
    reconnectionDelayMax?: number;
    randomizationFactor?: number;
    timeout?: number;
    autoConnect?: boolean;
    query?: Object;
    parser?: any;
  }

  interface Emitter {
    on(event: string, fn: Function): Emitter;
    once(event: string, fn: Function): Emitter;
    off(event: string, fn?: Function): Emitter;
    emit(event: string, ...args: any[]): Emitter;
    listeners(event: string): Function[];
    hasListeners(event: string): boolean;
  }

  interface Manager extends Emitter {
    reconnection(v: boolean): Manager;
    reconnectionAttempts(v: number): Manager;
    reconnectionDelay(v: number): Manager;
    reconnectionDelayMax(v: number): Manager;
    timeout(v: number): Manager;
    open(fn?: (err?: Error) => void): Manager;
    connect(fn?: (err?: Error) => void): Manager;
    socket(nsp: string, opts?: Object): Socket;
  }

  interface Socket extends Emitter {
    id: string;
    connected: boolean;
    disconnected: boolean;
    open(): Socket;
    connect(): Socket;
    send(...args: any[]): Socket;
    close(): Socket;
    disconnect(): Socket;
  }

  function io(uri: string, opts?: SocketOptions): Socket;
  namespace io {
    function connect(uri: string, opts?: SocketOptions): Socket;
    function manager(uri: string, opts?: SocketOptions): Manager;
    function socket(uri: string, opts?: SocketOptions): Socket;
  }

  export = io;
}

// 导出Socket类型供其他文件使用
export interface Socket {
  id: string;
  connected: boolean;
  disconnected: boolean;
  open(): Socket;
  connect(): Socket;
  send(...args: any[]): Socket;
  close(): Socket;
  disconnect(): Socket;
  on(event: string, fn: Function): Socket;
  once(event: string, fn: Function): Socket;
  off(event: string, fn?: Function): Socket;
  emit(event: string, ...args: any[]): Socket;
}
