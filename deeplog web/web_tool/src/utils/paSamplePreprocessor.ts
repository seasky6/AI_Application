/* eslint-disable no-console */
import * as XLSX from 'xlsx';
import type { PaSample, PaPreprocessedSampleRow } from '@/types';

/* =====================================================================================
 * 特征列表（与你的 src/types/index.d.ts 完全对应）
 * ===================================================================================== */
const NUMERIC_FEATURES: Array<keyof PaPreprocessedSampleRow> = [
    'DpaVddSv', 'PaVddSv',
    'IDpaSv:.0', 'IDpaSv:.1', 'IDpaSv:.2', 'IDpaSv:.3',
    'IMpaSv:.0', 'IMpaSv:.1', 'IMpaSv:.2', 'IMpaSv:.3',
    'LinAlarm', 'dpdNomPwr', 'dpdRestartCounter', 'powerClass', 'powerLevel',
    'rfPower', 'torGainBackoff', 'torTemp', 'txAtt', 'txDpdGainDefault',
    'txDpdPma', 'txPma', 'txPmb', 'txTorPmb'
];

const BOOL_FEATURES: Array<keyof PaPreprocessedSampleRow> = [
    'autoPeakPhaseCal',
    'delayEstimationEnable',
    'dpGainLoopEnable',
    'dpTsEnable',
    'dpdAutoStart',
    'gainAutoStart',
    'ganBoostModeEnable',
    'islastDelEstFracSuccess',
    'shpAutoStart',
    'shpGanAlgEnabled',
    'shpGanAlgFunctionStatus',
    'shpGanAlgHwCapablility',
    'torSupported'
];

const STR_FEATURES: Array<keyof PaPreprocessedSampleRow> = [
    'delayEst',
    'desc',
    'dpd',
    'gainStateMachine',
    'ganBoostModeState',
    'linearizationStateMachine',
    'runMode',
    'status',
    'statusBit',
    'subId'
];

//  Excel 列顺序
export const PREPROC_HEADER: Array<keyof PaPreprocessedSampleRow> = [
    'Serial', 'ProductName', 'Timestamp', 'SourceFile',
    ...NUMERIC_FEATURES,
    ...BOOL_FEATURES,
    ...STR_FEATURES
];

/* =====================================================================================
 * 工具函数：安全转换，保证永不返回 undefined
 * ===================================================================================== */
function toFloatOrNull(v: any): number | null {
    if (v === '' || v === null || v === undefined) return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
}

function toBoolOrNull(v: any): boolean | null {
    if (v === null || v === undefined || v === '') return null;
    if (typeof v === 'boolean') return v;
    if (typeof v === 'number') return v === 1 ? true : v === 0 ? false : null;
    if (typeof v === 'string') {
        const s = v.trim().toLowerCase();
        if (['true', 'yes', 'y', '1'].includes(s)) return true;
        if (['false', 'no', 'n', '0'].includes(s)) return false;
    }
    return null;
}

function toStrOrNull(v: any): string | null {
    if (v === null || v === undefined || v === '') return null;
    return String(v);
}

function meanOrNull(arr: (number | null)[]): number | null {
    const nums = arr.filter((n): n is number => typeof n === 'number' && Number.isFinite(n));
    return nums.length ? nums.reduce((a, b) => a + b, 0) / nums.length : null;
}

/* =====================================================================================
 * 读取 JSON
 * ===================================================================================== */
export async function readPaSamplesJsonFromHandle(handle: FileSystemFileHandle): Promise<PaSample[]> {
    const f = await handle.getFile();
    const s = await f.text();
    try {
        const json = JSON.parse(s);
        return Array.isArray(json) ? json : [];
    } catch {
        return [];
    }
}

/* =====================================================================================
 * 去重：按 Timestamp 保留第一条
 * ===================================================================================== */
export function dedupPaSamplesByTimestamp(samples: PaSample[]): PaSample[] {
    const seen = new Set<string>();
    const out: PaSample[] = [];
    for (const s of samples) {
        const ts = String(s.Timestamp || '').trim();
        if (!ts) continue;
        if (seen.has(ts)) continue;
        seen.add(ts);
        out.push(s);
    }
    return out;
}

/* =====================================================================================
 * 数值合并
 * ===================================================================================== */
function mergeVoltage(prefix: string, params: Record<string, any>): number | null {
    const arr = Array.from({ length: 8 }).map((_, i) => toFloatOrNull(params[`${prefix}:${i}`]));
    return meanOrNull(arr);
}

function mergeCurrent(prefix: string, params: Record<string, any>): Record<`.${number}`, number | null> {
    const out: any = {};
    for (const suf of ['0', '1', '2', '3']) {
        const arr = Array.from({ length: 8 }).map((_, i) =>
            toFloatOrNull(params[`${prefix}:${i}.${suf}`])
        );
        out[`.${suf}`] = meanOrNull(arr);
    }
    return out;
}

function extractOtherNumeric(params: Record<string, any>) {
    const out: any = {};
    for (const k of NUMERIC_FEATURES) {
        if (k.startsWith('IDpaSv') || k.startsWith('IMpaSv') || k.startsWith('DpaVdd') || k.startsWith('PaVdd')) continue;
        let v = params[k as string];
        if (k === 'powerClass' && typeof v === 'string') {
            const i = parseInt(v, 10);
            v = Number.isFinite(i) ? i : null;
        }
        out[k] = toFloatOrNull(v);
    }
    return out;
}

/* =====================================================================================
 * 分类特征
 * ===================================================================================== */
function extractBooleanCategorical(params: Record<string, any>) {
    const out: any = {};
    for (const k of BOOL_FEATURES) out[k] = toBoolOrNull(params[k as string]);
    return out;
}

function extractStringCategorical(params: Record<string, any>) {
    const out: any = {};
    for (const k of STR_FEATURES) out[k] = toStrOrNull(params[k as string]);
    return out;
}

/* =====================================================================================
 * 核心：预处理
 * ===================================================================================== */
export function preprocessPaSamples(samples: PaSample[]): PaPreprocessedSampleRow[] {
    const uniq = dedupPaSamplesByTimestamp(samples);
    const rows: PaPreprocessedSampleRow[] = [];

    for (const s of uniq) {
        const p = s.parameters || {};

        const voltDpa = mergeVoltage('DpaVddSv', p);
        const voltPa = mergeVoltage('PaVddSv', p);

        const curIdpa = mergeCurrent('IDpaSv', p);
        const curImpa = mergeCurrent('IMpaSv', p);

        const nums = extractOtherNumeric(p);
        const bools = extractBooleanCategorical(p);
        const strs = extractStringCategorical(p);

        const row: PaPreprocessedSampleRow = {
            Serial: s.Serial ?? '',
            ProductName: s.ProductName ?? '',
            Timestamp: s.Timestamp ?? '',
            SourceFile: s.source_file ?? '',

            DpaVddSv: voltDpa,
            PaVddSv: voltPa,

            'IDpaSv:.0': curIdpa['.0'],
            'IDpaSv:.1': curIdpa['.1'],
            'IDpaSv:.2': curIdpa['.2'],
            'IDpaSv:.3': curIdpa['.3'],

            'IMpaSv:.0': curImpa['.0'],
            'IMpaSv:.1': curImpa['.1'],
            'IMpaSv:.2': curImpa['.2'],
            'IMpaSv:.3': curImpa['.3'],

            ...nums,
            ...bools,
            ...strs
        };

        rows.push(row);
    }

    return rows;
}

/* =====================================================================================
 * 保存 JSON/XLSX
 * ===================================================================================== */
export async function savePaPreprocessedJsonToDir(
    dir: FileSystemDirectoryHandle,
    name: string,
    rows: PaPreprocessedSampleRow[]
) {
    const f = await dir.getFileHandle(name, { create: true });
    const w = await f.createWritable();
    await w.write(new Blob([JSON.stringify(rows, null, 2)], { type: 'application/json' }));
    await w.close();
    return f;
}

export async function savePaPreprocessedXlsxToDir(
    dir: FileSystemDirectoryHandle,
    name: string,
    rows: PaPreprocessedSampleRow[]
) {
    const ws = XLSX.utils.json_to_sheet(rows, { header: PREPROC_HEADER as string[] });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'samples_preprocessed');

    const buffer = XLSX.write(wb, { type: 'array', bookType: 'xlsx' });
    const fileHandle = await dir.getFileHandle(name, { create: true });
    const writer = await fileHandle.createWritable();
    await writer.write(buffer);
    await writer.close();
    return fileHandle;
}

/* =====================================================================================
 * 目录级入口（目录名 = 串号）
 * ===================================================================================== */
export function serialFromDirName(
    dirHandle: FileSystemDirectoryHandle,
    fallbackLabel?: string
): string {
    const n = (dirHandle as any)?.name ?? '';
    return String(n || fallbackLabel || '').trim();
}

export async function generatePaPreprocessedRowsFromDir(
    sampleJsonHandles: FileSystemFileHandle[],
    dirHandle: FileSystemDirectoryHandle,
    dirLabel?: string
) {
    const serial = serialFromDirName(dirHandle, dirLabel);
    if (!serial) return { serial: '', rows: [] };

    const all: PaSample[] = [];
    for (const h of sampleJsonHandles) {
        const part = await readPaSamplesJsonFromHandle(h);
        if (!Array.isArray(part)) continue;
        for (const s of part) {
            if (s.Serial === serial) all.push(s);
        }
    }
    return { serial, rows: preprocessPaSamples(all) };
}
