<template>
  <section class="hmi-dashboard" aria-label="环境试验箱实时监控仪表盘">
    <header class="hmi-header">
      <div>
        <span class="hmi-eyebrow">LIVE ENVIRONMENT</span>
        <h3>实时环境数据</h3>
      </div>
      <span class="hmi-live"><i></i>实时采集</span>
    </header>

    <div class="env-reading-grid">
      <article class="env-reading-card temperature">
        <div class="metric-heading">
          <span class="env-reading-icon"><Thermometer :size="18" :stroke-width="1.8" /></span>
          <span>当前温度</span>
        </div>
        <div class="metric-reading">
          <strong>{{ displayValue(temperature) }}</strong>
          <span>°C</span>
        </div>
        <div class="metric-target">
          <span>目标温度</span>
          <strong>{{ displayValue(targetTemperature) }} <small>°C</small></strong>
        </div>
        <div class="metric-meter" role="meter" :aria-valuenow="temperature" aria-valuemin="-40" aria-valuemax="100" aria-label="当前温度">
          <i :style="{ width: `${valuePercent(temperature, -40, 100)}%` }"></i>
        </div>
        <div class="metric-scale"><span>-40 °C</span><span>100 °C</span></div>
      </article>

      <article class="env-reading-card humidity">
        <div class="metric-heading">
          <span class="env-reading-icon"><Droplets :size="18" :stroke-width="1.8" /></span>
          <span>当前湿度</span>
        </div>
        <div class="metric-reading">
          <strong>{{ displayValue(humidity) }}</strong>
          <span>%RH</span>
        </div>
        <div class="metric-target">
          <span>目标湿度</span>
          <strong>{{ displayValue(targetHumidity) }} <small>%RH</small></strong>
        </div>
        <div class="metric-meter" role="meter" :aria-valuenow="humidity" aria-valuemin="0" aria-valuemax="100" aria-label="当前湿度">
          <i :style="{ width: `${valuePercent(humidity, 0, 100)}%` }"></i>
        </div>
        <div class="metric-scale"><span>0 %RH</span><span>100 %RH</span></div>
      </article>
    </div>

    <footer class="status-bar" aria-label="设备状态">
      <div v-for="item in statusItems" :key="item.label" class="status-item">
        <component :is="item.icon" class="status-icon" :size="17" :stroke-width="1.8" aria-hidden="true" />
        <div class="status-copy">
          <span>{{ item.label }}</span>
          <strong :class="statusTone(item.value)"><i></i>{{ item.value || "--" }}</strong>
        </div>
      </div>
    </footer>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { Activity, Droplets, Network, Thermometer, Timer } from "lucide-vue-next";

const props = defineProps({
  temperature: { type: Number, default: 0 },
  humidity: { type: Number, default: 0 },
  targetTemperature: { type: Number, default: 0 },
  targetHumidity: { type: Number, default: 0 },
  deviceStatus: { type: String, default: "未知" },
  runningMode: { type: String, default: "未知" },
  communicationStatus: { type: String, default: "未知" },
  startTime: { type: String, default: "--" }
});

function displayValue(value) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue.toFixed(1) : "--";
}

function valuePercent(value, minimum, maximum) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return 0;
  return Math.min(100, Math.max(0, ((numericValue - minimum) / (maximum - minimum)) * 100));
}

function statusTone(status) {
  const text = String(status || "");
  if (["运行", "正常", "在线", "已连接"].some((keyword) => text.includes(keyword))) return "positive";
  if (["停止", "中止", "保持", "暂停"].some((keyword) => text.includes(keyword))) return "warning";
  if (["离线", "异常", "报警", "故障", "失败"].some((keyword) => text.includes(keyword))) return "negative";
  return "neutral";
}

const statusItems = computed(() => [
  { icon: Activity, label: "设备状态", value: props.deviceStatus },
  { icon: Thermometer, label: "运行模式", value: props.runningMode },
  { icon: Network, label: "通讯状态", value: props.communicationStatus },
  { icon: Timer, label: "启动时间", value: props.startTime }
]);
</script>

<style scoped>
.hmi-dashboard {
  --metric-temp: #267fa5;
  --metric-humidity: #258a78;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 18px;
  box-sizing: border-box;
  min-width: 0;
  min-height: 0;
  padding: 18px 20px 14px;
  border: 1px solid #d9e0e4;
  border-radius: 10px;
  background: #fff;
  color: #22272b;
}

.hmi-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  min-width: 0;
}

.hmi-eyebrow {
  display: block;
  margin-bottom: 3px;
  color: #879198;
  font-size: 10px;
  font-weight: 700;
  line-height: 1.2;
}

.hmi-header h3 {
  margin: 0;
  color: #23282c;
  font-size: 18px;
  font-weight: 750;
  line-height: 1.35;
}

.hmi-live {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  flex: 0 0 auto;
  color: #667179;
  font-size: 12px;
  font-weight: 600;
}

.hmi-live i,
.status-copy strong i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #39a477;
}

.env-reading-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0;
  min-width: 0;
}

.env-reading-card {
  display: grid;
  grid-template-rows: auto auto auto auto auto;
  align-content: center;
  min-width: 0;
  padding: 12px 20px;
}

.env-reading-card + .env-reading-card {
  border-left: 1px solid #e2e7ea;
}

.env-reading-card.temperature { --metric-accent: var(--metric-temp); }
.env-reading-card.humidity { --metric-accent: var(--metric-humidity); }

.metric-heading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #59636a;
  font-size: 13px;
  font-weight: 650;
}

.env-reading-icon {
  display: inline-grid;
  width: 34px;
  height: 34px;
  place-items: center;
  border-radius: 8px;
  background: color-mix(in srgb, var(--metric-accent) 12%, white);
  color: var(--metric-accent);
}

.metric-heading small {
  margin-left: auto;
  color: #889198;
  font-size: 11px;
  font-weight: 600;
}

.metric-reading {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin: 12px 0 9px;
  color: #20262a;
  font-variant-numeric: tabular-nums;
}

.metric-reading strong {
  font-size: 58px;
  font-weight: 720;
  line-height: 1;
}

.metric-reading > span {
  color: #69747b;
  font-size: 14px;
  font-weight: 600;
}

.metric-target {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
  color: #778188;
  font-size: 12px;
}

.metric-target strong {
  color: #3d474e;
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.metric-target small { color: #7c878d; font-size: 11px; font-weight: 550; }

.metric-meter {
  position: relative;
  height: 8px;
  overflow: hidden;
  border-radius: 99px;
  background: #e4e9ec;
}

.metric-meter i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--metric-accent);
  transition: width .25s ease;
}

.metric-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
  color: #89939a;
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.status-bar {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  border-top: 1px solid #e2e7ea;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
  padding: 12px 10px 0;
  color: #6b757c;
}

.status-item:not(:first-child) { border-left: 1px solid #e2e7ea; }
.status-icon { flex: 0 0 auto; color: #727d84; }
.status-copy { display: grid; gap: 2px; min-width: 0; }
.status-copy > span { color: #858e94; font-size: 11px; line-height: 1.3; }
.status-copy strong {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  overflow: hidden;
  color: #444d53;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.status-copy strong i { width: 6px; height: 6px; flex: 0 0 auto; background: #98a2a8; }
.status-copy strong.positive { color: #267e5d; }
.status-copy strong.positive i { background: #39a477; }
.status-copy strong.warning { color: #9a702e; }
.status-copy strong.warning i { background: #d29b3d; }
.status-copy strong.negative { color: #ae4b4b; }
.status-copy strong.negative i { background: #c95757; }

@media (max-width: 900px) {
  .hmi-dashboard { gap: 14px; padding: 16px; }
  .status-item { padding-inline: 8px; }
}

@media (max-width: 700px) {
  .env-reading-grid { grid-template-columns: minmax(0, 1fr); }
  .env-reading-card { padding: 12px 8px; }
  .env-reading-card + .env-reading-card { border-top: 1px solid #e2e7ea; border-left: 0; }
  .status-bar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .status-item:nth-child(odd) { border-left: 0; }
  .status-item:nth-child(n + 3) { border-top: 1px solid #e2e7ea; }
  .metric-reading strong { font-size: 44px; }
}

@media (min-width: 861px) and (max-width: 950px) {
  .env-reading-grid { grid-template-columns: minmax(0, 1fr); }
  .env-reading-card { padding: 12px 8px; }
  .env-reading-card + .env-reading-card { border-top: 1px solid #e2e7ea; border-left: 0; }
}
</style>
