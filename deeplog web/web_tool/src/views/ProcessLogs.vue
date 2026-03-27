<template>
  <el-page-header
      :content="String($t('processLogPage.processLogs.title'))"
      @back="$router.push({ name: 'dashboard' })"
  />

  <!-- 选择待处理文件 -->
  <div class="deeplog-card" style="margin-top:16px">
    <h3>{{ $t('processLogPage.processLogs.source.title') }}</h3>
    <p class="desc">{{ $t('processLogPage.processLogs.source.desc') }}</p>

    <el-space wrap>
      <el-radio-group v-model="sourceMode">
        <el-radio label="files">{{ $t('processLogPage.processLogs.source.files') }}</el-radio>
        <el-radio label="folders">{{ $t('processLogPage.processLogs.source.folders') }}</el-radio>
      </el-radio-group>

      <!-- 选择 zip 文件 -->
      <el-upload
          v-if="sourceMode === 'files'"
          drag
          multiple
          :auto-upload="false"
          :show-file-list="false"
          :on-change="onFilesPicked"
          accept=".zip"
          style="width: 520px"
      >
        <i class="el-icon--upload el-icon">
          <svg viewBox="0 0 1024 1024" width="22" height="22">
            <path d="M512 64l256 256h-160v256h-192V320H256L512 64zM192 704h640v192H192V704z" fill="currentColor"></path>
          </svg>
        </i>
        <div class="el-upload__text">
          {{ $t('processLogPage.processLogs.source.dropOrClick') }}
          <em>{{ $t('processLogPage.processLogs.source.chooseFiles') }}</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">{{ $t('processLogPage.processLogs.source.filesTip') }}</div>
        </template>
      </el-upload>

      <!-- 选择文件夹（自动包含下面所有的 zip 文件） -->
      <div v-else>
        <el-button type="primary" @click="onPickFolder">
          {{ $t('processLogPage.processLogs.source.addFolder') }}
        </el-button>
        <el-button @click="clearFolders" :disabled="!dirHandles.length">
          {{ $t('processLogPage.processLogs.source.clearFolders') }}
        </el-button>
        <span class="hint" style="margin-left:12px">
          <el-tag v-if="!dirPickerSupported" type="warning" effect="plain" size="small">
            {{ $t('processLogPage.processLogs.source.dirNotSupported') }}
          </el-tag>
          <template v-else>
            {{ $t('processLogPage.processLogs.source.folderCount', { n: dirHandles.length }) }}
          </template>
        </span>
      </div>
    </el-space>


    <!-- Radio 类型选择 -->
    <div style="margin-top: 12px">
      <el-form-item :label="$t('processLogPage.processLogs.source.radioType')">
        <el-tooltip
            placement="right"
            effect="dark"
        >
          <!-- tooltip 内容（支持换行） -->
          <template #content>
            <div style="white-space: pre-line; max-width: 260px">
              {{ $t('processLogPage.processLogs.source.radioTypeTips') }}
            </div>
          </template>

          <!-- 下拉选择框 -->
          <el-select
              v-model="radioType"
              style="width: 240px"
              :disabled="running"
          >
            <el-option label="Remote" value="Remote" />
            <el-option label="AAS AIR6449" value="AAS AIR6449" />
          </el-select>
        </el-tooltip>
      </el-form-item>
    </div>


    <!-- 选择后的摘要 -->
    <div class="chosen" v-if="sourceMode==='files' ? files.length : dirHandles.length">
      <template v-if="sourceMode==='files'">
        <div class="sum-row">
          <strong>{{ $t('processLogPage.processLogs.source.filesChosen', { n: files.length }) }}</strong>
          <el-link v-if="files.length" type="primary" @click="clearFiles">
            {{ $t('processLogPage.common.clear') }}
          </el-link>
        </div>
        <ul class="list">
          <li v-for="f in files" :key="f.name + f.size">{{ f.name }}</li>
        </ul>
      </template>

      <template v-else>
        <div class="sum-row">
          <strong>{{ $t('processLogPage.processLogs.source.foldersChosen', { n: dirHandles.length }) }}</strong>
        </div>
        <ul class="list">
          <li v-for="(h, idx) in dirHandles" :key="idx">{{ folderLabels[idx] }}</li>
        </ul>
      </template>
    </div>
  </div>

  <!-- 处理结果 -->
  <div class="deeplog-card" style="margin-top:16px">
    <h3>{{ $t('processLogPage.processLogs.result.title') }}</h3>
    <p class="desc">{{ $t('processLogPage.processLogs.result.desc') }}</p>

    <el-space wrap>
      <el-button @click="chooseOutputDir" :disabled="!dirPickerSupported">
        {{ $t('processLogPage.processLogs.result.chooseOutputDir') }}
      </el-button>
      <span class="hint" v-if="outputDirLabel" style="margin-left:8px">
        {{ $t('processLogPage.processLogs.result.outputDirLabel') }}：<strong>{{ outputDirLabel }}</strong>
      </span>

      <div class="concurrency-field">
        <el-input-number
            v-model="concurrency"
            :min="1"
            :max="6"
            :step="1"
            :disabled="running"
            class="concurrency-input"
        />
        <span class="concurrency-help">
          {{ $t('processLogPage.processLogs.result.concurrencyDesc') }}
        </span>
      </div>

      <el-button type="primary" :disabled="!canRun" :loading="running" @click="onProcess">
        {{ $t('processLogPage.processLogs.result.onProcess') }}
      </el-button>
      <el-button type="danger" :disabled="!running" @click="onCancel">
        {{ $t('processLogPage.processLogs.result.onCancel') }}
      </el-button>
    </el-space>

    <!-- 进度 -->
    <div v-if="running || progress.total" class="bulk-progress">
      <el-progress :percentage="progressPercent" :text-inside="true" :stroke-width="18" />
      <div class="progress-line">
        <span>{{ $t('processLogPage.processLogs.result.progress') }}：{{ progress.done }}/{{ progress.total }}</span>
        <span v-if="progress.current" style="margin-left:12px">{{ progress.current }}</span>
      </div>
      <div class="progress-line">
        <span>{{ $t('processLogPage.processLogs.result.outFiles') }}：{{ outFiles }}</span>
        <span v-if="skipped" style="margin-left:12px;">{{ $t('processLogPage.processLogs.result.skip') }}：{{ skipped }}</span>
      </div>
    </div>
  </div>

  <!-- 执行日志 -->
  <div class="deeplog-card" v-if="messages.length" style="margin-top:16px">
    <h3>{{ $t('processLogPage.processLogs.result.eventLog') }}</h3>
    <ul class="list exec-log">
      <li v-for="(m, i) in messages" :key="i">{{ m }}</li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { ElMessage } from "element-plus";
import JSZip from "jszip";


// =====================================================================================================================
/* ------------------------------------------------ 第一部分：待处理文件 ------------------------------------------------ */
// =====================================================================================================================
/* -------------------- 待处理源文件选择 -------------------- */
type SourceMode = "files" | "folders";
const sourceMode = ref<SourceMode>("files");

const files = ref<File[]>([]);
const dirHandles = ref<FileSystemDirectoryHandle[]>([]);
const folderLabels = ref<string[]>([]);

const dirPickerSupported = typeof (window as any).showDirectoryPicker === "function";

function onFilesPicked(evt: any) {
  const f = evt?.raw as File | undefined;
  if (!f) return;
  if (!f.name.toLowerCase().endsWith(".zip")) {
    ElMessage.warning("Now only support .zip file processing");
    return;
  }
  files.value.push(f);

  radioType.value = '';
}

function clearFiles() { files.value = []; }

async function onPickFolder() {
  if (!dirPickerSupported) {
    ElMessage.warning("Browser doesn't support this directory");
    return;
  }
  try {
    const h = await (window as any).showDirectoryPicker();
    dirHandles.value.push(h);
    // @ts-ignore
    folderLabels.value.push((h as any).name || "Folder");
  } catch {}

  radioType.value = '';
}

function clearFolders() { dirHandles.value = []; folderLabels.value = []; }

/* -------------------- 支持处理 Radio 类型声明 -------------------- */
type RadioType = '' | 'Remote' | 'AAS AIR6449'
const radioType = ref<RadioType>('');

/* -------------------- 输出目录选择 -------------------- */
const outputDir = ref<FileSystemDirectoryHandle | null>(null);
const outputDirLabel = ref("");

async function chooseOutputDir() {
  if (!dirPickerSupported) {
    ElMessage.warning("Browser doesn't support writing to this directory");
    return;
  }
  try {
    const h = await (window as any).showDirectoryPicker();
    outputDir.value = h;
    // @ts-ignore
    outputDirLabel.value = (h as any).name || "(Chosen directory)";
  } catch {}
}

/* -------------------- 状态反馈 -------------------- */
const running = ref(false);
const cancelRequested = ref(false);
const concurrency = ref<number>(3);
const progress = ref({ total: 0, done: 0, current: "" });

const progressPercent = computed(() => {
  if (!progress.value.total) return 0;
  return Math.round((progress.value.done * 100) / progress.value.total);
});

const outFiles = ref(0);
const skipped = ref(0);
const messages = ref<string[]>([]);

const canRun = computed(
    () =>
        (sourceMode.value === "files"
            ? files.value.length > 0
            : dirHandles.value.length > 0) && !running.value
);

/* -------------------- 遍历目录中的 ZIP -------------------- */
async function* walkZipFilesFromDir(dir: FileSystemDirectoryHandle): AsyncGenerator<File> {
  // @ts-ignore
  for await (const [, handle] of (dir as any).entries()) {
    if ((handle as any).kind === "file") {
      const f: File = await (handle as any).getFile();
      if (f.name.toLowerCase().endsWith(".zip")) yield f;
    } else if ((handle as any).kind === "directory") {
      yield* walkZipFilesFromDir(handle as FileSystemDirectoryHandle);
    }
  }
}

async function collectZips(): Promise<File[]> {
  const out: File[] = [];
  for (const h of dirHandles.value) {
    for await (const f of walkZipFilesFromDir(h)) out.push(f);
  }
  return out;
}

/* -------------------- ZIP 中的 .log -------------------- */
async function readFirstLogText(zip: JSZip): Promise<{ name: string; text: string } | null> {
  const entries = Object.values(zip.files);
  const hit = entries.find((f) => !f.dir && f.name.toLowerCase().endsWith(".log"));
  if (!hit) return null;
  const text = await hit.async("text");
  return { name: hit.name, text };
}

/* -------------------- 并发控制 (Concurrency) -------------------- */
async function forEachLimit<T>(
    items: T[],
    limit: number,
    worker: (item: T, idx: number) => Promise<void>
): Promise<void> {
  const it = items.entries();
  const pool: Promise<void>[] = [];
  async function runOne(next: IteratorResult<[number, T]>): Promise<void> {
    if (next.done) return;
    const [idx, val] = next.value;
    await worker(val, idx);
    await runOne(it.next());
  }
  for (let i = 0; i < Math.min(limit, items.length); i++) {
    pool.push(runOne(it.next()));
  }
  await Promise.all(pool);
}


// =====================================================================================================================
/* ------------------------------------------------- 第二部分：文件处理 ------------------------------------------------- */
// =====================================================================================================================


// =====================================================================================================================
//                                        一. 通用工具函数 (for both LAT and Proactive)
// =====================================================================================================================
/* -------------------- 把文本按“行”切分成字符串数组，兼容 Windows / Linux 换行符 -------------------- */
function toLines(text: string): string[] {
  return text.split(/\r?\n/);
}

/* -------------------- 把任意字符串转换成“可以安全嵌入正则表达式的字面量字符串” -------------------- */
function escapeRe(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

/* -------------------- 通用 grep：返回 “行号: 原文” 支持持正则匹配 -------------------- */
function grepWithLineno(lines: string[], re: RegExp): string[] {
  const out: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    const s = lines[i];
    if (re.test(s)) out.push(`${i + 1}: ${s}`);
  }
  return out;
}

/* -------------------- 通用 File System 工具 -------------------- */
// 在给定的根目录 root 下，确保子目录 sub 存在
async function ensureDir(root: FileSystemDirectoryHandle, sub: string): Promise<FileSystemDirectoryHandle> {
  return await root.getDirectoryHandle(sub, { create: true });
}

// 在指定目录下，创建或覆盖一个文本文件，将字符串内容写入文件，并统计输出文件数量
async function writeTextFile(
    dir: FileSystemDirectoryHandle,
    name: string,
    content: string,
    bom = false
): Promise<void> {
  const fh = await dir.getFileHandle(name, { create: true });
  const w = await fh.createWritable();
  if (bom) await w.write("\uFEFF");
  await w.write(content);
  await w.close();
  outFiles.value++;
}

/* -------------------- 当内容非空时，拼装一个有标题的段 - 关键字所在行 -------------------- */
function buildKeywordLineSection(title: string, items: string[]): string {
  if (!items.length) return '';
  return [
    '===================================================================================================================',
    title,
    '===================================================================================================================',
    ...items,
    `总计: ${items.length} 行`,
    ''
  ].join('\n');
}

/* -------------------- 当内容非空时，拼装一个有标题的段 - 命令行对应的内容 -------------------- */
function buildCommandBlockSection(
    title: string,
    content: string | null | undefined,
    emptyHint = "(未找到对应表)"
): string {
  return [
    "===================================================================================================================",
    title,
    "===================================================================================================================",
    content || emptyHint,
    ""
  ].join("\n");
}


// =====================================================================================================================
//                                           二. LAT Log (Return Log): 通用函数
// =====================================================================================================================
/* -------------------- 提取 ZIP 文件名（去掉末尾 .zip，保留其余符号） -------------------- */
function zipBaseName(zipName: string): string {
  const i = zipName.toLowerCase().lastIndexOf('.zip');
  return i > 0 ? zipName.slice(0, i) : zipName;
}

/* -------------------- 从 ZIP 中的 CMD 目录中提取目标 txt 文本（大小写不敏感） -------------------- */
async function readCmdFileText(
    zip: JSZip,
    targetLower: 'elogread.txt'|'hwlogread.txt'|'telogread.txt'
): Promise<string | null> {

  const entries = Object.values(zip.files);

  for (const f of entries) {
    if (f.dir) continue;

    const rawPath = f.name;
    // 统一路径分隔符：\ -> /
    const normPath = rawPath.replace(/\\/g, '/');
    const pathLower = normPath.toLowerCase();

    if (!/(^|\/)cmd\//i.test(normPath)) continue; // 必须在 CMD 目录下
    const base = pathLower.split('/').pop() || '';

    if (base === targetLower) {
      return await f.async('text');
    }
  }
  return null;
}

/* -------------------- 按要求保存成对应的新 txt 文本 -------------------- */
async function processLatCommon(
    zipFile: File,
    rootOutDir: FileSystemDirectoryHandle
): Promise<{
  base: string;
  baseFolder: FileSystemDirectoryHandle;
  elogText: string | null;
  hwlogText: string | null;
  telogText: string | null;
}> {
  const name = zipFile.name;
  const zip = await JSZip.loadAsync(zipFile);
  Object.keys(zip.files);
  const base = zipBaseName(name);
  const baseFolder = await ensureDir(rootOutDir, base);

  const elogText = await readCmdFileText(zip, 'elogread.txt');
  const hwlogText = await readCmdFileText(zip, 'hwlogread.txt');
  const telogText = await readCmdFileText(zip, 'telogread.txt');

  if (elogText)  await writeTextFile(baseFolder, `${base}_elog.txt`,  elogText,  false);
  if (hwlogText) await writeTextFile(baseFolder, `${base}_hwlog.txt`, hwlogText, false);
  if (telogText) await writeTextFile(baseFolder, `${base}_telog.txt`, telogText, false);

  return { base, baseFolder, elogText, hwlogText, telogText };
}

/* -------------------- LAT Log Analysis Report 生成 -------------------- */
// 处理 HW Fault
function buildLatHwFaultReport(hwlogText?: string | null, elogText?: string | null): string {
  const hwLines = hwlogText ? toLines(hwlogText) : [];
  const elLines = elogText ? toLines(elogText) : [];

  // 1) hwlog: 'Lin. HW fault'
  const sec2 = grepWithLineno(hwLines, /\bLin\.\s*HW\s*fault\b/i);

  // 2) elog 关键字
  const elogKeys: { label: string; re: RegExp }[] = [
    { label: "subID=",                  re: /subID=/i },
    { label: "ler:tx:",                 re: /ler:tx:/i },
    { label: "txAtt",                   re: /\btxAtt\b/i },
    { label: "powerLevel",              re: /\bpowerLevel\b/i },
    { label: "txPma",                   re: /\btxPma\b/i },
    { label: "txDpdPma",                re: /\btxDpdPma\b/i },
    { label: "txPmb",                   re: /\btxPmb\b/i },
    { label: "txTorPmb",                re: /\btxTorPmb\b/i },
    { label: "rfPower",                 re: /\brfPower\b/i },
    { label: "PaVddSv",                 re: /\bPaVddSv\b/i },
    { label: "DpaVddSv",                re: /\bDpaVddSv\b/i },
    { label: "IDpaSv",                  re: /\bIDpaSv\b/i },
    { label: "IMpaSv",                  re: /\bIMpaSv\b/i },
    { label: "16: Lin. Fault",          re: /\b16:\s*Lin\.\s*Fault\b/i },
    { label: "52: Fault led state",     re: /\b52:\s*Fault\s*led\s*state\b/i },
    { label: "dpd restart daily status",re: /dpd\s*restart\s*daily\s*status/i },
    { label: "151: PA VDD Lower than threshold", re: /\b151:\s*PA\s*VDD\s*Lower\s*than\s*threshold\b/i },
  ];

  const sec3Groups: string[] = [];
  if (elLines.length) {
    for (const k of elogKeys) {
      const rows = grepWithLineno(elLines, k.re);
      if (rows.length) {
        sec3Groups.push(buildKeywordLineSection(`elog: ${k.label}`, rows));
      }
    }
  }

  // 3) hwlog: 'Initialization failure'
  const sec4 = grepWithLineno(hwLines, /\bInitialization\s*failure\b/i);

  // 4) hwlog: 'Int. DC fault'  （elog 的 151 关键字已并入 sec3Groups 中）
  const sec5_hw = grepWithLineno(hwLines, /\bInt\.\s*DC\s*fault\b/i);

  // 5) hwlog: 'LO out of lock'
  const sec6 = grepWithLineno(hwLines, /\bLO\s*out\s*of\s*lock\b/i);

  // 6) hwlog: 'Curr. MPA'
  const sec7 = grepWithLineno(hwLines, /\bCurr\.\s*MPA\b/i);

  // 汇总段落（只拼非空）
  const parts: string[] = [];
  const sec2Text = buildKeywordLineSection('hwlog: Lin. HW fault', sec2);             if (sec2Text) parts.push(sec2Text);
  parts.push(...sec3Groups.filter(Boolean));
  const sec4Text = buildKeywordLineSection('hwlog: Initialization failure', sec4);    if (sec4Text) parts.push(sec4Text);
  const sec5Text = buildKeywordLineSection('hwlog: Int. DC fault', sec5_hw);          if (sec5Text) parts.push(sec5Text);
  const sec6Text = buildKeywordLineSection('hwlog: LO out of lock', sec6);            if (sec6Text) parts.push(sec6Text);
  const sec7Text = buildKeywordLineSection('hwlog: Curr. MPA', sec7);                 if (sec7Text) parts.push(sec7Text);

  if (!parts.length) return ''; // 整体无内容 -> 不写报告
  return parts.join('\n');
}

// 判断 hwlog 是否包含一阶段的 5 个硬件故障信号
function hasHwFaultSignals(hwlogText?: string | null): boolean {
  if (!hwlogText) return false;
  const lines = toLines(hwlogText);
  const tests = [
    /\bLin\.\s*HW\s*fault\b/i,
    /\bInitialization\s*failure\b/i,
    /\bInt\.\s*DC\s*fault\b/i,
    /\bLO\s*out\s*of\s*lock\b/i,
    /\bCurr\.\s*MPA\b/i
  ];
  return tests.some(re => lines.some(l => re.test(l)));
}

// 将多个分组段落写为一个报告文件（仅当有内容时才写文件）
async function writeGroupedReport(
    baseFolder: FileSystemDirectoryHandle,
    outName: string,
    groups: Array<{ title: string; items: string[] }>
): Promise<boolean> {
  const parts: string[] = [];
  for (const g of groups) {
    const sec = buildKeywordLineSection(g.title, g.items);
    if (sec) parts.push(sec);
  }
  if (!parts.length) return false;
  await writeTextFile(baseFolder, outName, parts.join('\n'), true);
  return true;
}

// 处理非 HW Fault: 仅在 hwlog 未命中任何 5 个硬件故障信号时，基于 elog 生成其它 7 类报告
async function buildLatOtherFaultReports(
    elogText: string | null | undefined,
    baseFolder: FileSystemDirectoryHandle,
    base: string
): Promise<{ created: number; files: string[] }> {
  const files: string[] = [];
  if (!elogText) return { created: 0, files };

  const elLines = toLines(elogText);
  const collect = (pattern: string | RegExp) =>
      grepWithLineno(elLines, typeof pattern === 'string' ? new RegExp(escapeRe(pattern), 'i') : pattern);

  // 1) VSWR
  {
    const groups = [
      { title: 'elog: 90: VSWR',                 items: collect('90: VSWR') },
      { title: 'elog: 91: Return loss below',    items: collect('91: Return loss below') },
      { title: 'elog: 123: Site Info: 907',      items: collect('123: Site Info: 907') },
    ];
    const fname = `${base}_analysis_report_VSWR.txt`;
    if (await writeGroupedReport(baseFolder, fname, groups)) files.push(fname);
  }

  // 2) paPInterrupt
  {
    const groups = [
      { title: 'elog: paPInterruptSv',           items: collect('paPInterruptSv') },
      { title: 'elog: TRX JESD LINK FAILURE',    items: collect('TRX JESD LINK FAILURE') },
    ];
    const fname = `${base}_analysis_report_paPInterrupt.txt`;
    if (await writeGroupedReport(baseFolder, fname, groups)) files.push(fname);
  }

  // 3) LTU
  {
    const groups = [
      { title: 'elog: TUM status',               items: collect('TUM status') },
    ];
    const fname = `${base}_analysis_report_LTU.txt`;
    if (await writeGroupedReport(baseFolder, fname, groups)) files.push(fname);
  }

  // 4) SW-Reject
  {
    const groups = [
      { title: 'elog: 4: Reject',                items: collect('4: Reject') },
    ];
    const fname = `${base}_analysis_report_SW-Reject.txt`;
    if (await writeGroupedReport(baseFolder, fname, groups)) files.push(fname);
  }

  // 5) unsure
  {
    const groups = [
      { title: 'elog: 6: Client lost',           items: collect('6: Client lost') },
      { title: 'elog: 5: Client connected to RU',items: collect('5: Client connected to RU') },
      { title: 'elog: Power Cycle Restart',      items: collect('Power Cycle Restart') },
      { title: 'elog: PWR_ON',                   items: collect('PWR_ON') },
      { title: 'elog: POWER LOST',               items: collect('POWER LOST') },
      { title: 'elog: CRASH',                    items: collect('CRASH') },
      { title: 'elog: RU start/restarted',       items: collect('RU start/restarted') },
    ];
    const fname = `${base}_analysis_report_unsure.txt`;
    if (await writeGroupedReport(baseFolder, fname, groups)) files.push(fname);
  }

  // 6) HWSO
  {
    const groups = [
      { title: 'elog: HWSO Error Group', items: collect('HWSO Error Group') },
    ];
    const fname = `${base}_analysis_report_HWSO.txt`;
    if (await writeGroupedReport(baseFolder, fname, groups)) files.push(fname);
  }

  // 7) DC
  {
    const groups = [
      { title: 'elog: Fault: RC', items: collect('Fault: RC') },
      { title: 'elog: Fault: DC', items: collect('Fault: DC') },
    ];
    const fname = `${base}_analysis_report_DC.txt`;
    if (await writeGroupedReport(baseFolder, fname, groups)) files.push(fname);
  }

  return { created: files.length, files };
}


// =====================================================================================================================
//                                      三. LAT Log (Return Log): Remote Radio 工具函数
// =====================================================================================================================
/* -------------------- Remote Radio - LAT Log 处理：在三个 common 文件提取之后，执行分析报告生成逻辑 -------------------- */
async function processLatRemote(
    ctx: Awaited<ReturnType<typeof processLatCommon>>,
    zipName: string
): Promise<void> {
  const { base, baseFolder, elogText, hwlogText } = ctx;

  const latReport = buildLatHwFaultReport(hwlogText, elogText);
  if (latReport) {
    const fileName = `${base}_analysis_report_HW-fault.txt`;

    await writeTextFile(
        baseFolder,
        fileName,
        latReport,
        true
    );

    messages.value.push(`Remote/AAS Process: LAT Step 1: ${zipName} → 生成 HW fault 报告：${fileName}`);
  } else {
    messages.value.push(`Remote/AAS Process: LAT Step 1: ${zipName} → 未命中 HW fault，不生成 HW fault 报告`);
  }

  const hwHasSignals = hasHwFaultSignals(hwlogText);
  if (!hwHasSignals) {
    const { created, files } = await buildLatOtherFaultReports(elogText, baseFolder, base);
    if (created) {
      messages.value.push(`Remote/AAS Process: LAT Step 2: ${zipName} → 生成 Other fault ${created} 份报告：${files.join(', ')}`);
    } else {
      messages.value.push(`Remote/AAS Process: LAT Step 2: ${zipName} → 未命中任何 elog 关键字，不生成报告`);
    }
  }
}


// =====================================================================================================================
//                                      四. LAT Log (Return Log): AAS AIR6449 工具函数
// =====================================================================================================================
/* -------------------- AAS AIR6449 - LAT Log 处理：目前完全 follow 对 Remote Radio 的处理流程 -------------------- */
async function processLatAasAir6449(
    ctx: Awaited<ReturnType<typeof processLatCommon>>,
    zipName: string
): Promise<void> {
  // 目前对 AAS AIR6449 的处理完全复用 Remote Radio 的处理流程
  await processLatRemote(ctx, zipName);
}


// =====================================================================================================================
//                                            五. Proactive Log: 通用函数
// =====================================================================================================================
/* -------------------- Proactive Log 文件识别 -------------------- */
const reProSuffix = /_logfiles\.zip$/i;

function isProactiveZipName(name: string): boolean {
  return reProSuffix.test(name.trim());
}

/* -------------------- Proactive Log 名称解析  -------------------- */
function parseProNameParts(name: string): {
  serial: string; node: string; ymd: string; hms: string; baseFolder: string;
} | null {
  const s = name.trim();

  // NodeName 中可能涉及多个下划线，用两侧下划线限定 NodeName 的边界，这样 m[2] 不会包含边界下划线
  const m = s.match(/^([^_]+)_(.+)_(\d{8})_(\d{6})_(?:logfiles\.zip|ProactiveLog\.log)$/i);
  if (!m) return null;

  const serial = m[1];           // 第一个下划线前
  let   node   = m[2];           // 第一个下划线后到日期前的下划线前（内部可含 _）
  const ymd    = m[3];
  const hms    = m[4];

  // 保险起见，去掉 node 两端可能的下划线（正常情况不会有）
  node = node.replace(/^_+|_+$/g, "");

  // 基本校验，防止空内容
  if (!serial || !node || !/^\d{8}$/.test(ymd) || !/^\d{6}$/.test(hms)) return null;

  return {
    serial,
    node,
    ymd,
    hms,
    baseFolder: `${serial}_${node}_${ymd}_${hms}_Logfiles`,
  };
}

/* -------------------- Root Command 内容解析 (从任意 “xxx> cmd” 开始，到下一个 “xxx> xxx” 命令结束)  -------------------- */
function extractRootCommandBlock(lines: string[], cmd: string): string {
  // 1. 起始匹配：任意非空白字符序列 + '>' + 空白 + cmd（完整单词）
  const reStart = new RegExp(`\\S+\\s*>\\s*${escapeRe(cmd)}\\b`, "i");

  // 2. 终止匹配：字母/数字开头的节点名，紧跟 >，且 > 后只有一个空白，然后命令词(cmd)
  const reNext = new RegExp(`^\\s*[A-Za-z0-9][A-Za-z0-9_]*>\\s\\S+`, "i");

  // 查找起始行
  let start = -1;
  for (let i = 0; i < lines.length; i++) {
    if (reStart.test(lines[i])) {
      start = i;
      break;
    }
  }
  if (start === -1) return "";

  // 3. 起始行净化：仅保留从 “xxx> cmd” 开始至行尾的部分
  const startLine = lines[start];
  const match = startLine.match(new RegExp(`\\S+\\s*>\\s*${escapeRe(cmd)}\\b.*$`, "i"));
  const cleanStartLine = match ? match[0] : startLine;

  const output: string[] = [cleanStartLine];

  // 4. 收集后续输出，直到遇见下一个任意节点命令
  for (let j = start + 1; j < lines.length; j++) {
    const line = lines[j];
    if (reNext.test(line)) break;
    output.push(line);
  }

  return output.join("\n");
}

/* -------------------- 单个 RU Proactive Log 内容提取：lhsh command 之后的内容 -------------------- */
function findValidLhshOutputBlock(lines: string[], lnh: string, pattern: RegExp): string | null {
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (pattern.test(line)) {
      const nextLine = lines[i + 1];
      // 下一行存在且以 "lnh:" 开头（忽略前置空格）
      if (nextLine && nextLine.trim().startsWith(lnh + ':')) {
        // 提取输出块：从下一行开始，直到遇到下一个命令提示符（以 "coli>" 开头）
        const output: string[] = [];
        for (let j = i + 1; j < lines.length; j++) {
          const currentLine = lines[j];
          // 遇到下一个命令行（提示符）则终止 coli> 或 coli&gt; 都认为是下一个 prompt
          if (/^\s*coli(?:>|&gt;)/.test(currentLine)) break;
          output.push(currentLine);
        }
        return output.join('\n');
      }
    }
  }
  return null; // 全篇未找到符合条件的命令
}

/* -------------------- 单个 RU Proactive Log 内容行没有 '<LNH>:' 前缀 -------------------- */
function findLlogOutputBlock(
    lines: string[],
    lnh: string,
    cmdPattern: RegExp
): string | null {
  for (let i = 0; i < lines.length; i++) {
    if (!cmdPattern.test(lines[i])) continue;

    const out: string[] = [];
    for (let j = i + 1; j < lines.length; j++) {
      const l = lines[j];
      // 下一个命令开始，结束
      if (/^\s*coli(?:>|&gt;)/i.test(l)) break;
      out.push(l);
    }

    return out.length ? out.join("\n") : null;
  }
  return null;
}

/* -------------------- 全局解析 ProactiveLog_Report.txt 中的 Alarm RU Port(LNH) -------------------- */
/**
 * 规则：
 *  - 必须在同一行同时出现 "Port:" 和 "Alarms:"
 *  - 顺序不限（Port 在前或 Alarms 在前都可以）
 *  - 仅接受形如 BXP_x / fru_x 的 RU
 *  - 返回去 LNH 列表
 */
function parsePortsFromProReport(reportText: string): string[] {
  if (!reportText) return [];

  const lines = reportText.split(/\r?\n/);
  const out: string[] = [];
  const seen = new Set<string>();

  for (let i = 0; i < lines.length; i++) {
    // 注意：有些文本源可能把 "_" 写成 "\_"（例如从某些 markdown 渠道复制）
    // 这里做一次温和归一化，避免匹配失败
    const raw = (lines[i] ?? "");
    const line = raw.replace(/\\_/g, "_").trim();
    if (!line) continue;

    // 必须同一行同时出现 Port: 与 Alarms:
    if (!/Port\s*:/i.test(line) || !/Alarms\s*:/i.test(line)) continue;

    // 提取 Port 值：允许 "Port: BXP_2", "Port:BXP_2", "Port: BXP_2 ;"
    // 取到第一个 token（直到遇到 空白/; /,）
    const mPort = line.match(/Port\s*:\s*([A-Za-z0-9_]+)/i);
    if (!mPort) continue;

    const portRaw = (mPort[1] || "").trim();
    if (!portRaw) continue;

    // 只接受 RU(LNH) 形态
    if (!/^(BXP_|fru_)/i.test(portRaw)) continue;

    // 统一大小写形式可选：这里保持原样，但为了 Map key 稳定建议标准化
    const port = portRaw; // 或：portRaw.toUpperCase()

    if (!seen.has(port)) {
      seen.add(port);
      out.push(port);
    }
  }
  return out;
}

/* -------------------- 提取 "$ cmd" 到下一个 "$ xxx" 之前的块（包含起始行） -------------------- */
function extractDollarCommandBlock(lines: string[], cmd: string): string {
  const reStart = new RegExp(`^\\s*\\$\\s+${escapeRe(cmd)}\\b`, "i");
  const reNext  = /^\s*\$\s+\S+/; // 下一个 "$ xxx"

  let start = -1;
  for (let i = 0; i < lines.length; i++) {
    if (reStart.test(lines[i])) { start = i; break; }
  }
  if (start === -1) return "";

  let end = lines.length;
  for (let j = start + 1; j < lines.length; j++) {
    if (reNext.test(lines[j])) { end = j; break; }
  }

  return lines.slice(start, end).join("\n");
}

/* -------------------- 返回当前本地时间 -------------------- */
function nowLocalTimestampUTC8(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const da = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  return `${y}-${m}-${da} ${hh}-${mi}-${ss} CST`;
}

/* -------------- 通用 grep：返回 “行号: 原文” 支持多种匹配方式 -------------- */
function grep(lines: string[], pred: (l: string) => boolean): { count: number; items: string[] } {
  const items: string[] = [];
  for (let i = 0; i < lines.length; i++) {
    if (pred(lines[i])) items.push(`${i + 1}:${lines[i]}`);
  }
  return { count: items.length, items };
}


// =====================================================================================================================
//                                    六. Proactive Log: Remote Radio 工具函数
// =====================================================================================================================
/* -------------- Link Failure Report (e.g. SerialNo_NodeName_日期_时间_ProactiveLog_Link_Failure.txt) -------------- */
function buildLinkFailureReportText(
    text: string,
    meta: {
      serial: string;
      node: string;
      ymd: string;
      hms: string;
      folderName: string;
    }
): string | null {
  const lines = toLines(text);

  const secLinkFailure = grep(lines, l => /\bLink\s+Failure\b/i.test(l));

  const secResourceTimeout = grep(lines, l => /\bResource\s+Activation\s+Timeout\b/i.test(l));

  if (secLinkFailure.count === 0 && secResourceTimeout.count === 0) {return null;}

  const tbSDIC = extractRootCommandBlock(lines, "sdic");

  return [
    buildKeywordLineSection("日志分析报告 - Link Failure", secLinkFailure.items),
    buildKeywordLineSection("日志分析报告 - Resource Activation Timeout", secResourceTimeout.items),
    buildCommandBlockSection("日志分析报告 - sdic", tbSDIC, "(未找到 sdic 表)")
  ].filter(Boolean).join("\n");
}

/* --------------- HW Partial Fault Report (e.g. SerialNo_NodeName_日期_时间_ProactiveLog_Report.txt) --------------- */
function buildHwPartialFaultReportText(
    text: string,
    meta: {
      serial: string;
      node: string;
      ymd: string;
      hms: string;
      proLogFile: string;
      folderName: string;
    }
): string {
  const lines = toLines(text);

  // A: “HW Partial Fault” 严格匹配（包含空格）
  const secA = grep(lines, (l) => /\bHW Partial Fault\b/i.test(l));

  // B: “HWPartialFault” 与 “Alarms/alarms/Alarm/alarm” 同时存在
  const secB = grep(lines, (l) => /HWPartialFault/.test(l) && /(Alarms|alarms|Alarm|alarm)/.test(l));

  // C: SerialNo 和 RRU- 和 BXP_ 同时存在
  const secC = grep(lines, (l) => {
    const hasSerial = new RegExp(`\\b${escapeRe(meta.serial)}\\b`, "i").test(l);
    return hasSerial && /RRU-/i.test(l) && /BXP_/i.test(l);
  });

  // D: "SW Error" 宽松匹配（比如 SW Error, SW error, SWError, SwError, swerror, SW-Error etc.）
  const secD = grep(lines, (l) => /\bSW\s*Error\b/i.test(l));

  // E: {node}> sdic / sdijc / cvls / lhlist
  const tbSDIC  = extractRootCommandBlock(lines, "sdic");
  const tbSDIJC = extractRootCommandBlock(lines, "sdijc");
  const tbCVLS  = extractRootCommandBlock(lines, "cvls");
  const tbLHLIST= extractRootCommandBlock(lines, "lhlist");

  const header = [
    "===================================================================================================================",
    "日志分析报告 - Overall (Remote Radio)",
    "===================================================================================================================",
    `SerialNo: ${meta.serial}`,
    `NodeName: ${meta.node}`,
    `Date: ${meta.ymd}`,
    `Time: ${meta.hms}`,
    `源文件: ${meta.proLogFile}`,
    `提取起始时间: ${nowLocalTimestampUTC8()}`,
    `文件位置: ${meta.folderName}/${meta.serial}_${meta.node}_${meta.ymd}_${meta.hms}_ProactiveLog_Report.txt`,
    ""
  ].join("\n");

  const parts: string[] = [header];

  const secAtext = buildKeywordLineSection("日志分析报告 - HW Partial Fault", secA.items);
  if (secAtext) parts.push(secAtext);

  const secBtext = buildKeywordLineSection("日志分析报告 - HWPartialFault Alarm", secB.items);
  if (secBtext) parts.push(secBtext);

  const secCtext = buildKeywordLineSection("日志分析报告 - SerialNo, RRU-, BXP_", secC.items);
  if (secCtext) parts.push(secCtext);

  const secDtext = buildKeywordLineSection("日志分析报告 - SW Error", secD.items);
  if (secDtext) parts.push(secDtext);

  const secSDIC = buildCommandBlockSection("日志分析报告 - sdic", tbSDIC, "(未找到 sdic 表)");
  const secSDIJC = buildCommandBlockSection("日志分析报告 - sdijc", tbSDIJC, "(未找到 sdijc 表)");
  const secCVLS = buildCommandBlockSection("日志分析报告 - cvls", tbCVLS, "(未找到 cvls 表)");
  const secLHLIST = [buildCommandBlockSection("日志分析报告 - lhlist", tbLHLIST, "(未找到 lhlist 表)"),
    "===================================================================================================================",
    "报告结束",
    `提取完成时间: ${nowLocalTimestampUTC8()}`,
    "==================================================================================================================="
  ].join("\n");

  return [
    header,
    secAtext,
    secBtext,
    secCtext,
    secDtext,
    secSDIC,
    secSDIJC,
    secCVLS,
    secLHLIST
  ].join("\n");
}

/* ----------------- Each RU Proactive Log (e.g. SerialNo_NodeName_日期_时间_<LNH>_ProactiveLog.log) ----------------- */
function buildEachRuProReportText(text: string): Map<string, string> {
  const lines = toLines(text);

  // 1) 扫描所有 RU LNH（BXP_*/fru_*），以 coli>/fruacc/lhsh <LNH> 为锚点
  const reRuCmd = /^\s*coli(?:>|&gt;)\s*\/fruacc\/lhsh\s+((?:BXP_|fru_)[A-Za-z0-9_]+)\b/i;

  const lnhSet = new Set<string>();
  for (const l of lines) {
    const m = l.match(reRuCmd);
    if (m) lnhSet.add(m[1]); // 保留原样（BXP_2 / fru_2051）
  }

  // 没找到任何 RU
  if (!lnhSet.size) return new Map();

  // 2) 对于AAS，原文件中 fm getfaults 相关内容有两处：
  /**
   * coli>/fruacc/lhsh fru_2057 fm getfaults detail
   *   No raised fault was found
   * coli>/fruacc/lhsh fru_2057 fm getfaults
   *   fru_2057:    No raised fault was found
   * 并且前者早于后者出现，需要在正则时排除前者，否则会导致 fm getfaults 解析失败
   */
  const out = new Map<string, string>();

  for (const lnh of lnhSet) {
    const parts: string[] = [];
    parts.push(`${lnh} —— RU Extractions`);
    parts.push("==========================================================================================================");

    const sections: Array<{ title: string; pattern: RegExp }> = [
      { title: "sfp -d 0",               pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+sfp\\s+-d\\s+0`, "i") },
      { title: "sfp -d 1",               pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+sfp\\s+-d\\s+1`, "i") },
      { title: "ricr -a",                pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+ricr\\s+-a`, "i") },
      { title: "rioistat moddiag all",   pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+rioistat\\s+moddiag\\s+all`, "i") },
      { title: "pa read all",            pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+pa\\s+read\\s+all`, "i") },
      { title: "indicator get",          pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+indicator\\s+get`, "i") },
      { title: "cs read",                pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+cs\\s+read`, "i") },
      { title: "vs read",                pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+vs\\s+read`, "i") },
      { title: "ts read",                pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+ts\\s+read`, "i") },
      { title: "elog read",              pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+elog\\s+read`, "i") },
      // 关键：排除 detail（兼容 AAS 的特殊情况）
      { title: "fm getfaults",           pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+fm\\s+getfaults(?!\\s+detail)\\b`, "i") },
      { title: "hwlog read",             pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+hwlog\\s+read`, "i") },
      { title: "trx status",             pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+trx\\s+status`, "i") },
      { title: "lmclist",                pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+lmclist\\b`, "i") },
      { title: "llog -l",                pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+llog\\s+-l`, "i") },
      { title: "antCalBasic showAlg all",pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+antCalBasic\\s+showAlg\\s+all\\b`, "i")},
      { title: "fm getfaults detail",    pattern: new RegExp(`lhsh\\s+${escapeRe(lnh)}\\s+fm\\s+getfaults\\s+detail\\b`, "i")},
    ];

    for (const sec of sections) {
      parts.push("");
      parts.push(`coli>/fruacc/lhsh ${lnh} ${sec.title}`);
      parts.push("--------------------------------------------------------------------------------------------------------");

      let block: string | null = null;

      if (sec.title === "llog -l" || sec.title === "antCalBasic showAlg all" || sec.title === "fm getfaults detail") {
        // 特殊处理（内容行无 <LNH>: 前缀）
        block = findLlogOutputBlock(lines, lnh, sec.pattern);
      } else {
        // 原有 内容行有 <LNH>: 前缀 逻辑
        block = findValidLhshOutputBlock(lines, lnh, sec.pattern);
      }
      parts.push(block || "(No Output)");
    }
    out.set(lnh, parts.join("\n"));
  }
  return out;
}

/* ------------------------ Alarm RU Diagnostic Report 报告构建 ------------------------ */
// 构建 Alarm RU 的诊断报告（写入 ..._ProactiveLog_<LNH>_Diagnostic_Report.txt）
function buildAlarmDiagnosticReportText(
    ruText: string,
    mainProText: string,
    meta: { serial: string; node: string; ymd: string; hms: string; lnh: string; }
): string {
  const ruLines = toLines(ruText);
  const mainLines = toLines(mainProText);

  // 1) RU log：Fault 相关关键字（带行号）
  const faultItems = Array.from(new Set([
    ...grepWithLineno(ruLines, /\bFault\s*id\b/i),
    ...grepWithLineno(ruLines, /\bfault\s*id\b/i),
    ...grepWithLineno(ruLines, /\blocalFaultId\b/i),
    ...grepWithLineno(ruLines, /\bLin\.\s*HW\b/i),
    ...grepWithLineno(ruLines, /\b52:\s*Fault\s*led\s*state\b/i),
  ]));

  // 2) 主 ProactiveLog：$ cfheflist / $ cfhemap 块（存在才写）
  const cfheflistBlock = extractDollarCommandBlock(mainLines, "cfheflist");
  const cfhemapBlock   = extractDollarCommandBlock(mainLines, "cfhemap");

  // 3) RU log：你列出的详细参数关键行（带行号，分组标题）
  const ruKeyGroups: Array<{ title: string; items: string[] }> = [
    { title: "RU参数 - subId=",                   items: grepWithLineno(ruLines, /subId=/i) },
    { title: "RU参数 - ler:tx:",                  items: grepWithLineno(ruLines, /ler:tx:/i) },
    { title: "RU参数 - txAtt",                    items: grepWithLineno(ruLines, /\btxAtt\b/i) },
    { title: "RU参数 - powerLevel",               items: grepWithLineno(ruLines, /\bpowerLevel\b/i) },
    { title: "RU参数 - txPma",                    items: grepWithLineno(ruLines, /\btxPma\b/i) },
    { title: "RU参数 - txDpdPma",                 items: grepWithLineno(ruLines, /\btxDpdPma\b/i) },
    { title: "RU参数 - txPmb",                    items: grepWithLineno(ruLines, /\btxPmb\b/i) },
    { title: "RU参数 - txTorPmb",                 items: grepWithLineno(ruLines, /\btxTorPmb\b/i) },
    { title: "RU参数 - rfPower",                  items: grepWithLineno(ruLines, /\brfPower\b/i) },
    { title: "RU参数 - PaVddSv",                  items: grepWithLineno(ruLines, /\bPaVddSv\b/i) },
    { title: "RU参数 - DpaVddSv",                 items: grepWithLineno(ruLines, /\bDpaVddSv\b/i) },
    { title: "RU参数 - IDpaSv",                   items: grepWithLineno(ruLines, /\bIDpaSv\b/i) },
    { title: "RU参数 - IMpaSv",                   items: grepWithLineno(ruLines, /\bIMpaSv\b/i) },
    { title: "RU参数 - 16: Lin. Fault",           items: grepWithLineno(ruLines, /\b16:\s*Lin\.\s*Fault\b/i) },
    { title: "RU参数 - dpd restart daily status", items: grepWithLineno(ruLines, /dpd\s*restart\s*daily\s*status/i) },
    { title: "RU参数 - mod_ovf",                  items: grepWithLineno(ruLines, /mod_ovf/i) },
  ];

  const header = [
    "===================================================================================================================",
    `ProactiveLog Diagnostic Report - ${meta.lnh}`,
    "===================================================================================================================",
    `SerialNo: ${meta.serial}`,
    `NodeName: ${meta.node}`,
    `Date: ${meta.ymd}`,
    `Time: ${meta.hms}`,
    `Port(LNH): ${meta.lnh}`,
    ""
  ].join("\n");

  const parts: string[] = [header];

  // Fault 段（无命中也输出标题可选；这里沿用 buildKeywordLineSection：无命中则不输出）
  const faultSec = buildKeywordLineSection("RU诊断 - Fault id / localFaultId / Lin.HW / Fault led state", faultItems);
  if (faultSec) parts.push(faultSec);

  if (cfheflistBlock) {
    parts.push(buildCommandBlockSection("主日志块 - $ cfheflist", cfheflistBlock, "(未找到 cfheflist 输出)"));
  }

  if (cfhemapBlock) {
    parts.push(buildCommandBlockSection("主日志块 - $ cfhemap", cfhemapBlock, "(未找到 cfhemap 输出)"));
  }

  for (const g of ruKeyGroups) {
    const sec = buildKeywordLineSection(g.title, g.items);
    if (sec) parts.push(sec);
  }

  // 4) RU log：hwlog read 000 → On Site Time (带行号 + 提取时间)
  // 仅匹配 "000" 后面紧跟 "YY-MM-DD HH:MM:SS" 的格式，避免误匹配其它 000
  const onsiteItems: string[] = [];
  const re000Time = /\b000\b\s+(\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\b/;

  for (let i = 0; i < ruLines.length; i++) {
    const s = ruLines[i];
    const m = s.match(re000Time);
    if (!m) continue;
    const ts = m[1] || "(Time Not Found)";
    onsiteItems.push(`${i + 1}: ${s}\n    => On Site Time = ${ts}`);
  }

  // 输出 section（无命中则不输出，沿用 buildKeywordLineSection 的习惯）
  const onsiteSec = buildKeywordLineSection("RU诊断 - hwlog read - 000 (On Site Time)", onsiteItems);
  if (onsiteSec) parts.push(onsiteSec);

  // 5) 对 Fault ID 的处理
  // 对 "fault id:"（小写）的处理：提取时间戳 + token + 类别映射。注意：必须严格大小写匹配，"Fault Id:" 不算
  const FAULT_ID_CATEGORY: Record<string, string> = {
    "ELIB_CONST_FH_FAULT_ID_HWF_FOR_EVALUATION": "Linearization Fault",
    "ELIB_CONST_FH_FAULT_ID_LINEARIZATION_FAULT_PARTIAL": "Linearization Fault",
    "ELIB_CONST_FH_FAULT_ID_HW_FAULT_PARTIAL": "Linearization HW Fault",
  };

  const mainFaultIdColonItems: string[] = [];
  const tsRe = /\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\]/;

  for (let i = 0; i < mainLines.length; i++) {
    const s = mainLines[i];
    const pos = s.indexOf("fault id:"); // 严格大小写
    if (pos === -1) continue;

    const tm = s.match(tsRe);
    const ts = tm ? tm[1] : "(Time Not Found)";

    const after = s.slice(pos + "fault id:".length);
    const comma = after.indexOf(",");
    const token = (comma >= 0 ? after.slice(0, comma) : after).trim();
    const baseId = token.split("(")[0].trim();
    const cat = FAULT_ID_CATEGORY[baseId] ?? "(Unknown Category)";

    // 输出：原行 + 提取后（分行）
    mainFaultIdColonItems.push(`${i + 1}: ${s}\n    => ${ts}, ${token}, ${cat}`);
  }

  const mainFaultIdColonSec = buildKeywordLineSection("主日志解析 - strict 'fault id:' (time + token + category)", mainFaultIdColonItems);
  if (mainFaultIdColonSec) parts.push(mainFaultIdColonSec);


  // 对 "Fault id="的处理：提取从 "Fault id=" 到双引号前的内容
  const mainFaultIdEqItems: string[] = [];
  for (let i = 0; i < mainLines.length; i++) {
    const s = mainLines[i];
    const pos = s.indexOf("Fault id="); // 严格大小写
    if (pos === -1) continue;

    const rest = s.slice(pos);
    const quote = rest.indexOf('"');
    const picked = (quote >= 0 ? rest.slice(0, quote) : rest).trim();

    // 输出：原行 + 提取后（分行）
    mainFaultIdEqItems.push(`${i + 1}: ${s}\n    => ${picked}`);
  }

  const mainFaultIdEqSec = buildKeywordLineSection("主日志解析 - strict 'Fault id=' (extract to quote)", mainFaultIdEqItems);
  if (mainFaultIdEqSec) parts.push(mainFaultIdEqSec);

  return parts.join("\n");
}

/* ------------------------ Proactive Log - Remote Radio 处理主流程，由 onProcess 调用 ------------------------ */
async function processProactiveRemote(zipFile: File): Promise<void> {
  const name = zipFile.name;
  const parts = parseProNameParts(name);
  if (!parts) {
    skipped.value++;
    ElMessage.warning(`Remote Process: 文件名不符合 Proactive 规范: ${name}`);
    messages.value.push(`Remote Process: 跳过（命名不规范）: ${name}`);
    return;
  }

  // Step 1: 将原 .zip 文件中的 .log 转存到新的 _ProactiveLog.log 里
  const zip = await JSZip.loadAsync(zipFile);
  const logHit = await readFirstLogText(zip);
  if (!logHit) {
    ElMessage.warning(`Remote Process: 未找到 .log：${name}`);
    messages.value.push(`Remote Process: 未找到 .log：${name}`);
    return;
  }

  const root = outputDir.value!;
  const folder = await ensureDir(root, parts.baseFolder);

  const proactiveLogName = `${parts.serial}_${parts.node}_${parts.ymd}_${parts.hms}_ProactiveLog.log`;
  await writeTextFile(folder, proactiveLogName, logHit.text, false);

  messages.value.push(`Remote Process: Proactive Step 1 完成: ${name} → ${parts.baseFolder}/${proactiveLogName}`)

  // Step 2: Link Failure / Resource Activation Timeout
  const linkFailureReport = buildLinkFailureReportText(logHit.text, {
    serial: parts.serial,
    node: parts.node,
    ymd: parts.ymd,
    hms: parts.hms,
    folderName: parts.baseFolder,
  });

  if (linkFailureReport) {
    const lfName = `${parts.serial}_${parts.node}_${parts.ymd}_${parts.hms}_ProactiveLog_Link_Failure.txt`;
    await writeTextFile(folder, lfName, linkFailureReport, true);

    messages.value.push(`Remote Process: Proactive Step 2: ${name} → 生成 ${lfName}`);
  } else {
    messages.value.push(`Remote Process: Proactive Step 2: ${name} → 未命中 Link Failure / Resource Activation Timeout`);
  }

  // Step 3: HW Partial Fault
  const reportText = buildHwPartialFaultReportText(logHit.text, {
    serial: parts.serial, node: parts.node, ymd: parts.ymd, hms: parts.hms,
    proLogFile: proactiveLogName, folderName: parts.baseFolder
  });
  const reportName = `${parts.serial}_${parts.node}_${parts.ymd}_${parts.hms}_ProactiveLog_Report.txt`;
  await writeTextFile(folder, reportName, reportText, true);

  messages.value.push(`Remote Process: Proactive Step 3: ${name} → 生成 ${reportName}`);

  // Step 4: Each RU Proactive Log (BXP_/FRU_ 均支持)
  const ruPieces = buildEachRuProReportText(logHit.text);
  const ruMapLower = new Map<string, string>(); // 供 Diagnostic 使用（大小写兜底）
  let ruCreated = 0;
  for (const [lnh, ruText] of ruPieces.entries()) {
    const ruName = `${parts.serial}_${parts.node}_${parts.ymd}_${parts.hms}_${lnh}_ProactiveLog.log`;
    await writeTextFile(folder, ruName, ruText, true);
    ruCreated++;
    ruMapLower.set(lnh.toLowerCase(), ruText);
  }
  messages.value.push(`Remote Process: Proactive Step 4: ${name} → 生成 ${ruCreated} 个 RU 日志文件`);

  // Step 5: 只针对 alarm RU 的 Diagnostic Report
  const portsFromReport = parsePortsFromProReport(reportText);
  if (!portsFromReport.length) {
    messages.value.push(`Remote Process: Proactive Step 5: ${name} → Report 全文未找到合规 Port(LNH)（需同一行含 Alarms + Port），不生成诊断报告`);
  } else {
    let diagCreated = 0;
    for (const lnh of portsFromReport) {
      const ruText = ruMapLower.get(lnh.toLowerCase());
      if (!ruText) {
        messages.value.push(`Remote Process: Proactive Step 5: ${name} → 找到 Alarm Port=${lnh}，但未生成对应 RU log 内容，跳过`);
        continue;
      }

      const diagText = buildAlarmDiagnosticReportText(ruText, logHit.text, {serial: parts.serial, node: parts.node, ymd: parts.ymd, hms: parts.hms, lnh});

      const diagName = `${parts.serial}_${parts.node}_${parts.ymd}_${parts.hms}_${lnh}_ProactiveLog_Diagnostic_Report.txt`;
      await writeTextFile(folder, diagName, diagText, true);
      diagCreated++;
    }
    if (diagCreated) messages.value.push(`Remote Process: Proactive Step 5: ${name} → 生成 ${diagCreated} 份（仅限 Report 中“同行 Alarms + Port”定位到的 Alarm RU）`);
    else messages.value.push(`Remote Process: Proactive Step 5: ${name} → 虽找到合规 Port，但未匹配到对应 RU 内容，不生成文件`);
  }

  const ruCount = ruMapLower.size;
  messages.value.push(`Remote Process: Proactive 处理完成: ${name} → 输出：${proactiveLogName}, ${reportName}${ruCount ? `，RU*${ruCount}` : ""}`
  );
}

// =====================================================================================================================
//                                      七. Proactive Log: AAS AIR6419 工具函数
// =====================================================================================================================
/* --------------- HW Partial Fault Report (e.g. SerialNo_NodeName_日期_时间_ProactiveLog_Report.txt) --------------- */
/**
 *  AAS AIR6449 不同与 Remote Radio 的处理之处：
 *  1. 关键字所在行 C 只考虑 SerialNo + fru_ 同时出现
 *  2. 命令行内容不考虑 lhlist
 */
function buildHwPartialFaultReportTextAas(
    text: string,
    meta: {
      serial: string;
      node: string;
      ymd: string;
      hms: string;
      proLogFile: string;
      folderName: string;
    }
): string {
  const lines = toLines(text);

  // A: “HW Partial Fault”（复用 Remote）
  const secA = grep(lines, (l) => /\bHW Partial Fault\b/i.test(l));

  // B: “HWPartialFault” + Alarm(s)（复用 Remote）
  const secB = grep(
      lines,
      (l) => /HWPartialFault/.test(l) && /(Alarms|alarms|Alarm|alarm)/.test(l)
  );

  // C(AAS): SerialNo + fru_
  const secC = grep(lines, (l) => {
    const hasSerial = new RegExp(`\\b${escapeRe(meta.serial)}\\b`, "i").test(l);
    return hasSerial && /\bfru_/i.test(l);
  });

  // D: SW Error（可选；若不需要可整段删除）
  const secD = grep(lines, (l) => /\bSW\s*Error\b/i.test(l));

  // E(AAS): 命令相关内容
  const tbSDIC  = extractRootCommandBlock(lines, "sdic");
  const tbSDIJC = extractRootCommandBlock(lines, "sdijc");
  const tbCVLS  = extractRootCommandBlock(lines, "cvls");

  // Header
  const header = [
    "===================================================================================================================",
    "日志分析报告 - Overall (AAS AIR6449)",
    "===================================================================================================================",
    `SerialNo: ${meta.serial}`,
    `NodeName: ${meta.node}`,
    `Date: ${meta.ymd}`,
    `Time: ${meta.hms}`,
    `源文件: ${meta.proLogFile}`,
    `提取起始时间: ${nowLocalTimestampUTC8()}`,
    `文件位置: ${meta.folderName}/${meta.serial}_${meta.node}_${meta.ymd}_${meta.hms}_ProactiveLog_Report.txt`,
    ""
  ].join("\n");

  // 关键字所在行 Section
  const parts: string[] = [header];

  const secAText = buildKeywordLineSection("日志分析报告 - HW Partial Fault", secA.items);
  if (secAText) parts.push(secAText);

  const secBText = buildKeywordLineSection("日志分析报告 - HWPartialFault Alarm", secB.items);
  if (secBText) parts.push(secBText);

  const secCText = buildKeywordLineSection("日志分析报告 - SerialNo & fru_", secC.items);
  if (secCText) parts.push(secCText);

  const secDText = buildKeywordLineSection("日志分析报告 - SW Error", secD.items);
  if (secDText) parts.push(secDText);

  // 关键命令相关内容 Section
  parts.push(buildCommandBlockSection("日志分析报告 - sdic", tbSDIC, "(未找到 sdic 表)"));
  parts.push(buildCommandBlockSection("日志分析报告 - sdijc", tbSDIJC, "(未找到 sdijc 表)"));
  parts.push(buildCommandBlockSection("日志分析报告 - cvls", tbCVLS, "(未找到 cvls 表)"));

  return parts.join("\n");
}

/* --------------- SDIC Table 下的 Mapping 图 --------------- */
type FaultDiagAasResult = {
  frus: string[];                  // 5-1 识别到的 fru_xxx（小写）
  mappingBlocks: string[];         // 5-1 命中的 CPRI mapping 块（可选写进诊断报告）
  reportsByFru: Map<string, string>; // key=fru_xxx(小写)，value=诊断报告全文
};

/* ------------- 从 _Proactive_Report 中提取某个 section 的正文（title 为完整标题行，例如 "日志分析报告 - sdic"） ------------- */
function extractReportSection(reportText: string, title: string): string {
  const lines = reportText.split(/\r?\n/);
  const SEP = /^=+$/; // 兼容你的分隔线：很多个 '='

  // 找到 title 行
  let ti = -1;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].trim() === title) { ti = i; break; }
  }
  if (ti === -1) return "";

  // 期望结构：SEP, title, SEP, content..., ""(空行), SEP, next title ...
  // content 从 title 后面的下一个 SEP 的下一行开始
  let start = -1;
  for (let i = ti + 1; i < lines.length; i++) {
    if (SEP.test(lines[i].trim())) { start = i + 1; break; }
  }
  if (start === -1 || start >= lines.length) return "";

  // end：遇到下一段的 SEP + "日志分析报告 - xxx" / "报告结束" 时停止
  let end = lines.length;
  for (let i = start; i < lines.length; i++) {
    if (!SEP.test(lines[i].trim())) continue;

    const next = (lines[i + 1] ?? "").trim();
    if (next.startsWith("日志分析报告 -") || next === "报告结束") {
      end = i;
      break;
    }
  }

  // trimEnd：去掉末尾空行
  const slice = lines.slice(start, end);
  while (slice.length && slice[slice.length - 1].trim() === "") slice.pop();

  return slice.join("\n");
}

/* ----------------- 在 sdic 正文中找到“同一块里同时含 OKW + fru_xxx”的 mapping 块，并提取所有 fru_xxx ----------------- */
function findOkwFruMappingBlocks(sdicText: string): { frus: string[]; blocks: string[] } {
  const lines = sdicText.split(/\r?\n/);

  // 仍然保留“块”的概念：用于输出 mapping 图块（blocks）
  const blocks: string[] = [];
  let buf: string[] = [];

  const flush = () => {
    while (buf.length && buf[buf.length - 1].trim() === "") buf.pop();
    if (buf.length) blocks.push(buf.join("\n"));
    buf = [];
  };

  for (const l of lines) {
    if (l.trim() === "") flush();
    else buf.push(l);
  }
  flush();

  // 按“最近关键字”筛选 fru
  const fruSet = new Set<string>();
  const hitBlocks: string[] = [];

  const reFru = /\bfru_\d+\b/ig;

  // OKW：要匹配 OKW 或 OKW-39m 这种（\bOKW\b 对 OKW-39m 也成立）
  const reOKW = /\bOKW\b/i;

  // OK：匹配 OK 或 OK-36m，但必须排除 OKW（避免 OKW 被当成 OK）
  const reOK = /\bOK\b/i;

  for (const b of blocks) {
    const bLines = b.split(/\r?\n/);

    let lastStatus: "OKW" | "OK" | "" = "";

    // 在一个块内逐行扫描：最近状态覆盖更早状态
    const frusInThisBlock: string[] = [];

    for (const line of bLines) {
      const s = line;

      // 更新最近状态：OKW 优先，其次 OK（但 OK 行不能是 OKW）
      if (reOKW.test(s)) {
        lastStatus = "OKW";
      } else if (reOK.test(s) && !reOKW.test(s)) {
        lastStatus = "OK";
      }

      // 若行内出现 fru_xxx，则根据 lastStatus 判定是否属于 OKW 映射
      const ms = s.match(reFru);
      if (ms && ms.length) {
        for (const fruRaw of ms) {
          // 只接受“最近状态=OKW”的 fru
          if (lastStatus === "OKW") {
            fruSet.add(fruRaw.toLowerCase());
            frusInThisBlock.push(fruRaw.toLowerCase());
          }
          // lastStatus === "OK" → 明确排除（你的 bug case）
        }
      }
    }

    // blocks：只保留包含“OKW命中的 fru”的块（用于写入 Diagnostic header 的 mapping 图）
    if (frusInThisBlock.length) {
      hitBlocks.push(b);
    }
  }

  return { frus: Array.from(fruSet), blocks: hitBlocks };
}

// 提取对应 RU 文件里的 llog -l section
function extractLlogSectionFromRuText(ruText: string, fru: string): string {
  const lines = ruText.split(/\r?\n/);

  const reHead = new RegExp(
      `^\\s*coli(?:>|&gt;)\\/fruacc\\/lhsh\\s+${escapeRe(fru)}\\s+llog\\s+-l\\b`,
      "i"
  );
  const reNextSec = new RegExp(
      `^\\s*coli(?:>|&gt;)\\/fruacc\\/lhsh\\s+${escapeRe(fru)}\\b`,
      "i"
  );

  let start = -1;
  for (let i = 0; i < lines.length; i++) {
    if (reHead.test(lines[i])) { start = i + 1; break; }
  }
  if (start === -1) return "";

  // 跳过紧跟的横线分隔（你 llog 输出里会出现 "---------------------------------------------------"）
  while (start < lines.length && /^-+$/.test(lines[start].trim())) start++;

  let end = lines.length;
  for (let i = start; i < lines.length; i++) {
    if (reNextSec.test(lines[i])) { end = i; break; }
  }

  const slice = lines.slice(start, end);
  while (slice.length && slice[slice.length - 1].trim() === "") slice.pop();
  return slice.join("\n");
}

// 对于 llog -l section，筛选含 faulty/Faulty 的段落
function extractFaultySegmentsFromRuLlog(ruText: string, fru: string): string[] {
  const llog = extractLlogSectionFromRuText(ruText, fru);
  if (!llog.trim()) return [];

  const lines = llog.split(/\r?\n/);
  const SEP = /^-+\s*$/; // 形如 "---------------------------------------------------"
  const segs: string[] = [];

  let buf: string[] = [];

  const flush = () => {
    // 去掉尾部空行
    while (buf.length && buf[buf.length - 1].trim() === "") buf.pop();
    if (!buf.length) { buf = []; return; }

    const s = buf.join("\n");
    if (/faulty/i.test(s)) {
      // 为了保留你示例的上下分隔线，我们把分隔线也加回去
      segs.push(["---------------------------------------------------", s, "---------------------------------------------------"].join("\n"));
    }
    buf = [];
  };

  for (const l of lines) {
    if (SEP.test(l)) {
      // 遇到分隔线：结束上一段，开始下一段
      flush();
      continue;
    }
    buf.push(l);
  }
  flush();

  return segs;
}

// 组装一个“段落列表 section”
function buildSectionFromSegments(title: string, segs: string[], emptyHint: string): string {
  return [
    "===================================================================================================================",
    title,
    "===================================================================================================================",
    segs.length ? segs.join("\n\n") : emptyHint,
    ""
  ].join("\n");
}

// 对于 antCalBasic showAlg all 以及 fm getfaults detail sections 直接 copy 内容
function copyRuSection(
    ruText: string,
    fru: string,
    title: string
): string {
  const lines = ruText.split(/\r?\n/);

  const head = new RegExp(`^\\s*coli(?:>|&gt;|&amp;gt;)\\/fruacc\\/lhsh\\s+${escapeRe(fru)}\\s+${escapeRe(title)}\\s*$`, "i");

  const next = new RegExp(`^\\s*coli(?:>|&gt;|&amp;gt;)\\/fruacc\\/lhsh\\s+${escapeRe(fru)}\\b`, "i");

  let start = -1;
  for (let i = 0; i < lines.length; i++) {
    if (head.test(lines[i])) {
      start = i;
      break;
    }
  }
  if (start === -1) return "";

  let end = lines.length;
  for (let i = start + 1; i < lines.length; i++) {
    if (next.test(lines[i])) {
      end = i;
      break;
    }
  }

  return lines.slice(start, end).join("\n").trim();
}

// Fault sources 映射表
const FAULT_SOURCE_MAP: Array<{ name: string; mask: number }> = [
  { name: "NO_FAULT_SOURCE",                 mask: 0x0000 },
  { name: "CURRENT_EXCEPTION_LOW_EVENT",     mask: 0x0001 },
  { name: "CURRENT_EXCEPTION_HIGH_EVENT",    mask: 0x0002 },
  { name: "VOLTAGE_EXCEPTION_LOW_EVENT",     mask: 0x0004 },
  { name: "VOLTAGE_EXCEPTION_HIGH_EVENT",    mask: 0x0008 },
  { name: "TRX_HW_INIT_FAULT_EVENT",         mask: 0x0010 },
  { name: "TOR_JESD_LINK_FAILURE_EVENT",     mask: 0x0020 },
  { name: "RX_JESD_LINK_FAILURE_EVENT",      mask: 0x0040 },
  { name: "TX_JESD_LINK_FAILURE_EVENT",      mask: 0x0080 },
  { name: "TRX_DEVICE_INTERNAL_ERROR_EVENT", mask: 0x0100 },
  { name: "TRX_JESD_LINK_FAILURE_EVENT",     mask: 0x0200 },
  { name: "TRX_OUT_OF_LOCK_EVENT",           mask: 0x0400 },
  { name: "LINEARIZATION_FAULT_EVENT",       mask: 0x0800 },
  { name: "CPRI_LINK_FAULT_EVENT",           mask: 0x1000 },
  { name: "CPRI_EXT_LINK_FAULT_EVENT",       mask: 0x2000 },
  { name: "AC_DL_GAINLOSS",                  mask: 0x4000 },
  { name: "AC_UL_GAINLOSS",                  mask: 0x8000 },
  { name: "SLOT_INFO_MISSING",               mask: 0x10000 },
];

// 生成 hwlog read section - 000
function buildHwlog000MappingSection(hwlogRaw: string): string {
  const lines = hwlogRaw.split(/\r?\n/);

  // 匹配 hwlog id = 000（单独字段）
  const id000Re = /\b000\b/;

  // 匹配时间：YY-MM-DD HH:MM:SS
  const timeRe = /(\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})/;

  const hits: string[] = [];

  for (const line of lines) {
    if (!id000Re.test(line)) continue;

    const m = line.match(timeRe);
    const time = m ? m[1] : "(Time Not Found)";

    hits.push(
        `${line}\n    => On Site Time = ${time}`
    );
  }

  return [
    "===================================================================================================================",
    "RU诊断 - hwlog read: 000 (On Site Time)",
    "===================================================================================================================",
    hits.length ? hits.join("\n") : "(hwlog read 中未发现 000 记录)",
    ""
  ].join("\n");
}

// 在 hwlogRaw 中筛 770/771 行并提取 0x 值
function findHwlog770771Lines(hwlogSectionText: string): string[] {
  const lines = hwlogSectionText.split(/\r?\n/);
  const out: string[] = [];

  // 兼容带/不带 fru_xxx: 前缀，只要行内出现 " 770 " 或 " 771 "
  const re = /\b(770|771)\b/;

  for (const l of lines) {
    if (re.test(l)) out.push(l);
  }
  return out;
}

// 从 770/771 行里提取 0xXXXX
function extractFirstHex0x(line: string): string | null {
  const m = line.match(/0x[0-9a-fA-F]+/);
  return m ? m[0] : null;
}

// 把 0x 值映射成文字
function decodeFaultSource(hex0x: string): string {
  const v = parseInt(hex0x, 16);
  if (Number.isNaN(v)) return "(Invalid Hex)";

  if (v === 0) return "NO_FAULT_SOURCE";

  const hits = FAULT_SOURCE_MAP
      .filter(x => x.mask !== 0 && (v & x.mask) === x.mask)
      .map(x => x.name);

  return hits.length ? hits.join(" + ") : "(Unknown FaultSource)";
}

//  生成 hwlog read section - 770/771
function buildHwlog770771MappingSection(hwlogRaw: string): string {
  const hwLines = hwlogRaw ? findHwlog770771Lines(hwlogRaw) : [];

  if (!hwlogRaw.trim()) {
    return [
      "===================================================================================================================",
      "RU诊断 - hwlog read: 770/771 (Fault Source)",
      "===================================================================================================================",
      "(未找到 hwlog read 输出)",
      ""
    ].join("\n");
  }

  if (!hwLines.length) {
    return [
      "===================================================================================================================",
      "RU诊断 - hwlog read: 770/771 (Fault Source)",
      "===================================================================================================================",
      "(hwlog read 中未发现 770/771 行)",
      ""
    ].join("\n");
  }

  const mapped = hwLines.map(l => {
    const hex0x = extractFirstHex0x(l);
    const desc = hex0x ? decodeFaultSource(hex0x) : "(未找到 0x 开头16进制)";
    return `${l}\n    => ${hex0x || "(none)"} : ${desc}`;
  });

  return [
    "===================================================================================================================",
    "RU诊断 - hwlog read: 770/771 (Fault Source)",
    "===================================================================================================================",
    ...mapped,
    ""
  ].join("\n");
}

// AAS 版本：alarm 行相关内容提取（grep 风格）
function buildAlarmDiagnosticTextAas(ruText: string): string {
  const lines = ruText.split(/\r?\n/);

  const pick = (res: RegExp[]) => {
    const out: string[] = [];
    const seen = new Set<string>();
    for (const l of lines) {
      for (const re of res) {
        if (re.test(l)) {
          if (!seen.has(l)) {
            seen.add(l);
            out.push(l);
          }
          break;
        }
      }
    }
    return out;
  };

  const section = (title: string, items: string[]) => {
    return [
      "===================================================================================================================",
      title,
      "===================================================================================================================",
      items.length ? items.join("\n") : "(No Match)",
      ""
    ].join("\n");
  };

  // === Step 6: Fault id / localFaultId / Lin. HW / 52: Fault led state
  const secFaults = pick([
    /fault id/i,                 // 同时覆盖 "Fault id" / "fault id"
    /localFaultId/i,
    /Lin\. HW/i,
    /52:\s*Fault led state/i,
  ]);

  // === Step 7: subId=
  const secSubId = pick([
    /subId=/i,
  ]);

  // === Step 8: 一组 TX/PA/DPD/Lin 相关关键字
  const secParams = pick([
    /ler:tx:/i,
    /txAtt/i,
    /powerLevel/i,
    /txPma/i,
    /txDpdPma/i,
    /txPmb/i,
    /txTorPmb/i,
    /rfPower/i,
    /PaVddSv/i,
    /DpaVddSv/i,
    /IDpaSv/i,
    /IMpaSv/i,
    /16:\s*Lin\. Fault/i,
    /52:\s*Fault led state/i,
    /dpd restart daily status/i,
  ]);

  return [
    section("RU诊断 - Fault id / localFaultId / Lin. HW / 52: Fault led state 所在行", secFaults),
    section("RU诊断 - ‘subId=’ 所在行", secSubId),
    section("RU诊断 - TX/PA/DPD/Lin/POWER/FAULT/... 关键参数所在行", secParams),
  ].join("\n");
}


/* --------------- AAS Fault Diagnostic Report --------------- */
function buildFaultDiagnosticReportTextAas(
    reportText: string,
    ruMapLower: Map<string, string>,
    meta: { serial: string; node: string; ymd: string; hms: string; folderName: string }
): FaultDiagAasResult {

  // Report 中提取 sdic section，并找 OKW+fru_xxx mapping 块
  const sdicText = extractReportSection(reportText, "日志分析报告 - sdic");
  const pick = sdicText.trim() ? findOkwFruMappingBlocks(sdicText) : { frus: [], blocks: [] };

  const frus = pick.frus.map(f => f.toLowerCase());

  // 对每个 fru 抓取 llog -l 的 faulty 段落， antCalBasic showAlg all 内容, fm getfaults detail 内容, hwlog 的 fault source 内容
  const reportsByFru = new Map<string, string>();

  for (const fru of frus) {
    const ruText = ruMapLower.get(fru);
    const faultySegs = ruText ? extractFaultySegmentsFromRuLlog(ruText, fru) : [];

    const title = [
      "===================================================================================================================",
      "AAS AIR6449 - ProactiveLog Diagnostic Report",
      "===================================================================================================================",
      `SerialNo: ${meta.serial}`,
      `NodeName: ${meta.node}`,
      `Date: ${meta.ymd}`,
      `Time: ${meta.hms}`,
      `FRU: ${fru}`,
      `提取时间: ${nowLocalTimestampUTC8 ? nowLocalTimestampUTC8() : nowLocalTimestampUTC8()}`, // 你已计划改名的话优先新名
      ""
    ].join("\n");

    const secMapping = pick.blocks.length
        ? [
          "===================================================================================================================",
          "主日志解析 - sdic 中 OKW 和 FRU 的 CPRI link mapping 关系",
          "===================================================================================================================",
          ...pick.blocks,
          ""
        ].join("\n")
        : [
          "===================================================================================================================",
          "主日志解析 - sdic 中 OKW 和 FRU 的 CPRI link mapping 关系",
          "===================================================================================================================",
          "(未找到 OKW + fru_xxx 同时出现的 mapping 块)",
          ""
        ].join("\n");

    const secLlog = buildSectionFromSegments(
        `RU诊断 - llog -l 中的 faulty/Faulty 段落`,
        faultySegs,
        ruText ? "(llog -l 未命中 faulty/Faulty)" : "(未找到对应 RU 日志内容)"
    );

    const antCalBasic = ruText
        ? copyRuSection(ruText, fru, "antCalBasic showAlg all")
        : "";

    const secantCalBasic = [
      "===================================================================================================================",
      "RU诊断 - antCalBasic showAlg all",
      "===================================================================================================================",
      antCalBasic || "(No Output)",
      ""
    ].join("\n");

    const fmFaultDetail = ruText
        ? copyRuSection(ruText, fru, "fm getfaults detail")
        : "";

    const secfmFaultDetail = [
      "===================================================================================================================",
      "RU诊断 - fm getfaults detail",
      "===================================================================================================================",
      fmFaultDetail || "(No Output)",
      ""
    ].join("\n");

    const hwlogRaw = ruText ? copyRuSection(ruText, fru, "hwlog read") : "";
    // 从 RU 文件中提取 hwlog read section (logid=000) 部分
    const secHwLogOnSiteTime = buildHwlog000MappingSection(hwlogRaw);

    // 从 RU 文件中提取 hwlog read section (logid=770/771) 部分
    const secHwLogFaultSource = buildHwlog770771MappingSection(hwlogRaw);

    // Alarm items 部分
    const secAlarmItems = [buildAlarmDiagnosticTextAas(ruText || ""), ""].join("\n");

    const footer = [
      "",
      "===================================================================================================================",
      "报告结束",
      `提取完成时间: ${nowLocalTimestampUTC8 ? nowLocalTimestampUTC8() : nowLocalTimestampUTC8}`,
      "==================================================================================================================="
    ].join("\n");

    reportsByFru.set(
        fru,
        [title, secMapping, secLlog, secantCalBasic, secfmFaultDetail, secHwLogOnSiteTime, secHwLogFaultSource, secAlarmItems, footer].join("\n")
    );
  }

  return { frus, mappingBlocks: pick.blocks, reportsByFru };
}


/* ------------------------ Proactive Log - AAS AIR6449 处理主流程，由 onProcess 调用 ------------------------ */
async function processProactiveAasAir6449(zipFile: File): Promise<void> {
  // 解析命名
  const name = zipFile.name;
  const parts = parseProNameParts(name);
  if (!parts) {
    skipped.value++;
    ElMessage.warning(`AAS Process: 文件名不符合规范: ${name}`);
    messages.value.push(`AAS Process: 跳过（命名不规范）: ${name}`);
    return;
  }

  // Step 1: 将原 .zip 文件中的 .log 转存到新的 _ProactiveLog.log 里 （完全复用 Remote 处理）
  // 解压 zip，读取第一个 .log
  const zip = await JSZip.loadAsync(zipFile);
  const logHit = await readFirstLogText(zip);
  if (!logHit) {
    ElMessage.warning(`AAS Process: 未找到 .log：${name}`);
    messages.value.push(`AAS Process: 未找到 .log：${name}`);
    return;
  }
  // 创建输出目录
  const root = outputDir.value!;
  const folder = await ensureDir(root, parts.baseFolder);
  // Step 1: ProactiveLog.log（完全复用 Remote 处理）
  const proactiveLogName = `${parts.serial}_${parts.node}_${parts.ymd}_${parts.hms}_ProactiveLog.log`;
  await writeTextFile(folder, proactiveLogName, logHit.text, false);

  messages.value.push(`AAS Process: Proactive Step 1: ${name} → ${parts.baseFolder}/${proactiveLogName}`)

  // Step 2：Link Failure / Resource Activation Timeout（完全复用 Remote 处理）
  const linkFailureText = buildLinkFailureReportText(logHit.text, {
    serial: parts.serial,
    node: parts.node,
    ymd: parts.ymd,
    hms: parts.hms,
    folderName: parts.baseFolder,
  });

  if (linkFailureText) {
    const lfName = `${parts.serial}_${parts.node}_${parts.ymd}_${parts.hms}_ProactiveLog_Link_Failure.txt`;
    await writeTextFile(folder, lfName, linkFailureText, true);

    messages.value.push(`AAS Process: Proactive Step 2: ${name} → 生成 ${lfName}`);
  } else {
    messages.value.push(`AAS Process: Proactive Step 2: ${name} → 未命中 Link Failure / Resource Activation Timeout`);
  }

  // Step 3：HW Partial Fault (AAS AIR6449)
  const reportText = buildHwPartialFaultReportTextAas(logHit.text, {
    serial: parts.serial,
    node: parts.node,
    ymd: parts.ymd,
    hms: parts.hms,
    proLogFile: proactiveLogName,
    folderName: parts.baseFolder,
  });

  const reportName = `${parts.serial}_${parts.node}_${parts.ymd}_${parts.hms}_ProactiveLog_Report.txt`;
  await writeTextFile(folder, reportName, reportText, true);

  messages.value.push(`AAS Process: Proactive Step 3: ${name} → 生成 ${reportName}`);

  // Step 4: Each RU Proactive Log (BXP_/FRU_ 均支持)（完全复用 Remote 处理）
  const ruPieces = buildEachRuProReportText(logHit.text);
  const ruMapLower = new Map<string, string>(); // 供 Diagnostic 使用（大小写兜底）
  let ruCreated = 0;
  for (const [lnh, ruText] of ruPieces.entries()) {
    const ruName = `${parts.serial}_${parts.node}_${parts.ymd}_${parts.hms}_${lnh}_ProactiveLog.log`;
    await writeTextFile(folder, ruName, ruText, true);
    ruCreated++;
    ruMapLower.set(lnh.toLowerCase(), ruText);
  }
  messages.value.push(`AAS Process: Proactive Step 4: ${name} → 生成 ${ruCreated} 个 RU 日志文件`);

  // Step 5: Fault Diagnostic Report (AAS AIR6449)
  const diag = buildFaultDiagnosticReportTextAas(
      reportText,
      ruMapLower,
      { serial: parts.serial, node: parts.node, ymd: parts.ymd, hms: parts.hms, folderName: parts.baseFolder }
  );

  if (!diag.frus.length) {
    messages.value.push(`AAS Process: Proactive Step 5: ${name} → sdic 未找到 OKW+fru_xxx mapping，不生成诊断报告`);
  } else {
    let created = 0;
    for (const fru of diag.frus) {
      const outText = diag.reportsByFru.get(fru);
      if (!outText) continue;

      const diagName = `${parts.serial}_${parts.node}_${parts.ymd}_${parts.hms}_${fru}_ProactiveLog_Diagnostic_Report.txt`;
      await writeTextFile(folder, diagName, outText, true);
      created++;
    }
    messages.value.push(`AAS Process: Proactive Step 5: ${name} → 生成 ${created} 份 FRU 诊断报告（llog faulty 段落）`);
  }

}


// =====================================================================================================================
//                                          八. Overall onProcess / onCancel
// =====================================================================================================================
async function onProcess(): Promise<void> {
  // Radio 类型分流
  if (radioType.value !== 'Remote' && radioType.value !== 'AAS AIR6449') {
    messages.value.push(
        `Only supports Remote and AAS AIR6449, current type is "${radioType.value}", which is unsupported`
    );
    return;
  }

  if (!dirPickerSupported) {
    ElMessage.warning("Browser does not support writing to this directory");
    return;
  }
  if (!outputDir.value) {
    await chooseOutputDir();
    if (!outputDir.value) return;
  }

  let zips: File[];
  if (sourceMode.value === "files") {
    zips = [...files.value];
  } else {
    zips = await collectZips();
  }
  if (!zips.length) {
    ElMessage.info("No .zip file to be processed");
    return;
  }

  running.value = true;
  cancelRequested.value = false;
  progress.value = { total: zips.length, done: 0, current: "" };
  outFiles.value = 0;
  skipped.value = 0;
  messages.value = [];

  try {
    await forEachLimit(zips, concurrency.value, async (zipFile) => {
      if (cancelRequested.value) return;

      const name = zipFile.name;
      progress.value.current = name;

      // ====== LAT log 分支 ======
      try {
        // 按名称判断：Proactive vs LAT
        if (!isProactiveZipName(name)) {
          // --- LAT：先走 common 提取 ---
          const ctx = await processLatCommon(zipFile, outputDir.value!);

          // Remote / AAS 分支预留
          if (radioType.value === 'Remote') {
            await processLatRemote(ctx, name);
          } else {
            await processLatAasAir6449(ctx, name); // 目前为空壳（只做了 common 提取）
          }

          const extracted = [
            ctx.elogText ? 'elog' : null,
            ctx.hwlogText ? 'hwlog' : null,
            ctx.telogText ? 'telog' : null
          ].filter(Boolean).join('/');

          messages.value.push(`LAT 完成：${name} → 输出到 ${ctx.base}/；提取: ${extracted || '无'}`);
          return;
        }

        // ====== Proactive Log 分支 ======
        if (radioType.value === 'Remote') {
          await processProactiveRemote(zipFile);
        } else {
          await processProactiveAasAir6449(zipFile);
        }
      } catch (e: any) {
        ElMessage.error(e?.message || `处理失败：${name}`);
        messages.value.push(`失败：${name} - ${e?.message || e}`);
      } finally {
        progress.value.done++;
      }
    });

    if (cancelRequested.value) ElMessage.info("已取消处理");
    else ElMessage.success("处理完成");
  } finally {
    running.value = false;
    progress.value.current = "";
  }
}

function onCancel(): void {
  cancelRequested.value = true;
}
</script>

<style scoped>
.desc {
  color: var(--text-2);
  margin-top: 2px;
  margin-bottom: 12px;
}
.hint { color: var(--text-2); }

.list {
  margin: 6px 0;
  padding-left: 16px;
  max-height: 220px;
  overflow: auto;
}
.sum-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}
.chosen { margin-top: 10px; }

.bulk-progress { margin: 12px 0; max-width: 640px; }
.progress-line { color: var(--text-2); font-size: 12px; margin-top: 4px; }

/* 深色背景白字：已选文件/执行日志等 */
.list li,
.chosen,
.sum-row,
.progress-line,
.exec-log li {
  color: #ffffff !important;
}

/* 并行设置容器：列方向，固定宽度，左对齐 */
.concurrency-field {
  display: flex;
  flex-direction: column;
  align-items: flex-start;   /* 确保子项左对齐 */
  margin-left: 16px;         /* 与左侧控件（按钮/目录标签）保持间距 */
  width: 160px;              /* 统一容器宽度，使上下对齐 */
}

/* 统一 input-number 的宽度 */
.concurrency-input {
  width: 160px;
}

/* 下方说明的样式（与上传控件提示类似） */
.concurrency-help {
  font-size: 12px;
  color: var(--text-2);
  margin-top: 4px;
  line-height: 1.4;
  text-align: left;          /* 明确左对齐 */
  width: 100%;               /* 与容器同宽，边缘对齐 input */
}
</style>
