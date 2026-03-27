<template>

  <el-page-header
      :content="String($t('predictPage.processLogs.title'))"
      @back="$router.push({ name: 'dashboard' })"
  />

  <!-- ============================================================================================================= -->
  <!-- 1. 数据抓取与数据处理 -->
  <!-- ============================================================================================================= -->
  <div class="deeplog-card" style="margin-top:16px">
    <h3>{{ $t('predictPage.processLogs.source.title') }}</h3>
    <p class="desc">{{ $t('predictPage.processLogs.source.desc') }}</p>




    <el-space wrap>
      <el-radio-group v-model="sourceMode">
        <el-radio label="files">{{ $t('predictPage.processLogs.source.files') }}</el-radio>
        <el-radio label="folders">{{ $t('predictPage.processLogs.source.folders') }}</el-radio>
      </el-radio-group>

      <!-- 选择 ZIP 文件 -->
      <el-upload
          v-if="sourceMode === 'files'"
          drag
          multiple
          :auto-upload="false"
          :on-change="onFilesPicked"
          :show-file-list="false"
          accept=".zip"
          style="width:520px"
      >
        <i class="el-icon--upload el-icon">
          <svg viewBox="0 0 1024 1024" width="22" height="22">
            <path d="M512 64l256 256h-160v256h-192V320H256L512 64zM192 704h640v192H192V704z" fill="currentColor" />
          </svg>
        </i>
        <div class="el-upload__text">
          {{ $t('predictPage.processLogs.source.dropOrClick') }}
          <em>{{ $t('predictPage.processLogs.source.chooseFiles') }}</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            {{ $t('predictPage.processLogs.source.filesTip') }}
          </div>
        </template>
      </el-upload>

      <!-- 选择目录 -->
      <div v-else>
        <el-button type="primary" @click="onPickFolder">
          {{ $t('predictPage.processLogs.source.addFolder') }}
        </el-button>

        <el-button @click="clearFolders" :disabled="!dirHandles.length">
          {{ $t('predictPage.processLogs.source.clearFolders') }}
        </el-button>

        <span class="hint" style="margin-left:12px">
          <el-tag v-if="!dirPickerSupported" type="warning" size="small" effect="plain">
            {{ $t('predictPage.processLogs.source.dirNotSupported') }}
          </el-tag>

          <template v-else>
            {{ $t('predictPage.processLogs.source.folderCount', { n: dirHandles.length }) }}
          </template>
        </span>
      </div>
    </el-space>

    <!-- 多产品模式/自动预测开关（仅 folders 模式可用） -->
    <el-divider direction="vertical" />

    <el-switch
        v-model="multiProductMode"
        :disabled="sourceMode !== 'folders'"
        active-text="多个产品预测"
        inactive-text="单个产品预测"
    />

    <el-switch
        v-model="autoPredictAfterProcess"
        :disabled="!multiProductMode || !modelReady"
        active-text="直接预测"
        inactive-text="只处理日志文件，稍后手动触发预测"
    />


<!--    &lt;!&ndash; =================================================================== &ndash;&gt;-->
<!--    &lt;!&ndash; 从 PQAT 下载并自动处理：固定按 SN 创建子目录           &ndash;&gt;-->
<!--    &lt;!&ndash; =================================================================== &ndash;&gt;-->
<!--    <el-divider />-->

<!--    <h4>{{ $t('downloadLogPage.download') }}</h4>-->
<!--    <p class="desc">{{ $t('downloadLogPage.downloadDesc') }}</p>-->

<!--    <el-form :model="pqatForm" label-width="140px" class="form" @submit.prevent>-->
<!--      <el-form-item :label="$t('downloadLogPage.eidUser') as string">-->
<!--        <el-input v-model="pqatForm.eidUser" autocomplete="username" placeholder="e.g., erid12345" />-->
<!--      </el-form-item>-->

<!--      <el-form-item :label="$t('downloadLogPage.eidKey') as string">-->
<!--        <el-input v-model="pqatForm.eidKey" type="password" autocomplete="current-password" show-password />-->
<!--      </el-form-item>-->

<!--      <el-form-item :label="$t('downloadLogPage.serialNumber') as string">-->
<!--        <el-input-->
<!--            v-model="pqatForm.serialsText"-->
<!--            type="textarea"-->
<!--            :rows="4"-->
<!--            placeholder="支持多行或逗号分隔，如：&#10;CN38699365&#10;TU8U02GTHS"-->
<!--        />-->
<!--      </el-form-item>-->

<!--      <el-form-item :label="$t('downloadLogPage.logType')">-->
<!--        <el-select v-model="pqatForm.logType" style="min-width: 240px">-->
<!--          <el-option :label="'All (0)'" :value="0" />-->
<!--          <el-option :label="'ExtLog (1)'" :value="1" />-->
<!--          <el-option :label="'Site Failure Note (2)'" :value="2" />-->
<!--          <el-option :label="'Proactive Logs (3)'" :value="3" />-->
<!--          <el-option :label="'HWS Scrap Pictures (4)'" :value="4" />-->
<!--        </el-select>-->
<!--      </el-form-item>-->

<!--      <el-form-item :label="$t('downloadLogPage.logTimeWindow')">-->
<!--        <el-radio-group v-model="pqatForm.timeStrobe">-->
<!--          <el-radio :value="0">All</el-radio>-->
<!--          <el-radio :value="-1">Latest</el-radio>-->
<!--        </el-radio-group>-->
<!--        <el-input-number-->
<!--            v-model="pqatForm.timeCount"-->
<!--            :min="1"-->
<!--            :step="1"-->
<!--            controls-position="right"-->
<!--            style="margin-left:16px; width: 160px"-->
<!--            :placeholder="'N (可选)'"-->
<!--        />-->
<!--        <span class="hint">{{ $t('downloadLogPage.timeHint') }}</span>-->
<!--      </el-form-item>-->

<!--      &lt;!&ndash; 保存根目录 &ndash;&gt;-->
<!--      <el-form-item :label="$t('predictPage.processLogs.run.chooseOutputDir') as string">-->
<!--        <el-button @click="onChoosePqatRoot" :disabled="pqatDownloading">-->
<!--          选择保存目录-->
<!--        </el-button>-->
<!--        <el-button @click="onClearPqatRoot" :disabled="pqatDownloading || !pqatRootLabel">-->
<!--          清除-->
<!--        </el-button>-->
<!--        <span class="hint" style="margin-left:8px" v-if="pqatRootLabel">-->
<!--          已选择：<strong>{{ pqatRootLabel }}</strong>-->
<!--        </span>-->
<!--      </el-form-item>-->

<!--      &lt;!&ndash; 一键下载并处理 &ndash;&gt;-->
<!--      <el-form-item>-->
<!--        <el-button-->
<!--            type="primary"-->
<!--            :loading="pqatDownloading"-->
<!--            @click="onDownloadAndProcess"-->
<!--        >-->
<!--          一键处理-->
<!--        </el-button>-->

<!--        &lt;!&ndash; 复用已有开关：处理后自动预测 &ndash;&gt;-->
<!--        <el-checkbox-->
<!--            v-model="autoPredictAfterProcess"-->
<!--            :disabled="!modelReady"-->
<!--            style="margin-left:16px"-->
<!--        >-->
<!--          处理后自动预测-->
<!--        </el-checkbox>-->

<!--        <span v-if="!modelReady" class="hint" style="margin-left:8px">（未加载模型时将跳过自动预测）</span>-->
<!--      </el-form-item>-->
<!--    </el-form>-->

    <!-- 下载进度 -->
    <div v-if="pqatDownloading" class="bulk-progress">
      <el-progress :percentage="pqatPercent" :text-inside="true" :stroke-width="18" />
      <div class="progress-line">
        <span>下载进度：{{ pqatProgress.done }}/{{ pqatProgress.total }}</span>
        <span v-if="pqatProgress.current" style="margin-left:12px">{{ pqatProgress.current }}</span>
      </div>
    </div>


    <!-- 已选摘要 -->
    <div class="chosen" v-if="sourceMode === 'files' ? files.length : dirHandles.length">
      <template v-if="sourceMode === 'files'">
        <div class="sum-row">
          <strong>{{ $t('predictPage.processLogs.source.filesChosen', { n: files.length }) }}</strong>
          <el-link v-if="files.length" type="primary" @click="clearFiles">{{ $t('predictPage.common.clear') }}</el-link>
        </div>
        <ul class="list">
          <li v-for="f in files" :key="f.name + f.size">{{ f.name }}</li>
        </ul>
      </template>
      <template v-else>
        <div class="sum-row">
          <strong>{{ $t('predictPage.processLogs.source.foldersChosen', { n: dirHandles.length }) }}</strong>
        </div>
        <ul class="list">
          <li v-for="(dirHandle, idx) in dirHandles" :key="idx">
            {{ dirHandle.name || 'Folder' }}
          </li>
        </ul>
      </template>
    </div>

    <!-- 操作按钮 -->
    <div style="margin-top:16px">
      <el-space wrap>
        <!-- 输出目录 -->
        <div>
          <el-button @click="onChooseOutputDir" :disabled="running">
            {{ $t('predictPage.processLogs.run.chooseOutputDir') }}
          </el-button>
          <el-button @click="onClearOutputDir" :disabled="running || !outputDirHandle">
            {{ $t('predictPage.processLogs.run.clearOutputDir') }}
          </el-button>
          <span class="hint" style="margin-left:8px" v-if="outputDirLabel">
            {{ $t('predictPage.processLogs.run.outputDirLabel') }}: <strong>{{ outputDirLabel }}</strong>
          </span>
        </div>

        <div class="concurrency-field">
          <el-input-number
              v-model="concurrency"
              :min="1"
              :max="8"
              :step="1"
              :disabled="running"
              style="width:160px"
              :placeholder="$t('predictPage.processLogs.run.concurrency')"
          />
          <span class="concurrency-help">
            {{ $t('predictPage.processLogs.run.concurrencyDesc') }}
          </span>
        </div>

        <el-button
            type="primary"
            :disabled="!canRun"
            :loading="running"
            @click="onRun"
        >
          {{ $t('predictPage.processLogs.run.start') }}
        </el-button>

        <el-button type="danger" :disabled="!running" @click="onCancel">
          {{ $t('predictPage.processLogs.run.cancel') }}
        </el-button>

        <!-- 已移除：导出CSV / 保存到目录 -->
      </el-space>
    </div>




    <!-- 进度 -->
    <div v-if="running || progress.totalFiles" class="bulk-progress">
      <el-progress :percentage="progressPercent" :text-inside="true" :stroke-width="18" />
      <div class="progress-line">
        <span>{{ $t('predictPage.processLogs.run.filesProgress', { d: progress.doneFiles, t: progress.totalFiles }) }}</span>
        <span v-if="progress.currentName" style="margin-left:12px">{{ progress.currentName }}</span>
      </div>
      <div class="progress-line">
        <span>{{ $t('predictPage.processLogs.run.entriesAccum', { n: progress.totalEntries }) }}</span>
        <span v-if="errors.length" style="margin-left:12px;color:#d93025">
          {{ $t('predictPage.processLogs.run.errors', { n: errors.length }) }}
        </span>
      </div>
    </div>

    <!-- 处理结果：展示文件列表 -->
    <div style="margin-top:16px">
      <h4>{{ $t('predictPage.processLogs.result.title') }}</h4>
      <p class="desc">{{ $t('predictPage.processLogs.result.desc2') }}</p>

      <template v-if="generatedFiles.length">
        <el-table :data="generatedFiles" height="340" size="small" style="margin-top:12px">
          <!-- 原 ZIP -->
          <el-table-column prop="zipName" :label="$t('predictPage.processLogs.result.srcZip')" width="320" />

          <!-- 抽取 XLSX -->
          <el-table-column prop="xlsxName" :label="$t('predictPage.processLogs.result.outXlsx')" width="360">
            <template #default="{ row }">
              <el-link type="primary" @click="openSavedFile({ handle: row.xlsxHandle, url: row.xlsxUrl })">
                {{ row.xlsxName }}
              </el-link>
            </template>
          </el-table-column>

          <!-- 解析 JSON -->
          <el-table-column prop="parsedJsonName" :label="$t('predictPage.processLogs.result.outParsedJson')" width="360">
            <template #default="{ row }">
              <template v-if="row.parsedJsonName">
                <el-link type="primary" @click="openSavedFile({ handle: row.parsedJsonHandle, url: row.parsedJsonUrl })">
                  {{ row.parsedJsonName }}
                </el-link>
              </template>
              <span v-else>—</span>
            </template>
          </el-table-column>

          <!-- 解析 XLSX -->
          <el-table-column prop="parsedXlsxName" :label="$t('predictPage.processLogs.result.outParsedXlsx')" width="360">
            <template #default="{ row }">
              <template v-if="row.parsedXlsxName">
                <el-link type="primary" @click="openSavedFile({ handle: row.parsedXlsxHandle, url: row.parsedXlsxUrl })">
                  {{ row.parsedXlsxName }}
                </el-link>
              </template>
              <span v-else>—</span>
            </template>
          </el-table-column>

          <!-- 样本生成 JSON -->
          <el-table-column prop="paSamplesJsonName" :label="$t('predictPage.processLogs.result.paSamplesJson')" width="360">
            <template #default="{ row }">
              <template v-if="row.paSamplesJsonName">
                <el-link type="primary" @click="openSavedFile({ handle: row.paSamplesJsonHandle, url: row.paSamplesJsonUrl })">
                  {{ row.paSamplesJsonName }}
                </el-link>
              </template>
              <span v-else>—</span>
            </template>
          </el-table-column>

          <!-- 样本生成 XLSX -->
          <el-table-column prop="paSamplesXlsxName" :label="$t('predictPage.processLogs.result.paSamplesXlsx')" width="360">
            <template #default="{ row }">
              <template v-if="row.paSamplesXlsxName">
                <el-link type="primary" @click="openSavedFile({ handle: row.paSamplesXlsxHandle, url: row.paSamplesXlsxUrl })">
                  {{ row.paSamplesXlsxName }}
                </el-link>
              </template>
              <span v-else>—</span>
            </template>
          </el-table-column>

          <!-- 样本预处理 JSON -->
          <el-table-column prop="paSamplesPreprocessJsonName" :label="$t('predictPage.processLogs.result.samplesPreJson')" width="420">
            <template #default="{ row }">
              <template v-if="row.paSamplesPreprocessJsonName">
                <el-link type="primary"
                         @click="openSavedFile({ handle: row.paSamplesPreprocessJsonHandle, url: row.paSamplesPreprocessJsonUrl })">
                  {{ row.paSamplesPreprocessJsonName }}
                </el-link>
              </template>
              <span v-else>—</span>
            </template>
          </el-table-column>

          <!-- 样本预处理 XLSX -->
          <el-table-column prop="paSamplesPreprocessXlsxName" :label="$t('predictPage.processLogs.result.samplesPreXlsx')" width="420">
            <template #default="{ row }">
              <template v-if="row.paSamplesPreprocessXlsxName">
                <el-link type="primary"
                         @click="openSavedFile({ handle: row.paSamplesPreprocessXlsxHandle, url: row.paSamplesPreprocessXlsxUrl })">
                  {{ row.paSamplesPreprocessXlsxName }}
                </el-link>
              </template>
              <span v-else>—</span>
            </template>
          </el-table-column>

          <!-- 文件位置 -->
          <el-table-column :label="$t('predictPage.processLogs.result.location')">
            <template #default="{ row }">
              <span v-if="row.dirLabel">{{ row.dirLabel }}</span>
              <span v-else>—</span>
            </template>
          </el-table-column>

        </el-table>
      </template>
      <el-empty v-else :description="$t('predictPage.processLogs.result.placeholder')" />
    </div>

    <!-- 错误列表 -->
    <div v-if="errors.length" style="margin-top:16px">
      <h4>{{ $t('predictPage.processLogs.errors.title') }}</h4>
      <el-alert
          v-for="(e, idx) in errors"
          :key="idx"
          type="error"
          :title="e.name"
          :description="e.message"
          show-icon
          :closable="false"
      />
    </div>
  </div>

  <!-- ============================================================================================================= -->
  <!-- 2. 模型预测 (Version1, XGBOOST without/with CGAN) —— 调用后端 Flask API -->
  <!-- ============================================================================================================= -->
  <div class="deeplog-card" style="margin-top:16px">
    <h3>{{ $t('predictPage.model.title') }}</h3>
    <p class="desc">{{ $t('predictPage.model.desc') }}</p>

    <!-- 控件区 -->
    <el-space wrap>
      <!-- 目标数据来源（已从上一阶段生成） -->
      <el-tag type="info" effect="plain">
        {{ $t('predictPage.model.sourceHint', { n: generatedFiles.length }) }}
      </el-tag>

      <!-- 加载模型（探测后端健康） -->
      <el-button :loading="modelLoading" :disabled="modelReady"
                 type="primary" @click="onLoadModels">
        {{ modelReady ? $t('predictPage.model.loaded') : $t('predictPage.model.load') }}
      </el-button>

      <!-- 开跑 -->
      <el-button type="success"
                 :disabled="!modelReady || !hasPreprocessedJson || predicting"
                 :loading="predicting"
                 @click="onRunPrediction">
        {{ $t('predictPage.model.run') }}
      </el-button>

      <!-- 清理结果 -->
      <el-button :disabled="predicting || !predictionResults.length" @click="onClearPrediction">
        {{ $t('predictPage.model.clear') }}
      </el-button>

      <!-- 打印报告 -->
      <el-button :disabled="!predictionResults.length" @click="onPrintReport">
        {{ $t('predictPage.model.print') }}
      </el-button>
    </el-space>

    <!-- 推理进度 -->
    <div v-if="predicting || predictProgress.totalSteps" class="bulk-progress" style="margin-top:12px">
      <el-progress :percentage="predictProgressPercent" :text-inside="true" :stroke-width="18" />
      <div class="progress-line">
        <span>{{ $t('predictPage.model.progressFiles', { d: predictProgress.doneUnits, t: predictProgress.totalUnits }) }}</span>
        <span v-if="predictProgress.currentName" style="margin-left:12px">{{ predictProgress.currentName }}</span>
      </div>
      <div class="progress-line">
        <span>{{ $t('predictPage.model.progressSteps', { d: predictProgress.doneSteps, t: predictProgress.totalSteps }) }}</span>
        <span v-if="predictionErrors.length" style="margin-left:12px;color:#d93025">
        {{ $t('predictPage.model.errors', { n: predictionErrors.length }) }}
      </span>
      </div>
    </div>

    <!-- 结果汇总（产品级别） -->
    <div v-if="predictionResults.length" style="margin-top:18px">
      <h4>{{ $t('predictPage.model.resultSummary') }}</h4>
      <p class="desc">{{ $t('predictPage.model.resultSummaryDesc') }}</p>

      <el-table :data="predictionResults" height="320" size="small" style="margin-top:8px">
        <el-table-column prop="serial" :label="$t('predictPage.model.col.serial')" width="180" />
        <el-table-column prop="productName" :label="$t('predictPage.model.col.productName')" width="220" />
        <el-table-column prop="normalModelMajority" :label="$t('predictPage.model.col.normalModel')" width="160">
          <template #default="{ row }">
            <el-tag :type="row.normalModelMajority==='PA Abnormal' ? 'danger' : 'success'">
              {{ row.normalModelMajority }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="cganModelMajority" :label="$t('predictPage.model.col.cganModel')" width="160">
          <template #default="{ row }">
            <el-tag :type="row.cganModelMajority==='PA Abnormal' ? 'danger' : 'success'">
              {{ row.cganModelMajority }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="finalDecision" :label="$t('predictPage.model.col.finalDecision')" width="180">
          <template #default="{ row }">
            <el-tag
                :type="row.finalDecision==='PA Abnormal' ? 'danger' : (row.finalDecision==='May PA Abnormal' ? 'warning' : 'success')">
              {{ row.finalDecision }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="$t('predictPage.model.col.distribution')">
          <template #default="{ row }">
            <!-- 空样本：固定文案 -->
            <div v-if="row.noFeatures" style="line-height:1.5">
              <div><strong>XGBoost (Normal):</strong> 无PA异常相关特征值</div>
              <div><strong>XGBoost (CGAN):</strong> 无PA异常相关特征值</div>
            </div>

            <!-- 非空样本：显示百分比 -->
            <div v-else style="line-height:1.5">
              <div><strong>XGBoost (Normal):</strong>
                {{ $t('predictPage.model.dist', { pa: (row.distribution.normal.paAbnormalPct*100).toFixed(1), nor: (row.distribution.normal.normalPct*100).toFixed(1) }) }}
              </div>
              <div><strong>XGBoost (CGAN):</strong>
                {{ $t('predictPage.model.dist', { pa: (row.distribution.cgan.paAbnormalPct*100).toFixed(1), nor: (row.distribution.cgan.normalPct*100).toFixed(1) }) }}
              </div>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 结果详情（条目级别） -->
    <div v-if="predictionResults.length" style="margin-top:16px" ref="printAreaRef">
      <h4>{{ $t('predictPage.model.resultDetails') }}</h4>
      <p class="desc">{{ $t('predictPage.model.resultDetailsDesc') }}</p>

      <el-space style="margin-bottom:8px">
        <span style="color:var(--text-2)">{{ $t('predictPage.model.col.serial') }}:</span>
        <el-select
            v-model="selectedSerial"
            filterable
            clearable
            style="width:220px"
            :placeholder="$t('predictPage.model.col.serial')"
        >
          <el-option v-for="sn in serialOptions" :key="sn" :label="sn" :value="sn" />
        </el-select>
        <el-tag v-if="selectedSerial" type="info" effect="plain">SN: {{ selectedSerial }}</el-tag>
      </el-space>

      <el-collapse accordion>
        <el-collapse-item v-for="(grp, idx) in entryLevelResultsToShow" :key="grp.serial + '_' + idx"
                          :title="`${grp.serial} / ${grp.productName}  —  ${$t('predictPage.model.final')}: ${grp.finalDecision}`">
          <div style="margin:6px 0 10px">
            <el-tag>{{ $t('predictPage.model.col.normalModel') }}: {{ grp.normalModelMajority }}</el-tag>
            <el-tag style="margin-left:8px" type="warning">{{ $t('predictPage.model.col.cganModel') }}: {{ grp.cganModelMajority }}</el-tag>
            <el-tag style="margin-left:8px" :type="grp.finalDecision==='PA Abnormal' ? 'danger' : (grp.finalDecision==='May PA Abnormal' ? 'warning' : 'success')">
              {{ $t('predictPage.model.col.finalDecision') }}: {{ grp.finalDecision }}
            </el-tag>
          </div>

          <el-table :data="grp.entries" height="360" size="small">
            <el-table-column prop="timestamp" :label="$t('predictPage.model.col.timestamp')" width="180" />
            <el-table-column prop="sourceFile" :label="$t('predictPage.model.col.sourceFile')" width="340" />
            <el-table-column prop="normalLabel" :label="$t('predictPage.model.col.normalModel')" width="160">
              <template #default="{ row }">
                <el-tag :type="row.normalLabel==='PA Abnormal' ? 'danger' : 'success'">{{ row.normalLabel }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="cganLabel" :label="$t('predictPage.model.col.cganModel')" width="160">
              <template #default="{ row }">
                <el-tag :type="row.cganLabel==='PA Abnormal' ? 'danger' : 'success'">{{ row.cganLabel }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-collapse-item>
      </el-collapse>
    </div>

    <!-- 错误列表 -->
    <div v-if="predictionErrors.length" style="margin-top:16px">
      <h4>{{ $t('predictPage.model.errorList') }}</h4>
      <el-alert
          v-for="(e, idx) in predictionErrors"
          :key="idx"
          type="error"
          :title="e.name"
          :description="e.message"
          show-icon
          :closable="false"
      />
    </div>
  </div>

</template>

<script setup lang="ts">
import {computed, onMounted, ref, watch} from 'vue';
import { ElMessage } from 'element-plus';
import * as XLSX from 'xlsx';

import type { ExtractedEntry, GeneratedRow, PaPreprocessedSampleRow } from '@/types';
import { extractFromZip } from '@/utils/zipExtractor';
import { parseExtracted } from '@/utils/logParser';
import {
  readExtractedFromHandle,
  saveJsonToDir,
  saveJsonWithPicker,
  saveParsedXlsxToDir,
  saveParsedXlsxWithPicker
} from '@/utils/xlsx';
import { generatePaIssueSamplesFromDir, saveSamplesJsonToDir, saveSamplesXlsxToDir } from '@/utils/paSampleGenerator';
import {
  generatePaPreprocessedRowsFromDir,
  savePaPreprocessedJsonToDir,
  savePaPreprocessedXlsxToDir
} from '@/utils/paSamplePreprocessor';

// === 后端 API 客户端（封装在 src/api/predict.ts） ===
import { apiHealth, apiPredict } from '@/api/predict';
import type { EntryPredictionRow, ProductSummary } from '@/api/predict';

import { downloadFromPQAT, fetchFileById, isDirectoryPickerAvailable } from '@/api/pqat';

// -------------------------- 基础状态 --------------------------
type SourceMode = 'files' | 'folders';
const sourceMode = ref<SourceMode>('files');

const files = ref<File[]>([]);
const dirHandles = ref<FileSystemDirectoryHandle[]>([]);
const folderLabels = ref<string[]>([]);

const dirPickerSupported = typeof (window as any).showDirectoryPicker === 'function';

const running = ref(false);
const cancelRequested = ref(false);
const concurrency = ref<number>(4);

// 多产品模式与自动预测
// 多产品模式：根目录下含多个 SN 子目录
const multiProductMode = ref<boolean>(true);
// 是否在处理完成后，按子目录依次自动调用后端预测
const autoPredictAfterProcess = ref<boolean>(false);
// 结果详情的 SN 选择器
const selectedSerial = ref<string>('');


// 不再使用 resultsRaw 作为承载数据表
const errors = ref<Array<{ name: string; message: string }>>([]);
const progress = ref({ totalFiles: 0, doneFiles: 0, totalEntries: 0, currentName: '', totalSteps: 0, doneSteps: 0 });

// 输出目录（可选）
const outputDirHandle = ref<FileSystemDirectoryHandle | null>(null);
const outputDirLabel = computed(() => (outputDirHandle.value as any)?.name || '');

// 生成的 xlsx 文件清单（用于展示 & 打开）
const generatedFiles = ref<GeneratedRow[]>([]);

const canRun = computed(() =>
    (sourceMode.value === 'files' ? files.value.length : dirHandles.value.length) && !running.value
);

const progressPercent = computed(() =>
    progress.value.totalSteps ? Math.min(100, Math.round((progress.value.doneSteps * 100) / progress.value.totalSteps)) : 0
);

// Excel 单个单元格最多容纳 32,767 个字符
const EXCEL_CELL_MAX = 32767;           // Excel 单元格上限
const SAFE_CHUNK_LEN = 32000;           // 给元数据留余量，避免边界粘连

// 页面加载后自动加载模型
onMounted(() => {
  autoLoadModel();
});

// 后端模型自动加载
async function autoLoadModel() {
  try {
    const h = await apiHealth();
    if (h.ok && h.ready) {
      modelReady.value = true;
    } else {
      console.warn('模型未就绪：', h.error);
    }
  } catch (e) {
    console.warn('自动加载模型失败：', e);
  }
}

// -------------------------- PQAT 下载表单与进度 --------------------------
const pqatForm = ref({
  eidUser: '',
  eidKey: '',
  serialsText: '',
  logType: 0 as 0 | 1 | 2 | 3 | 4,
  timeStrobe: 0 as number,
  timeCount: undefined as number | undefined
});

const pqatRootHandle = ref<FileSystemDirectoryHandle | null>(null);
const pqatRootLabel = computed(() => (pqatRootHandle.value as any)?.name || '');

const pqatDownloading = ref(false);
const pqatProgress = ref({ total: 0, done: 0, current: '' });
const pqatPercent = computed(() =>
    pqatProgress.value.total ? Math.min(100, Math.round((pqatProgress.value.done * 100) / pqatProgress.value.total)) : 0
);

// -------------------------- PQAT 输入解析与文件名工具（带前缀，避免与现有函数重名） --------------------------
function pqatNormalizeSerials(t: string): string[] {
  return [...new Set(t.split(/[\n,;，；\s]+/g).map(s => s.trim()).filter(Boolean))];
}
function pqatResolveTimeStrobe(base: number, n?: number) {
  return base === -1 ? -1 : n && n > 0 ? n : 0;
}
function pqatToSafeFileName(
    row: { sn: string; logType: string; fileId: string; date: string },
    origin?: string
): string {
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

// =====================================================================================================================
// 第一步：前端日志下载 + 数据处理
// =====================================================================================================================
// 根目录选择函数
async function onChoosePqatRoot() {
  if (!isDirectoryPickerAvailable()) {
    ElMessage.warning('当前浏览器不支持目录保存（建议使用 Chromium 内核浏览器）');
    return;
  }
  try {
    pqatRootHandle.value = await (window as any).showDirectoryPicker();
    ElMessage.success('已选择保存根目录');
  } catch {}
}


function onClearPqatRoot() {
  pqatRootHandle.value = null;
}

// -------------------------- 文件选择 --------------------------
function onFilesPicked(uploadFile: any) {
  const raw = uploadFile?.raw as File | undefined;
  if (!raw) return;
  if (!raw.name.toLowerCase().endsWith('.zip')) {
    ElMessage.warning('仅支持 .zip 文件');
    return;
  }
  files.value.push(raw);
}
function clearFiles() {
  files.value = [];
}

async function onPickFolder() {
  if (!dirPickerSupported) {
    ElMessage.warning('浏览器不支持目录选择');
    return;
  }
  try {
    const handle = await (window as any).showDirectoryPicker();
    dirHandles.value.push(handle);
    folderLabels.value.push((handle as any).name || 'Folder');
  } catch {}
}
function clearFolders() {
  dirHandles.value = [];
  folderLabels.value = [];
}

// -------------------------- 输出目录 --------------------------
async function onChooseOutputDir() {
  if (!dirPickerSupported) {
    ElMessage.warning('当前浏览器不支持目录保存');
    return;
  }
  try {
    outputDirHandle.value = await (window as any).showDirectoryPicker();
    ElMessage.success('已选择输出目录');
  } catch {}
}
function onClearOutputDir() {
  outputDirHandle.value = null;
}

// -------------------------- 遍历 ZIP（带父目录） --------------------------
type ZipWithParent = { file: File; parent?: FileSystemDirectoryHandle };

async function* walk(dir: FileSystemDirectoryHandle): AsyncGenerator<ZipWithParent> {
  // @ts-ignore
  for await (const [, handle] of (dir as any).entries()) {
    const entry = handle as FileSystemHandle; // 明确类型
    if (entry.kind === 'file') {
      const fileHandle = entry as FileSystemFileHandle;
      const file = await fileHandle.getFile();
      if (file.name.toLowerCase().endsWith('.zip')) {
        yield { file, parent: dir };
      }
    } else if ((handle as any).kind === 'directory') {
      const subDir = entry as FileSystemDirectoryHandle;
      yield* walk(subDir);
    }
  }
}
async function collectZipFiles(): Promise<ZipWithParent[]> {
  const out: ZipWithParent[] = [];
  for (const h of dirHandles.value) {
    for await (const it of walk(h)) out.push(it);
  }
  return out;
}

// -------------------------- 并发控制 --------------------------
async function forEachLimit<T>(
    items: T[],
    limit: number,
    worker: (item: T, idx: number) => Promise<void>
) {
  const it = items.entries();
  const pool: Promise<void>[] = [];

  async function runOne(entry: IteratorResult<[number, T]>) {
    if (entry.done) return;
    const [idx, item] = entry.value;
    await worker(item, idx);
    await runOne(it.next());
  }

  for (let i = 0; i < Math.min(items.length, limit); i++) {
    pool.push(runOne(it.next()));
  }
  await Promise.all(pool);
}

// -------------------------- 保存 Excel --------------------------
function makeExtractedXlsxName(zipName: string): string {
  return zipName.replace(/\.zip$/i, '') + '_extracted.xlsx';
}

// === toWorkbook(entries)：对超长 log_line 自动切片 ===
function splitLongText(s: string, chunkSize = SAFE_CHUNK_LEN): string[] {
  if (!s) return [''];
  if (s.length <= EXCEL_CELL_MAX) return [s];
  const out: string[] = [];
  for (let i = 0; i < s.length; i += chunkSize) {
    out.push(s.slice(i, i + chunkSize));
  }
  return out;
}

function normalizeStr(v: any): string {
  if (v == null) return '';
  return String(v);
}

function toWorkbook(entries: ExtractedEntry[]) {
  const rows: Array<{
    AuditDate: string;
    Serial: string;
    ProductName: string;
    log_type: string;
    log_line: string; // 当前分片
    part: number;     // 分片序号（>=1）
    parts: number;    // 分片总数
  }> = [];

  let longCount = 0;

  for (const e of entries) {
    const base = {
      AuditDate: normalizeStr(e.AuditDate),
      Serial: normalizeStr(e.Serial),
      ProductName: normalizeStr(e.ProductName),
      log_type: normalizeStr(e.log_type)
    };
    const line = normalizeStr(e.log_line);
    const chunks = splitLongText(line);
    const parts = chunks.length;

    if (parts > 1) longCount += 1;

    chunks.forEach((chunk, idx) => {
      rows.push({
        ...base,
        log_line: chunk,
        part: idx + 1,
        parts
      });
    });
  }

  const header = ['AuditDate', 'Serial', 'ProductName', 'log_type', 'log_line', 'part', 'parts'];
  const ws = XLSX.utils.json_to_sheet(rows, { header });
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'extracted');

  if (longCount > 0) {
    try {
      ElMessage.info(`有 ${longCount} 条日志因超出 Excel 单元格限制而分片保存（part/parts 列可见）`);
    } catch {}
  }

  return wb;
}

async function saveXlsxToDir(dir: FileSystemDirectoryHandle, name: string, entries: ExtractedEntry[]) {
  const wb = toWorkbook(entries);
  const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
  const fileHandle = await dir.getFileHandle(name, { create: true });
  const writer = await fileHandle.createWritable();
  await writer.write(new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
  await writer.close();
  return fileHandle as FileSystemFileHandle;
}

async function saveXlsxWithPicker(name: string, entries: ExtractedEntry[]) {
  // @ts-ignore
  const handle: FileSystemFileHandle = await (window as any).showSaveFilePicker({
    suggestedName: name,
    types: [{ description: 'Excel', accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] } }]
  });
  const wb = toWorkbook(entries);
  const wbout = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
  const writer = await handle.createWritable();
  await writer.write(new Blob([wbout], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }));
  await writer.close();

  const file = await handle.getFile();
  const url = URL.createObjectURL(file);
  return { handle, url };
}

// -------------------------- 主执行：抽取/解析/样本生成/预处理 --------------------------
async function onRun() {
  try {
    running.value = true;
    cancelRequested.value = false;

    // 清理旧状态
    errors.value = [];
    generatedFiles.value.forEach(f => {
      f.xlsxUrl && URL.revokeObjectURL(f.xlsxUrl);
      f.parsedJsonUrl && URL.revokeObjectURL(f.parsedJsonUrl!);
      f.parsedXlsxUrl && URL.revokeObjectURL(f.parsedXlsxUrl!);
      f.paSamplesJsonUrl && URL.revokeObjectURL(f.paSamplesJsonUrl!);
      f.paSamplesXlsxUrl && URL.revokeObjectURL(f.paSamplesXlsxUrl!);
    });
    generatedFiles.value = [];

    progress.value = {
      totalFiles: 0, doneFiles: 0, totalEntries: 0, currentName: '',
      totalSteps: 0, doneSteps: 0,
    };

    // 收集输入
    type ZipWithParent = { file: File; parent?: FileSystemDirectoryHandle };
    let zips: Array<File | ZipWithParent>;
    if (sourceMode.value === 'files') {
      zips = [...files.value];
      if (!outputDirHandle.value) {
        ElMessage.info('提示：未设置输出目录，将为每个文件弹出“另存为”对话框（样本条目生成建议选择输出目录以便同目录聚合）');
      }
    } else {
      if (!dirPickerSupported) {
        ElMessage.warning('浏览器不支持目录读取');
        return;
      }
      zips = await collectZipFiles();
      if (!zips.length) {
        ElMessage.info('文件夹中无 zip 文件');
        return;
      }
    }

    progress.value.totalFiles = zips.length;

    // 第一阶段：每个 ZIP 固定 6 步
    const stepsPerZip = 6;
    progress.value.totalSteps = stepsPerZip * zips.length;

    await forEachLimit(zips as any[], concurrency.value, async (item: any) => {
      if (cancelRequested.value) return;

      const zipFile = sourceMode.value === 'files' ? (item as File) : (item as ZipWithParent).file;
      const parentDir = sourceMode.value === 'files' ? undefined : (item as ZipWithParent).parent;

      progress.value.currentName = zipFile.name;

      try {
        // (1) 抽取
        const { entries } = await extractFromZip(zipFile);
        progress.value.totalEntries += entries.length;
        progress.value.doneSteps += 1;

        // (2) 写 extracted.xlsx
        const xlsxName = makeExtractedXlsxName(zipFile.name);
        let xlsxHandle: FileSystemFileHandle | undefined;
        let xlsxUrl: string | undefined;
        let dirLabel = '';
        let dirHandleUsed: FileSystemDirectoryHandle | undefined;

        // 写 extracted.xlsx：多产品模式优先写回子目录
        if (multiProductMode.value && parentDir) {
          dirHandleUsed = parentDir;
          xlsxHandle = await saveXlsxToDir(parentDir, xlsxName, entries);
          dirLabel = (parentDir as any).name || '';
        } else if (outputDirHandle.value) {
          dirHandleUsed = outputDirHandle.value;
          xlsxHandle = await saveXlsxToDir(outputDirHandle.value, xlsxName, entries);
          dirLabel = (outputDirHandle.value as any).name || '';
        } else if (parentDir) {
          dirHandleUsed = parentDir;
          xlsxHandle = await saveXlsxToDir(parentDir, xlsxName, entries);
          dirLabel = (parentDir as any).name || '';
        } else {
          const out2 = await saveXlsxWithPicker(xlsxName, entries);
          xlsxHandle = out2.handle;
          xlsxUrl = out2.url;
        }

        progress.value.doneSteps += 1;

        // (3) 读 extracted.xlsx
        const extractedRows: ExtractedEntry[] = xlsxHandle
            ? await readExtractedFromHandle(xlsxHandle)
            : entries;
        progress.value.doneSteps += 1;

        // (4) 解析
        const parsed = parseExtracted(extractedRows);
        progress.value.doneSteps += 1;

        // (5) 写 parsed.json
        const parsedJsonName = xlsxName.replace(/\.xlsx$/i, '_parsed.json');
        let parsedJsonHandle: FileSystemFileHandle | undefined;
        let parsedJsonUrl: string | undefined;

        // 写 parsed.json：多产品模式优先写回子目录
        if (multiProductMode.value && parentDir) {
          parsedJsonHandle = await saveJsonToDir(parentDir, parsedJsonName, parsed);
        } else if (dirHandleUsed) {
          parsedJsonHandle = await saveJsonToDir(dirHandleUsed, parsedJsonName, parsed);
        } else if (outputDirHandle.value) {
          parsedJsonHandle = await saveJsonToDir(outputDirHandle.value, parsedJsonName, parsed);
        } else if (parentDir) {
          parsedJsonHandle = await saveJsonToDir(parentDir, parsedJsonName, parsed);
        } else {
          const out3 = await saveJsonWithPicker(parsedJsonName, parsed);
          parsedJsonHandle = out3.handle;
          parsedJsonUrl = out3.url;
        }

        progress.value.doneSteps += 1;

        // (6) 写 parsed.xlsx
        const parsedXlsxName = xlsxName.replace(/\.xlsx$/i, '_parsed.xlsx');
        let parsedXlsxHandle: FileSystemFileHandle | undefined;
        let parsedXlsxUrl: string | undefined;

        // 写 parsed.xlsx：多产品模式优先写回子目录
        if (multiProductMode.value && parentDir) {
          parsedXlsxHandle = await saveParsedXlsxToDir(parentDir, parsedXlsxName, parsed);
        } else if (dirHandleUsed) {
          parsedXlsxHandle = await saveParsedXlsxToDir(dirHandleUsed, parsedXlsxName, parsed);
        } else if (outputDirHandle.value) {
          parsedXlsxHandle = await saveParsedXlsxToDir(outputDirHandle.value, parsedXlsxName, parsed);
        } else if (parentDir) {
          parsedXlsxHandle = await saveParsedXlsxToDir(parentDir, parsedXlsxName, parsed);
        } else {
          const out4 = await saveParsedXlsxWithPicker(parsedXlsxName, parsed);
          parsedXlsxHandle = out4.handle;
          parsedXlsxUrl = out4.url;
        }

        progress.value.doneSteps += 1;

        // 记录行
        const row: GeneratedRow = {
          zipName: zipFile.name,
          xlsxName,
          xlsxHandle,
          xlsxUrl,
          parsedJsonName,
          parsedJsonHandle,
          parsedJsonUrl,
          parsedXlsxName,
          parsedXlsxHandle,
          parsedXlsxUrl,
          dirLabel,
          dirHandle: dirHandleUsed ?? parentDir ?? (outputDirHandle.value || undefined)
        };
        generatedFiles.value.push(row);

      } catch (err: any) {
        errors.value.push({ name: zipFile.name, message: err?.message || String(err) });
      } finally {
        progress.value.doneFiles += 1;
      }
    });

    if (cancelRequested.value) {
      ElMessage.info('已取消');
      return;
    }

    // 第二阶段：样本条目生成（每个目录 3 步）
    const dirGroups = new Map<FileSystemDirectoryHandle, { handles: FileSystemFileHandle[]; rowIndices: number[]; dirLabel?: string }>();

    for (let i = 0; i < generatedFiles.value.length; i++) {
      const row = generatedFiles.value[i];
      if (!row.parsedJsonHandle || !row.parsedJsonName) continue;
      if (!row.dirHandle) continue;

      if (!dirGroups.has(row.dirHandle)) {
        dirGroups.set(row.dirHandle, { handles: [], rowIndices: [], dirLabel: row.dirLabel });
      }
      const g = dirGroups.get(row.dirHandle)!;
      g.handles.push(row.parsedJsonHandle);
      g.rowIndices.push(i);
    }

    progress.value.totalSteps += dirGroups.size * 3;

    for (const [dirHandle, bucket] of dirGroups) {
      try {
        // (S1) 生成样本
        const { serial, samples } = await generatePaIssueSamplesFromDir(bucket.handles, dirHandle, bucket.dirLabel);
        progress.value.doneSteps += 1;

        if (!serial) {
          console.warn('[samples] 无法从目录句柄获取目录名（串号），跳过该目录');
          progress.value.doneSteps += 2; // 让进度条不阻塞
          continue;
        }

        // (S2) 保存样本 JSON
        const paSamplesJsonName = `${serial}_entry_sample_generated.json`;
        const paSamplesJsonHandle = await saveSamplesJsonToDir(dirHandle, paSamplesJsonName, samples);
        progress.value.doneSteps += 1;

        // (S3) 保存样本 XLSX
        const paSamplesXlsxName = `${serial}_entry_sample_generated.xlsx`;
        const paSamplesXlsxHandle = await saveSamplesXlsxToDir(dirHandle, paSamplesXlsxName, samples);
        progress.value.doneSteps += 1;

        for (const idx of bucket.rowIndices) {
          const row = generatedFiles.value[idx];
          row.paSamplesJsonName = paSamplesJsonName;
          row.paSamplesJsonHandle = paSamplesJsonHandle;
          row.paSamplesXlsxName = paSamplesXlsxName;
          row.paSamplesXlsxHandle = paSamplesXlsxHandle;
        }

      } catch (e: any) {
        errors.value.push({ name: 'samples', message: e?.message || String(e) });
        progress.value.doneSteps += 3;
      }
    }

    if (cancelRequested.value) {
      ElMessage.info('已取消');
      return;
    }

    // 第三阶段：样本预处理（每个目录 3 步）
    progress.value.totalSteps += dirGroups.size * 3;

    for (const [dirHandle, bucket] of dirGroups) {
      try {
        // 获取该目录下所有样本 JSON 句柄（通常只有一个）
        const sampleHandles = bucket.rowIndices
            .map(idx => generatedFiles.value[idx].paSamplesJsonHandle)
            .filter((h): h is FileSystemFileHandle => !!h);
        if (sampleHandles.length === 0) {
          console.warn('[preprocess] 无样本 JSON 句柄，跳过该目录');
          progress.value.doneSteps += 3;
          continue;
        }

        // (P1) 读取并预处理
        const { serial, rows: preprocessedRows } = await generatePaPreprocessedRowsFromDir(
            sampleHandles,
            dirHandle,
            bucket.dirLabel
        );
        progress.value.doneSteps += 1;

        if (!serial) {
          console.warn('[preprocess] 无法获取串号，跳过保存');
          progress.value.doneSteps += 2;
          continue;
        }

        // (P2) 保存预处理 JSON
        const preJsonName = `${serial}_entry_sample_generated_preprocessed.json`;
        const preJsonHandle = await savePaPreprocessedJsonToDir(dirHandle, preJsonName, preprocessedRows);
        progress.value.doneSteps += 1;

        // (P3) 保存预处理 XLSX
        const preXlsxName = `${serial}_entry_sample_generated_preprocessed.xlsx`;
        const preXlsxHandle = await savePaPreprocessedXlsxToDir(dirHandle, preXlsxName, preprocessedRows);
        progress.value.doneSteps += 1;

        for (const idx of bucket.rowIndices) {
          const row = generatedFiles.value[idx];
          row.paSamplesPreprocessJsonName = preJsonName;
          row.paSamplesPreprocessJsonHandle = preJsonHandle;
          row.paSamplesPreprocessXlsxName = preXlsxName;
          row.paSamplesPreprocessXlsxHandle = preXlsxHandle;
        }

      } catch (e: any) {
        errors.value.push({ name: 'preprocess', message: e?.message || String(e) });
        progress.value.doneSteps += 3;
      }
    }

    // 多产品模式下的“处理后自动预测”（按子目录顺序串行）
    if (!cancelRequested.value && multiProductMode.value && autoPredictAfterProcess.value) {
      if (!modelReady.value) {
        ElMessage.info('后端模型未就绪，已跳过自动预测。可在“模型预测”区域点击“加载模型/运行”。');
      } else {
        await predictPerDirSequentially(dirGroups);
      }
    }

    if (!cancelRequested.value) ElMessage.success('处理完成');
    else ElMessage.info('已取消');

  } finally {
    running.value = false;
    progress.value.currentName = '';
  }
}

function onCancel() {
  cancelRequested.value = true;
}


// 从 PQAT 下载 -> 保存到根目录/SN/ -> 设置来源为 folders -> 自动 onRun()
async function onDownloadAndProcess() {
  // 基本校验
  const serials = pqatNormalizeSerials(pqatForm.value.serialsText);
  if (!serials.length) return ElMessage.warning('请输入至少一个序列号');
  if (!pqatForm.value.eidUser || !pqatForm.value.eidKey) return ElMessage.warning('请输入 EID 与 Key');

  if (!isDirectoryPickerAvailable()) {
    ElMessage.warning('当前浏览器不支持目录保存（需要 Chromium 内核浏览器）');
    return;
  }
  // 选择根目录（若尚未选择）
  if (!pqatRootHandle.value) {
    try {
      pqatRootHandle.value = await (window as any).showDirectoryPicker();
      ElMessage.success('已选择保存根目录');
    } catch {
      return;
    }
  }

  // 拉取可下载条目列表
  pqatDownloading.value = true;
  pqatProgress.value = { total: 0, done: 0, current: '' };

  try {
    const tsParam = pqatResolveTimeStrobe(pqatForm.value.timeStrobe, pqatForm.value.timeCount);
    const entries = await downloadFromPQAT({
      eidUser: pqatForm.value.eidUser,
      eidKey: pqatForm.value.eidKey,
      serials,
      logType: pqatForm.value.logType,
      timeStrobe: tsParam
    });

    // 转换为 DownloadLogs.vue Row 结构（为了重用命名）
    type Row = { date: string; sn: string; logType: string; fileId: string; url: string };
    const rows: Row[] = entries.map((e: any) => {
      const sn = (e.text.split(' - ')[0] || '').trim();
      const log = (e.text.split(' - ')[1] || '').trim();
      const id = e.text.match(/#(\d+)/)?.[1] || '';
      return { date: e.ts, sn, logType: log, fileId: id, url: e.raw || '' };
    }).filter(r => !!r.fileId);

    if (!rows.length) {
      ElMessage.info('未获取到可下载条目');
      return;
    }

    // 统计：总数
    pqatProgress.value.total = rows.length;

    // A1-1：固定按 SN 创建子目录，写入文件
    const group: Record<string, Row[]> = rows.reduce((acc, r) => {
      const key = r.sn || 'UNKNOWN_SN';
      (acc[key] ||= []).push(r);
      return acc;
    }, {} as Record<string, Row[]>);

    for (const [sn, list] of Object.entries(group)) {
      const snDir = await pqatRootHandle.value!.getDirectoryHandle(sn || 'UNKNOWN_SN', { create: true });

      // 适度并发下载
      await forEachLimit(list, 3, async (row) => {
        pqatProgress.value.current = `${sn} / #${row.fileId}`;
        const { blob, filename } = await fetchFileById(pqatForm.value.eidUser, pqatForm.value.eidKey, row.fileId);
        const safeName = pqatToSafeFileName(row, filename);

        const fileHandle = await snDir.getFileHandle(safeName, { create: true });
        const writer = await fileHandle.createWritable();
        await writer.write(blob);
        await writer.close();

        pqatProgress.value.done += 1;
      });
    }

    ElMessage.success('下载完成，开始处理…');

    // 设置来源为 “folders” 并指向根目录（walk() 会递归 SN 子目录）
    sourceMode.value = 'folders';
    files.value = [];
    dirHandles.value = [pqatRootHandle.value!];
    folderLabels.value = [pqatRootLabel.value];

    // 直接调用现有 onRun() —— 它会清空旧数据并开始三阶段处理（抽取/解析/样本/预处理）
    await onRun();
    // 注：是否自动预测，仍由 onRun() 内部基于 autoPredictAfterProcess + modelReady 决定

  } catch (e: any) {
    console.error(e);
    ElMessage.error(e?.message || '下载或处理失败');
  } finally {
    pqatDownloading.value = false;
    pqatProgress.value.current = '';
  }
}


// 打开已保存的 Excel
async function openSavedFile(opts: { handle?: FileSystemFileHandle; url?: string }) {
  try {
    if (opts.handle) {
      const f = await opts.handle.getFile();
      const url = URL.createObjectURL(f);
      window.open(url, '_blank');
      setTimeout(() => URL.revokeObjectURL(url), 10000);
    } else if (opts.url) {
      window.open(opts.url, '_blank');
    } else {
      ElMessage.warning('无法打开文件：没有可用的 URL/句柄');
    }
  } catch (e: any) {
    ElMessage.error(e?.message || '无法打开文件');
  }
}

// =====================================================================================================================
// 下一步：模型预测（后端推理）
// =====================================================================================================================
// -------------------------- 模型预测：状态 --------------------------
type BinaryLabel = 'PA Abnormal' | 'PA Normal';
type FinalDecision = 'PA Abnormal' | 'May PA Abnormal' | 'PA Normal';

const modelLoading = ref(false);
const modelReady = ref(false);
const predicting = ref(false);
const predictionErrors = ref<Array<{ name: string; message: string }>>([]);
const predictionResults = ref<ProductSummary[]>([]);
const entryLevelResults = ref<Array<ProductSummary & { entries: EntryPredictionRow[] }>>([]);

// =================================
// 响应式变量与计算属性
// =================================
// 可选 SN 列表（来自产品级预测汇总）
const serialOptions = computed(() =>
    Array.from(new Set(predictionResults.value.map(r => r.serial)))
);
// 条目级结果的过滤视图
const entryLevelResultsToShow = computed(() =>
    selectedSerial.value
        ? entryLevelResults.value.filter(g => g.serial === selectedSerial.value)
        : entryLevelResults.value
);
// 当有新结果时，若尚未选择 SN，则自动选中第一个
watch(predictionResults, (vals) => {
  if (!selectedSerial.value && vals.length > 0) {
    selectedSerial.value = vals[0].serial;
  }
}, { deep: true });

const printAreaRef = ref<HTMLDivElement | null>(null);

// 推理进度
const predictProgress = ref({
  totalUnits: 0, // 总产品（或目录）数量
  doneUnits: 0,
  totalSteps: 0,
  doneSteps: 0,
  currentName: '',
});
const predictProgressPercent = computed(() =>
    predictProgress.value.totalSteps
        ? Math.min(100, Math.round((predictProgress.value.doneSteps * 100) / predictProgress.value.totalSteps))
        : 0
);

// 是否存在样本预处理 JSON（作为开跑前置条件）
const hasPreprocessedJson = computed(() =>
    generatedFiles.value.some(r => r.paSamplesPreprocessJsonHandle)
);

// -------------------------- 读取样本预处理 JSON --------------------------
type PreRow = PaPreprocessedSampleRow;

async function readPreprocessedSamplesFromHandle(handle: FileSystemFileHandle): Promise<PreRow[]> {
  const file = await handle.getFile();
  const txt = await file.text();
  return JSON.parse(txt) as PreRow[];
}

// 将当前页面所有目录聚合：每个目录一份预处理 JSON（通常为一份）
async function collectAllPreprocessed(): Promise<Array<{ dirLabel?: string; rows: PreRow[] }>> {
  const groups = new Map<FileSystemDirectoryHandle, { dirLabel?: string; handles: FileSystemFileHandle[] }>();
  for (const row of generatedFiles.value) {
    if (row.dirHandle && row.paSamplesPreprocessJsonHandle) {
      if (!groups.has(row.dirHandle)) groups.set(row.dirHandle, { dirLabel: row.dirLabel, handles: [] });
      groups.get(row.dirHandle)!.handles.push(row.paSamplesPreprocessJsonHandle);
    }
  }
  const out: Array<{ dirLabel?: string; rows: PreRow[] }> = [];
  for (const [, bucket] of groups) {
    let merged: PreRow[] = [];
    for (const h of bucket.handles) {
      const part = await readPreprocessedSamplesFromHandle(h);
      merged = merged.concat(part);
    }
    out.push({ dirLabel: bucket.dirLabel, rows: merged });
  }
  return out;
}

// -------------------------- 后端交互：加载模型（健康探测） --------------------------
async function onLoadModels() {
  modelLoading.value = true;
  predictionErrors.value = [];
  try {
    const h = await apiHealth();
    if (!h.ok || !h.ready) {
      throw new Error(h.error || '后端未就绪');
    }
    modelReady.value = true;
    ElMessage.success('后端模型已就绪');
  } catch (e: any) {
    modelReady.value = false;
    predictionErrors.value.push({ name: 'loadModel', message: e?.message || String(e) });
    ElMessage.error(e?.message || '后端不可用');
  } finally {
    modelLoading.value = false;
  }
}

// -------------------------- 总控：跑预测（改为调用后端） --------------------------
async function onRunPrediction() {
  if (!modelReady.value) {
    ElMessage.warning('请先“加载模型”（检查后端）');
    return;
  }
  predicting.value = true;
  predictionErrors.value = [];
  predictionResults.value = [];
  entryLevelResults.value = [];
  predictProgress.value = { totalUnits: 0, doneUnits: 0, totalSteps: 0, doneSteps: 0, currentName: '' };

  try {
    const all = await collectAllPreprocessed();
    if (!all.length) {
      ElMessage.info('未发现预处理样本（SN_entry_sample_generated_preprocessed.json）');
      return;
    }

    // 每个目录一批
    predictProgress.value.totalUnits = all.length;
    predictProgress.value.totalSteps = all.length * 4; // 准备/调用后端/写入UI/完成

    for (const batch of all) {
      predictProgress.value.currentName = batch.dirLabel || 'SN Batch';

      // (1) 准备
      const rows = batch.rows;
      predictProgress.value.doneSteps += 1;

      // =============================
      // empty rows 分支 —— 不报错，不调后端，直接判定为 PA Normal，并写入展示
      // =============================
      if (!rows || rows.length === 0) {
        const summary: any = {
          serial: batch.dirLabel || 'UNKNOWN',
          productName: '', // 保持为空（按你的要求）
          normalModelMajority: 'PA Normal',
          cganModelMajority: 'PA Normal',
          finalDecision: 'PA Normal',
          distribution: {
            normal: { paAbnormalPct: 0, normalPct: 1 },
            cgan:   { paAbnormalPct: 0, normalPct: 1 }
          },
          noFeatures: true // 用于前端模板决定显示“无PA异常相关特征值”
        };

        predictionResults.value.push(summary as ProductSummary);
        entryLevelResults.value.push({ ...(summary as ProductSummary), entries: [] });

        // 推进进度：跳过“调用后端”与“解析返回”，但 UI 与完成步骤保持一致
        predictProgress.value.doneSteps += 1; // 视作“调用后端”这步
        predictProgress.value.doneSteps += 1; // 写入 UI
        predictProgress.value.doneUnits += 1;
        predictProgress.value.doneSteps += 1; // 完成本批
        continue; // 直接进入下一批
      }

      // (2) 调后端
      let resp;
      try {
        resp = await apiPredict(rows);
        if (!resp.ok) throw new Error(resp.error || '后端预测失败');
      } catch (e: any) {
        predictionErrors.value.push({ name: 'predict', message: e?.message || String(e) });
        predictProgress.value.doneSteps += 3; // 这批剩余步骤略过
        continue;
      }
      predictProgress.value.doneSteps += 1;

      // (3) 将后端返回数据写入前端展示结构
      const byProduct = new Map<string, { serial: string; productName: string; entries: EntryPredictionRow[] }>();
      for (const e of resp.entries as EntryPredictionRow[]) {
        const key = `${e.serial}||${e.productName}`;
        if (!byProduct.has(key)) byProduct.set(key, { serial: e.serial, productName: e.productName, entries: [] });
        byProduct.get(key)!.entries.push(e);
      }

      predictionResults.value.push(...(resp.summaries as ProductSummary[]));

      for (const sum of resp.summaries as ProductSummary[]) {
        const key = `${sum.serial}||${sum.productName}`;
        const bucket = byProduct.get(key);
        if (!bucket) continue;
        entryLevelResults.value.push({
          ...sum,
          entries: bucket.entries
        });
      }
      predictProgress.value.doneSteps += 1;

      // (4) 完成本批
      predictProgress.value.doneUnits += 1;
      predictProgress.value.doneSteps += 1;
    }

    ElMessage.success('预测完成');
  } catch (e: any) {
    predictionErrors.value.push({ name: 'predict', message: e?.message || String(e) });
    ElMessage.error(e?.message || '预测失败');
  } finally {
    predicting.value = false;
    predictProgress.value.currentName = '';
  }
}

// 逐子目录顺序预测：与 onRunPrediction 相同的 UI/进度语义
async function predictPerDirSequentially(
    dirGroups: Map<FileSystemDirectoryHandle, { handles: FileSystemFileHandle[]; rowIndices: number[]; dirLabel?: string }>
) {
  predictionErrors.value = [];
  // 不清空已有 predictionResults/entryLevelResults，允许累加（也可视需要先清空）
  // predictionResults.value = [];
  // entryLevelResults.value = [];

  // 统计每个目录中的“预处理 JSON 句柄”集合
  const batches: Array<{ dirLabel?: string; rows: PreRow[] }> = [];
  for (const [dirHandle, bucket] of dirGroups) {
    const sampleHandles = bucket.rowIndices
        .map(idx => generatedFiles.value[idx].paSamplesPreprocessJsonHandle)
        .filter((h): h is FileSystemFileHandle => !!h);

    if (!sampleHandles.length) continue;

    let merged: PreRow[] = [];
    for (const h of sampleHandles) {
      const part = await readPreprocessedSamplesFromHandle(h);
      merged = merged.concat(part);
    }
    batches.push({ dirLabel: bucket.dirLabel, rows: merged });
  }

  // 进度
  predictProgress.value = { totalUnits: batches.length, doneUnits: 0, totalSteps: batches.length * 4, doneSteps: 0, currentName: '' };

  for (const b of batches) {
    predictProgress.value.currentName = b.dirLabel || 'SN Batch';

    // (1) 准备
    const rows = b.rows;
    predictProgress.value.doneSteps += 1;

    // =============================
    // empty rows 分支 —— 不报错，不调后端，直接判定为 PA Normal，并写入展示
    // =============================
    if (!rows || rows.length === 0) {
      const summary: any = {
        serial: b.dirLabel || 'UNKNOWN',
        productName: '', // 保持为空（按你的要求）
        normalModelMajority: 'PA Normal',
        cganModelMajority: 'PA Normal',
        finalDecision: 'PA Normal',
        distribution: {
          normal: { paAbnormalPct: 0, normalPct: 1 },
          cgan:   { paAbnormalPct: 0, normalPct: 1 }
        },
        noFeatures: true
      };

      predictionResults.value.push(summary as ProductSummary);
      entryLevelResults.value.push({ ...(summary as ProductSummary), entries: [] });

      // 推进进度
      predictProgress.value.doneSteps += 1; // 视作“调用后端”这步
      predictProgress.value.doneSteps += 1; // 写入 UI
      predictProgress.value.doneUnits += 1;
      predictProgress.value.doneSteps += 1; // 完成本批
      continue;
    }

    // (2) 调后端
    let resp;
    try {
      resp = await apiPredict(rows);
      if (!resp.ok) throw new Error(resp.error || '后端预测失败');
    } catch (e: any) {
      predictionErrors.value.push({ name: 'predict', message: e?.message || String(e) });
      predictProgress.value.doneSteps += 3;
      continue;
    }
    predictProgress.value.doneSteps += 1;

    // (3) 写入 UI：产品汇总与条目级详情
    const byProduct = new Map<string, { serial: string; productName: string; entries: EntryPredictionRow[] }>();
    for (const e of resp.entries as EntryPredictionRow[]) {
      const key = `${e.serial}||${e.productName}`;
      if (!byProduct.has(key)) byProduct.set(key, { serial: e.serial, productName: e.productName, entries: [] });
      byProduct.get(key)!.entries.push(e);
    }

    predictionResults.value.push(...(resp.summaries as ProductSummary[]));

    for (const sum of resp.summaries as ProductSummary[]) {
      const key = `${sum.serial}||${sum.productName}`;
      const bucket = byProduct.get(key);
      if (!bucket) continue;
      entryLevelResults.value.push({ ...sum, entries: bucket.entries });
    }
    predictProgress.value.doneSteps += 1;

    // (4) 完成本批
    predictProgress.value.doneUnits += 1;
    predictProgress.value.doneSteps += 1;
  }

  ElMessage.success('自动预测完成');
}

function onClearPrediction() {
  predictionResults.value = [];
  entryLevelResults.value = [];
  predictionErrors.value = [];
  predictProgress.value = { totalUnits: 0, doneUnits: 0, totalSteps: 0, doneSteps: 0, currentName: '' };
}

function onPrintReport() {
  window.print();
}
</script>

<style scoped>
.desc { color: var(--text-2); margin: 2px 0 12px; }

.list {
  margin-top: 8px;
  max-height: 160px;
  overflow: auto;
  padding-left: 14px;
}

.sum-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 6px;
}

.bulk-progress {
  margin-top: 12px;
  max-width: 640px;
}

.progress-line {
  font-size: 12px;
  margin-top: 6px;
  color: var(--text-2);
}

.kpi {
  display: flex;
  gap: 16px;
}

.kpi__item {
  padding: 12px 16px;
  border: 1px solid var(--border);
  background: var(--bg-1);
  border-radius: var(--radius);
  min-width: 120px;
  text-align: center;
}

.kpi__value {
  font-size: 20px;
  font-weight: bold;
  color: var(--e-blue);
}

.kpi__label {
  font-size: 12px;
  color: var(--text-2);
}

/* 让表格字体变黑，不会被白色背景覆盖 */
:deep(.el-table) {
  --el-table-text-color: #000;
  --el-table-header-text-color: #000;
}

/* 明确表格单元格字体颜色，避免主题覆盖 */
:deep(.el-table__row td) {
  color: #000 !important;
}

/* 如果表头看不清，也同步处理一下 */
:deep(.el-table__header th) {
  color: var(--text-2);
}

/* 并行设置容器：列方向，固定宽度，左对齐 */
.concurrency-field {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-left: 16px;
  width: 160px;
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
  text-align: left;
  width: 100%;
}

@media print {
  body * { visibility: hidden; }
  .deeplog-card, .deeplog-card * { visibility: visible; }
  .el-page-header { display: none !important; }
  /* 仅打印详情区域（如果只想打印条目详情）：
  [ref="printAreaRef"] { visibility: visible !important; }
  body > *:not([ref="printAreaRef"]) { display: none !important; }
  */
}
</style>
