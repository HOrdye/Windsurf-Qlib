declare module 'antd/lib/locale/zh_CN' {
  import { Locale } from 'antd/lib/locale-provider';
  
  const locale: Locale;
  
  export default locale;
}

declare module 'antd/lib/locale-provider' {
  import * as React from 'react';
  
  export interface Locale {
    locale: string;
    Pagination?: object;
    DatePicker?: object;
    TimePicker?: object;
    Calendar?: object;
    Table?: object;
    Modal?: object;
    Popconfirm?: object;
    Transfer?: object;
    Select?: object;
    Upload?: object;
    Form?: object;
    Empty?: object;
    global?: object;
    PageHeader?: object;
    Icon?: object;
    Text?: object;
    PageContainer?: object;
    [key: string]: any;
  }
  
  export interface LocaleProviderProps {
    locale: Locale;
    children?: React.ReactNode;
  }
  
  export default class LocaleProvider extends React.Component<LocaleProviderProps, any> {}
}
