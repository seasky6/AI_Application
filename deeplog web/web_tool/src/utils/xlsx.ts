import * as XLSX from 'xlsx';
import type { ExtractedEntry, LogEntry } from '@/types';

/** 读取 *_extracted.xlsx（工作表：extracted） */
export async function readExtractedFromHandle(handle: FileSystemFileHandle): Promise<ExtractedEntry[]> {
    const file = await handle.getFile();
    const buf = await file.arrayBuffer();
    const wb = XLSX.read(buf, { type: 'array' });
    const ws = wb.Sheets['extracted'];
    if (!ws) return [];
    const json = XLSX.utils.sheet_to_json<any>(ws, { defval: '' });
    return json.map((r: any) => ({
        AuditDate: r.AuditDate ?? null,
        Serial: r.Serial ?? null,
        ProductName: r.ProductName ?? null,
        log_type: r.log_type ?? '',
        log_line: r.log_line ?? '',
    }));
}

/** 保存 *_parsed.json 到目录 */
export async function saveJsonToDir(dir: FileSystemDirectoryHandle, name: string, data: any) {
    const fileHandle = await dir.getFileHandle(name, { create: true });
    const writer = await fileHandle.createWritable();
    await writer.write(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    await writer.close();
    return fileHandle as FileSystemFileHandle;
}

/** 另存 *_parsed.json */
export async function saveJsonWithPicker(name: string, data: any) {
    const handle: FileSystemFileHandle = await (window as any).showSaveFilePicker({
        suggestedName: name,
        types: [{ description: 'JSON', accept: { 'application/json': ['.json'] } }]
    });
    const writer = await handle.createWritable();
    await writer.write(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
    await writer.close();
    const file = await handle.getFile();
    const url = URL.createObjectURL(file);
    return { handle, url };
}

/** 保存 *_parsed.xlsx（工作表：parsed），列顺序与 LogEntryDict 对齐 */
export async function saveParsedXlsxToDir(dir: FileSystemDirectoryHandle, name: string, rows: LogEntry[]) {
    const header = ['Index','Serial','ProductName','LogType','Timestamp','LogID','Content','Slogan',
        'Key','Value','ValueType','IsMeasuredValue','ParentIndex'];
    const ws = XLSX.utils.json_to_sheet(rows, { header });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'parsed');
    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const fileHandle = await dir.getFileHandle(name, { create: true });
    const writer = await fileHandle.createWritable();
    await writer.write(new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
    await writer.close();
    return fileHandle as FileSystemFileHandle;
}

/** 另存 *_parsed.xlsx */
export async function saveParsedXlsxWithPicker(name: string, rows: LogEntry[]) {
    const handle: FileSystemFileHandle = await (window as any).showSaveFilePicker({
        suggestedName: name,
        types: [{ description: 'Excel', accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] } }]
    });
    const header = ['Index','Serial','ProductName','LogType','Timestamp','LogID','Content','Slogan',
        'Key','Value','ValueType','IsMeasuredValue','ParentIndex'];
    const ws = XLSX.utils.json_to_sheet(rows, { header });
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'parsed');
    const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const writer = await handle.createWritable();
    await writer.write(new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
    await writer.close();
    const file = await handle.getFile();
    const url = URL.createObjectURL(file);
    return { handle, url };
}
