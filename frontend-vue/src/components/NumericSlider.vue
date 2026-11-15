<template>
  <div class="numeric-slider" :class="{ 'numeric-slider-compact': compact, 'numeric-slider-no-range': !slider }">
    <input :id="id || undefined" class="numeric-slider-value" type="number" :value="modelValue" :min="min ?? undefined" :max="max ?? undefined" :step="step" :required="required" :aria-label="label" @input="onNumberInput" @blur="clampOnBlur">
    <span class="numeric-slider-unit" :aria-hidden="!unit">{{ unit }}</span>
    <input v-if="slider" class="numeric-slider-range" type="range" :min="bounds.min" :max="bounds.max" :step="rangeStep" :value="sliderValue" :style="rangeStyle" :aria-label="`${label}滑动调节`" @input="emit('update:modelValue', Number($event.target.value))">
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  modelValue: { type: [Number, String], default: 0 },
  label: { type: String, required: true },
  id: { type: String, default: "" },
  unit: { type: String, default: "" },
  min: { type: Number, default: null },
  max: { type: Number, default: null },
  sliderMin: { type: Number, default: null },
  sliderMax: { type: Number, default: null },
  step: { type: [String, Number], default: 0.1 },
  palette: { type: String, default: "temperature" },
  compact: { type: Boolean, default: false },
  slider: { type: Boolean, default: true },
  required: { type: Boolean, default: false }
});
const emit = defineEmits(["update:modelValue"]);
const palettes = {
  temperature: ["#72b4e8", "#80ccd4", "#f2d49b", "#e98c89"],
  humidity: ["#90b9de", "#80d0d4", "#73bfae"],
  ramp: ["#a6bfd3", "#e3b085"],
  frequency: ["#acbbce", "#b4a8cd"]
};
const rangeStep = computed(() => props.step === "any" ? "any" : !Number.isFinite(Number(props.step)) || Number(props.step) <= 0 ? 0.1 : Number(props.step));
const enteredValue = computed(() => props.modelValue === "" || props.modelValue == null ? NaN : Number(props.modelValue));
const hasFixedMin = computed(() => props.min !== null && Number.isFinite(props.min));
const hasFixedMax = computed(() => props.max !== null && Number.isFinite(props.max));
const baseBounds = computed(() => {
  const start = props.sliderMin ?? props.min;
  const end = props.sliderMax ?? props.max;
  const min = start == null ? NaN : Number(start);
  const max = end == null ? NaN : Number(end);
  if (Number.isFinite(min) && Number.isFinite(max) && max > min) return { min, max };
  if (Number.isFinite(min)) return { min, max: min + 100 };
  if (Number.isFinite(max)) return { min: max - 100, max };
  return { min: -100, max: 100 };
});
const expandedMin = ref(Infinity);
const expandedMax = ref(-Infinity);
watch([enteredValue, baseBounds], ([value, base]) => {
  if (!Number.isFinite(value)) return;
  const lower = Math.min(base.min, expandedMin.value);
  const upper = Math.max(base.max, expandedMax.value);
  const padding = (upper - lower) * 0.2;
  if (!hasFixedMin.value && value <= lower) expandedMin.value = value - padding;
  if (!hasFixedMax.value && value >= upper) expandedMax.value = value + padding;
}, { immediate: true });
const bounds = computed(() => ({
  min: hasFixedMin.value ? baseBounds.value.min : Math.min(baseBounds.value.min, expandedMin.value),
  max: hasFixedMax.value ? baseBounds.value.max : Math.max(baseBounds.value.max, expandedMax.value)
}));
const sliderValue = computed(() => Number.isFinite(enteredValue.value) ? enteredValue.value : bounds.value.min);
const rangeStyle = computed(() => {
  const progress = Math.min(100, Math.max(0, (sliderValue.value - bounds.value.min) / (bounds.value.max - bounds.value.min) * 100));
  const colors = palettes[props.palette] || palettes.temperature;
  const position = progress / 100 * (colors.length - 1);
  const left = colors[Math.floor(position)];
  const right = colors[Math.min(colors.length - 1, Math.ceil(position))];
  const fraction = position - Math.floor(position);
  const channel = (index) => Math.round(parseInt(left.slice(index, index + 2), 16) * (1 - fraction) + parseInt(right.slice(index, index + 2), 16) * fraction);
  return { "--range-progress": `${progress}%`, "--range-start": colors[0], "--range-end": `rgb(${channel(1)}, ${channel(3)}, ${channel(5)})` };
});

function onNumberInput(event) {
  const raw = event.target.value;
  const parsed = Number(raw);
  emit("update:modelValue", raw === "" ? "" : Number.isFinite(parsed) ? parsed : raw);
}

function clampOnBlur() {
  if (!Number.isFinite(enteredValue.value)) return;
  const value = Math.max(props.min ?? -Infinity, Math.min(props.max ?? Infinity, enteredValue.value));
  if (value !== enteredValue.value) emit("update:modelValue", value);
}
</script>

<style scoped>
.numeric-slider { display: grid; grid-template-columns: 76px 44px minmax(60px, 1fr); align-items: center; gap: 6px; min-width: 0; width: 100%; }
.numeric-slider .numeric-slider-value { box-sizing: border-box; width: 100%; min-width: 0; height: 38px; min-height: 38px; padding: 6px; border: 1px solid rgba(98, 108, 118, .22); border-radius: 8px; background: #fff; color: #24292e; font: 700 14px "Roboto Mono", Consolas, monospace; text-align: center; appearance: textfield; box-shadow: none; }
.numeric-slider .numeric-slider-value::-webkit-inner-spin-button, .numeric-slider .numeric-slider-value::-webkit-outer-spin-button { -webkit-appearance: none; margin: 0; }
.numeric-slider .numeric-slider-value:focus-visible { outline: 2px solid #3e626e; outline-offset: 2px; }
.numeric-slider .numeric-slider-unit { color: #69737c; font: 600 12px "Roboto Mono", Consolas, monospace; white-space: nowrap; }
.numeric-slider .numeric-slider-range { display: block; box-sizing: border-box; width: 100%; min-width: 0; height: 30px; min-height: 30px; margin: 0; padding: 0 8px; border: 0; border-radius: 999px; appearance: none; background: linear-gradient(90deg, var(--range-start) 0%, var(--range-end) var(--range-progress), #d8dee2 var(--range-progress), #d8dee2 100%); box-shadow: inset 0 1px 3px rgba(31, 42, 50, .18); cursor: pointer; }
.numeric-slider .numeric-slider-range::-webkit-slider-thumb { width: 20px; height: 20px; border: 2px solid #fff; border-radius: 50%; appearance: none; background: #fff; box-shadow: 0 1px 3px rgba(22, 30, 38, .2); }
.numeric-slider .numeric-slider-range::-moz-range-thumb { width: 16px; height: 16px; border: 2px solid #fff; border-radius: 50%; background: #fff; }
.numeric-slider .numeric-slider-range::-moz-range-track { border: 0; background: transparent; }
.numeric-slider .numeric-slider-range:focus-visible { outline: 2px solid #3e626e; outline-offset: 3px; }
.numeric-slider-compact { grid-template-columns: 64px 44px minmax(56px, 1fr); gap: 5px; }
.numeric-slider-no-range { grid-template-columns: 76px 44px; width: max-content; max-width: 100%; }
.numeric-slider-compact.numeric-slider-no-range { grid-template-columns: 64px 44px; }
.numeric-slider-compact .numeric-slider-value { height: 34px; min-height: 34px; padding: 4px; font-size: 12px; }
.numeric-slider-compact .numeric-slider-unit { font-size: 10px; }
.numeric-slider-compact .numeric-slider-range { height: 24px; min-height: 24px; padding: 0 6px; }
.numeric-slider-compact .numeric-slider-range::-webkit-slider-thumb { width: 17px; height: 17px; }
@media (max-width: 600px) {
  .numeric-slider { grid-template-columns: 68px 38px minmax(48px, 1fr); gap: 5px; }
  .numeric-slider-compact { grid-template-columns: 58px 38px minmax(48px, 1fr); gap: 4px; }
  .numeric-slider-no-range { grid-template-columns: 68px 38px; }
  .numeric-slider-compact.numeric-slider-no-range { grid-template-columns: 58px 38px; }
  .numeric-slider-unit { font-size: 10px; }
}
</style>
