// src/api/pqat.ts
// PQAT Viewer/API 前端访问封装：
// - 通过 Vite 代理把跨域改为同源：/pqat (Viewer) /pqat-api (API)
// - 解析 Viewer 页面 HTML，抽取可下载条目（id/sn/log/date）
// - 过滤：logType & timeStrobe
// - 提供按 fileId 触发浏览器下载的方法

import type {LogEntry} from '@/types';

export interface PQATDownloadParams {
    eidUser: string;           // EID 账号
    eidKey: string;            // Key/密码
    serials: string[];         // 序列号列表
    logType?: number;          // 0=All; 1=ExtLog; 2=Site Failure Note; 3=Proactive Logs; 4=HWS Scrap Pictures
    timeStrobe?: number;       // 0=All; -1=Latest; >0=最早N条; <-1=最后|N|条（可扩展）
}

// 走 Vite 代理（开发环境）；生产建议由后端或网关转发
const PQAT_VIEWER_BASE = '/pqat';               // 实际指向 .../PQATViewer// 实际指向 .../pqat_viewer_api/v0.6_b/api.php

// -------------------- 内部工具 --------------------

function basicAuthHeader(user: string, key: string): string {
    return 'Basic ' + btoa(`${user}:${key}`);
}

function buildSearchUrl(serial: string): string {
    const u = new URL(PQAT_VIEWER_BASE + '/', window.location.origin);
    u.searchParams.set('serialno', serial);
    return u.pathname + u.search; // 返回相对路径，确保走代理
}

function buildFileDownloadUrl(fileId: string): string {
    return `${PQAT_VIEWER_BASE}/files/${encodeURIComponent(fileId)}?download=true`;
}

// 解析 HTML -> { id, sn, log, date }[]
function parseIdListFromHtml(html: string): Array<{ id: string; sn: string; log: string; date: string }> {
    const out: Array<{ id: string; sn: string; log: string; date: string }> = [];
    try {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const container = doc.querySelector('div#filesearch');
        if (!container) return out;

        // 方案 1：优先按 <p class="thumbnail" id="p_thumbnail_XXXX">...<br>...<br>...</p>
        const pThumbs = Array.from(container.querySelectorAll('p.thumbnail[id^="p_thumbnail_"]')) as HTMLElement[];
        pThumbs.forEach((p) => {
            const idAttr = p.getAttribute('id') || '';           // p_thumbnail_408813649
            const id = idAttr.replace(/^p_thumbnail_/, '');      // 408813649

            // p.innerHTML 里用 <br> 分行；先替换成 \n，再去掉所有标签
            const text = p.innerHTML
                .replace(/<br\s*\/?>/gi, '\n')
                .replace(/<[^>]+>/g, '')
                .replace(/\r/g, '')
                .trim();

            const parts = text.split('\n').map(s => s.trim()).filter(Boolean);
            const sn   = parts[0] || '';
            const log  = parts[1] || '';
            const date = parts[2] || '';

            if (id) out.push({ id, sn, log, date });
        });

        // 方案 2（兜底）：按 <img id="img_thumbnail_XXXX"> 补齐缺失的条目
        if (out.length === 0) {
            const imgs = Array.from(container.querySelectorAll('img.thumbnail[id^="img_thumbnail_"]')) as HTMLElement[];
            imgs.forEach((img) => {
                const idAttr = img.getAttribute('id') || '';       // img_thumbnail_408813649
                const id = idAttr.replace(/^img_thumbnail_/, '');
                // 试着找到同块里的 <p id="p_thumbnail_XXXX">
                const pid = `p_thumbnail_${id}`;
                const p = container.querySelector(`p.thumbnail#${CSS.escape(pid)}`) as HTMLElement | null;

                let sn = '', log = '', date = '';
                if (p) {
                    const text = p.innerHTML
                        .replace(/<br\s*\/?>/gi, '\n')
                        .replace(/<[^>]+>/g, '')
                        .replace(/\r/g, '')
                        .trim();
                    const parts = text.split('\n').map(s => s.trim()).filter(Boolean);
                    sn   = parts[0] || '';
                    log  = parts[1] || '';
                    date = parts[2] || '';
                }
                if (id) out.push({ id, sn, log, date });
            });
        }
    } catch (e) {
        console.error('[PQAT] parseIdListFromHtml error:', e);
    }
    return out;
}


// 过滤逻辑（把参数名改回 logType，更清晰）
function filterIdList(
    list: Array<{ id: string; sn: string; log: string; date: string }>,
    logType = 0,
    timeStrobe = 0
) {
    let res = [...list];

    // 日志类型过滤
    if (logType !== 0) {
        const typeMap: Record<number, RegExp> = {
            1: /ExtLog/i,
            2: /Site\s*Failure\s*Note/i,
            3: /Proactive\s*Logs?/i,
            4: /HWS\s*Scrap\s*Pictures?/i
        };
        const re = typeMap[logType];
        if (re) res = res.filter((x) => re.test(x.log));
    }

    // 日期升序（old -> new）
    res.sort((a, b) => (new Date(a.date).getTime() || 0) - (new Date(b.date).getTime() || 0));

    // 时间窗口选择
    if (timeStrobe === 0) {
        // all
    } else if (timeStrobe === -1) {
        res = res.slice(-1);
    } else if (timeStrobe > 0) {
        res = res.slice(0, timeStrobe);
    } else if (timeStrobe < -1) {
        res = res.slice(timeStrobe); // 负值：取最后 |n|
    }
    return res;
}


// 从 Content-Disposition 中取文件名
function filenameFromContentDisposition(cd?: string | null): string | null {
    if (!cd) return null;
    // 兼容常见格式：attachment; filename="xxx.zip"
    const m = cd.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
    return m ? decodeURIComponent(m[1]) : null;
}

// -------------------- 导出 API --------------------

/**
 * 拉取可下载日志条目：
 * - 对每个 SN 请求 Viewer 页面 → 解析文件 id/sn/log/date
 * - 过滤（logType/timeStrobe）
 * - 返回 LogEntry[]（ts/level/text/raw），raw 为下载 URL
 */
export async function downloadFromPQAT(params: PQATDownloadParams): Promise<{
    ts: string;
    level: string;
    text: string;
    raw: string
}[]> {
    const { eidUser, eidKey, serials, logType = 0, timeStrobe = 0 } = params;
    if (!eidUser || !eidKey) throw new Error('Missing EID or Key');

    const auth = basicAuthHeader(eidUser, eidKey);
    const allItems: Array<{ id: string; sn: string; log: string; date: string }> = [];

    for (const sn of serials) {
        const url = buildSearchUrl(sn);
        const resp = await fetch(url, {
            method: 'GET',
            headers: {
                Authorization: auth
            }
        });
        if (!resp.ok) {
            throw new Error(`Viewer request failed: ${resp.status} ${resp.statusText}`);
        }
        const html = await resp.text();
        const items = parseIdListFromHtml(html);
        const filtered = filterIdList(items, logType, timeStrobe);
        allItems.push(...filtered);
    }

    // 转换为页面可展示的 LogEntry 结构
    return allItems.map((x) => ({
        ts: safeToIso(x.date),
        level: x.log, // 占位用：把日志类型放在 level 列
        text: `${x.sn} - ${x.log} - #${x.id}`,
        raw: buildFileDownloadUrl(x.id) // 点击下载时使用
    }));
}

/**
 * 按 fileId 下载文件：生成 Blob 并触发浏览器保存
 */
export async function downloadFileById(
    eidUser: string,
    eidKey: string,
    fileId: string,
    sn?: string
): Promise<void> {
    const auth = basicAuthHeader(eidUser, eidKey);
    const url = buildFileDownloadUrl(fileId);

    const resp = await fetch(url, {
        method: 'GET',
        headers: { Authorization: auth }
    });
    if (!resp.ok) {
        throw new Error(`Download failed: ${resp.status} ${resp.statusText}`);
    }

    const blob = await resp.blob();
    const cd = resp.headers.get('Content-Disposition');
    const origin = filenameFromContentDisposition(cd) || `pqat_${fileId}`;


    // 在原文件名基础上加 SN_ 前缀（若有）
    const safeSn = (sn || '').replace(/[\\/:*?"<>|]+/g, '_');
    const filename = safeSn ? `${safeSn}_${origin}` : origin;

    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    URL.revokeObjectURL(link.href);
    document.body.removeChild(link);
}
// -------------------- 辅助 --------------------

function safeToIso(ts: string): string {
    const t = new Date(ts);
    return isNaN(t.getTime()) ? '' : t.toISOString();
}

// -------------------- 在线解压解析 --------------------
export async function fetchFileBlobById(eidUser: string, eidKey: string, fileId: string): Promise<Blob> {
    const auth = 'Basic ' + btoa(`${eidUser}:${eidKey}`);
    const url = `/pqat/files/${encodeURIComponent(fileId)}?download=true`; // 走 Vite 代理
    const resp = await fetch(url, { headers: { Authorization: auth } });
    if (!resp.ok) throw new Error(`Fetch blob failed: ${resp.status} ${resp.statusText}`);
    return await resp.blob();
}


// src/api/pqat.ts （新增导出）
/**
 * 按 fileId 拉取文件内容 + 建议文件名（来自 Content-Disposition 或回退名）
 */
export async function fetchFileById(
    eidUser: string,
    eidKey: string,
    fileId: string
): Promise<{ blob: Blob; filename: string }> {
    const auth = basicAuthHeader(eidUser, eidKey);
    const url = buildFileDownloadUrl(fileId);

    const resp = await fetch(url, { method: 'GET', headers: { Authorization: auth } });
    if (!resp.ok) {
        throw new Error(`Download failed: ${resp.status} ${resp.statusText}`);
    }

    const blob = await resp.blob();
    const cd = resp.headers.get('Content-Disposition');
    const filename = filenameFromContentDisposition(cd) || `pqat_${fileId}`;

    return { blob, filename };
}

/** 浏览器是否支持文件系统目录选择器（仅 Chromium 系） */
export function isDirectoryPickerAvailable(): boolean {
    return typeof (window as any).showDirectoryPicker === 'function';
}
