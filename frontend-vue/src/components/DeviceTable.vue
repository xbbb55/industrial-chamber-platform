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
          <td>{{ device.current_temperature.toFixed(1) }} C</td>
          <td>{{ device.current_humidity.toFixed(1) }} %</td>
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
</script>
