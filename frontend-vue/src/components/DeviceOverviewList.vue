<template>
  <div class="overview-list">
    <div v-if="devices.length" class="overview-list-head" aria-hidden="true">
      <span>设备</span>
      <span>通讯状态</span>
      <span>当前温度</span>
      <span>当前湿度</span>
      <span>运行状态</span>
      <span>报警</span>
      <span></span>
    </div>
    <button
      v-for="device in devices"
      :key="device.device_id"
      class="overview-row"
      type="button"
      @click="$emit('select', device.device_id)"
    >
      <div class="overview-device">
        <span class="overview-product-image">
          <img
            src="/assets/chamber-product.png"
            :data-device-id="device.device_id"
            :alt="`${device.name || device.device_id}设备图片`"
          />
        </span>
        <span :class="['state-dot', stateClass(device)]"></span>
        <div class="overview-device-copy">
          <strong>{{ device.device_id }}</strong>
          <p>{{ device.name }}</p>
          <small>IP {{ device.device_ip || device.ip_address || device.ip || "--" }}</small>
        </div>
      </div>

      <div class="overview-cell overview-communication">
        <span class="overview-mobile-label">通讯状态</span>
        <strong class="overview-communication-status" :class="deviceCommunicationClass(device)">
          <i aria-hidden="true"></i>{{ deviceCommunicationLabel(device) }}
        </strong>
        <small class="communication-health">{{ communicationHealthLabel(device) }}</small>
      </div>

      <div class="overview-cell overview-temperature">
        <span class="overview-mobile-label">当前温度</span>
        <strong class="overview-reading">{{ formatNumber(device.current_temperature) }}<small>°C</small></strong>
      </div>

      <div class="overview-cell overview-humidity">
        <span class="overview-mobile-label">当前湿度</span>
        <strong class="overview-reading">{{ formatNumber(device.current_humidity) }}<small>%RH</small></strong>
      </div>

      <div class="overview-cell overview-run-state">
        <span class="overview-mobile-label">运行状态</span>
        <strong :class="stateClass(device)">{{ runStateLabel(device.run_state) }}</strong>
      </div>

      <div class="overview-cell overview-alarm">
        <span class="overview-mobile-label">报警</span>
        <strong :class="{ alarm: device.alarm }">{{ device.alarm || "无" }}</strong>
      </div>

      <AppIcon class="overview-enter-icon" name="chevronRight" :size="18" />
    </button>

    <div v-if="!devices.length" class="overview-empty">
      <strong>等待设备数据</strong>
      <span>共享内存有数据写入后，这里会自动显示每台试验箱的状态。</span>
    </div>
  </div>
</template>

<script setup>
import AppIcon from "./AppIcon.vue";
import {
  communicationHealthLabel,
  deviceCommunicationClass,
  deviceCommunicationLabel,
  runStateLabel
} from "../utils/state";

defineProps({
  devices: { type: Array, required: true }
});

defineEmits(["select"]);

function stateClass(device) {
  if (device.run_state === "ALARM" || device.alarm) return "alarm";
  if (["STOPPED", "STOPPING", "ABORTING"].includes(device.run_state)) return "stopped";
  if (device.run_state === "IDLE") return "idle";
  if (!device.run_state || ["OFFLINE", "UNKNOWN"].includes(device.run_state)) return "unknown";
  if (device.online === false) return "idle";
  return "running";
}

function formatNumber(value) {
  return value == null || value === "" || !Number.isFinite(Number(value)) ? "--" : Number(value).toFixed(1);
}
</script>
