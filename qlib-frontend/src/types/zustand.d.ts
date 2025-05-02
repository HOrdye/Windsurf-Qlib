declare module 'zustand' {
  export type StateCreator<T, CustomSetState = SetState<T>, CustomGetState = GetState<T>, CustomStoreApi = StoreApi<T>> =
    (set: CustomSetState, get: CustomGetState, api: CustomStoreApi) => T;

  export type GetState<T> = () => T;
  export type SetState<T> = (partial: T | Partial<T> | ((state: T) => T | Partial<T>), replace?: boolean) => void;
  export type Subscribe<T> = (listener: (state: T, prevState: T) => void) => () => void;
  export type Destroy = () => void;

  export interface StoreApi<T> {
    getState: GetState<T>;
    setState: SetState<T>;
    subscribe: Subscribe<T>;
    destroy: Destroy;
  }

  export type UseBoundStore<T> = T extends object
    ? (<U>(selector: (state: T) => U, equals?: (a: U, b: U) => boolean) => U) & (() => T) & StoreApi<T>
    : never;

  export function create<T>(createState: StateCreator<T>): UseBoundStore<T>;
  export function createStore<T>(createState: StateCreator<T>): StoreApi<T>;
}

declare module 'zustand/middleware' {
  import { StateCreator, StoreApi } from 'zustand';

  export type NamedSet<T> = {
    <K extends string, V extends T[Extract<keyof T, string>]>(
      key: K,
      value: V,
      replace?: boolean,
      name?: string,
    ): void;
    <T>(partial: T | Partial<T>, replace?: boolean, name?: string): void;
  };

  export type DevtoolsOptions = {
    name?: string;
    enabled?: boolean;
    anonymousActionType?: string;
  };

  export function devtools<T>(
    initializer: StateCreator<T>,
    options?: DevtoolsOptions,
  ): StateCreator<T>;

  export function persist<T>(
    initializer: StateCreator<T>,
    options?: {
      name?: string;
      getStorage?: () => Storage;
      serialize?: (state: T) => string;
      deserialize?: (str: string) => T;
      blacklist?: (keyof T)[];
      whitelist?: (keyof T)[];
      onRehydrateStorage?: (state: T) => ((state: T) => void) | void;
      version?: number;
      migrate?: (persistedState: any, version: number) => T;
      merge?: (persistedState: any, currentState: T) => T;
    },
  ): StateCreator<T>;

  export function immer<T>(initializer: StateCreator<T>): StateCreator<T>;
}
