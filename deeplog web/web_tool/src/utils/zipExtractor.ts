/* eslint-disable no-console */
import JSZip from 'jszip';
import type {ExtractedEntry, ZipKind} from '@/types';

/**
 * 入口：解析一个 ZIP（Proactive 或 Return）
 */
export async function extractFromZip(fileOrBlob: File | Blob): Promise<{
    kind: ZipKind;
    entries: ExtractedEntry[];
}> {
    const zip = await JSZip.loadAsync(fileOrBlob);
    const filename = (fileOrBlob as File).name || 'unknown.zip';

    const kind = detectZipKind(filename);
    if (kind === 'proactive') {
        const entries = await parseProactiveZip(zip, filename);
        return { kind, entries };
    } else {
        const entries = await parseReturnZip(zip, filename);
        return { kind, entries };
    }
}

/* --------------------------------------------
 * Proactive ZIP 解析
 *  - 查找 .log
 *  - 文件名解析审计日期
 *  - 解析 SDIC 表
 *  - 解析命令输出（按 LNH 匹配）
 * ------------------------------------------- */
async function parseProactiveZip(zip: JSZip, zipName: string): Promise<ExtractedEntry[]> {
    // 1) 找到第一个 .log
    const file = Object.values(zip.files).find(f => f.name.toLowerCase().endsWith('.log'));
    if (!file) throw new Error('No .log file found in zip');

    const text = await file.async('text');
    const lines = text.split(/\r?\n/);

    // 2) 审计日期
    let auditDate = '';
    try {
        auditDate = parseAuditDateFromProFilename(zipName);
    } catch {
        auditDate = fallbackAuditDate(zipName);
    }

    // 3) 解析 SDIC 表
    const sdic = parseSDICTable(lines);

    // 4) 解析无线电日志输出（根据 SDIC 格式判断命令行正则）
    const { rows } = parseRadioLogs(lines, sdic);

    // 5) 生成结果
    return rows.map(r => ({
        AuditDate: auditDate,
        Serial: r.Serial ?? null,
        ProductName: r.ProductName ?? null,
        log_type: r.log_type,
        log_line: r.log_line,
        LNH: r.LNH
    }));
}

/* ---- Proactive: 文件名日期 ---- */
function parseAuditDateFromProFilename(fileName: string): string {
    // 支持 *_YYYYMMDD_HHMMSS_Logfiles.zip / *_YYYYMMDD_HHMMSS_logfiles.zip
    const m = fileName.match(/_(\d{8})_(\d{6})_[Ll]ogfiles\.zip$/i);
    if (!m) throw new Error('proactive filename not matched');
    const date = `${m[1].slice(0, 4)}-${m[1].slice(4, 6)}-${m[1].slice(6, 8)}`;
    const time = `${m[2].slice(0, 2)}:${m[2].slice(2, 4)}:${m[2].slice(4, 6)}`;
    return `${date}T${time}`;
}
function fallbackAuditDate(fileName: string): string {
    const d = fileName.match(/(\d{8})/);
    const t = fileName.match(/(\d{6})/);
    const date = d ? `${d[1].slice(0, 4)}-${d[1].slice(4, 6)}-${d[1].slice(6, 8)}` : '1970-01-01';
    const time = t ? `${t[1].slice(0, 2)}:${t[1].slice(2, 4)}:${t[1].slice(4, 6)}` : '00:00:00';
    return `${date}T${time}`;
}

/* ---- Proactive: 解析 SDIC 表 ---- */
type SDICRow = { LNH?: string; BOARD?: string; SERIAL?: string } | { 'MO (LNH)'?: string; XPBOARD?: string; 'SERIAL/NAME'?: string };
type SDIC = { rows: SDICRow[]; format: 'standard' | 'alternative' };

function parseSDICTable(lines: string[]): SDIC {
    const standardHeaders = ['LNH', 'BOARD', 'SERIAL'];
    const alternativeHeaders = ['XPBOARD', 'SERIAL/NAME', 'MO (LNH)'];

    const tableLines: string[] = [];
    let headerFound = false;
    let useAlt = false;

    const isAll = (s: string, set: string) => !!s && [...s].every(ch => set.includes(ch));

    for (let i = 0; i < lines.length; i++) {
        const raw = lines[i];
        const line = (raw).trim();
        if (!line) continue;
        // 跳过全等号
        if (isAll(line, '=')) continue;

        if (headerFound && (isAll(line, '-') || isAll(line, '*'))) break;

        if (!headerFound) {
            const headers = line.split(';').map(h => (h ?? '').toString().trim()).filter(Boolean);
            if (standardHeaders.every(h => headers.includes(h))) {
                headerFound = true;
                useAlt = false;
                tableLines.push(line);
                continue;
            }
            if (alternativeHeaders.every(h => headers.includes(h))) {
                headerFound = true;
                useAlt = true;
                tableLines.push(line);
            }
        } else {
            tableLines.push(line);
        }
    }

    if (!headerFound || tableLines.length === 0) {
        // 返回空但保留格式
        return { rows: [], format: 'standard' };
    }

    // 以 ; 分隔解析
    const header = tableLines[0].split(';').map(h => h.trim());
    const rows: SDICRow[] = tableLines.slice(1).map((l) => {
        const vals = l.split(';').map(v => v.trim());
        const rec: Record<string, string> = {};
        header.forEach((key, idx) => { rec[key] = vals[idx] ?? ''; });
        return rec as SDICRow;
    });

    return { rows, format: useAlt ? 'alternative' : 'standard' };
}

/* ---- Proactive: 解析命令输出 ---- */
function parseRadioLogs(lines: string[], sdic: SDIC): {
    rows: Array<{ LNH: string; Serial?: string; ProductName?: string; log_type: string; log_line: string }>;
} {
    const df: Array<{ line: string }> = lines.map(line => ({ line }));

    const isAlt = sdic.format === 'alternative';
    const cmdRe = isAlt
        ? /\$ lhsh\s+(\S+)\s+(\S+)(?:\s+(?:read|status))?/i   // alternative
        : /coli>\/fruacc\/lhsh\s+(\S+)\s+(\S+)(?:\s+(?:read|status))?/i; // standard

    const outRe = /^(\S+):\s+(.*)/;

    let lastLNH = '';
    let lastType = '';

    const records: Array<{ LNH: string; log_type: string; log_line: string }> = [];

    for (const { line } of df) {
        const cmd = line.match(cmdRe);
        if (cmd) {
            lastLNH = cmd[1];
            lastType = normalizeLogType(cmd[2]);
            continue;
        }
        const out = line.match(outRe);
        if (out) {
            // alternative 需要把 0001p1d7 → 000100/port_1_dev_7
            const outLNH = isAlt ? altLnhToStandard(out[1]) : out[1];
            if (outLNH === lastLNH && lastType) {
                records.push({ LNH: lastLNH, log_type: lastType, log_line: out[2] });
            }
        }
    }

    // 合并 SDIC
    const withMeta = records.map((r) => {
        const meta = findSdicByLnh(sdic, r.LNH);
        const board = meta?.BOARD ?? (meta as any)?.XPBOARD ?? '';
        const productName = formatProductName(board);
        const serial = meta?.SERIAL ?? (meta as any)?.['SERIAL/NAME'] ?? '';
        return { ...r, Serial: serial || undefined, ProductName: productName || undefined };
    });

    return { rows: withMeta };
}

function normalizeLogType(raw: string): string {
    const m = raw.toLowerCase();
    const map: Record<string, string> = {
        cs: 'csread',
        vs: 'vsread',
        ts: 'tsread',
        elog: 'elog',
        hwlog: 'hwlog',
        trx: 'trx_status'
    };
    return map[m] || m;
}
function altLnhToStandard(s: string): string {
    // 0001p1d7 => 000100/port_1_dev_7
    const m = s.match(/^(\d{4})p(\d+)d(\d+)$/);
    if (!m) return s;
    return `${m[1]}00/port_${m[2]}_dev_${m[3]}`;
}
function findSdicByLnh(sdic: SDIC, lnh: string): { LNH?: string; BOARD?: string; SERIAL?: string } | undefined {
    if (sdic.rows.length === 0) return undefined;

    if (sdic.format === 'standard') {
        return sdic.rows.find((r: any) => r.LNH === lnh) as any;
    }
    // alternative: 先将 'MO (LNH)' 提取括号内内容
    for (const row of sdic.rows as any[]) {
        let rowLnh = row['MO (LNH)'] as string | undefined;
        if (rowLnh && rowLnh.includes('(') && rowLnh.includes(')')) {
            rowLnh = rowLnh.split('(')[1]?.split(')')[0];
        }
        if (rowLnh === lnh) {
            const mapped = {
                LNH: lnh,
                BOARD: row['XPBOARD'] ?? '',
                SERIAL: row['SERIAL/NAME'] ?? ''
            };
            return mapped as any;
        }
    }
    return undefined;
}

/* ---- Proactive / Return：产品名格式化 ---- */
function formatProductName(board?: string): string {
    if (!board) return '';
    let v = board.trim().replace(/\*+$/g, '');

    if (v.startsWith('Radio')) {
        const rest = v.slice(5).trim();
        if (!rest) return v;

        const parts = rest.split(/\s+/);
        const model = parts[0] ?? '';
        const bandParts = parts.slice(1);
        const cleanBands: string[] = [];

        for (const p of bandParts) {
            if (p === 'C') continue;
            if (p.includes('44B')) {
                const bands = p.match(/B\d+/g) ?? [];
                cleanBands.push(...bands);
            } else cleanBands.push(p);
        }
        return cleanBands.length ? `Radio ${model} ${cleanBands.join('')}` : `Radio ${model}`;
    }

    if (v.startsWith('AIR')) return `AIR${v.slice(3).trim()}`;

    if (v.startsWith('RRU')) {
        const remainder = v.slice(3);

        // RRU4471HPB1 → Radio 4471HP B1（以及更复杂 HP）
        const hp = remainder.match(/^(\d{4}HP)(.*)$/);
        if (hp) {
            const modelPart = hp[1];
            const bandPart = hp[2];
            const bands = bandPart.match(/B\d+/g) ?? [];
            const clean = bands.map(b => {
                let digits = b.replace(/^B/, '').replace(/C$/i, '');
                if (digits.length >= 3 && new Set(digits.slice(1)).size === 1) {
                    digits = digits[0];
                } else if (digits.length === 2 && digits[0] === digits[1]) {
                    digits = digits[0];
                }
                return `B${digits}`;
            });
            return `Radio ${modelPart} ${clean.join('')}`;
        }

        // 常规：取前4位数字作为 model
        let modelNumber = '';
        for (let i = 0; i < remainder.length && modelNumber.length < 4; i++) {
            if (/\d/.test(remainder[i])) modelNumber += remainder[i];
        }
        if (!modelNumber) return `Radio ${remainder}`;

        let rest = remainder.replace(modelNumber, '');
        // 清理重复的型号前缀
        const prefix = modelNumber.slice(0, 2);
        const firstB = rest.indexOf('B');
        if (firstB >= 2 && rest.slice(firstB - 2, firstB) === prefix) {
            rest = rest.slice(0, firstB - 2) + rest.slice(firstB);
        }
        // 抽取所有 B 段，去尾 C
        const bands: string[] = [];
        let pos = 0;
        while (true) {
            const b = rest.indexOf('B', pos);
            if (b === -1) break;
            const next = rest.indexOf('B', b + 1);
            let seg = next === -1 ? rest.slice(b) : rest.slice(b, next);
            seg = seg.replace(/C$/i, '');
            bands.push(seg);
            pos = next === -1 ? rest.length : next;
        }
        return bands.length ? `Radio ${modelNumber} ${bands.join('')}` : `Radio ${modelNumber}`;
    }

    return v;
}


/* --------------------------------------------
 * Return ZIP 解析
 *  - 文件名解析 Return Date（格式1/2/3）
 *  - 读取 parget.txt（元数据）
 *  - 读取各类 *read.txt / trxstatus.txt
 * ------------------------------------------- */
async function parseReturnZip(zip: JSZip, zipName: string): Promise<ExtractedEntry[]> {
    const auditDate = parseReturnDate(zipName);


    console.log('[zipExtractor][return][ALL FILES]');
    for (const f of Object.values(zip.files)) {
        console.log(' -', f.name);
    }


    // 预期文件
    const expected: Record<string, string> = {
        'parget.txt': 'metadata',
        'elogread.txt': 'elog',
        'hwlogread.txt': 'hwlog',
        'vsread.txt': 'vsread',
        'csread.txt': 'csread',
        'tsread.txt': 'tsread',
        'trxstatus.txt': 'trx_status',
        'llog.txt': 'llog',
        'lmclist.txt': 'lmclist',
        'telogread.txt': 'telog',
    };

    let meta: Record<string, string> = {};
    const buckets: Record<string, string[]> = {};
    Object.values(expected).forEach(v => { if (v !== 'metadata') buckets[v] = []; });

    // 扫描所有文件（包括子目录）
    const entries = Object.values(zip.files);

    for (const f of entries) {
        if (f.dir) continue;

        const base = basename(f.name).toLowerCase();

        // 允许内部文件位于任意子目录
        if (!Object.prototype.hasOwnProperty.call(expected, base)) {
            continue;
        }

        const type = expected[base];
        const text = await f.async('text');

        if (type === 'metadata') {
            meta = parseParget(text);
        } else {
            const list = text.split(/\r?\n/);
            buckets[type].push(...list);
        }
    }

    const serial = meta['SYS_HW_SERIAL'] ?? null;
    const rawProd = meta['SYS_HW_MARKET_NAME'] ?? '';
    console.debug('[zipExtractor][return] SYS_HW_MARKET_NAME=', rawProd, 'SYS_HW_SERIAL=', serial);
    const productName = formatProductName(rawProd) || null;

    const out: ExtractedEntry[] = [];
    for (const [logType, lines] of Object.entries(buckets)) {
        if (!lines.length) continue;
        for (const line of lines) {
            if (!line) continue;
            out.push({
                AuditDate: auditDate,
                Serial: serial,
                ProductName: productName,
                log_type: logType,
                log_line: line,
                LNH: line
            });
        }
    }
    return out;
}

/* ---- Return: 文件名日期 ---- */
function parseReturnDate(fileName: string): string {

    // format_1: YYYY-MM-DD_hh.mm.ss-*.zip
    let m = fileName.match(/^(\d{4}-\d{2}-\d{2})_(\d{2}\.\d{2}\.\d{2})-.*\.zip$/);
    if (m) return `${m[1]}T${m[2].replace(/\./g, ':')}`;

    // format_2: *_YYYY-MM-DD_hh.mm.ss-*.zip
    m = fileName.match(/_(\d{4}-\d{2}-\d{2})_(\d{2}\.\d{2}\.\d{2})-.*\.zip$/);
    if (m) return `${m[1]}T${m[2].replace(/\./g, ':')}`;

    // format_3: *_YYYY-MM-DD_hh.mm.ss - *.zip
    m = fileName.match(/_(\d{4}-\d{2}-\d{2})_(\d{2}\.\d{2}\.\d{2})\s*-\s*.*\.zip$/);
    if (m) return `${m[1]}T${m[2].replace(/\./g, ':')}`;

    // format_4: *_YYYY-MM-DD hh.mm.ss-*.zip
    m = fileName.match(/_(\d{4}-\d{2}-\d{2})\s+(\d{2}\.\d{2}\.\d{2})-.*\.zip$/);
    if (m) return `${m[1]}T${m[2].replace(/\./g, ':')}`;

    // format_5: *_YYYY-MM-DD hh.mm.ss - *.zip
    m = fileName.match(/_(\d{4}-\d{2}-\d{2})\s+(\d{2}\.\d{2}\.\d{2})\s*-\s*.*\.zip$/);
    if (m) return `${m[1]}T${m[2].replace(/\./g, ':')}`;

    throw new Error(`Return filename not matched: ${fileName}`);
}

/* ---- Return: 解析 parget.txt ---- */

function parseParget(text: string): Record<string, string> {
    const meta: Record<string, string> = {};
    const lines = text.split(/\r?\n/);

    for (const l of lines) {
        const line = l.trim();
        if (!line) continue;

        // 形式 1：'KEY' = 'VALUE'
        let m = line.match(/'([^']+)'\s*=\s*'([^']+)'/);
        if (m) {
            meta[m[1].trim()] = m[2].trim();
            continue;
        }

        // 形式 2：KEY = VALUE（无引号）
        // 允许 KEY 中出现字母数字/下划线/斜杠/括号/连字符/空格
        m = line.match(/^\s*([A-Za-z0-9_\/()\-\s]+)\s*=\s*(.+?)\s*$/);
        if (m) {
            const key = m[1].trim();
            const val = m[2].trim();
            meta[key] = val;
            continue;
        }

        //（可选兜底）形式 3：KEY: VALUE
        m = line.match(/^\s*([A-Za-z0-9_\/()\-\s]+)\s*:\s*(.+?)\s*$/);
        if (m) {
            const key = m[1].trim();
            const val = m[2].trim();
            meta[key] = val;
            continue;
        }
    }
    return meta;
}

/* --------------------------------------------
 * 其它工具
 * ------------------------------------------- */
function detectZipKind(fileName: string): ZipKind {
    const lower = fileName.toLowerCase().trim();
    // 先尝试 Return 的几种命名格式
    // 1) YYYY-MM-DD_hh.mm.ss-*.zip
    if (/^\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2}-.*\.zip$/.test(lower)) return 'return';
    // 2) *_YYYY-MM-DD_hh.mm.ss-*.zip
    if (/.*_\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2}-.*\.zip$/.test(lower)) return 'return';
    // 3) *_YYYY-MM-DD_hh.mm.ss - *.zip
    if (/.*_\d{4}-\d{2}-\d{2}_\d{2}\.\d{2}\.\d{2}\s*-\s*.*\.zip$/.test(lower)) return 'return';
    // 4) *_YYYY-MM-DD hh.mm.ss-*.zip
    if (/.*_\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2}-.*\.zip$/.test(lower)) return 'return';
    // 5) *_YYYY-MM-DD hh.mm.ss - *.zip
    if (/.*_\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2}\s*-\s*.*\.zip$/.test(lower)) return 'return';

    // 再尝试 Proactive 的几种命名格式
    // Proactive：*_YYYYMMDD_HHMMSS_logfiles.zip
    if (/.*_\d{8}_\d{6}_logfiles\.zip$/.test(lower)) return 'proactive';
    // Proactive：*_YYYYMMDD_HHMMSS_Logfiles.zip
    if (/.*_\d{8}_\d{6}_Logfiles\.zip$/.test(lower)) return 'proactive';

    // 默认 Return (如果不被判定为 proactive log)
    return 'return';
}

function basename(p: string): string {
    if (!p) return p;
    // 同时找 / 和 \，取最后出现的位置
    const i1 = p.lastIndexOf('/');
    const i2 = p.lastIndexOf('\\');   // 关键修复
    const idx = Math.max(i1, i2);
    return idx >= 0 ? p.slice(idx + 1) : p;
}
