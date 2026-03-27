<template>
  <div class="app">

    <!-- Header 区域 -->
    <HeaderBar
        :logoSrc="logoUrl"
        :title="$t('app.title')"
        :brandClickable="true"
        @back="$router.push({name: 'dashboard'})"
    >
      <!-- 中间区域：导航标签 -->
      <template #center>
        <HeaderTabs />
      </template>

      <!-- 右侧区域：语言切换器 -->
      <template #right>
        <LanguageSwitcher />
      </template>
    </HeaderBar>

    <!-- 主内容区域 -->
    <main class="app-main">
      <router-view />
    </main>

    <!-- 底部 Footer 区域 -->
    <FooterBar />

  </div>
</template>

<script setup lang="ts">
import HeaderBar from '@/components/HeaderBar.vue';
import HeaderTabs from '@/components/HeaderTabs.vue';
import LanguageSwitcher from '@/components/LanguageSwitcher.vue';
import FooterBar from '@/components/FooterBar.vue';

import logoUrl from '@/assets/ericsson_logo.png';
</script>

<style scoped>
.app {
  /* 使 Footer 自然贴底：三段式布局（header / main / footer） */
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto 1fr auto;

  background: var(--bg-0);
  color: var(--text-1);
}

/* 主内容区 */
.app-main {
  padding: 24px;
  max-width: 1320px;
  margin: 0 auto;
  width: 100%;
}

</style>
