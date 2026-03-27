<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';

// 读取环境变量
const START_YEAR = Number(import.meta.env.VITE_COPYRIGHT_START_YEAR ?? '2025');
const COMPANY = String(import.meta.env.VITE_COMPANY_NAME ?? 'Ericsson');

const { t } = useI18n();

const nowYear = new Date().getFullYear();
const yearRange = computed(() =>
    START_YEAR < nowYear ? `${START_YEAR}-${nowYear}` : `${nowYear}`
);

const footerText = computed(() =>
    t('footer.copyright', {
      company: COMPANY,
      yearRange: yearRange.value,
      product: t('app.title'),
    })
);
</script>

<template>
  <footer class="footer-wrap">
    <div class="footer-inner">
      <div class="footer-center">
        {{ footerText }}
      </div>
    </div>
  </footer>
</template>

<style scoped>
.footer-wrap {
  border-top: 1px solid var(--border); /* #2a313a */
  background: var(--bg-1); /* #161c22 */
  color: var(--text-1); /* 白色 */

  /* 固定在底部：保持“常驻底部”，可用 fixed；若让内容自然下沉，用 relative */
  position: sticky; /* 可选：改为 fixed */
  bottom: 0;
  width: 100%;
  z-index: 10;

  padding: 6px 0;
  text-align: center;
}

.footer-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 10px 16px;
  display: grid;
  grid-template-columns: 1fr;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  line-height: 1.4;
  opacity: 0.9;
  justify-items: center;
}

.footer-center {
  text-align: center;
  word-break: break-word;
  font-size: 14px;
  opacity: 0.9;
  letter-spacing: 0;
}

/* 小屏适配 */
@media (max-width: 640px) {
  .footer-inner {
    grid-template-columns: 1fr;
    text-align: center;
  }
}
</style>
