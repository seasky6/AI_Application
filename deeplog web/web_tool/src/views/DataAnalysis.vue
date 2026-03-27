<template>

  <el-page-header
      :content="String($t('dataAnalysisPage.title'))"
      @back="$router.push({ name: 'dashboard' })"
  />

  <!-- ===== 1) 数据库部分（Database Section） ===== -->
  <DatabaseSection />

  <!-- ===== 2) 数据分析部分（Analytics Section） ===== -->
  <AnalyticsSection />

</template>


<script setup lang="ts">
// 占位页，无逻辑。后续可接入统计图、对比分析、模型评估等模块。
import DatabaseSection from "@/components/data-analysis/DatabaseSection.vue";
import AnalyticsSection from "@/components/data-analysis/AnalyticsSection.vue";
</script>


<style scoped>

</style>
