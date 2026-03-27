import { createI18n } from 'vue-i18n';
import zhCN from './zh-CN.json';
import enUS from './en-US.json';

const saved = localStorage.getItem('DEEPLOG_LANG');
const locale =
    saved ||
    (navigator.language.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en-US');

export const i18n = createI18n({
    legacy: false,
    locale,
    fallbackLocale: 'en-US',
    messages: {
        'en-US': enUS,
        'zh-CN': zhCN
    }
});
