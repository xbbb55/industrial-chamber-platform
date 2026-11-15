<template>
  <div v-if="desktopWindow" class="window-controls" aria-label="窗口控制">
    <button type="button" title="全屏" aria-label="全屏" @click="desktopWindow.toggleFullscreen()">
      <Maximize :size="15" />
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
import { Maximize, Minus, X } from "lucide-vue-next";

const desktopWindow = window.desktopWindow;
</script>
