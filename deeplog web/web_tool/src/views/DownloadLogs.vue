<template>

  <el-page-header
      :content="String($t('downloadLogPage.title'))"
      @back="$router.push({ name: 'dashboard' })"
  />

  <!-- 1) 下载 PQAT 样本日志 -->
  <div class="deeplog-card" style="margin-top:16px">
    <h3>{{ $t('downloadLogPage.download') }}</h3>
    <p class="desc">{{ $t('downloadLogPage.downloadDesc') }}</p>

    <el-form :model="form" label-width="140px" class="form" @submit.prevent>
      <el-form-item :label="$t('downloadLogPage.eidUser') as string">
        <el-input v-model="form.eidUser" autocomplete="username" placeholder="e.g., erid12345" />
      </el-form-item>

      <el-form-item :label="$t('downloadLogPage.eidKey') as string">
        <el-input v-model="form.eidKey" type="password" autocomplete="current-password" show-password />
      </el-form-item>

      <el-form-item :label="$t('downloadLogPage.serialNumber') as string">
        <el-input
            v-model="form.serialsText"
            type="textarea"
            :rows="4"
            placeholder="支持多行或逗号分隔，如：&#10;CN38699365&#10;TU8U02GTHS"
        />
      </el-form-item>

      <el-form-item :label="$t('downloadLogPage.logType')">
        <el-select v-model="form.logType" style="min-width: 240px">
          <el-option :label="'All (0)'" :value="0" />
          <el-option :label="'ExtLog (1)'" :value="1" />
          <el-option :label="'Site Failure Note (2)'" :value="2" />
          <el-option :label="'Proactive Logs (3)'" :value="3" />
          <el-option :label="'HWS Scrap Pictures (4)'" :value="4" />
        </el-select>
      </el-form-item>

      <el-form-item :label="$t('downloadLogPage.logTimeWindow')">
        <el-radio-group v-model="form.timeStrobe">
          <el-radio :value="0">All</el-radio>
          <el-radio :value="-1">Latest</el-radio>
        </el-radio-group>
        <el-input-number
            v-model="form.timeCount"
            :min="1"
            :step="1"
            controls-position="right"
            style="margin-left:16px; width: 160px"
            :placeholder="'N (可选)'"
        />
        <span class="hint">{{ $t('downloadLogPage.timeHint') }}</span>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" :loading="downloading" @click="onDownload">
          {{ $t('downloadLogPage.downloadBtn') }}
        </el-button>

        <!-- 批量下载 -->
        <el-space style="margin-left:16px">
          <el-checkbox v-model="bulkBySn">
            {{ $t('downloadLogPage.bySn') }}
          </el-checkbox>

          <el-select v-model="bulkMode" style="min-width: 200px">
            <el-option :label="$t('downloadLogPage.modeZip')" value="zip" />
            <el-option :label="$t('downloadLogPage.modeDir')" value="dir" />
          </el-select>

          <el-button
              type="success"
              :disabled="!rows.length"
              :loading="bulkLoading"
              @click="onDownloadAll"
          >
            {{ $t('downloadLogPage.downloadAll') }}
          </el-button>
        </el-space>
      </el-form-item>

      <!-- 批量下载进度 -->
      <div v-if="bulkLoading" class="bulk-progress">
        <el-progress :percentage="bulkPercent" :text-inside="true" :stroke-width="18" />
        <div class="progress-line">
          <span>{{ $t('downloadLogPage.progress') }}: {{ progress.done }}/{{ progress.total }}</span>
          <span v-if="progress.current" style="margin-left:12px">{{ progress.current }}</span>
        </div>
      </div>
    </el-form>

    <!-- 表格 -->
    <el-table v-if="rows.length" :data="rows" height="280" size="small" style="margin-top:12px">
      <el-table-column prop="date" label="Date" width="180" />
      <el-table-column prop="sn" label="SN" width="160" />
      <el-table-column prop="logType" label="Log Type" width="200" />
      <el-table-column prop="fileId" label="File ID" width="140" />

      <el-table-column label="Actions" width="140">
        <template #default="{ row }">
          <el-button size="small" @click="onDownloadFile(row)">下载</el-button>
        </template>
      </el-table-column>

      <el-table-column prop="url" label="URL" />
    </el-table>

    <el-empty v-else :description="$t('downloadLogPage.placeholder1')" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import { ElMessage } from 'element-plus';
import { downloadFromPQAT, downloadFileById, fetchFileById, isDirectoryPickerAvailable } from '@/api/pqat';

const form = ref({
  eidUser: '',
  eidKey: '',
  serialsText: '',
  logType: 0 as 0 | 1 | 2 | 3 | 4,
  timeStrobe: 0 as number,
  timeCount: undefined as number | undefined
});

type Row = {
  date: string;
  sn: string;
  logType: string;
  fileId: string;
  url: string;
};

const rows = ref<Row[]>([]);
const downloading = ref(false);

// ---------------- 批量下载状态 ----------------
const bulkBySn = ref(true);
const bulkMode = ref<'zip' | 'dir'>('zip');
const bulkLoading = ref(false);
const progress = ref({ total: 0, done: 0, current: '' });
const bulkPercent = computed(() =>
    progress.value.total ? Math.min(100, Math.round((progress.value.done * 100) / progress.value.total)) : 0
);

// ---------------- 获取列表 ----------------
async function onDownload() {
  const serials = normalizeSerials(form.value.serialsText);
  if (!serials.length) return ElMessage.warning('请输入至少一个序列号');
  if (!form.value.eidUser || !form.value.eidKey) return ElMessage.warning('请输入 EID 与 Key');

  downloading.value = true;
  try {
    const tsParam = resolveTimeStrobe(form.value.timeStrobe, form.value.timeCount);
    const entries = await downloadFromPQAT({
      eidUser: form.value.eidUser,
      eidKey: form.value.eidKey,
      serials,
      logType: form.value.logType,
      timeStrobe: tsParam
    });

    rows.value = entries.map(toRow).filter(Boolean) as Row[];
    if (!rows.value.length) ElMessage.info('未获取到可下载条目');
  } catch (e: any) {
    ElMessage.error(e?.message || '下载失败');
  } finally {
    downloading.value = false;
  }
}

// ---------------- 单条下载 ----------------
async function onDownloadFile(row: Row) {
  try {
    await downloadFileById(form.value.eidUser, form.value.eidKey, row.fileId, row.sn);
  } catch (e) {
    ElMessage.error('文件下载失败');
  }
}

// ---------------- 批量下载入口 ----------------
async function onDownloadAll() {
  if (!rows.value.length) {
    ElMessage.warning('请先生成可下载列表');
    return;
  }

  // 目录模式校验
  if (bulkMode.value === 'dir' && !isDirectoryPickerAvailable()) {
    ElMessage.info('当前浏览器不支持目录保存，已自动切换 ZIP 打包下载');
    bulkMode.value = 'zip';
  }

  bulkLoading.value = true;
  progress.value = { total: rows.value.length, done: 0, current: '' };

  try {
    if (bulkBySn.value) {
      // 按 SN 分组
      const groups = groupBySn(rows.value);
      if (bulkMode.value === 'dir') {
        await downloadAllToDirectory(groups);
      } else {
        await downloadAllToZip(groups);
      }
    } else {
      // 不分组
      if (bulkMode.value === 'dir') {
        const root = await (window as any).showDirectoryPicker();
        await downloadFlatToDirectory(root, rows.value);
      } else {
        await downloadFlatToZip(rows.value);
      }
    }
    ElMessage.success('批量下载完成');
  } catch (e: any) {
    console.error(e);
    ElMessage.error(e?.message || '批量下载失败');
  } finally {
    bulkLoading.value = false;
  }
}

// ---------------- ZIP：按 SN 分组 → 一个 ZIP（多子目录） ----------------
async function downloadAllToZip(groups: Record<string, Row[]>) {
  const zip = new JSZip();
  const sns = Object.keys(groups);

  for (const sn of sns) {
    const folder = zip.folder(sn) as JSZip;
    const items = groups[sn];

    await forEachLimit(items, 4, async (row) => {
      progress.value.current = `${sn} / #${row.fileId}`;
      const { blob, filename } = await fetchFileById(form.value.eidUser, form.value.eidKey, row.fileId);
      const safeName = toSafeFileName(row, filename);
      folder.file(safeName, blob);
      progress.value.done += 1;
    });
  }

  progress.value.current = '打包中...';
  const zipBlob = await zip.generateAsync({ type: 'blob' });
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '');
  saveAs(zipBlob, `pqat_logs_${ts}.zip`);
}

// ---------------- ZIP：不分组 → 一个 ZIP（根目录平铺） ----------------
async function downloadFlatToZip(list: Row[]) {
  const zip = new JSZip();

  await forEachLimit(list, 4, async (row) => {
    progress.value.current = `#${row.fileId}`;
    const { blob, filename } = await fetchFileById(form.value.eidUser, form.value.eidKey, row.fileId);
    const safeName = toSafeFileName(row, filename);
    zip.file(safeName, blob);
    progress.value.done += 1;
  });

  progress.value.current = '打包中...';
  const zipBlob = await zip.generateAsync({ type: 'blob' });
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '');
  saveAs(zipBlob, `pqat_logs_${ts}.zip`);
}

// ---------------- 目录：按 SN 分组 → 保存到目录 ----------------
async function downloadAllToDirectory(groups: Record<string, Row[]>) {
  const root: FileSystemDirectoryHandle = await (window as any).showDirectoryPicker();

  for (const [sn, items] of Object.entries(groups)) {
    const snDir = await root.getDirectoryHandle(sn || 'UNKNOWN_SN', { create: true });

    await forEachLimit(items, 3, async (row) => {
      progress.value.current = `${sn} / #${row.fileId}`;
      const { blob, filename } = await fetchFileById(form.value.eidUser, form.value.eidKey, row.fileId);
      const safeName = toSafeFileName(row, filename);

      const fileHandle = await snDir.getFileHandle(safeName, { create: true });
      const writer = await fileHandle.createWritable();
      await writer.write(blob);
      await writer.close();
      progress.value.done += 1;
    });
  }
}

// ---------------- 目录：不分组 → 保存到目录 ----------------
async function downloadFlatToDirectory(root: FileSystemDirectoryHandle, list: Row[]) {
  await forEachLimit(list, 3, async (row) => {
    progress.value.current = `#${row.fileId}`;
    const { blob, filename } = await fetchFileById(form.value.eidUser, form.value.eidKey, row.fileId);
    const safeName = toSafeFileName(row, filename);

    const fileHandle = await root.getFileHandle(safeName, { create: true });
    const writer = await fileHandle.createWritable();
    await writer.write(blob);
    await writer.close();
    progress.value.done += 1;
  });
}

// ---------------- 工具：按 SN 分组 ----------------
function groupBySn(list: Row[]): Record<string, Row[]> {
  const map: Record<string, Row[]> = {};
  for (const r of list) {
    const key = r.sn || 'UNKNOWN_SN';
    if (!map[key]) map[key] = [];
    map[key].push(r);
  }
  return map;
}

// ---------------- 工具：构造安全文件名（SN_前缀） ----------------
function toSafeFileName(row: Row, origin?: string): string {
  const sanitize = (s?: string) => (s || '').replace(/[\\/:*?"<>|]+/g, '_');

  const sn = sanitize(row.sn) || 'SN';
  const base = sanitize(origin);
  const fid = sanitize(row.fileId) || 'id';
  const log = sanitize(row.logType) || 'Log';
  const dateShort = row.date ? row.date.slice(0, 19).replace(/[:T]/g, '') : '';

  const fallback = `${log}__${dateShort}__#${fid}`;
  const nameWithoutSn = base || fallback;
  return `${sn}_${nameWithoutSn}`;
}

// ---------------- 工具：并发限制 ----------------
async function forEachLimit<T>(
    items: T[],
    limit: number,
    worker: (item: T, index: number) => Promise<void>
) {
  const queue = [...items].entries();
  const running: Promise<void>[] = [];

  async function runOne(entry: IteratorResult<[number, T]>) {
    if (entry.done) return;
    const [idx, it] = entry.value;
    await worker(it, idx);
    const next = queue.next();
    if (!next.done) {
      await runOne(next);
    }
  }

  for (let i = 0; i < Math.min(limit, items.length); i++) {
    running.push(runOne(queue.next()));
  }
  await Promise.all(running);
}

// ---------------- 其他工具 ----------------
function normalizeSerials(t: string): string[] {
  return [...new Set(t.split(/[\n,;，；\s]+/g).map(s => s.trim()).filter(Boolean))];
}

function resolveTimeStrobe(base: number, n?: number) {
  return base === -1 ? -1 : n && n > 0 ? n : 0;
}

function toRow(e: any): Row {
  const sn = (e.text.split(' - ')[0] || '').trim();
  const log = (e.text.split(' - ')[1] || '').trim();
  const id = e.text.match(/#(\d+)/)?.[1] || '';
  const iso = safeToIso(e.ts);
  return { date: iso, sn, logType: log, fileId: id, url: e.raw || '' };
}

function safeToIso(ts: string): string {
  const t = new Date(ts);
  return isNaN(t.getTime()) ? '' : t.toISOString();
}
</script>

<style scoped>
.desc { color: var(--text-2); margin: 2px 0 12px; }
.form { max-width: 820px; }
.hint { color: var(--text-2); margin-left: 12px; }

.bulk-progress { margin-top: 12px; max-width: 640px; }
.progress-line { font-size: 12px; margin-top: 6px; color: var(--text-2); }

/* 表格文字颜色修复，使字体偏深 */
:deep(.el-table) {
  --el-table-text-color: var(--text-2);
  --el-table-header-text-color: var(--text-2);
}
:deep(.el-table__row td) { color: #000 !important; }
</style>
