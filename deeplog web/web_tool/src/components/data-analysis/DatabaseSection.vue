<template>
  <div class="deeplog-card" style="margin-top: 24px">
    <h3>{{ $t('dataAnalysisPage.database.title') }}</h3>
    <p style="opacity:.8">{{ $t('dataAnalysisPage.database.desc') }}</p>

    <!-- 选择文件夹 + PQAT 凭据 + 导入 -->
    <el-form label-width="160px" style="margin-top:16px">

      <!-- PQAT 凭据 -->
      <el-form-item :label="$t('dataAnalysisPage.database.eidUser')">
        <el-input v-model="eidUser" autocomplete="username" placeholder="e.g. ehuabox" />
      </el-form-item>
      <el-form-item :label="$t('dataAnalysisPage.database.eidKey')">
        <el-input v-model="eidKey" type="password" autocomplete="current-password" show-password />
      </el-form-item>

      <!-- 选择数据源文件夹 -->
      <el-form-item :label="$t('dataAnalysisPage.database.sourceFolder')">
        <div class="row">
          <el-input
              v-model="displayPath"
              :placeholder="$t('dataAnalysisPage.database.pickFolderPlaceholder') as string"
              readonly
              style="flex:1"
          />
          <el-button type="default" style="margin-left:8px" @click="onPickFolder">
            {{ $t('dataAnalysisPage.database.pickFolderBtn') }}
          </el-button>
        </div>
      </el-form-item>

      <!-- 导入数据库 -->
      <el-form-item>
        <el-button type="primary" :disabled="!dirHandle || loading" @click="onImport">
          {{ $t('dataAnalysisPage.database.importButton') }}
        </el-button>
      </el-form-item>
    </el-form>

    <!-- 进度条 -->
    <div v-if="loading" style="margin-top:20px">
      <el-progress :percentage="progress" :stroke-width="16" />
      <p style="margin-top:8px;opacity:.8">{{ progressText }}</p>
    </div>

    <!-- 导入结果简报 -->
    <div v-if="lastReport && !loading" class="parsed-box">
      <h4>{{ $t('dataAnalysisPage.database.importSummary') }}</h4>
      <ul>
        <li>{{ $t('dataAnalysisPage.database.scannedZips') }}: {{ lastReport.totalZips }}</li>
        <li>{{ $t('dataAnalysisPage.database.uniqueSNs') }}: {{ lastReport.uniqueSnCount }}</li>
        <li>{{ $t('dataAnalysisPage.database.invalidSnCount') }}: {{ lastReport.invalidSnCount }}</li>
        <li>{{ $t('dataAnalysisPage.database.pqatQueried') }}: {{ lastReport.pqatQueried }}</li>
      </ul>
    </div>

    <!-- 二维表格（仅 serialNumber） -->
    <div v-if="!loading && tableRows.length" class="table-box">
      <div class="table-toolbar">
        <el-input
            v-model="querySn"
            :placeholder="$t('dataAnalysisPage.database.searchSnPlaceholder') as string"
            clearable
            style="width: 320px"
        />
        <el-button style="margin-left:8px" @click="querySn = ''">
          {{ $t('dataAnalysisPage.common.clear') }}
        </el-button>

        <!-- reload：弹窗里提供“选择新 DB 文件” -->
        <el-button type="default" style="margin-left:auto" @click="showDbPicker = true">
          {{ $t('dataAnalysisPage.database.reloadDbBtn') }}
        </el-button>

        <el-dialog
            v-model="showDbPicker"
            title="Choose the DB file"
            width="480px"
        >
          <div style="padding-bottom: 12px;">
            <el-button type="primary" @click="pickDbFile">
              Choose the new DB file...
            </el-button>
          </div>

          <template #footer>
            <el-button @click="showDbPicker = false">Cancel</el-button>
          </template>
        </el-dialog>
      </div>

      <el-table
          :data="filteredRows"
          size="small"
          border
          stripe
          style="width:100%; margin-top:10px"
      >
        <el-table-column prop="serialNumber" :label="$t('dataAnalysisPage.database.col.serialNumber')" min-width="160"/>

        <el-table-column prop="productName" :label="$t('dataAnalysisPage.database.col.productName')" min-width="200"/>

        <el-table-column :label="$t('dataAnalysisPage.database.col.firstDate')" min-width="160">
          <template #default="{ row }">{{ formatIsoToLocal(row.firstDate) }}</template>
        </el-table-column>

        <el-table-column :label="$t('dataAnalysisPage.database.col.lastDate')" min-width="160">
          <template #default="{ row }">{{ formatIsoToLocal(row.lastDate) }}</template>
        </el-table-column>

        <el-table-column prop="logTypes" :label="$t('dataAnalysisPage.database.col.logTypes')" min-width="220">
          <template #default="{ row }">{{ row.logTypes.join(', ') }}</template>
        </el-table-column>


        <el-table-column prop="subLogTypes" :label="$t('dataAnalysisPage.database.col.subLogTypes')" min-width="200">
          <template #default="{ row }">{{ (row.subLogTypes ?? []).join(', ') }}</template>
        </el-table-column>


        <el-table-column prop="zipCount" :label="$t('dataAnalysisPage.database.col.zipCount')"  min-width="120"/>
      </el-table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { downloadFromPQAT } from '@/api/pqat';
import { extractFromZip } from "@/utils/zipExtractor";
import JSZip from "jszip";

// ================== 常量 ==================
const DB_FILE_NAME = 'deeplog_db.json';
const DB_VERSION = 1;

// ================== 类型 ==================
type ZipHandle = { fileHandle: FileSystemFileHandle; relativePath: string };

type DbRecord = {
  serialNumber: string;
  productName?: string | null;
  firstDate?: string | null;
  lastDate?: string | null;
  logTypes: string[];
  subLogTypes?: string[];
  zips: string[];
};

type DbFile = {
  version: number;
  updatedAt: string;
  records: DbRecord[];
};

type ImportReport = {
  totalZips: number;
  uniqueSnCount: number;
  invalidSnCount: number;
  pqatQueried: number;
  logTypeDist: Record<string, number>;
};

// ================== UI 状态 ==================
const dirHandle = ref<FileSystemDirectoryHandle | null>(null);
const displayPath = ref('');

const eidUser = ref('');
const eidKey = ref('');

const loading = ref(false);
const progress = ref(0);
const progressText = ref('');
const lastReport = ref<ImportReport | null>(null);

type TableRow = {
  serialNumber: string;
  productName?: string | null;
  firstDate?: string | null;
  lastDate?: string | null;
  logTypes: string[];
  subLogTypes?: string[];
  zipCount: number;
};
const tableRows = ref<TableRow[]>([]);
const querySn = ref('');

// 重新选择 DB 文件的对话框
const showDbPicker = ref(false);

// ================== 筛选 ==================
const filteredRows = computed(() => {
  const q = querySn.value.trim().toUpperCase();
  if (!q) return tableRows.value;
  return tableRows.value.filter(r =>
      (r.serialNumber || '').toUpperCase().includes(q)
  );
});

// ================== 选择源目录文件夹 ==================
async function onPickFolder() {
  try {
    const handle = await (window as any).showDirectoryPicker({ mode: 'readwrite' });
    dirHandle.value = handle;
    displayPath.value = handle.name;
    await reloadFromDb();
  } catch {}
}

// ================== 导入数据库 ==================
const snToTs = new Map<string, number[]>();

async function onImport() {
  if (!dirHandle.value) return;

  loading.value = true;
  progress.value = 0;
  progressText.value = 'Scanning ZIP files...';

  const zipHandles: ZipHandle[] = [];
  for await (const e of walkFiles(dirHandle.value)) {
    if (e.fileHandle.name.toLowerCase().endsWith('.zip')) {

      console.log('[Import][ZIP found] ' + JSON.stringify({
            relativePath: e.relativePath,
        fileName: e.fileHandle.name
      }, null, 2));

      zipHandles.push(e);
    }
  }

  // === SN 来自父目录名 ===
  const INVALID: string[] = [];
  const snToZips = new Map<string, string[]>();
  snToTs.clear(); // 清空时间戳聚合表

  for (const e of zipHandles) {
    const sn = extractSnFromZipFileName(e.fileHandle.name);

    console.log('[Import][SN parsed] ' + JSON.stringify({
          relativePath: e.relativePath,
          parsedSN: sn,
      isValid: isValidSn(sn)
    }, null, 2));

    if (!isValidSn(sn)) {
      console.warn('[Import][INVALID SN]' + JSON.stringify({
        relativePath: e.relativePath,
        parsedSN: sn,
        reason: 'Folder name not matching SN rule /^[A-Za-z][A-Za-z0-9]{9}$/'
      }, null,2));
      INVALID.push(e.relativePath);
    } else {
      const key = sn.toUpperCase();
      if (!snToZips.has(key)) snToZips.set(key, []);
      snToZips.get(key)!.push(e.relativePath);

      // 从“文件名”解析时间戳，并按 SN 聚合
      const ts = parseTimestampFromZipName(e.fileHandle.name);
      if (ts != null) {
        const bucket = snToTs.get(key) ?? [];
        bucket.push(ts);
        snToTs.set(key, bucket);
      }
    }
  }

  console.error('[Import][INVALID summary] ' + JSON.stringify({
    invalidCount: INVALID.length,
    invalidPaths: INVALID,
    note: 'ANY invalid ZIP causes immediate abort (current logic)'
  }, null, 2));

if (snToZips.size === 0) {
    loading.value = false;
    alert('No qualified SN was found, provide the data file again');
    return;
  }

  const SNs = Array.from(snToZips.keys());
  const newRecords: DbRecord[] = [];
  const logTypeDist: Record<string, number> = {};

  progressText.value = 'Getting data from PQAT...';

  for (let i = 0; i < SNs.length; i++) {
    const sn = SNs[i];

    console.log('[Import][SN Process Begin] ' + JSON.stringify({
      index: i,
      sn,
      zipCountForSN: snToZips.get(sn)?.length
    }, null, 2));

  progress.value = Math.round((i / SNs.length) * 100);

    const items = await downloadFromPQAT({
      eidUser: eidUser.value,
      eidKey: eidKey.value,
      serials: [sn],
      logType: 0,
      timeStrobe: 0
    });

    const logTypes = Array.from(new Set(items.map(x => normalizeLogType(x.level || ''))));

    // 先用 文件名解析得到的时间戳，再回退到 PQAT 的日期 与 时间 表示
    // 1) 文件名时间（优先，包含 时分秒）
    const nameTsList = (snToTs.get(sn) ?? []).filter(n => Number.isFinite(n)).sort((a, b) => a - b);

    // 2) PQAT 时间（可能只有日期，没有时间-时分秒）
    const pqDates = items
        .map(x => new Date(x.ts))
        .filter(d => !isNaN(d.getTime()))
        .sort((a, b) => a.getTime() - b.getTime());

    const firstFromPqat = pqDates.length ? pqDates[0].toISOString() : null;
    const lastFromPqat  = pqDates.length ? pqDates[pqDates.length - 1].toISOString() : null;

    // 3) 取最终值（优先文件名时间）
    let firstDate: string | null = null;
    let lastDate: string | null = null;

    // SN 情况 1：只有一个 ZIP 文件
    if ((snToZips.get(sn)?.length ?? 0) === 1) {
      if (nameTsList.length === 1) {
        const t = nameTsList[0];
        const iso = new Date(t).toISOString();
        firstDate = iso;
        lastDate = iso;
      } else {
        firstDate = firstFromPqat;
        lastDate = lastFromPqat;
      }
    }
    // SN 情况 2：多个 ZIP 文件
    else {
      const firstFromName = nameTsList.length ? new Date(nameTsList[0]).toISOString() : null;
      const lastFromName  = nameTsList.length ? new Date(nameTsList[nameTsList.length - 1]).toISOString() : null;

      firstDate = firstFromName ?? firstFromPqat;
      lastDate  = lastFromName  ?? lastFromPqat;
    }

    //从 zip 内容抽取 productName & subLogTypes（优先 ExtLog，其次 Proactive）
    const { productName, subLogTypes } = await extractProductAndSubLogsForSN(
        sn,
        snToZips.get(sn) || [],
        dirHandle.value!
    );

    for (const lt of logTypes) {
      logTypeDist[lt] = (logTypeDist[lt] || 0) + 1;
    }

    newRecords.push({
      serialNumber: sn,
      productName,
      firstDate,
      lastDate,
      logTypes,
      subLogTypes,
      zips: snToZips.get(sn) || []
    });
  }

  // 写入数据库文件
  await mergeAndWriteDb(dirHandle.value!, newRecords);
  await reloadFromDb();

  lastReport.value = {
    totalZips: zipHandles.length,
    uniqueSnCount: SNs.length,
    invalidSnCount: 0,
    pqatQueried: SNs.length,
    logTypeDist
  };

  progress.value = 100;
  progressText.value = 'Done';
  loading.value = false;
}

// ================== DB 读/写/合并 ==================
async function readDb(dir: FileSystemDirectoryHandle): Promise<DbFile> {
  try {
    const h = await dir.getFileHandle(DB_FILE_NAME, { create: false });
    const f = await h.getFile();
    return JSON.parse(await f.text());
  } catch {
    return { version: DB_VERSION, updatedAt: new Date().toISOString(), records: [] };
  }
}

async function writeDb(dir: FileSystemDirectoryHandle, db: DbFile) {
  // @ts-ignore
  const fh = await dir.getFileHandle(DB_FILE_NAME, { create: true });
  // @ts-ignore
  const w = await fh.createWritable();
  await w.write(JSON.stringify(db, null, 2));
  await w.close();
}

// === 合并逻辑使用 serialNumber 唯一键 ===
function mergeRecords(oldR: DbRecord[], newR: DbRecord[]): DbRecord[] {
  const m = new Map<string, DbRecord>();
  for (const r of oldR) m.set(r.serialNumber.toUpperCase(), { ...r });

  for (const n of newR) {
    const key = n.serialNumber.toUpperCase();
    if (!m.has(key)) {
      m.set(key, { ...n });
      continue;
    }
    const o = m.get(key)!;
    // 合并日期
    const f = [o.firstDate, n.firstDate].filter(Boolean).map(d => new Date(d!)).sort((a, b) => a.getTime() - b.getTime());
    const l = [o.lastDate, n.lastDate].filter(Boolean).map(d => new Date(d!)).sort((a, b) => a.getTime() - b.getTime());
    o.firstDate = f.length ? f[0].toISOString() : null;
    o.lastDate = l.length ? l[l.length - 1].toISOString() : null;
    // 合并 logTypes 与 zips
    o.logTypes = Array.from(new Set([...o.logTypes, ...n.logTypes]));
    o.zips = Array.from(new Set([...o.zips, ...n.zips]));
    // 合并 productName：优先新值（新为空则保留旧值）
    o.productName = n.productName ?? o.productName ?? null;
    // 合并 subLogTypes：并集
    o.subLogTypes = Array.from(new Set([...(o.subLogTypes ?? []), ...(n.subLogTypes ?? [])]));
    m.set(key, o);
  }

  return Array.from(m.values()).sort((a, b) =>
      a.serialNumber.localeCompare(b.serialNumber)
  );
}

async function mergeAndWriteDb(dir: FileSystemDirectoryHandle, newRecs: DbRecord[]) {
  const existing = await readDb(dir);
  const merged = mergeRecords(existing.records || [], newRecs);
  const db: DbFile = {
    version: DB_VERSION,
    updatedAt: new Date().toISOString(),
    records: merged
  };
  await writeDb(dir, db);
  return db;
}

// === 从 DB 读取表格 ===
async function reloadFromDb() {
  if (!dirHandle.value) return;
  const db = await readDb(dirHandle.value);
  tableRows.value = db.records.map((r: DbRecord) => ({
    serialNumber: r.serialNumber,
    productName: r.productName,
    firstDate: r.firstDate,
    lastDate: r.lastDate,
    logTypes: r.logTypes,
    subLogTypes: r.subLogTypes,
    zipCount: r.zips.length
  }));
}

// 选择并加载新 DB 文件
async function pickDbFile() {
  try {
    const [handle] = await (window as any).showOpenFilePicker({
      types: [
        {
          description: 'DeepLog DB File',
          accept: { 'application/json': ['.json'] }
        }
      ],
      multiple: false
    });

    await loadDbFromFileHandle(handle);
    showDbPicker.value = false;

  } catch (err) {
    console.warn('DB file pick cancelled or failed:', err);
  }
}

async function loadDbFromFileHandle(fileHandle: FileSystemFileHandle) {
  const file = await fileHandle.getFile();
  const json = JSON.parse(await file.text()) as DbFile;

  if (!json.records) {
    alert('No valid DeepLog DB file');
    return;
  }

  tableRows.value = json.records.map((r: DbRecord) => ({
    serialNumber: r.serialNumber,
    firstDate: r.firstDate,
    lastDate: r.lastDate,
    logTypes: r.logTypes,
    zipCount: r.zips.length
  }));
}

// ====================================================== 工具函数 ======================================================
async function* walkFiles(
    root: FileSystemDirectoryHandle,
    parent: string = ''
): AsyncGenerator<{ fileHandle: FileSystemFileHandle; relativePath: string }>
{
  for await (const entry of (root as any).values()) {
    if (entry.kind === 'file') {
      const rel = parent ? `${parent}/${entry.name}` : entry.name;
      yield { fileHandle: entry as FileSystemFileHandle, relativePath: rel };
    } else if (entry.kind === 'directory') {
      const dir = entry as FileSystemDirectoryHandle;
      const rel = parent ? `${parent}/${dir.name}` : dir.name;
      yield* walkFiles(dir, rel);
    }
  }
}

function isValidSn(sn: string): boolean {
  return /^[A-Za-z][A-Za-z0-9]{9}$/.test(sn);
}

function normalizeLogType(x: string): string {
  const s = x.toLowerCase();
  if (/proactive/.test(s)) return 'Proactive Logs';
  if (/extlog|ext log/.test(s)) return 'ExtLog';
  if (/site\s*failure/.test(s)) return 'Site Failure Note';
  if (/hws\s*scrap/.test(s)) return 'HWS Scrap Pictures';
  return x;
}

// 从 .zip 文件名解析时间戳（多格式）
function parseTimestampFromZipName(filename: string): number | null {
  const name = filename.trim();
  // 1) Proactive: *_YYYYMMDD_HHMMSS_...
  {
    const m = name.match(/_(\d{8})_(\d{6})(?!\d)/);
    if (m) {
      const y = m[1].slice(0, 4);
      const M = m[1].slice(4, 6);
      const d = m[1].slice(6, 8);
      const hh = m[2].slice(0, 2);
      const mm = m[2].slice(2, 4);
      const ss = m[2].slice(4, 6);
      const iso = `${y}-${M}-${d}T${hh}:${mm}:${ss}`;
      const t = new Date(iso).getTime();
      return isNaN(t) ? null : t;
    }
  }
  // 2) LAT/Return: YYYY-MM-DD_HH.MM.SS-*.zip
  {
    const m = name.match(/(\d{4}-\d{2}-\d{2})_(\d{2})\.(\d{2})\.(\d{2})/);
    if (m) {
      const [_, date, hh, mm, ss] = m;
      const iso = `${date}T${hh}:${mm}:${ss}`;
      const t = new Date(iso).getTime();
      return isNaN(t) ? null : t;
    }
  }
  // 3) LAT/Return: *_YYYY-MM-DD HH.MM.SS - *.zip
  {
    const m = name.match(/(\d{4}-\d{2}-\d{2})\s+(\d{2})\.(\d{2})\.(\d{2})/);
    if (m) {
      const [_, date, hh, mm, ss] = m;
      const iso = `${date}T${hh}:${mm}:${ss}`;
      const t = new Date(iso).getTime();
      return isNaN(t) ? null : t;
    }
  }
  // TODO: 新格式继续在此追加
  return null;
}

// 将 ISO 字符串（UTC）格式化为 "YYYY-MM-DD HH:mm:ss"（本地时间）
function formatIsoToLocal(iso: string | null | undefined): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return '';

  const pad = (n: number) => String(n).padStart(2, '0');
  const yyyy = d.getFullYear();
  const MM = pad(d.getMonth() + 1);
  const dd = pad(d.getDate());
  const HH = pad(d.getHours());
  const mm = pad(d.getMinutes());
  const ss = pad(d.getSeconds());

  return `${yyyy}-${MM}-${dd} ${HH}:${mm}:${ss}`;
}

// 从 zip 文件名自动提取 SN（字母开头 + 9位字母数字）
function extractSnFromZipFileName(fileName: string): string {
  const m = fileName.match(/^([A-Za-z][A-Za-z0-9]{9})/);
  return m ? m[1] : '';
}

// 抓取日志文件中的 productName 和 subLogTypes 信息
/** 解析一个 SN 的 zip，抽取 productName/subLogTypes
 *  优先 ExtLog（非 *_logfiles.zip），否则 Proactive（*_logfiles.zip）
 */
// ====== 判断是否 proactive 命名（*_YYYYMMDD_HHMMSS_logfiles.zip）======
function isProactiveZip(name: string): boolean {
  return /_\d{8}_\d{6}_[Ll]ogfiles\.zip$/i.test(name);
}

// ====== 从 entries 里汇总我们关心的子日志类型（elog/hwlog/llog/telog/lmclist）======
const SUBLOG_WHITELIST = new Set(['elog', 'hwlog', 'llog', 'telog', 'lmclist']);

// ====== 从 entries 中提取子日志（已按 zipExtractor 的 normalizeLogType() 归一化）======
function pickSubLogsFromEntries(entries: Array<{ log_type?: string }>): string[] {
  const set = new Set<string>();
  for (const e of entries) {
    const t = (e.log_type || '').toLowerCase();
    if (SUBLOG_WHITELIST.has(t)) set.add(t);
  }
  return Array.from(set);
}

// ===== 工具：从 entries 中挑 ProductName（取出现频次最高的非空值）=====
function pickProductName(entries: Array<{ ProductName?: string | null }>): string | null {
  const vals = entries.map(e => (e.ProductName || '').trim()).filter(Boolean);
  if (vals.length === 0) return null;
  const freq = new Map<string, number>();
  for (const v of vals) freq.set(v, (freq.get(v) || 0) + 1);
  let best = vals[0]; let max = 0;
  for (const [k, c] of freq) { if (c > max) { max = c; best = k; } }
  return best || null;
}

/**
 * 解析 SN：逐个 zip 尝试
 * - ExtLog（非 *_logfiles.zip）：CMD folder 下命中 parget/*read 即停止
 * - Proactive（*_logfiles.zip）：
 *    A) ProductName：逐包全文搜索 SYS_HW_MARKET_NAME，命中即停止
 *    B) SubLogTypes：对每包 extractFromZip(entries)，仅保留 entries.Serial === SN 的条目统计子日志并集
 * - 若 A 与 B 都满足（找到了 productName 且 subLogTypes 非空）→ 立即停止
 */
async function extractProductAndSubLogsForSN(
    sn: string,
    zipRelPaths: string[],
    root: FileSystemDirectoryHandle
): Promise<{ productName: string | null; subLogTypes: string[] }> {
  if (!zipRelPaths.length) return { productName: null, subLogTypes: [] };

  const snUpper = sn.toUpperCase();
  const extLogs = zipRelPaths.filter(p => !isProactiveZip(p)).sort();
  const proLogs = zipRelPaths.filter(p =>  isProactiveZip(p)).sort();

  // -------- Step 1: ExtLog 优先，命中即停 --------
  for (const rel of extLogs) {
    try {
      const fh = await resolveFileHandleByPath(root, rel);
      const file = await fh.getFile();
      const { kind, entries } = await extractFromZip(file); // return/entries from zipExtractor

      const pName = pickProductName(entries);     // parget.txt -> SYS_HW_MARKET_NAME
      const subLogs = pickSubLogsFromEntries(entries);

      console.debug('[Extract][ExtLog]', { sn, rel, kind, entriesCount: entries.length, productName: pName, subLogs });

      if (pName || subLogs.length > 0) {
        console.debug('[Extract][ExtLog Hit]', { sn, rel, productName: pName, subLogTypes: subLogs });
        return { productName: pName, subLogTypes: subLogs };
      }
    } catch (e) {
      console.warn('[Extract][ExtLog Error]', { sn, rel, error: (e as Error)?.message || e });
    }
  }

  // -------- Step 2: Proactive 其次，命中即停 --------
  let proProductName: string | null = null;
  let proSubLogs: string[] = []; // 并集

  for (const rel of proLogs) {
    try {
      const fh = await resolveFileHandleByPath(root, rel);
      const file = await fh.getFile();

      // 2A) productName：逐包全文搜索 SYS_HW_MARKET_NAME
      if (!proProductName) {
        const zip = await JSZip.loadAsync(file);
        const files = Object.values(zip.files).filter(f => !f.dir);

        for (const f of files) {
          const base = f.name.toLowerCase();
          // 仅看文本类，避免大二进制
          if (!base.endsWith('.txt') && !base.endsWith('.log')) continue;

          const text = await f.async('text');
          // 兼容 'SYS_HW_MARKET_NAME' = 'Radio 4471HP B3' / SYS_HW_MARKET_NAME = Radio 4471HP B3
          // 带引号：
          let m = text.match(/['"]?SYS_HW_MARKET_NAME['"]?\s*=\s*['"]([^'"]+)['"]/i);
          if (m && m[1]) {
            proProductName = m[1].trim();
            console.debug('[Extract][Proactive ProductName Found]', { sn, rel, file: f.name, value: proProductName });
            break; // 本包已命中，后续文件无需再扫
          }
          // 无引号：
          m = text.match(/\bSYS_HW_MARKET_NAME\b\s*=\s*([^\r\n]+)/i);
          if (m && m[1]) {
            proProductName = m[1].trim();
            console.debug('[Extract][Proactive ProductName Found(NoQuotes)]', { sn, rel, file: f.name, value: proProductName });
            break;
          }
        }
      }

      // 2B) 从 zipExtractor 拿 entries[*].LNH
      const { entries } = await extractFromZip(file);

      // —— 2B-1：从 SDIC 对齐后的 entries 中，收集“当前 SN 对应的 LNH 集合”
      const lnhSet = new Set(
          entries
              .filter(e => (e.Serial || '').toUpperCase() === snUpper && (e.LNH || '').trim() !== '')
              .map(e => (e.LNH as string).trim())
      );

      console.debug('[Extract][Proactive LNH Set]', { sn, rel, lnhs: Array.from(lnhSet) });

      // 如果 SDIC 没把 SN 映射到任何 LNH，则该包无法提供该 SN 的子日志
      if (lnhSet.size === 0) {
        console.debug('[Extract][Proactive No LNH for SN]', { sn, rel });
      } else {
        // —— 2B-2：仅针对 lnhSet 中的 LNH 判断 5 类子日志是否存在
        const have = new Set<string>();
        for (const t of SUBLOG_WHITELIST) {
          const hit = entries.some(e =>
              (e.log_type || '').toLowerCase() === t &&
              !!e.LNH && lnhSet.has(e.LNH.trim())
          );
          if (hit) have.add(t);
        }

        if (have.size > 0) {
          // 并集（多个 proactive 包）
          proSubLogs = Array.from(new Set([...proSubLogs, ...Array.from(have)]));
          console.debug('[Extract][Proactive SubLogs Hit]', { sn, rel, subLogTypes: Array.from(have) });
        }
      }

      // 2C）已经拿到 productName 且 subLogTypes 非空 → 直接返回
      if (proProductName && proSubLogs.length > 0) {
        console.debug('[Extract][Proactive Hit]', { sn, rel, productName: proProductName, subLogTypes: proSubLogs });
        return { productName: proProductName, subLogTypes: proSubLogs };
      }
    } catch (e) {
      console.warn('[Extract][Proactive Error]', { sn, rel, error: (e as Error)?.message || e });
    }
  }

  // -------- Step 3: 结束条件 --------
  if (proProductName || proSubLogs.length > 0) {
    console.debug('[Extract][Proactive Final]', { sn, productName: proProductName, subLogTypes: proSubLogs });
  } else {
    console.debug('[Extract][Proactive MissAll]', { sn });
  }
  return { productName: proProductName, subLogTypes: proSubLogs };
}


// ====== [若你的文件中还没有该方法，请保留；已有则不动] 通过相对路径获取文件句柄 ======
async function resolveFileHandleByPath(
    root: FileSystemDirectoryHandle,
    relPath: string
): Promise<FileSystemFileHandle> {
  const segs = relPath.split(/[/\\]+/).filter(Boolean);
  let dir = root;
  for (let i = 0; i < segs.length - 1; i++) {
    dir = await dir.getDirectoryHandle(segs[i], { create: false });
  }
  return await dir.getFileHandle(segs[segs.length - 1], { create: false });
}

</script>

<style scoped>
.row { display: flex; width: 100%; }
.parsed-box {
  margin-top: 20px;
  padding: 16px;
  background: var(--bg-2);
  border-radius: 6px;
}
.table-box {
  margin-top: 20px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}
.table-toolbar {
  display: flex;
  align-items: center;
}

/* ========== 深色主题下设置白底表格对应的深色字体 ========== */
:deep(.el-table) {
  --el-table-bg-color: #ffffff;
  --el-table-text-color: #1a1a1a;
  --el-table-row-hover-bg-color: #f5f7fa;
  color: #1a1a1a !important;
}
:deep(.el-table td) {
  color: #1a1a1a !important;
}
:deep(.el-table thead th) {
  background-color: var(--bg-1) !important;
  color: #ffffff !important;
  font-weight: 600;
}
:deep(.el-table thead th .cell) {
  color: #ffffff !important;
}
:deep(.el-table__column-resize-proxy) {
  background-color: #ffffff !important;
}
</style>
