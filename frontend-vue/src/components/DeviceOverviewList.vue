<template>
  <div class="overview-list">
    <button
      v-for="device in devices"
      :key="device.device_id"
      class="overview-row"
      type="button"
      @click="$emit('select', device.device_id)"
    >
      <div class="overview-device">
        <span :class="['state-dot', stateClass(device)]"></span>
        <div>
          <strong>{{ device.device_id }}</strong>
          <p>{{ device.name }}</p>
        </div>
      </div>

      <div class="overview-cell">
        <span>IP 地址</span>
        <strong>{{ device.ip_address || device.ip || "--" }}</strong>
      </div>

      <div class="overview-cell">
        <span>当前温度</span>
        <strong>{{ formatNumber(device.current_temperature) }} C</strong>
      </div>

      <div class="overview-cell">
        <span>当前湿度</span>
        <strong>{{ formatNumber(device.current_humidity) }} %</strong>
      </div>

      <div class="overview-cell">
        <span>运行状态</span>
        <strong :class="stateClass(device)">{{ stateLabel(device.run_state) }}</strong>
      </div>

      <div class="overview-cell">
        <span>报警</span>
        <strong :class="{ alarm: device.alarm }">{{ device.alarm || "无" }}</strong>
      </div>
    </button>

    <div v-if="!devices.length" class="overview-empty">
      <strong>等待设备数据</strong>
      <span>共享内存有数据写入后，这里会自动显示每台试验箱的状态。</span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  devices: { type: Array, required: true }
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

function stateLabel(state) {
  return stateTextMap[state] || state || "未知";
}

function stateClass(device) {
  if (device.run_state === "ALARM" || device.alarm) return "alarm";
  if (["STOPPED", "STOPPING", "ABORTING", "OFFLINE"].includes(device.run_state)) return "stopped";
  if (device.run_state === "IDLE") return "idle";
  if (device.online === false) return "idle";
  return "running";
}

function formatNumber(value) {
  return Number(value ?? 0).toFixed(1);
}
</script>
