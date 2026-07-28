<template>
  <div class="app-shell">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">IC</div>
        <div>
          <h1>环境试验箱平台</h1>
          <p>Industrial Chamber QC</p>
        </div>
      </div>

      <nav class="nav-list">
        <button
          v-for="item in navItems"
          :key="item.key"
          :class="{ active: activeView === item.key }"
          @click="activeView = item.key"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-foot">
        <p>总控服务</p>
        <strong>{{ connectionText }}</strong>
      </div>
    </aside>

    <section class="main-shell">
      <header class="topbar">
        <div>
          <h2>{{ currentTitle }}</h2>
          <p>共享内存实时读取，FastAPI 路由转发，WebSocket 推送</p>
        </div>
        <div class="top-actions">
          <div class="search">搜索设备、状态或报警</div>
          <div class="notify"></div>
          <div class="user-card">
            <div>
              <strong>Admin User</strong>
              <span>系统管理员</span>
            </div>
            <div class="avatar">A</div>
          </div>
        </div>
      </header>

      <main class="content">
        <section v-if="activeView === 'dashboard'" class="page-stack">
          <div class="kpi-grid">
            <MetricCard label="在线设备" :value="`${onlineCount}/${devices.length}`" unit="台设备" tone="blue" />
            <MetricCard label="运行中" :value="runningCount" unit="正在执行试验" tone="green" />
            <MetricCard label="报警设备" :value="alarmCount" unit="需要处理" tone="red" />
            <MetricCard label="共享内存占用" :value="payloadUsage" unit="当前 payload" tone="purple" />
          </div>

          <div class="split-grid">
            <section class="panel">
              <div class="panel-title">
                <h3>系统实时状态</h3>
                <span class="live-pill"><i></i>实时</span>
              </div>
              <div class="metric-mini-grid">
                <div class="mini-box">
                  <span>写入序号</span>
                  <strong>{{ sequence }}</strong>
                </div>
                <div class="mini-box">
                  <span>读取延迟</span>
                  <strong>{{ readLatency }}</strong>
                </div>
                <div class="mini-box">
                  <span>刷新频率</span>
                  <strong>250ms</strong>
                </div>
                <div class="mini-box">
                  <span>数据来源</span>
                  <strong>{{ sourceName }}</strong>
                </div>
              </div>
            </section>

            <section class="panel">
              <div class="panel-title">
                <h3>效率指标</h3>
                <span>模拟计算</span>
              </div>
              <div class="metric-mini-grid">
                <div class="mini-box">
                  <span>平均温度偏差</span>
                  <strong>{{ avgTempDelta }}C</strong>
                  <div class="bar"><b :style="{ width: `${Math.min(avgTempDelta * 18, 100)}%` }"></b></div>
                </div>
                <div class="mini-box">
                  <span>平均湿度偏差</span>
                  <strong>{{ avgHumDelta }}%</strong>
                  <div class="bar green"><b :style="{ width: `${Math.min(avgHumDelta * 18, 100)}%` }"></b></div>
                </div>
              </div>
            </section>
          </div>

          <div class="split-grid">
            <section class="panel chart-panel">
              <div class="panel-title">
                <h3>实时温湿度趋势</h3>
                <span>蓝色温度 / 绿色湿度</span>
              </div>
              <canvas ref="trendCanvas" width="760" height="280"></canvas>
            </section>

            <section class="panel">
              <div class="panel-title">
                <h3>设备状态墙</h3>
                <span>{{ devices.length }} 台</span>
              </div>
              <div class="machine-wall">
                <DeviceTile
                  v-for="device in devices"
                  :key="device.device_id"
                  :device="device"
                  :active="selectedDeviceId === device.device_id"
                  @select="selectedDeviceId = device.device_id"
                />
              </div>
            </section>
          </div>

          <section class="panel">
            <div class="panel-title">
              <h3>设备实时列表</h3>
              <span>来自共享内存</span>
            </div>
            <DeviceTable :devices="devices" />
          </section>
        </section>

        <section v-else-if="activeView === 'machines'" class="page-stack">
          <div class="section-head">
            <h2>设备监控</h2>
            <span class="live-pill"><i></i>实时连接</span>
          </div>
          <div class="machine-detail-grid">
            <DeviceDetailCard
              v-for="device in devices"
              :key="device.device_id"
              :device="device"
            />
          </div>
        </section>

        <section v-else-if="activeView === 'memory'" class="page-stack">
          <div class="section-head">
            <h2>共享内存检查</h2>
            <a class="link-button" href="/debug" target="_blank">打开调试页</a>
          </div>
          <div class="kpi-grid">
            <MetricCard label="共享内存名称" :value="memoryName" unit="固定映射名" tone="blue" />
            <MetricCard label="总容量" :value="memoryTotal" unit="共享内存大小" tone="green" />
            <MetricCard label="数据长度" :value="payloadLength" unit="当前 JSON" tone="purple" />
            <MetricCard label="可读状态" :value="memoryStableText" unit="版本号机制" tone="red" />
          </div>
          <section class="panel">
            <div class="panel-title">
              <h3>完整快照 JSON</h3>
              <span>{{ new Date().toLocaleTimeString() }}</span>
            </div>
            <pre class="json-view">{{ formattedSnapshot }}</pre>
          </section>
        </section>

        <section v-else class="page-stack">
          <div class="section-head">
            <h2>{{ currentTitle }}</h2>
            <span>预留模块</span>
          </div>
          <section class="panel empty-panel">
            <h3>模块待接入</h3>
            <p>这里将接入历史曲线、试验报告、报警处理、配方管理和权限审批。</p>
          </section>
        </section>
      </main>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import MetricCard from "./components/MetricCard.vue";
import DeviceTile from "./components/DeviceTile.vue";
import DeviceTable from "./components/DeviceTable.vue";
import DeviceDetailCard from "./components/DeviceDetailCard.vue";

const activeView = ref("dashboard");
const devices = ref([]);
const snapshot = ref(null);
const routerReadAt = ref(null);
const connectionText = ref("连接中");
const selectedDeviceId = ref(null);
const trendCanvas = ref(null);
const trendPoints = ref([]);

const navItems = [
  { key: "dashboard", label: "总览看板", icon: "D" },
  { key: "machines", label: "设备监控", icon: "M" },
  { key: "memory", label: "共享内存", icon: "S" },
  { key: "alarms", label: "报警中心", icon: "A" },
  { key: "reports", label: "试验报告", icon: "R" },
  { key: "settings", label: "系统设置", icon: "C" }
];

const titleMap = {
  dashboard: "环境试验箱数据看板",
  machines: "设备监控",
  memory: "共享内存检查",
  alarms: "报警中心",
  reports: "试验报告",
  settings: "系统设置"
};

const currentTitle = computed(() => titleMap[activeView.value]);
const onlineCount = computed(() => devices.value.filter(device => device.online).length);
const runningCount = computed(() => devices.value.filter(device => device.run_state === "RUNNING").length);
const alarmCount = computed(() => devices.value.filter(device => device.run_state === "ALARM" || device.alarm).length);
const sequence = computed(() => snapshot.value?.sequence ?? "--");
const sourceName = computed(() => snapshot.value?.source ?? "--");
const readLatency = computed(() => {
  if (!snapshot.value || !routerReadAt.value) return "--";
  return `${Math.max(0, (routerReadAt.value - snapshot.value.written_at) * 1000).toFixed(0)}ms`;
});

const avgTempDelta = computed(() => averageDelta("current_temperature", "target_temperature"));
const avgHumDelta = computed(() => averageDelta("current_humidity", "target_humidity"));
const payloadUsage = computed(() => {
  const bytes = new Blob([JSON.stringify(snapshot.value || {})]).size;
  return `${(bytes / 1024).toFixed(1)}KB`;
});
const payloadLength = computed(() => payloadUsage.value);
const memoryName = computed(() => "industrial_chamber_realtime_v1");
const memoryTotal = computed(() => "256KB");
const memoryStableText = computed(() => "稳定可读");
const formattedSnapshot = computed(() => JSON.stringify(snapshot.value, null, 2));

function averageDelta(currentKey, targetKey) {
  if (!devices.value.length) return "--";
  const total = devices.value.reduce((sum, device) => sum + Math.abs(device[currentKey] - device[targetKey]), 0);
  return (total / devices.value.length).toFixed(1);
}

function connectSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${location.host}/ws/memory`);
  socket.onopen = () => {
    connectionText.value = "已连接";
  };
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.type === "memory_not_ready") {
      connectionText.value = "共享内存未就绪";
      return;
    }
    snapshot.value = message.snapshot;
    routerReadAt.value = message.router_read_at;
    devices.value = message.snapshot.devices || [];
    if (!devices.value.some(device => device.device_id === selectedDeviceId.value)) {
      selectedDeviceId.value = devices.value[0]?.device_id || null;
    }
    pushTrendPoint();
  };
  socket.onclose = () => {
    connectionText.value = "重连中";
    setTimeout(connectSocket, 1200);
  };
}

function pushTrendPoint() {
  const first = devices.value[0];
  if (!first) return;
  trendPoints.value.push({
    temp: first.current_temperature,
    hum: first.current_humidity
  });
  if (trendPoints.value.length > 100) trendPoints.value.shift();
  drawTrend();
}

function drawTrend() {
  nextTick(() => {
    const canvas = trendCanvas.value;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    const pad = 34;
    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = "#293142";
    ctx.font = "12px Segoe UI";
    ctx.fillStyle = "#9ca3af";

    for (let i = 0; i < 5; i++) {
      const y = pad + i * ((h - pad * 2) / 4);
      ctx.beginPath();
      ctx.setLineDash([4, 4]);
      ctx.moveTo(pad, y);
      ctx.lineTo(w - pad, y);
      ctx.stroke();
    }

    ctx.setLineDash([]);
    drawSeries(ctx, trendPoints.value.map(point => point.temp), "#3b82f6", -30, 90, w, h, pad);
    drawSeries(ctx, trendPoints.value.map(point => point.hum), "#22c55e", 0, 100, w, h, pad);
  });
}

function drawSeries(ctx, values, color, min, max, w, h, pad) {
  if (values.length < 2) return;
  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = pad + index * ((w - pad * 2) / Math.max(values.length - 1, 1));
    const y = h - pad - ((value - min) / (max - min)) * (h - pad * 2);
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

onMounted(connectSocket);
watch(activeView, () => nextTick(drawTrend));
</script>
