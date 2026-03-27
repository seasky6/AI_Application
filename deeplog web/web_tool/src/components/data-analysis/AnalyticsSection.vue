<template>
  <div class="deeplog-card" style="margin-top: 24px">
    <h3>{{ $t('dataAnalysisPage.analysis.title') }}</h3>

    <!-- 选择数据库文件 -->
    <el-form label-width="140px" style="margin-top:16px">

      <el-form-item :label="$t('dataAnalysisPage.analysis.chooseDbFile')">
        <el-button type="primary" @click="pickDbFile">
          {{ $t('dataAnalysisPage.analysis.chooseDbBtn') }}
        </el-button>
        <span v-if="dbFileName" style="margin-left:12px; opacity:.7">
          {{ dbFileName }}
        </span>
      </el-form-item>

      <!-- 分析类型：现阶段只支持日志类型统计 -->
      <el-form-item :label="$t('dataAnalysisPage.analysis.analysisType')">
        <el-select v-model="analysisType" style="width:240px">
          <el-option label="Log Type Statistic" value="logType" />
          <el-option label="Product Type Statistic" value="productType" />
          <el-option label="Sub Log Type Statistic" value="subLogType" />
        </el-select>
      </el-form-item>

      <el-form-item :label="$t('dataAnalysisPage.analysis.chartType')">
        <el-select v-model="chartType" style="width:240px">
          <!-- ProductType 可以用 Pie -->
          <el-option v-if="analysisType === 'productType'" label="Pie" value="pie" />
          <el-option label="Histogram" value="bar" />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="handleAnalyze" :disabled="!dbReady">
          {{ $t('dataAnalysisPage.analysis.analyzeBtn') }}
        </el-button>
      </el-form-item>

    </el-form>

    <!-- 分析结果：图表 -->
    <div v-if="chartOption" style="margin-top:20px">
      <h4>{{ $t('dataAnalysisPage.analysis.result') }}</h4>
      <div ref="chartRef" style="width:100%; height:420px;"></div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue';
import * as echarts from 'echarts';

type DbRecord = {
  serialNumber: string;
  firstDate?: string | null;
  lastDate?: string | null;
  logTypes: string[];
  zips: string[];
};
type DbFile = {
  version: number;
  updatedAt: string;
  records: DbRecord[];
};

// UI 数据
const dbFileName = ref('');
const dbRecords = ref<DbRecord[]>([]);
const dbReady = ref(false);

const analysisType = ref<'logType' | 'productType' | 'subLogType'>('logType'); // 当前分析项
const chartType = ref<'pie' | 'bar'>('pie'); // 图表样式

const chartOption = ref<any>(null);
const chartRef = ref<HTMLDivElement | null>(null);


watch(analysisType, (v) => {
  if (v === 'logType' || v === 'subLogType') {
    chartType.value = 'bar';           // ★ 强制柱状图
  }
});


// 复用 ECharts 实例，避免重复 init
const chartIns = ref<echarts.ECharts | null>(null);

function ensureChart() {
  if (chartRef.value && !chartIns.value) {
    chartIns.value = echarts.init(chartRef.value);
    // 可选：窗口自适应
    window.addEventListener('resize', () => chartIns.value?.resize());
  }
}

// 压缩产品型号名称（去掉前缀 Radio/AIR/RRU，只保留后部）
function simplifyProductName(name: string): string {
  if (!name) return '';
  return name
      .replace(/^Radio\s+/i, '')   // 删除 “Radio ”
      .replace(/^AIR\s*/i, '')     // 删除 “AIR ”
      .replace(/^RRU\s*/i, '')     // 删除 “RRU ”
      .trim();
}

// ===================================================
// 1) 通用工具函数
// ===================================================
// 选择数据库文件
async function pickDbFile() {
  try {
    const [handle] = await (window as any).showOpenFilePicker({
      types: [
        {
          description: 'DeepLog DB',
          accept: { 'application/json': ['.json'] }
        }
      ],
      multiple: false
    });

    const file = await handle.getFile();
    const json = JSON.parse(await file.text()) as DbFile;
    if (!json.records) {
      alert('Not a valid DeepLog database file!');
      return;
    }

    dbFileName.value = file.name;
    dbRecords.value = json.records;
    dbReady.value = true;

  } catch (err) {
    console.warn('DB pick cancelled:', err);
  }
}

// 日志/子日志类型 按 SN 是否出现计数(0/1) 每个 SN 对同一类型最多贡献 1 次（出现过即记 1）
function buildPresenceCounterBySn<T extends { serialNumber: string }>(
    records: T[],
    // 提取某记录中“类型列表”的函数，例如 r.logTypes / r.subLogTypes
    pickTypes: (r: T) => string[] | undefined,
    // 归一化（大小写、空白等）
    normalize?: (s: string) => string
): { labels: string[]; values: number[]; totalSN: number; counts: Record<string, number> } {
  const norm = normalize ?? ((s: string) => (s || '').trim());
  const perSnSets = new Map<string, Set<string>>(); // SN -> Set(出现过的类型)

  for (const r of records) {
    const sn = (r.serialNumber || '').trim();
    if (!sn) continue;
    const types = (pickTypes(r) || []).map(norm).filter(Boolean);
    if (types.length === 0) {
      if (!perSnSets.has(sn)) perSnSets.set(sn, new Set());
      continue;
    }
    const set = perSnSets.get(sn) ?? new Set<string>();
    for (const t of types) set.add(t);
    perSnSets.set(sn, set);
  }

  // 汇总：对每个类型，统计“有该类型的 SN 数量”
  const counter = new Map<string, number>();
  for (const [, typeSet] of perSnSets) {
    for (const t of typeSet) {
      counter.set(t, (counter.get(t) || 0) + 1);
    }
  }

  const labels = Array.from(counter.keys());
  const values = labels.map(l => counter.get(l)!);
  const totalSN = perSnSets.size || records.length; // 通常等于 records.length（每条记录一个 SN）

  // 回传一个 counts 便于 tooltip/label 函数使用
  const counts: Record<string, number> = {};
  labels.forEach((l, i) => (counts[l] = values[i]));

  return { labels, values, totalSN, counts };
}

function toPct(n: number, d: number): string {
  if (!d) return '0.0';
  return ((n / d) * 100).toFixed(1);
}

// ===================================================
// 2) 分析：日志类别统计，产品型号统计，子日志类别统计
// ===================================================
function handleAnalyze() {
  if (!dbReady.value) {
    alert('Choose a DB file！');
    return;
  }

  if (analysisType.value === 'logType') {
    analyzeLogTypes();
  } else if (analysisType.value === 'productType') {
    analyzeProductTypes();
  } else if (analysisType.value === 'subLogType') {
    analyzeSubLogTypes();
  }
}

// 遍历所有 logTypes 统计数量 + 百分比
function analyzeLogTypes() {
  // 1) 用新口径统计：某 SN 只要包含某 logType 就记 1 次
  const { labels, values, totalSN, counts } = buildPresenceCounterBySn(
      dbRecords.value,
      (r) => r.logTypes,                    // 从记录里取“类型列表”
      (s) => (s || '').trim()               // 可以在这里做 normalize（大小写归一、别名映射等）
  );
  // 2) 仅柱状图
  chartOption.value = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params;
        const name = p.name;
        const cnt = counts[name] ?? p.value;
        const pct = toPct(cnt, totalSN);
        return `${name}<br/>SN count: ${cnt}/${totalSN}<br/>Percent: ${pct}%`;
      }
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        color: '#ffffff',
        fontWeight: 'bold',
        // 如需展示全部且避免重叠：
        // interval: 0,
        // rotate: 30
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#ffffff', fontWeight: 'bold' }
    },
    series: [
      {
        type: 'bar',
        data: values, // 仍使用“次数”
        label: {
          show: true,
          color: '#ffffff',
          fontWeight: 'bold',
          textShadowColor: 'transparent',
          textShadowBlur: 0,
          formatter: (p: any) => {
            const name = p.name;
            const cnt = counts[name] ?? p.value;
            const pct = toPct(cnt, totalSN);
            return `${cnt} (${pct}%)`;
          }
        }
      }
    ]
  };
  // 渲染图表
  nextTick(() => {
    const inst = chartRef.value ? (echarts.getInstanceByDom(chartRef.value) || echarts.init(chartRef.value)) : null;
    if (!inst) return;
    inst.clear();
    inst.setOption(chartOption.value, { notMerge: true });
  });
}

// 遍历所有 productName 统计数量 + 百分比
function analyzeProductTypes() {
  const counter: Record<string, number> = {};

  for (const rec of dbRecords.value) {
    const raw = (rec as any).productName || '';
    const name = simplifyProductName(raw);   // ★ 压缩名称

    if (!name) continue;
    counter[name] = (counter[name] || 0) + 1;
  }

  const total = Object.values(counter).reduce((a, b) => a + b, 0);
  const labels = Object.keys(counter);
  const values = labels.map(l => counter[l]);

  if (chartType.value === 'pie' && analysisType.value === 'productType') {
    chartOption.value = {
      tooltip: { trigger: 'item' },
      grid: { left: 0, right: 0, top: 0, bottom: 0 },
      series: [{
        type: 'pie',
        radius: '60%',
        label: {
          color: '#ffffff',
          fontWeight: 'bold',
          textShadowColor: 'transparent',
          textShadowBlur: 0
        },
        data: labels.map(l => ({
          name: `${l} (${((counter[l] / total) * 100).toFixed(1)}%)`,
          value: counter[l]
        }))
      }]
    };
  } else {
    chartOption.value = {
      tooltip: {},
      xAxis: {
        type: 'category',
        data: labels,
        axisLabel: {
          color: '#ffffff',
          fontWeight: 'bold',
          interval: 0,        // ★ 显示所有标签
          rotate: 45,         // ★ 避免重叠（可改 30/60/90）
        }
      },
      yAxis: {
        type: 'value',
        axisLabel: { color: '#ffffff', fontWeight: 'bold' }
      },
      series: [{
        type: 'bar',
        data: values,
        label: {
          show: true,
          color: '#ffffff',
          fontWeight: 'bold',
          textShadowColor: 'transparent',
          textShadowBlur: 0
        }
      }]
    };
  }
  // 渲染
  nextTick(() => {
    ensureChart();
    if (chartIns.value) {
      chartIns.value.clear();                                 // ★ 先清空，去除遗留坐标轴
      chartIns.value.setOption(chartOption.value, {
        notMerge: true,                                       // ★ 禁止合并
        lazyUpdate: false
      });
    }
  });
}

// 遍历所有 subLogTypes 统计数量 + 百分比
function analyzeSubLogTypes() {
  // 1) 新口径：对每个 SN，subLogTypes 去重后每种子日志最多记 1 次
  const { labels, values, totalSN, counts } = buildPresenceCounterBySn(
      dbRecords.value as any,
      (r: any) => r.subLogTypes as string[] | undefined,
      (s) => (s || '').trim().toLowerCase()
  );
  chartOption.value = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params;
        const name = p.name;
        const cnt = counts[name] ?? p.value;
        const pct = toPct(cnt, totalSN);
        return `${name}<br/>SN count: ${cnt}/${totalSN}<br/>Percent: ${pct}%`;
      }
    },
    xAxis: {
      type: 'category',
      data: labels,
      axisLabel: {
        color: '#ffffff',
        fontWeight: 'bold',
        // interval: 0,
        // rotate: 30
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#ffffff', fontWeight: 'bold' }
    },
    series: [
      {
        type: 'bar',
        data: values,
        label: {
          show: true,
          color: '#ffffff',
          fontWeight: 'bold',
          textShadowColor: 'transparent',
          textShadowBlur: 0,
          formatter: (p: any) => {
            const name = p.name;
            const cnt = counts[name] ?? p.value;
            const pct = toPct(cnt, totalSN);
            return `${cnt} (${pct}%)`;
          }
        }
      }
    ]
  };
  nextTick(() => {
    const inst = chartRef.value ? (echarts.getInstanceByDom(chartRef.value) || echarts.init(chartRef.value)) : null;
    if (!inst) return;
    inst.clear();
    inst.setOption(chartOption.value, { notMerge: true });
  });
}
</script>

<style scoped>
</style>
