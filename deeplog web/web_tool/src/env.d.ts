/// <reference types="vite/client" />

//（通常上面这一行已足够）
// 如果 IDE 仍然找不到 .vue 类型，再加下面的兜底声明：
declare module '*.vue' {
    import type { DefineComponent } from 'vue';
    const component: DefineComponent<{}, {}, any>;
    export default component;
}
