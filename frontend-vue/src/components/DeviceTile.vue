<template>
  <button class="device-tile" :class="{ active }" @click="$emit('select')">
    <div class="device-tile-head">
      <strong>{{ device.device_id }}</strong>
      <span :class="['state-dot', stateClass]"></span>
    </div>
    <p>{{ device.name }}</p>
    <div class="tile-row">
      <span>运行状态</span>
      <b :class="stateClass">{{ stateText }}</b>
    </div>
    <div class="tile-row">
      <span>通讯状态</span>
      <b :class="communicationClass(device.online)">{{ communicationLabel(device.online) }}</b>
    </div>
    <div class="tile-row">
      <span>温湿度</span>
      <b>{{ device.current_temperature.toFixed(1) }}C / {{ device.current_humidity.toFixed(1) }}%</b>
    </div>
    <div class="tile-row">
      <span>报警</span>
      <b>{{ device.alarm || "无" }}</b>
    </div>
  </button>
</template>

<script setup>
import { computed } from "vue";
import { communicationClass, communicationLabel, runStateLabel } from "../utils/state";

const props = defineProps({
  device: { type: Object, required: true },
  active: { type: Boolean, default: false }
});

defineEmits(["select"]);

const stateText = computed(() => runStateLabel(props.device.run_state));
const stateClass = computed(() => {
  if (props.device.run_state === "ALARM" || props.device.alarm) return "alarm";
  if (["STOPPED", "STOPPING", "ABORTING"].includes(props.device.run_state)) return "stopped";
  if (props.device.run_state === "IDLE") return "idle";
  if (props.device.online === false) return "idle";
  return "running";
});
</script>
