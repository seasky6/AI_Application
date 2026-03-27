/* eslint-disable no-console */
import * as XLSX from 'xlsx';
import type { LogEntry, PaSample } from '@/types';


/** ========== 工具：保存 Samples ========== */
export async function saveSamplesJsonToDir(
    dir: FileSystemDirectoryHandle,
    name: string,
    samples: PaSample[]
) {
    const fh = await dir.getFileHandle(name, { create: true });
    const writer = await fh.createWritable();
    await writer.write(new Blob([JSON.stringify(samples, null, 2)], { type: 'application/json' }));
    await writer.close();
    return fh as FileSystemFileHandle;
}


/** 将 parameters 的所有键合并为表头、展开为多列写入 Excel */
export async function saveSamplesXlsxToDir(
    dir: FileSystemDirectoryHandle,
    name: string,
    samples: PaSample[]
) {
    // 1) 收集所有参数键（全量并集），保证列覆盖所有样本的 parameters
    const paramKeysSet = new Set<string>();
    for (const s of samples) {
        const p = s.parameters || {};
        Object.keys(p).forEach(k => {
            if (k) paramKeysSet.add(k);
        });
    }
    const paramKeys = Array.from(paramKeysSet);

    // 2) 构造表头（基础字段 + 参数键）
    const baseHeaders = ['Serial', 'ProductName', 'Timestamp', 'SourceFile'];
    const header = [...baseHeaders, ...paramKeys];

    // 3) 组装行：把 parameters 按表头逐列展开
    const rows = samples.map(s => {
        const base = {
            Serial: s.Serial ?? '',
            ProductName: s.ProductName ?? '',
            Timestamp: s.Timestamp ?? '',
            SourceFile: s.source_file ?? ''
        } as Record<string, any>;

        const p = s.parameters || {};
        for (const key of paramKeys) {
            const v = p[key];
            // 规范化值：数值/布尔直接放，数组/对象转 JSON 字符串，null/undefined 用空串
            if (v === null || v === undefined) {
                base[key] = '';
            } else if (Array.isArray(v) || (typeof v === 'object')) {
                base[key] = JSON.stringify(v);
            } else {
                base[key] = v;
            }
        }
        return base;
    });

    // 4) 生成工作簿
    const ws = XLSX.utils.json_to_sheet(rows, { header });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'samples');

    // 5) 写入到目录
    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const fh = await dir.getFileHandle(name, { create: true });
    const writer = await fh.createWritable();
    await writer.write(new Blob([wbout], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    }));
    await writer.close();
    return fh as FileSystemFileHandle;
}


/** ========== 只生成目标串号 ========== */
type StrMapList<T> = Map<string, T[]>;

const TARGET_LOG_IDS = new Set(['10', '16', '27', '52']);
const EXCLUDED_KEYS = new Set(['Case', 'Event ID', 'Carrier Info', 'Invalid command']);
const MIN_WINDOW_SEC = 5;

/** ========== 解析时间戳 'YYYY-MM-DD HH:MM:SS' → Date，失败返回最小时间 ========== */
function parseTs(ts: string | undefined): Date {
    try {
        if (!ts) return new Date(0);
        return new Date(ts.replace(' ', 'T') + 'Z'); // 与前面生成的时间戳格式对齐
    } catch {
        return new Date(0);
    }
}

function addParam(sample: PaSample, entry: LogEntry) {
    const key = entry.Key || '';
    const value = entry.Value as any;
    if (key && (value !== undefined && value !== null)) {
        sample.parameters[key] = value;
    }
}

/** ========== 将 entries（仅目标串号）按时间升序排列 ========== */
function sortByTimestamp(entries: LogEntry[]) {
    return [...entries].sort((a, b) => +parseTs(a.Timestamp) - +parseTs(b.Timestamp));
}

/** ========== 将已排序 entries 用 5 秒窗口切分  */
function groupByTimeWindow(sortedEntries: LogEntry[]) {
    if (!sortedEntries.length) return [] as LogEntry[][];
    const windows: LogEntry[][] = [];
    let current: LogEntry[] = [];
    let base = parseTs(sortedEntries[0].Timestamp);

    for (const e of sortedEntries) {
        const t = parseTs(e.Timestamp);
        const diff = (t.getTime() - base.getTime()) / 1000;
        if (diff <= MIN_WINDOW_SEC) {
            current.push(e);
        } else {
            if (current.length) windows.push(current);
            current = [e];
            base = t;
        }
    }
    if (current.length) windows.push(current);
    return windows;
}

/** ========== 同一时间戳合并为一组 ========== */
function groupByTimestamp(entries: LogEntry[]): StrMapList<LogEntry> {
    const m = new Map<string, LogEntry[]>();
    for (const e of entries) {
        const ts = e.Timestamp || '';
        if (!m.has(ts)) m.set(ts, []);
        m.get(ts)!.push(e);
    }
    return m;
}

/** ========== 在一个窗口内：配对 log10 与 其后 0..5 秒内的 log27（可能多组） ========== */
function pairLog10AndLog27(
    serial: string,
    log10Groups: StrMapList<LogEntry>,
    log27Groups: StrMapList<LogEntry>,
    sourceFile: string
): PaSample[] {
    const samples: PaSample[] = [];
    const log10Ts = Array.from(log10Groups.keys()).sort();
    const log27Ts = Array.from(log27Groups.keys()).sort();

    if (!log10Ts.length || !log27Ts.length) return samples;

    for (const ts10 of log10Ts) {
        const t10 = parseTs(ts10);
        const matched27: LogEntry[][] = [];
        for (const ts27 of log27Ts) {
            const t27 = parseTs(ts27);
            const diff = (t27.getTime() - t10.getTime()) / 1000;
            if (diff >= 0 && diff <= MIN_WINDOW_SEC) {
                matched27.push(log27Groups.get(ts27)!);
            } else if (diff > MIN_WINDOW_SEC) {
                break;
            }
        }
        if (matched27.length) {
            // 以该 log10 时间戳生成一个样本，合并后续 0..5 秒内所有 log27 组
            const log10s = log10Groups.get(ts10)!;
            const productName = log10s[0]?.ProductName || '';
            const sample: PaSample = {
                Serial: serial,
                ProductName: productName,
                Timestamp: ts10,
                parameters: {},
                source_file: sourceFile,
            };
            // 添加 log10 参数
            for (const e of log10s) addParam(sample, e);

            // 添加所有匹配 log27 参数
            for (const group of matched27) {
                for (const e of group) addParam(sample, e);
            }
            // 先挂一个临时字段，窗口结束后再统一计算 LinAlarm
            // @ts-ignore
            sample.temp_lin_alarm = 0;
            samples.push(sample);
        }
    }
    return samples;
}

/** ========== 对窗口样本分配 LinAlarm（log16 unique timestamps + log52 'state'=='ON' count） ========== */
function assignLinAlarmToWindowSamples(windowEntries: LogEntry[], samples: PaSample[]) {
    const log16Ts = new Set<string>();
    let log52On = 0;

    for (const e of windowEntries) {
        const id = String(e.LogID || '');
        if (id === '16') {
            const sl = e.Slogan || '';
            if (sl.startsWith('Lin. fault port') || sl.startsWith('Lin fault port')) {
                if (e.Timestamp) log16Ts.add(e.Timestamp);
            }
        } else if (id === '52') {
            if (e.Key === 'state' && e.Value === 'ON') log52On += 1;
        }
    }

    const linAlarm = log16Ts.size + log52On;
    for (const s of samples) {
        // @ts-ignore
        s.temp_lin_alarm = (s.temp_lin_alarm || 0) + linAlarm;
    }
}

/** ========== 最终：从同一目录的多个 *_parsed.json 中生成目标串号（serial）样本 ========== */
export async function generatePaIssueSamplesFromDir(
    parsedJsonHandles: FileSystemFileHandle[],
    dirHandle: FileSystemDirectoryHandle,
    dirLabel?: string
): Promise<{ serial: string; samples: PaSample[] }> {
    const serial = serialFromDir(dirHandle, dirLabel);
    if (!serial) return { serial: '', samples: [] };

    // 读取所有 parsed.json，并只保留该串号 & 目标 ID & 过滤键
    const valid: Array<{ fileName: string; entries: LogEntry[] }> = [];
    for (const h of parsedJsonHandles) {
        try {
            const f = await h.getFile();
            const name = f.name;
            const data = JSON.parse(await f.text()) as LogEntry[];

            const filtered = data.filter(e => {
                if (e.Serial !== serial) return false;      // ✅ 仅该目录对应串号
                if (e.LogType !== 'elog') return false;
                const id = String(e.LogID || '');
                const key = String(e.Key || '');
                return TARGET_LOG_IDS.has(id) && !EXCLUDED_KEYS.has(key);
            });

            if (filtered.length) valid.push({ fileName: name, entries: filtered });
        } catch (e) {
            console.warn('[samples] 跳过解析文件（读取失败）：', e);
        }
    }

    if (!valid.length) return { serial, samples: [] };

    // 按“窗口→配对→分配 LinAlarm”生成样本（与之前完全一致）
    const allSamples: PaSample[] = [];
    const perSampleTempLinAlarm: number[] = [];

    for (const { fileName, entries } of valid) {
        const sorted = sortByTimestamp(entries);
        const windows = groupByTimeWindow(sorted);

        for (const w of windows) {
            const log10 = groupByTimestamp(w.filter(e => String(e.LogID || '') === '10'));
            const log27 = groupByTimestamp(w.filter(e => String(e.LogID || '') === '27'));

            const samples = pairLog10AndLog27(serial, log10, log27, fileName);
            if (!samples.length) continue;

            assignLinAlarmToWindowSamples(w, samples);

            for (const s of samples) {
                // @ts-ignore
                perSampleTempLinAlarm.push(s.temp_lin_alarm || 0);
                allSamples.push(s);
            }
        }
    }

    // 将 LinAlarm 汇总为该串号的总和，写入每个样本
    const totalLinAlarm = perSampleTempLinAlarm.reduce((a, b) => a + b, 0);
    for (const s of allSamples) {
        // @ts-ignore
        delete s.temp_lin_alarm;
        s.parameters['LinAlarm'] = String(totalLinAlarm);
    }

    return { serial, samples: allSamples };
}

/** ========== 直接从解析文件所在目录获取串号（folder 名即为串号） ========== */
export function serialFromDir(
    dirHandle: FileSystemDirectoryHandle,
    fallbackLabel?: string
): string {
    // File System Access API 的目录句柄有 name 属性
    const n = (dirHandle as any)?.name ?? '';
    return String(n || fallbackLabel || '').trim();
}
