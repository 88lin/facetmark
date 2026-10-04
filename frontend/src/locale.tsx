import {createContext, useContext} from 'react';
export type Language = 'zh' | 'en';
export const Locale = createContext<Language>('zh');
export function useText() { const language = useContext(Locale); return (zh: string, en: string) => language === 'zh' ? zh : en; }
