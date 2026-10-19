<template>
  <Transition name="workspace-refresh">
    <div v-if="shown && bounds" class="workspace-refresh-layer" :style="bounds">
      <div class="workspace-refresh-panel" :data-state="phase" role="status" aria-live="polite" aria-atomic="true">
        <button
          v-if="error"
          class="workspace-refresh-close"
          type="button"
          title="关闭"
          aria-label="关闭"
          @click="dismissError"
        >
          <AppIcon name="close" :size="17" :stroke-width="1.9" />
        </button>
        <div class="workspace-refresh-mark" aria-hidden="true">
          <svg class="workspace-refresh-ring" viewBox="0 0 64 64">
            <circle class="workspace-refresh-track" cx="32" cy="32" r="27" />
            <circle class="workspace-refresh-arc" cx="32" cy="32" r="27" />
          </svg>
          <Transition name="refresh-symbol" mode="out-in">
            <AppIcon :key="phase" :name="error ? 'alarms' : pending ? 'activity' : 'check'" :size="22" />
          </Transition>
        </div>
        <strong>{{ error ? errorTitle : pending ? title : completeTitle }}</strong>
        <span v-if="error" class="workspace-refresh-detail">{{ error }}</span>
        <button v-if="error" class="workspace-refresh-retry" type="button" @click="$emit('retry')">
          <AppIcon name="refresh" :size="15" />重新读取
        </button>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import AppIcon from "./AppIcon.vue";

const props = defineProps({
  target: { type: Object, default: null },
  pending: Boolean,
  visible: Boolean,
  error: { type: String, default: "" },
  title: { type: String, required: true },
  completeTitle: { type: String, required: true },
  errorTitle: { type: String, required: true }
});
const emit = defineEmits(["retry", "dismiss"]);

const shown = ref(false);
const bounds = ref(null);
const dismissed = ref(false);
const phase = computed(() => props.error ? "error" : props.pending ? "loading" : "complete");
let shownAt = 0;
let dismissTimer;

watch(() => [props.visible, props.pending, props.error], ([visible, pending, error], previous) => {
  window.clearTimeout(dismissTimer);
  const stateChanged = !previous
    || visible !== previous[0]
    || pending !== previous[1]
    || error !== previous[2];
  if (stateChanged && previous) dismissed.value = false;
  if ((visible || error) && !dismissed.value) {
    if (!shown.value) shownAt = performance.now();
    shown.value = true;
  } else if (shown.value && !pending && !dismissed.value) {
    // Keep completion readable; data and control availability update immediately.
    const remaining = Math.max(280, 480 - (performance.now() - shownAt));
    dismissTimer = window.setTimeout(() => { shown.value = false; }, remaining);
  }
}, { immediate: true });

function dismissError() {
  dismissed.value = true;
  shown.value = false;
  window.clearTimeout(dismissTimer);
  emit("dismiss");
}

watch([shown, () => props.target], ([active, target], _, onCleanup) => {
  if (!active || !target) return;
  let frame;
  const viewport = window.visualViewport;
  function measure() {
    const rect = target.getBoundingClientRect();
    const viewportLeft = viewport?.offsetLeft || 0;
    const viewportTop = viewport?.offsetTop || 0;
    const left = Math.max(rect.left, viewportLeft);
    const top = Math.max(rect.top, viewportTop);
    // Use the visible part of the workspace, including on long, scrolled pages.
    bounds.value = {
      left: `${left}px`,
      top: `${top}px`,
      width: `${Math.max(0, Math.min(rect.right, viewportLeft + (viewport?.width || window.innerWidth)) - left)}px`,
      height: `${Math.max(0, Math.min(rect.bottom, viewportTop + (viewport?.height || window.innerHeight)) - top)}px`
    };
  }
  function scheduleMeasure() {
    window.cancelAnimationFrame(frame);
    frame = window.requestAnimationFrame(measure);
  }
  measure();
  const observer = new ResizeObserver(scheduleMeasure);
  observer.observe(target);
  window.addEventListener("resize", scheduleMeasure);
  window.addEventListener("scroll", scheduleMeasure, { capture: true, passive: true });
  viewport?.addEventListener("resize", scheduleMeasure);
  viewport?.addEventListener("scroll", scheduleMeasure);
  onCleanup(() => {
    observer.disconnect();
    window.cancelAnimationFrame(frame);
    window.removeEventListener("resize", scheduleMeasure);
    window.removeEventListener("scroll", scheduleMeasure, true);
    viewport?.removeEventListener("resize", scheduleMeasure);
    viewport?.removeEventListener("scroll", scheduleMeasure);
  });
}, { flush: "post", immediate: true });

onBeforeUnmount(() => window.clearTimeout(dismissTimer));
</script>
