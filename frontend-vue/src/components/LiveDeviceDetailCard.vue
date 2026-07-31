<template>
  <article
    class="detail-card clickable-detail-card"
    role="button"
    tabindex="0"
    @click="$emit('select', device.device_id)"
    @keydown.enter="$emit('select', device.device_id)"
    @keydown.space.prevent="$emit('select', device.device_id)"
  >
    <div v-if="showHeader" class="detail-head">
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
        <strong>{{ formatNumber(device.current_temperature) }} C</strong>
      </div>
      <div class="mini-box">
        <span>当前湿度</span>
        <strong>{{ formatNumber(device.current_humidity) }} %</strong>
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
  device: { type: Object, required: true },
  showHeader: { type: Boolean, default: true }
});

defineEmits(["select"]);

const stateTextMap = {
  OFFLINE: "离线",
  IDLE: "空闲",
  READY: "就绪",
  WAIT_LOCAL_CONFIRM: "等待本机确认",
  RUNNING: "运行中",
  PAUSED: "已暂停",
  COMPLETED: "已完成",
  STOPPED: "已停止",
  STOPPING: "停止中",
  ABORTING: "中止中",
  ALARM: "报警",
  MAINTENANCE: "维护中"
};

const stateClass = computed(() => {
  if (props.device.run_state === "ALARM" || props.device.alarm) return "alarm";
  if (["STOPPED", "STOPPING", "ABORTING"].includes(props.device.run_state)) return "stopped";
  if (props.device.run_state === "IDLE") return "idle";
  if (props.device.online === false) return "idle";
  return "running";
});

function stateLabel(state) {
  return stateTextMap[state] || state || "未知";
}

function formatNumber(value) {
  return Number(value ?? 0).toFixed(1);
}
</script>
