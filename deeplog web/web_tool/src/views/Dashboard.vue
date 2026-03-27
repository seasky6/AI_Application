<template>
  <div class="dashboard">
    <div class="welcome-card deeplog-card">
      <h1 class="welcome-title">{{ $t("dashboard.welcomeTitle") }}</h1>
      <p class="welcome-desc">{{ $t("dashboard.welcomeSubtitle") }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.dashboard {
  display: flex;
  justify-content: center;
  margin-top: 40px;
}

.welcome-card {
  max-width: 760px;
  text-align: center;
  padding: 40px;
}

.welcome-title {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 16px;
  color: var(--text-1);
}

.welcome-desc {
  font-size: 18px;
  color: var(--text-2);
  line-height: 1.6;
}
</style>