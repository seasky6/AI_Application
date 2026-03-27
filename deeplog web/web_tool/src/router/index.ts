import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router';

const routes: RouteRecordRaw[] = [
    { path: '/', name: 'dashboard', component: () => import('@/views/Dashboard.vue') },

    // 1) 日志下载
    { path: '/download-logs', name: 'download-logs', component: () => import('@/views/DownloadLogs.vue') },

    // 2) NFF数据处理
    { path: '/process-logs', name: 'process-logs', component: () => import('@/views/ProcessLogs.vue') },

    // 3) PA异常预测
    { path: '/predict-samples', name: 'predict-samples', component: () => import('@/views/PredictSamples.vue') },

    // 4） 数据分析
    { path: '/data-analysis', name: 'data-analysis', component: () => import('@/views/DataAnalysis.vue') },
];

export default createRouter({
    history: createWebHistory(),
    routes
});
