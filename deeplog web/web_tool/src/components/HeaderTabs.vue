<template>
  <nav class="tabs">
    <RouterLink class="tab" :class="{ active: $route.name === 'dashboard' }" :to="{ name: 'dashboard' }">
      {{ $t('menu.dashboard') }}
    </RouterLink>

    <RouterLink class="tab" :class="{ active: $route.name === 'download-logs' }" :to="{ name: 'download-logs' }">
      {{ $t('menu.downloadLog') }}
    </RouterLink>

    <RouterLink class="tab" :class="{ active: $route.name === 'process-logs' }" :to="{ name: 'process-logs' }">
      {{ $t('menu.processLog') }}
    </RouterLink>

    <RouterLink class="tab" :class="{ active: $route.name === 'predict-samples' }" :to="{ name: 'predict-samples' }">
      {{ $t('menu.samplePrediction') }}
    </RouterLink>

    <RouterLink class="tab" :class="{ active: $route.name === 'data-analysis' }" :to="{ name: 'data-analysis' }">
      {{ $t('menu.dataAnalysis') }}
    </RouterLink>

  </nav>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 16px;
}

.tab {
  color: var(--text-2);
  text-decoration: none;
  padding: 8px 10px;
  border-radius: 6px;
  transition: 0.2s ease;
}

.tab:hover {
  background: var(--bg-2);
  color: var(--text-1);
}

.tab.active {
  background: var(--bg-2);
  color: var(--e-blue) !important;
  border: 1px solid var(--e-blue);
}
</style>
