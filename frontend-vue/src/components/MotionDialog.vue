<template>
  <Teleport to=".app-shell" defer>
  <Transition name="pilot-dialog" @enter="focusDialog" @after-leave="finishLeave">
    <div v-if="open" :class="['pilot-dialog-backdrop', backdropClass]" :style="{ zIndex: layer }" :inert="!isTop" @click.self="$emit('close')">
      <section ref="panel" :class="['pilot-dialog-panel', panelClass]" role="dialog" aria-modal="true" :aria-labelledby="labelledby" tabindex="-1">
        <slot />
      </section>
    </div>
  </Transition>
  </Teleport>
</template>

<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useDialogStack } from "../composables/useDialogStack";

const props = defineProps({
  open: Boolean,
  backdropClass: { type: String, required: true },
  panelClass: { type: String, required: true },
  labelledby: { type: String, required: true },
  returnFocus: { type: String, default: "" }
});
const emit = defineEmits(["close"]);
const panel = ref(null);
const { isTop, layer, register, release } = useDialogStack();
let opener;

function focusableElements() {
  return [...(panel.value?.querySelectorAll("button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex='0']") || [])]
    .filter(element => element.getClientRects().length && !element.closest("[inert]"));
}

async function focusDialog() {
  await nextTick();
  if (props.open && isTop.value) (panel.value?.querySelector("[data-dialog-autofocus]") || focusableElements()[0] || panel.value)?.focus({ preventScroll: true });
}

async function finishLeave() {
  if (props.open) return;
  release();
  await nextTick();
  const target = opener?.isConnected && !opener.closest("[inert]") ? opener : document.querySelector(props.returnFocus || ".nav-list button.active");
  if (!props.open) target?.focus({ preventScroll: true });
}

function handleKeydown(event) {
  if (!props.open || !isTop.value) return;
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopImmediatePropagation();
    emit("close");
  } else if (event.key === "Tab") {
    const items = focusableElements();
    const first = items[0] || panel.value;
    const last = items.at(-1) || panel.value;
    if (!panel.value?.contains(document.activeElement) || (event.shiftKey && document.activeElement === first)) {
      event.preventDefault();
      (event.shiftKey ? last : first)?.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first?.focus();
    }
  }
}

watch(() => props.open, open => {
  document.removeEventListener("keydown", handleKeydown, true);
  if (open) {
    opener = document.activeElement;
    register();
    document.addEventListener("keydown", handleKeydown, true);
  }
}, { flush: "sync", immediate: true });
onBeforeUnmount(() => {
  release();
  document.removeEventListener("keydown", handleKeydown, true);
});
</script>
