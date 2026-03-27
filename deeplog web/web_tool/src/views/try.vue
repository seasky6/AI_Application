<script setup lang="ts">

const header = [
  "===================================================================================================================",
  "日志分析报告 - Overall",
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

</script>

<template>



</template>

<style scoped>

</style>