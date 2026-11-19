<template>
  <Teleport to="body">
    <section v-if="target" ref="panel" class="virtual-keyboard" :class="{ 'is-numeric': numeric, 'is-dragging': drag }"
      :style="position ? { left: `${position.x}px`, top: `${position.y}px` } : { visibility: 'hidden' }"
      :aria-label="keyboardLabel" @pointerdown.prevent>
      <div class="keyboard-heading" @pointerdown="startDrag" @lostpointercapture="stopDrag">
        <span class="keyboard-label"><Keyboard :size="17" aria-hidden="true" />{{ keyboardLabel }}</span>
        <GripHorizontal class="keyboard-grip" :size="20" aria-hidden="true" />
        <button type="button" class="keyboard-icon" aria-label="关闭键盘" title="关闭键盘" @pointerdown.stop.prevent @click="close">
          <X :size="17" />
        </button>
      </div>
      <div class="keyboard-body">
        <output v-if="nativeNumber" class="keyboard-value" aria-label="当前数值">{{ numberDraft }}</output>
        <div v-if="numeric" class="number-keys">
          <button v-for="digit in digits" :key="digit" type="button" @click="typeKey(digit)">{{ digit }}</button>
          <button type="button" :disabled="!allowMinus" aria-label="负号" @click="typeKey('-')">-</button>
          <button type="button" @click="typeKey('0')">0</button>
          <button type="button" :disabled="!allowDecimal" aria-label="小数点" @click="typeKey('.')">.</button>
          <button type="button" class="keyboard-function keyboard-compact-label" @click="clear">清空</button>
          <button type="button" class="keyboard-function" aria-label="退格" title="退格" @click="erase"><Delete :size="18" /></button>
          <button type="button" class="keyboard-done" aria-label="完成" title="完成" @click="finish"><Check :size="19" /></button>
        </div>
        <template v-else>
          <div v-for="row in letterRows" :key="row" class="letter-row">
            <button v-for="key in row" :key="key" type="button" @click="typeKey(key)">{{ key }}</button>
          </div>
          <div class="keyboard-actions">
            <button type="button" class="keyboard-function" :aria-pressed="shifted" aria-label="切换大小写" title="切换大小写" @click="shifted = !shifted"><ArrowUp :size="19" /></button>
            <button type="button" class="keyboard-function keyboard-compact-label" :aria-pressed="symbols" aria-label="切换数字与符号" title="切换数字与符号" @click="symbols = !symbols">{{ symbols ? 'ABC' : '123' }}</button>
            <button type="button" class="keyboard-space" aria-label="空格" title="空格" @click="typeKey(' ')"><Space :size="18" /></button>
            <button v-if="multiline" type="button" class="keyboard-function" aria-label="换行" title="换行" @click="typeKey('\n')"><CornerDownLeft :size="17" /></button>
            <button type="button" class="keyboard-function" aria-label="退格" title="退格" @click="erase"><Delete :size="18" /></button>
            <button type="button" class="keyboard-done" aria-label="完成" title="完成" @click="finish"><Check :size="19" /></button>
          </div>
        </template>
      </div>
    </section>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, shallowRef, watch } from "vue";
import { ArrowUp, Check, CornerDownLeft, Delete, GripHorizontal, Keyboard, Space, X } from "lucide-vue-next";

const fieldSelector = "textarea, input:is(:not([type]), [type=text], [type=search], [type=number], [type=password], [type=email], [type=url], [type=tel])";
const target = shallowRef(null);
const panel = ref(null);
const position = shallowRef(null);
const drag = shallowRef(null);
const viewportGap = 12;
let moved = false;
const shifted = ref(false);
const symbols = ref(false);
const numberDraft = ref("");
const digits = "789456123";
const alphabet = ["1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm,."];
const punctuation = ["1234567890", "-_=+@#$%&*", "!?/\\:;()[]", "{}<>^~`|\"'"];
const letterRows = computed(() => symbols.value ? punctuation : shifted.value ? alphabet.map(row => row.toUpperCase()) : alphabet);
const multiline = computed(() => target.value instanceof HTMLTextAreaElement);
const nativeNumber = computed(() => target.value?.type === "number");
const numeric = computed(() => nativeNumber.value || ["numeric", "decimal"].includes(target.value?.inputMode));
const keyboardLabel = computed(() => numeric.value ? "数字键盘" : "字母键盘");
const allowMinus = computed(() => nativeNumber.value && (!target.value.min || Number(target.value.min) < 0));
const allowDecimal = computed(() => nativeNumber.value
  ? target.value.step === "any" || !Number.isInteger(Number(target.value.step)) || !Number.isInteger(Number(target.value.min))
  : target.value?.inputMode === "decimal");

function editable(element) {
  return element?.isConnected && element.matches?.(fieldSelector) && !element.matches(":disabled, [readonly]") && !element.closest("[inert]");
}

function open(input) {
  if (target.value === input) return;
  target.value = input;
  numberDraft.value = nativeNumber.value ? input.value : "";
  shifted.value = false;
  symbols.value = false;
  if (!moved) position.value = null;
  nextTick(place);
}

function close() {
  target.value = null;
  numberDraft.value = "";
  drag.value = null;
  moved = false;
}

function onInteraction(event) {
  if (panel.value?.contains(event.target)) return;
  if (editable(event.target)) open(event.target);
  else if (event.type !== "click") close();
}

function onFocusOut(event) {
  if (event.target !== target.value && !panel.value?.contains(event.target)) return;
  if (event.relatedTarget === target.value || panel.value?.contains(event.relatedTarget)) return;
  close();
}

function onEscape(event) {
  if (event.key !== "Escape" || !target.value) return;
  event.preventDefault();
  event.stopPropagation();
  finish();
}

function viewportBounds(width = panel.value.offsetWidth, height = panel.value.offsetHeight) {
  return {
    maxX: Math.max(viewportGap, window.innerWidth - width - viewportGap),
    maxY: Math.max(viewportGap, window.innerHeight - height - viewportGap)
  };
}

function keepInViewport(x, y, { maxX, maxY } = viewportBounds()) {
  const nextX = Math.max(viewportGap, Math.min(x, maxX));
  const nextY = Math.max(viewportGap, Math.min(y, maxY));
  if (position.value?.x !== nextX || position.value?.y !== nextY) position.value = { x: nextX, y: nextY };
}

function startDrag(event) {
  if (!event.isPrimary || event.button !== 0 || !position.value || drag.value) return;
  const { x, y } = position.value;
  event.currentTarget.setPointerCapture(event.pointerId);
  drag.value = { id: event.pointerId, offsetX: event.clientX - x, offsetY: event.clientY - y };
}

function moveDrag(event) {
  if (drag.value?.id !== event.pointerId) return;
  if (!event.buttons) return stopDrag(event);
  moved = true;
  keepInViewport(event.clientX - drag.value.offsetX, event.clientY - drag.value.offsetY);
}

function stopDrag(event) {
  if (drag.value?.id === event.pointerId) drag.value = null;
}

function place() {
  const input = target.value;
  if (!input || !panel.value) return;
  if (!editable(input) || !input.getClientRects().length) return close();
  const { offsetWidth: width, offsetHeight: height } = panel.value;
  const bounds = viewportBounds(width, height);
  if (moved) return keepInViewport(position.value.x, position.value.y, bounds);
  const field = input.getBoundingClientRect();
  const gap = viewportGap;
  const { maxX, maxY } = bounds;
  const topLimit = Math.min(76, maxY);
  const below = field.bottom + gap;
  const above = field.top - height - gap;
  if (below <= maxY) keepInViewport(field.left, Math.max(topLimit, below), bounds);
  else if (above >= topLimit) keepInViewport(field.left, above, bounds);
  else {
    const side = field.right + gap <= maxX ? field.right + gap : field.left - width - gap;
    const top = field.top > window.innerHeight / 2 ? topLimit : maxY;
    keepInViewport(side >= gap ? side : field.left, top, bounds);
  }
}

function finish() {
  const input = target.value;
  if (panel.value?.contains(document.activeElement)) input?.focus({ preventScroll: true });
  input?.blur();
  close();
}

function emitInput(input, inputType, data = null) {
  input.dispatchEvent(new InputEvent("input", { bubbles: true, inputType, data }));
}

function setNumber(input, draft, inputType, data) {
  if (draft && !/^-?(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?$/i.test(draft) && draft !== "-") return;
  numberDraft.value = draft;
  const value = draft === "-" ? "" : draft.endsWith(".") ? draft.slice(0, -1) : draft;
  if (input.value === value) return;
  input.value = value;
  emitInput(input, inputType, data);
}

function editText(input, text, inputType) {
  const selectionStart = input.selectionStart;
  const start = selectionStart ?? input.value.length;
  const end = input.selectionEnd ?? start;
  const from = inputType === "deleteContentBackward" && start === end
    ? start - (Array.from(input.value.slice(0, start)).at(-1)?.length || 0)
    : start;
  if (input.maxLength >= 0 && input.value.length - (end - from) + text.length > input.maxLength) return;
  if (selectionStart !== null) input.setRangeText(text, from, end, "end");
  else input.value = input.value.slice(0, from) + text + input.value.slice(end);
  emitInput(input, inputType, text || null);
}

function typeKey(key) {
  const input = target.value;
  if (!editable(input)) return close();
  if (!nativeNumber.value) return editText(input, key, key === "\n" ? "insertLineBreak" : "insertText");
  const draft = numberDraft.value;
  if (key === "-") {
    if (allowMinus.value) setNumber(input, draft.startsWith("-") ? draft.slice(1) : "-" + draft, "insertText", key);
  } else if (key === ".") {
    if (allowDecimal.value && !/[.e]/i.test(draft)) {
      setNumber(input, (draft === "" || draft === "-" ? draft + "0" : draft) + ".", "insertText", key);
    }
  } else {
    setNumber(input, draft === "0" || draft === "-0" ? draft.slice(0, -1) + key : draft + key, "insertText", key);
  }
}

function erase() {
  const input = target.value;
  if (!editable(input)) return close();
  if (nativeNumber.value) setNumber(input, numberDraft.value.slice(0, -1).replace(/e[+-]?$/i, ""), "deleteContentBackward");
  else editText(input, "", "deleteContentBackward");
}

function clear() {
  const input = target.value;
  if (!editable(input)) return close();
  if (nativeNumber.value) setNumber(input, "", "deleteContentBackward");
  else {
    input.value = "";
    emitInput(input, "deleteContentBackward");
  }
}

function syncNumber(event) {
  if (event.isTrusted && event.target === target.value && nativeNumber.value) numberDraft.value = event.target.value;
}

const listeners = {
  focusin: onInteraction,
  focusout: onFocusOut,
  pointerdown: onInteraction,
  pointermove: moveDrag,
  pointerup: stopDrag,
  pointercancel: stopDrag,
  click: onInteraction,
  input: syncNumber,
  scroll: place,
  resize: place,
  transitionend: place,
  keydown: onEscape
};
const panelResize = new ResizeObserver(place);
watch(panel, (element, previous) => {
  if (previous) panelResize.unobserve(previous);
  if (element) panelResize.observe(element);
});
onMounted(() => {
  for (const [name, handler] of Object.entries(listeners)) window.addEventListener(name, handler, true);
});
onUnmounted(() => {
  for (const [name, handler] of Object.entries(listeners)) window.removeEventListener(name, handler, true);
  panelResize.disconnect();
});
</script>

<style scoped>
.virtual-keyboard {
  --key-gap: 6px;
  position: fixed;
  -webkit-app-region: no-drag;
  z-index: 20000;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  width: min(640px, calc(100vw - 24px));
  max-height: calc(100vh - 24px);
  border: 1px solid var(--system-line-strong);
  border-radius: var(--system-radius);
  background: #eef1f3;
  box-shadow: 0 2px 5px #20232612, 0 14px 36px #20232630;
  color: var(--system-ink);
  user-select: none;
}

.virtual-keyboard.is-numeric { width: min(312px, calc(100vw - 24px)); }
.keyboard-heading {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  min-height: 42px;
  padding-inline: 12px 6px;
  border-bottom: 1px solid var(--system-line);
  cursor: grab;
  touch-action: none;
}
.is-dragging .keyboard-heading { cursor: grabbing; }
.keyboard-label { display: flex; align-items: center; gap: 7px; color: var(--system-ink-soft); font-size: 13px; font-weight: 700; white-space: nowrap; }
.keyboard-grip { color: var(--system-ink-muted); }
.keyboard-body { display: grid; gap: var(--key-gap); overflow: auto; overscroll-behavior: contain; padding: 10px; }
.keyboard-value {
  display: block;
  min-width: 0;
  min-height: 34px;
  overflow: hidden;
  padding: 5px 10px;
  border: 1px solid var(--system-line);
  border-radius: 8px;
  background: var(--system-surface-strong);
  text-align: right;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 17px;
  font-weight: 600;
  line-height: 22px;
  font-variant-numeric: tabular-nums;
}
.virtual-keyboard button {
  display: grid;
  place-items: center;
  min-width: 0;
  height: 42px;
  padding: 0;
  border: 1px solid var(--system-line);
  border-bottom-color: var(--system-line-strong);
  border-radius: 8px;
  background: #fff;
  color: inherit;
  font-family: inherit;
  font-size: 17px;
  font-weight: 600;
  line-height: 1;
  box-shadow: 0 1px 1px #20232612;
  cursor: pointer;
  touch-action: manipulation;
}
.virtual-keyboard button:hover:not(:disabled) { background: #f8fafb; border-color: var(--system-line-strong); }
.virtual-keyboard button:active:not(:disabled) { background: #dce3e7; box-shadow: inset 0 1px 2px #20232618; }
.virtual-keyboard button:focus-visible { outline: 2px solid var(--system-ink-soft); outline-offset: -3px; }
.virtual-keyboard button:disabled { background: #e8ecef; color: #626d76; cursor: default; box-shadow: none; }
.virtual-keyboard .keyboard-icon { justify-self: end; width: 34px; height: 32px; border-color: transparent; background: transparent; color: var(--system-ink-soft); box-shadow: none; }
.letter-row, .keyboard-actions { display: flex; justify-content: center; gap: var(--key-gap); }
.letter-row button { flex: 0 0 calc((100% - 9 * var(--key-gap)) / 10); }
.keyboard-actions button { flex: 1 1 0; }
.keyboard-actions .keyboard-space { flex: 4 1 0; }
.number-keys { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--key-gap); }
.number-keys button { height: 43px; font-size: 20px; font-variant-numeric: tabular-nums; }
.virtual-keyboard .keyboard-function { background: #e1e6ea; color: var(--system-ink-soft); }
.virtual-keyboard .keyboard-compact-label { font-size: 13px; font-weight: 700; }
.virtual-keyboard button[aria-pressed="true"]:not(:disabled) { border-color: #87949e; background: #cbd5dc; color: var(--system-ink); }
.virtual-keyboard .keyboard-done { background: #202326; border-color: #202326; color: #fff; }
.virtual-keyboard .keyboard-done:hover:not(:disabled) { background: #393f43; }
.virtual-keyboard .keyboard-done:active:not(:disabled) { background: #101214; }
.virtual-keyboard .keyboard-done:focus-visible { outline-color: #fff; }

@media (max-width: 560px) {
  .virtual-keyboard { --key-gap: 4px; }
  .keyboard-body { padding: 7px; }
  .letter-row button, .keyboard-actions button { height: 36px; }
}
</style>
