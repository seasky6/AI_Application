// web_tool/src/api/predict.ts
// console.log("VITE_PREDICT_API_TOKEN =", import.meta.env.VITE_PREDICT_API_TOKEN);

import type { PaPreprocessedSampleRow } from '@/types';

export interface EntryPredictionRow {
    serial: string;
    productName: string;
    timestamp: string;
    sourceFile: string;
    normalLabel: 'PA Abnormal'|'PA Normal';
    cganLabel:   'PA Abnormal'|'PA Normal';
}
export interface ProductSummary {
    serial: string;
    productName: string;
    distribution: {
        normal: { paAbnormalPct: number; normalPct: number };
        cgan:   { paAbnormalPct: number; normalPct: number };
    };
    normalModelMajority: 'PA Abnormal'|'PA Normal';
    cganModelMajority:   'PA Abnormal'|'PA Normal';
    finalDecision:       'PA Abnormal'|'May PA Abnormal'|'PA Normal';
}
export type HealthResp  = { ok: boolean; ready: boolean; models?: any; error?: string };
export type PredictResp = { ok: boolean; entries: EntryPredictionRow[]; summaries: ProductSummary[]; error?: string };

// 基础配置（支持 .env）
const API_BASE  = import.meta.env.VITE_PREDICT_API_BASE || '/mlapi';
const API_TOKEN = import.meta.env.VITE_PREDICT_API_TOKEN || '';

async function request<T>(path: string, options: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...(API_TOKEN ? { 'X-API-TOKEN': API_TOKEN } : {}),
            ...(options.headers || {})
        }
    });
    return res.json() as Promise<T>;
}

export async function apiHealth(): Promise<HealthResp> {
    return request<HealthResp>('/health', { method: 'GET' });
}

export async function apiPredict(rows: PaPreprocessedSampleRow[]): Promise<PredictResp> {
    return request<PredictResp>('/predict', { method: 'POST', body: JSON.stringify({ rows }) });
}
