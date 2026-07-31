<template>
  <article class="detail-card">
    <div class="detail-head">
      <div class="detail-id">
        <div class="detail-icon">箱</div>
        <div>
          <h3>{{ device.device_id }}</h3>
          <p :class="stateClass">{{ runStateLabel(device.run_state) }}</p>
        </div>
      </div>
      <div class="detail-communication" :class="communicationClass(device.online)">
        <span class="status-dot"></span>
        <span>{{ communicationLabel(device.online) }}</span>
      </div>
    </div>

    <div class="detail-grid">
      <div class="mini-box">
        <span>当前温度</span>
        <strong>{{ device.current_temperature.toFixed(1) }} C</strong>
      </div>
      <div class="mini-box">
        <span>当前湿度</span>
        <strong>{{ device.current_humidity.toFixed(1) }} %</strong>
      </div>
      <div class="mini-box">
        <span>目标温度</span>
        <strong>{{ device.target_temperature }} C</strong>
      </div>
      <div class="mini-box">
        <span>目标湿度</span>
        <strong>{{ device.target_humidity }} %</strong>
      </div>
    </div>

    <div v-if="device.alarm" class="alarm-box">
      <strong>报警激活</strong>
      <span>{{ device.alarm }}</span>
    </div>
  </article>
</template>

<script setup>
import { computed } from "vue";
import { communicationClass, communicationLabel, runStateLabel } from "../utils/state";

const props = defineProps({
  device: { type: Object, required: true }
});

const stateClass = computed(() => {
  if (props.device.run_state === "ALARM" || props.device.alarm) return "alarm";
  if (["STOPPED", "STOPPING", "ABORTING"].includes(props.device.run_state)) return "stopped";
  if (props.device.run_state === "IDLE") return "idle";
  if (props.device.online === false) return "idle";
  return "running";
});
</script>
