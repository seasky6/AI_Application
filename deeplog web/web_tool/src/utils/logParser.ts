/* eslint-disable no-console */
import type { ExtractedEntry, LogEntry } from '@/types';

/** ===================== Log Patterns ===================== */
const Patterns = {
    elog: /\[(\d{6})\s(\d{6})]\s+(\d+):\s(.+)/,
    elog10_abn: /(\w+)=([^,]+)/g,
    elog10_case: /Case:(\d+)(?:\s+Event\s+ID:(\d+))?/,
    elog16: /^(.*?)\s*;\s*(\w+):([^;]+);\s*(\w+):([^;]+);\s*(\w+):([^;]+)$/,
    elog27: /PA measured values for driver name:\s*([^;]+);\s*value:\s*(\d+);\s*branch Id:\s*(\d)/,
    elog42: /Temperature:\s*(.+)/,
    elog43: /PA current:\s*(.+)/,
    elog52: /^([^:]+):\s*([^;]+);\s*(\w+):\s*(\d+)$/,
    hwlog: /(\d+)\s+(\d+)\s+(\d{2}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})\s+(.+)/,
    pareadall: /^(Invalid command):\s*(.+)$/,
    trx_branch: /branch\s*(\d+)/i,
    trx_date: /Date:\s*(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})/,
    trx_section: /^(Header|HW|Calibration info|Supervision|Diagnostic|DPD|Board)$/i,
};

/** ===================== Timestamp yymmdd+HHMMSS -> YYYY-MM-DD HH:MM:SS ===================== */
function parseTimestamp(date6: string, time6: string): string {
    const y = parseInt(date6.slice(0, 2), 10);
    const year = y >= 70 ? 1900 + y : 2000 + y; // 与 pandas 接近
    const date = `${year}-${date6.slice(2,4)}-${date6.slice(4,6)}`;
    const time = `${time6.slice(0,2)}:${time6.slice(2,4)}:${time6.slice(4,6)}`;
    return `${date} ${time}`;
}

const MIN_VALID = new Date('2022-01-01T00:00:00Z');

/** ===================== Base Parser ===================== */
class Base {
    logEntries: LogEntry[] = [];
    logIndex = 0;
    patterns = Patterns;

    add(e: Omit<LogEntry, 'Index'|'ParentIndex'> & { ParentIndex?: number }) {
        this.logIndex += 1;
        this.logEntries.push({
            Index: this.logIndex,
            ParentIndex: e.ParentIndex ?? this.logIndex,
            ...e,
        });
    }
}

/** ===================== CS/VS/TS Read Parser ===================== */
function parseRead(base: Base, serial: string, product: string, logType: string, entry: string) {
    const line = entry.trim();
    const parts = line.split(':');
    if (parts.length < 2) return;
    const key = parts.slice(0, parts.length - 1).join(':').trim();
    const rawVal = parts[parts.length - 1].trim();

    const sp = rawVal.split(/\s+/);
    const numeric = sp.length > 1 ? sp.slice(0, sp.length - 1).join(' ') : rawVal;

    let value: any = numeric, valueType: LogEntry['ValueType'] = 'string';
    if (/^[+-]?\d+$/.test(numeric)) { value = parseInt(numeric, 10); valueType = 'int'; }
    else if (/^[+-]?\d+\.\d+$/.test(numeric)) { value = parseFloat(numeric); valueType = 'float'; }

    base.add({
        Serial: serial, ProductName: product, LogType: logType,
        Timestamp: '', LogID: '', Content: line, Slogan: '',
        Key: key, Value: value, ValueType: valueType, IsMeasuredValue: true,
    });
}

/** ===================== hwlog Parser ===================== */
function parseHwlog(base: Base, serial: string, product: string, logType: string, entry: string) {
    const line = entry.trim();
    if (!line || (/^no/i.test(line) && line.includes('logid') && line.includes('time'))) return;
    if (/^[\s-]+$/.test(line)) return;

    const m = base.patterns.hwlog.exec(line);
    const parent = base.logIndex + 1;
    if (m) {
        const [, no, hwid, d, t, msg] = m;
        const date = d.replace(/-/g, '');
        const time = t.replace(/:/g, '');
        const ts = parseTimestamp(date, time);
        base.add({
            Serial: serial, ProductName: product, LogType: logType,
            Timestamp: ts, LogID: hwid, Content: '',
            Slogan: `no ${no}`, Key: 'msg', Value: msg, ValueType: 'string', IsMeasuredValue: false,
            ParentIndex: parent,
        });
    }
}

/** ===================== elog Parsers ===================== */
function parseElog10SimpleKV(base: Base, serial: string, product: string, timestamp: string, parentIndex: number, line: string) {
    // 没有标准前缀的 elog10 行：键值对或 Carrier Info
    const raw = line.startsWith('####') ? line.slice(4).trim() : line;
    if (!raw.includes(':')) {
        base.add({
            Serial: serial, ProductName: product, LogType: 'elog',
            Timestamp: timestamp, LogID: '10', Content: raw,
            Slogan: 'Event trace', Key: 'Carrier Info', Value: raw, ValueType: 'string', IsMeasuredValue: false,
            ParentIndex: parentIndex,
        });
        return;
    }
    const [k, v0] = raw.split(':', 1 + 1);
    const v = (v0 ?? '').trim();

    // 智能数值：True/False, 40W, 47.23 dBm[53W], 579 [0.1C]
    let value: any = v, vt: LogEntry['ValueType'] = 'string';
    const s = v.toLowerCase().trim();
    if (s === 'true' || s === 'false') { value = s === 'true'; vt = 'bool'; }
    else {
        const unitRules: Array<[RegExp, 'int'|'float', number?]> = [
            [/^(\d+)W$/, 'int', undefined],
            [/^([\d.]+)\s*dBm/, 'float', undefined],
            [/^(\d+)\s*\[/, 'float', 0.1],
            [/^([\d.]+)\s*\[/, 'float', 0.1],
        ];
        let matched = false;
        for (const [re, ty, factor] of unitRules) {
            const m = re.exec(v);
            if (m) {
                value = ty === 'int' ? parseInt(m[1], 10) : parseFloat(m[1]);
                if (factor != null) value = Math.round(value * factor * 10) / 10;
                vt = ty === 'int' ? 'int' : 'float';
                matched = true; break;
            }
        }
        if (!matched) {
            if (/^[+-]?\d+$/.test(v)) { value = parseInt(v, 10); vt = 'int'; }
            else if (/^[+-]?\d+\.\d+$/.test(v)) { value = parseFloat(v); vt = 'float'; }
        }
    }

    base.add({
        Serial: serial, ProductName: product, LogType: 'elog',
        Timestamp: timestamp, LogID: '10', Content: raw,
        Slogan: 'Event trace', Key: k.trim(), Value: value, ValueType: vt, IsMeasuredValue: vt !== 'string',
        ParentIndex: parentIndex,
    });
}

function parseElog10(base: Base, serial: string, product: string, ts: string, parent: number, line: string) {
    // ABN
    if (line.includes('ABN:')) {
        const [sloganRaw, content] = line.split(':', 1 + 1);
        const slogan = sloganRaw.trim();
        const tail = (content ?? '').trim();
        const parts = tail.split(' ', 3);
        const abn = parts[1] ? parts[1].slice(0, -1) : '';
        base.add({
            Serial: serial, ProductName: product, LogType: 'elog',
            Timestamp: ts, LogID: '10', Content: line, Slogan: slogan,
            Key: 'ABN', Value: abn, ValueType: 'string', IsMeasuredValue: false, ParentIndex: parent,
        });
        if (parts[2]) {
            let m: RegExpExecArray | null;
            const re = Patterns.elog10_abn;
            re.lastIndex = 0;
            while ((m = re.exec(parts[2])) != null) {
                base.add({
                    Serial: serial, ProductName: product, LogType: 'elog',
                    Timestamp: ts, LogID: '10', Content: line, Slogan: slogan,
                    Key: m[1].trim(), Value: m[2].trim(), ValueType: 'string', IsMeasuredValue: false, ParentIndex: parent,
                });
            }
        }
        return;
    }

    // Case
    const caseM = Patterns.elog10_case.exec(line);
    if (caseM) {
        const slogan = line.split(':', 1)[0].trim();
        base.add({
            Serial: serial, ProductName: product, LogType: 'elog',
            Timestamp: ts, LogID: '10', Content: line, Slogan: slogan,
            Key: 'Case', Value: caseM[1], ValueType: 'string', IsMeasuredValue: false, ParentIndex: parent,
        });
        if (caseM[2]) {
            base.add({
                Serial: serial, ProductName: product, LogType: 'elog',
                Timestamp: ts, LogID: '10', Content: line, Slogan: slogan,
                Key: 'Event ID', Value: caseM[2], ValueType: 'string', IsMeasuredValue: false, ParentIndex: parent,
            });
        }
        return;
    }

    // 空内容
    if (/^\s*$/.test(line)) {
        base.add({
            Serial: serial, ProductName: product, LogType: 'elog',
            Timestamp: ts, LogID: '10', Content: line, Slogan: '',
            Key: '', Value: '', ValueType: '', IsMeasuredValue: false, ParentIndex: parent,
        });
        return;
    }

    // 其余：KV 线路/Carrier Info
    parseElog10SimpleKV(base, serial, product, ts, parent, line);
}

function parseElog16(base: Base, serial: string, product: string, ts: string, parent: number, line: string) {
    const m = Patterns.elog16.exec(line);
    if (!m) return;
    const [ , slogan, k1, v1, k2, v2, k3, v3 ] = m;
    const add = (k: string, v: string) =>
        base.add({ Serial: serial, ProductName: product, LogType: 'elog', Timestamp: ts, LogID: '16',
            Content: line, Slogan: slogan, Key: k, Value: String(v), ValueType: 'str', IsMeasuredValue: false, ParentIndex: parent });
    add(k1, v1); add(k2, v2); add(k3, v3);
}

function parseElog27(base: Base, serial: string, product: string, ts: string, parent: number, line: string) {
    const m = Patterns.elog27.exec(line);
    if (!m) return;
    const [ , driver, value ] = m;
    base.add({
        Serial: serial, ProductName: product, LogType: 'elog',
        Timestamp: ts, LogID: '27', Content: line, Slogan: 'PA measured values for',
        Key: driver, Value: parseInt(value, 10), ValueType: 'int', IsMeasuredValue: true, ParentIndex: parent,
    });
}

function parseElog42or43(base: Base, serial: string, product: string, ts: string, parent: number, line: string, logId: '42'|'43') {
    const re = logId === '42' ? Patterns.elog42 : Patterns.elog43;
    const m = re.exec(line); if (!m) return;
    const data = m[1];
    const pairs = data.split(',').map(s => s.trim()).filter(Boolean);
    const slogan = logId === '42' ? 'Temperature' : 'PA current';
    for (const p of pairs) {
        const sp = p.split(/\s+/);
        if (sp.length < 2) continue;
        const key = sp[0];
        const vals = sp.slice(1).join(' ');
        if (vals === 'count_0') {
            base.add({ Serial: serial, ProductName: product, LogType: 'elog',
                Timestamp: ts, LogID: logId, Content: line, Slogan: slogan,
                Key: key, Value: 'count_0', ValueType: 'str', IsMeasuredValue: false, ParentIndex: parent });
        } else {
            const nums = vals.split(';').map(v => parseInt(v, 10)).filter(n => !Number.isNaN(n));
            base.add({ Serial: serial, ProductName: product, LogType: 'elog',
                Timestamp: ts, LogID: logId, Content: line, Slogan: slogan,
                Key: key, Value: nums, ValueType: 'List[int]', IsMeasuredValue: true, ParentIndex: parent });
        }
    }
}

function parseElog52(base: Base, serial: string, product: string, ts: string, parent: number, line: string) {
    const m = Patterns.elog52.exec(line); if (!m) return;
    const [ , slogan, stateVal, clientKey, clientVal ] = m;
    base.add({ Serial: serial, ProductName: product, LogType: 'elog',
        Timestamp: ts, LogID: '52', Content: line, Slogan: slogan,
        Key: 'state', Value: String(stateVal), ValueType: 'str', IsMeasuredValue: false, ParentIndex: parent });
    base.add({ Serial: serial, ProductName: product, LogType: 'elog',
        Timestamp: ts, LogID: '52', Content: line, Slogan: slogan,
        Key: clientKey, Value: String(clientVal), ValueType: 'str', IsMeasuredValue: false, ParentIndex: parent });
}

/** Elog 主解析（含标准格式和 10/16/27/42/43/52 分发） */
function parseElogLine(
    base: Base, serial: string, product: string, line: string,
    elog10Anchor: { ts: string, parent: number } | undefined,
    cacheSetElog10Anchor: (anchor: { ts: string, parent: number }) => void
) {
    const m = Patterns.elog.exec(line);
    const parent = base.logIndex + 1;

    if (!m) {
        // 非标准格式：视作 elog10 纯 KV 与 Carrier Info，复用最近的 elog10 timestamp
        const ts = elog10Anchor?.ts ?? '';
        const parentIndex = elog10Anchor?.parent ?? parent;
        parseElog10SimpleKV(base, serial, product, ts, parentIndex, line);
        return;
    }

    const [, d6, t6, logId, content] = m;
    const ts = parseTimestamp(d6, t6);

    if (logId === '10') {
        cacheSetElog10Anchor({ ts, parent: parent });
        parseElog10(base, serial, product, ts, parent, content);
    } else if (logId === '16') {
        parseElog16(base, serial, product, ts, parent, content);
    } else if (logId === '27') {
        parseElog27(base, serial, product, ts, parent, content);
    } else if (logId === '42' || logId === '43') {
        parseElog42or43(base, serial, product, ts, parent, content, logId as any);
    } else if (logId === '52') {
        parseElog52(base, serial, product, ts, parent, content);
    } else {
        // 其他 ID：保留 Content
        base.add({
            Serial: serial, ProductName: product, LogType: 'elog',
            Timestamp: ts, LogID: logId, Content: content, Slogan: content,
            Key: '', Value: '', ValueType: '', IsMeasuredValue: false, ParentIndex: parent,
        });
    }
}

/** ===================== pareadall Parser ===================== */
function parsePareadall(base: Base, serial: string, product: string, logType: string, entry: string) {
    const m = Patterns.pareadall.exec(entry.trim());
    if (!m) return;
    const key = m[1]; const value = m[2];
    base.add({
        Serial: serial, ProductName: product, LogType: logType,
        Timestamp: '', LogID: '', Content: '', Slogan: "Execute 'help' for available commands",
        Key: key, Value: value, ValueType: 'string', IsMeasuredValue: false,
    });
}

/** ===================== trx_status Parser（顺序合并） ===================== */
function parseTrxStatusGroup(base: Base, serial: string, product: string, lines: string[]) {
    // 将同一 serial 的 trx_status 逐行扫描，合并为分节 key:value
    let currentBranch = ''; let timestamp = ''; let currentSection: string | null = null; const sectionLines: string[] = [];
    let parent = base.logIndex + 1;

    function flush() {
        if (currentSection && sectionLines.length) {
            base.add({
                Serial: serial, ProductName: product, LogType: 'trx_status',
                Timestamp: timestamp, LogID: '', Content: '',
                Slogan: currentBranch, Key: currentSection, Value: sectionLines.join('\n'),
                ValueType: 'dict', IsMeasuredValue: false, ParentIndex: parent,
            });
        }
    }

    for (const raw of lines) {
        const line = (raw ?? '').trim();
        const mb = Patterns.trx_branch.exec(line);
        if (mb) {
            // 新 Branch：先冲刷上一段
            flush();
            currentSection = null; sectionLines.length = 0;
            currentBranch = `Branch ${mb[1]}`;
            timestamp = ''; parent = base.logIndex + 1;
            continue;
        }
        const md = Patterns.trx_date.exec(line);
        if (md) { timestamp = md[1]; continue; }
        const ms = Patterns.trx_section.exec(line);
        if (ms) {
            // 切换 section
            flush();
            currentSection = ms[1]; sectionLines.length = 0;
            continue;
        }
        if (line) sectionLines.push(line);
    }
    flush();
}

/** ===================== 二次处理：时间戳回填（简化版） ===================== */
function postProcess(entries: LogEntry[]) {
    // 1) 将空时间戳回填为最近的 elog10 时间戳（同 Serial）
    const lastElog10PerSerial = new Map<string, string>();
    for (const e of entries) {
        if (e.LogType === 'elog' && e.LogID === '10' && e.Timestamp) {
            lastElog10PerSerial.set(e.Serial, e.Timestamp);
        }
    }
    for (const e of entries) {
        if (!e.Timestamp) {
            const ts = lastElog10PerSerial.get(e.Serial);
            if (ts) e.Timestamp = ts;
        } else {
            const dt = new Date(e.Timestamp.replace(' ', 'T') + 'Z');
            if (isFinite(+dt) && dt < MIN_VALID) {
                const ts = lastElog10PerSerial.get(e.Serial);
                if (ts) e.Timestamp = ts;
            }
        }
    }
}

/** ===================== 对外主入口 ===================== */
export function parseExtracted(entries: ExtractedEntry[]): LogEntry[] {
    const base = new Base();

    // 先按 Serial 分桶，确保 trx_status 可顺序解析
    const bySerial = new Map<string, ExtractedEntry[]>();
    for (const e of entries) {
        const key = String(e.Serial ?? '');
        if (!bySerial.has(key)) bySerial.set(key, []);
        bySerial.get(key)!.push(e);
    }

    for (const [serial, list] of bySerial.entries()) {
        const productName = (list.find(x => !!x.ProductName)?.ProductName ?? '') as string;

        // 单独收集 trx_status 行，实现顺序分段
        const trxLines: string[] = [];

        // 为 elog10 KV 行做锚点缓存
        let elog10Anchor: { ts: string, parent: number } | undefined;

        const setAnchor = (a: { ts: string, parent: number }) => { elog10Anchor = a; };

        for (const row of list) {
            const lt = (row.log_type || '').toLowerCase();
            const line = row.log_line || '';

            if (lt === 'trx_status') {
                trxLines.push(line);
                continue;
            }

            if (lt === 'csread' || lt === 'vsread' || lt === 'tsread') {
                parseRead(base, serial, productName, lt, line);
            } else if (lt === 'hwlog') {
                parseHwlog(base, serial, productName, lt, line);
            } else if (lt === 'pareadall') {
                parsePareadall(base, serial, productName, lt, line);
            } else if (lt === 'elog') {
                parseElogLine(base, serial, productName, line, elog10Anchor, setAnchor);
            } else {
                // 其它类型：原样落表，保留内容
                base.add({
                    Serial: serial, ProductName: productName, LogType: lt,
                    Timestamp: '', LogID: '', Content: line, Slogan: '', Key: '', Value: '', ValueType: '', IsMeasuredValue: false,
                });
            }
        }

        if (trxLines.length) parseTrxStatusGroup(base, serial, productName, trxLines);
    }

    // 二次处理
    postProcess(base.logEntries);

    return base.logEntries;
}
