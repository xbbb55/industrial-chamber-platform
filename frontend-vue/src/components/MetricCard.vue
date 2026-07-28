<template>
  <article class="metric-card">
    <div class="metric-head">
      <div>
        <p>{{ label }}</p>
        <strong>{{ value }}</strong>
        <span>{{ unit }}</span>
      </div>
      <div class="metric-icon" :class="tone">{{ iconText }}</div>
    </div>
  </article>
</template>

<script setup>
const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  unit: { type: String, default: "" },
  tone: { type: String, default: "blue" }
});

const iconText = props.label.slice(0, 1);
</script>

