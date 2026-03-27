<template>
  <header
      class="header-bar"
      :class="[{ 'is-sticky': sticky, 'has-border': showBorder, 'is-dark': dark }]"
      role="banner"
  >
    <!-- 左侧：Logo + 标题 -->
    <div class="left" @click="onBrandClick" :style="{ cursor: brandClickable ? 'pointer' : 'default' }">
      <img
          v-if="logoSrc"
          :src="logoSrc"
          :alt="title"
          class="logo"
          :style="logoStyle"
          decoding="async"
          loading="eager"
          @error="onLogoError"
      />
      <span v-if="title" class="title" :title="title">{{ title }}</span>
    </div>

    <!-- 中间：可选返回或自定义插槽 -->
    <div class="center">
      <slot name="center">
        <el-button
            v-if="showBack"
            text
            size="small"
            @click="emit('back')"
            class="back-btn"
        >
          ← {{ backText }}
        </el-button>
      </slot>
    </div>

    <!-- 右侧：常放语言切换器、用户菜单等 -->
    <div class="right">
      <slot name="right" />
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';

type LogoFit = 'contain' | 'cover' | 'fill' | 'none' | 'scale-down';

interface Props {
  /** 标题文本 */
  title?: string;
  /** 本地图片地址（建议从 src/assets 以 ESM 导入） */
  logoSrc?: string;
  /** 点击左侧 Brand 是否跳转到根路由（默认 true） */
  brandClickable?: boolean;
  /** 是否吸顶（position: sticky） */
  sticky?: boolean;
  /** 是否显示底部分隔线边框（默认 true） */
  showBorder?: boolean;
  /** 启用深色背景（会自动调整文字与分隔线） */
  dark?: boolean;
  /** Logo 高度（px，默认 28） */
  logoHeight?: number;
  /** Logo 宽度（px，默认 auto） */
  logoWidth?: number | 'auto';
  /** object-fit（默认 contain） */
  logoFit?: LogoFit;
  /** 是否显示返回按钮（居中区域） */
  showBack?: boolean;
  /** 返回按钮文案（默认 'Back' / '返回'） */
  backText?: string;
}

const props = withDefaults(defineProps<Props>(), {
  title: 'DeepLog Offline',
  brandClickable: true,
  sticky: false,
  showBorder: true,
  dark: false,
  logoHeight: 30,
  logoWidth: 'auto',
  logoFit: 'contain',
  showBack: false,
  backText: 'Back'
});

const emit = defineEmits<{
  (e: 'brand-click'): void;
  (e: 'back'): void;
  (e: 'logo-error'): void;
}>();

const router = useRouter();

const logoStyle = computed(() => ({
  height: `${props.logoHeight}px`,
  width: typeof props.logoWidth === 'number' ? `${props.logoWidth}px` : props.logoWidth,
  objectFit: props.logoFit as LogoFit
}));

function onBrandClick() {
  emit('brand-click');
  if (props.brandClickable) {
    router.push({ name: 'dashboard' }).catch(() => void 0);
  }
}
function onLogoError() {
  emit('logo-error');
}
</script>

<style scoped>
.header-bar {
  --hb-height: 50px;
  --hb-padding-x: 16px;
  --hb-gap: 10px;

  position: relative;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: var(--hb-gap);
  height: var(--hb-height);
  padding: 0 var(--hb-padding-x);
  background: #fff;
  color: #1f1f1f;
  z-index: 10;
}

.left,
.center,
.right {
  display: flex;
  align-items: center;
  min-width: 0;
}

.left {
  justify-self: start;
  gap: var(--hb-gap);
}

.center {
  justify-self: center;
}
.right {
  justify-self: end;
  gap: 8px;
}

.logo {
  display: block;
  width: auto;
  aspect-ratio: auto;
}

.title {
  font-size: 18px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 返回按钮样式微调（Element Plus 的 text 按钮） */
.back-btn {
  color: inherit;
  font-weight: 500;
}

/* 小屏优化 */
@media (max-width: 640px) {
  .title {
    font-size: 16px;
  }
  .header-bar {
    --hb-height: 52px;
    --hb-padding-x: 12px;
  }
}
</style>
