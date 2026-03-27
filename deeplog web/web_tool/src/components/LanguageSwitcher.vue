<template>
  <el-select v-model="lang" size="small" style="width: 140px" @change="onChange">
    <el-option label="中文(简体)" value="zh-CN" />
    <el-option label="English" value="en-US" />
  </el-select>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { ref, watchEffect } from 'vue';

const { locale } = useI18n();
const lang = ref<string>(locale.value);

function onChange(v: string) {
  locale.value = v;
  localStorage.setItem('DEEPLOG_LANG', v);
}
watchEffect(() => (lang.value = locale.value));
</script>
