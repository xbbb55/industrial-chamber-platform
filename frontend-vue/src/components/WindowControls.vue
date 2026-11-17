<template>
  <div v-if="desktopWindow" class="window-controls" aria-label="窗口控制">
    <button type="button" :title="fullscreenLabel" :aria-label="fullscreenLabel" @click="handleFullscreenAction">
      <Minimize2 v-if="isFullscreen" :size="15" />
      <Maximize v-else :size="15" />
    </button>
    <button type="button" title="最小化" aria-label="最小化" @click="desktopWindow.minimize()">
      <Minus :size="15" />
    </button>
    <button class="window-close" type="button" title="关闭" aria-label="关闭" @click="desktopWindow.close()">
      <X :size="15" />
    </button>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { Maximize, Minimize2, Minus, X } from "lucide-vue-next";

const desktopWindow = window.desktopWindow;
const isFullscreen = ref(false);
const fullscreenLabel = computed(() => isFullscreen.value ? "还原窗口" : "全屏");
let removeFullscreenListener;

function handleFullscreenAction() {
  if (isFullscreen.value) desktopWindow.restoreWindow();
  else desktopWindow.enterFullscreen();
}

onMounted(() => {
  if (!desktopWindow) return;
  removeFullscreenListener = desktopWindow.onFullscreenChange(value => {
    isFullscreen.value = value;
  });
  desktopWindow.isFullscreen().then(value => {
    isFullscreen.value = value;
  });
});

onBeforeUnmount(() => removeFullscreenListener?.());
</script>
