<template>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>设备</th>
          <th>名称</th>
          <th>运行状态</th>
          <th>通讯状态</th>
          <th>当前温度</th>
          <th>当前湿度</th>
          <th>目标值</th>
          <th>步骤</th>
          <th>报警</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="device in devices" :key="device.device_id">
          <td>{{ device.device_id }}</td>
          <td>{{ device.name }}</td>
          <td>{{ runStateLabel(device.run_state) }}</td>
          <td :class="communicationClass(device.online)">{{ communicationLabel(device.online) }}</td>
          <td>{{ formatNumber(device.current_temperature) }} C</td>
          <td>{{ formatNumber(device.current_humidity) }} %</td>
          <td>{{ device.target_temperature }} C / {{ device.target_humidity }} %</td>
          <td>{{ device.total_steps ? `${device.current_step}/${device.total_steps}` : "--" }}</td>
          <td>{{ device.alarm || "无" }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { communicationClass, communicationLabel, runStateLabel } from "../utils/state";

defineProps({
  devices: { type: Array, required: true }
});

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

function formatNumber(value) {
  return Number(value ?? 0).toFixed(1);
}
</script>
