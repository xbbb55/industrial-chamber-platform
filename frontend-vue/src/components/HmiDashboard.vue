<template>
  <section class="hmi-dashboard" aria-label="环境试验箱实时监控仪表盘">
    <header class="hmi-header">
      <div class="header-line header-line-left" aria-hidden="true"><i></i><b></b><b></b><b></b></div>
      <div class="header-title">
        <h3>环境试验箱实时监控</h3>
        <p>ENVIRONMENTAL CHAMBER MONITORING</p>
      </div>
      <div class="header-line header-line-right" aria-hidden="true"><i></i><b></b><b></b><b></b></div>
    </header>

    <div class="gauge-stage">
      <article
        v-for="gauge in gauges"
        :key="gauge.kind"
        class="gauge-card"
        :class="gauge.kind"
        :aria-label="`${gauge.label}：${gauge.displayValue} ${gauge.unit}`"
      >
        <div class="metal-ring" aria-hidden="true"></div>
        <div class="gauge-ticks" aria-hidden="true">
          <i
            v-for="tick in dialTicks"
            :key="tick.index"
            class="gauge-tick"
            :class="tick.zone"
            :style="{ '--tick-angle': `${tick.angle}deg` }"
          ></i>
        </div>
        <div class="gauge-numbers" aria-hidden="true">
          <span
            v-for="(reading, index) in gauge.readings"
            :key="reading"
            :style="numberPosition(index, gauge.readings.length)"
          >{{ reading }}</span>
        </div>
        <div class="pointer" :style="{ transform: `rotate(${gauge.pointerAngle}deg)` }" aria-hidden="true">
          <i></i>
        </div>
        <div class="gauge-face">
          <div class="dial-content">
            <div class="gauge-label">{{ gauge.label }}</div>
            <div class="gauge-subtitle">{{ gauge.subtitle }}</div>
            <div class="digital-value" :class="gauge.kind">
              <strong :aria-label="gauge.displayValue">
                <template v-for="(character, index) in gauge.characters" :key="`${character}-${index}`">
                  <span v-if="character === '.'" class="seven-dot" aria-hidden="true"></span>
                  <span v-else-if="character === '-'" class="seven-minus" aria-hidden="true"></span>
                  <span v-else class="seven-digit" aria-hidden="true">
                    <i
                      v-for="segment in segments"
                      :key="segment"
                      :class="[segment, { on: activeSegments[character]?.includes(segment) }]"
                    ></i>
                  </span>
                </template>
              </strong>
              <span>{{ gauge.unit }}</span>
            </div>
          </div>
        </div>
      </article>
    </div>

    <footer class="status-bar">
      <div v-for="item in statusItems" :key="item.label" class="status-item">
        <component :is="item.icon" class="status-icon" :size="30" :stroke-width="1.7" aria-hidden="true" />
        <div class="status-copy">
          <span>{{ item.label }}</span>
          <strong :class="[item.tone, statusTone(item.value)]">{{ item.value }}<i v-if="['green', 'red'].includes(statusTone(item.value) || item.tone)"></i></strong>
        </div>
      </div>
    </footer>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { Clock3, Database, Network, ServerCog } from "lucide-vue-next";

const props = defineProps({
  temperature: { type: Number, default: 0 },
  humidity: { type: Number, default: 0 },
  deviceStatus: { type: String, default: "未知" },
  updatedAt: { type: String, default: "--" },
  communicationStatus: { type: String, default: "未知" },
  dataSource: { type: String, default: "--" }
});

const segments = ["a", "b", "c", "d", "e", "f", "g"];
const activeSegments = {
  0: ["a", "b", "c", "d", "e", "f"],
  1: ["b", "c"],
  2: ["a", "b", "g", "e", "d"],
  3: ["a", "b", "c", "d", "g"],
  4: ["f", "g", "b", "c"],
  5: ["a", "f", "g", "c", "d"],
  6: ["a", "f", "g", "e", "c", "d"],
  7: ["a", "b", "c"],
  8: ["a", "b", "c", "d", "e", "f", "g"],
  9: ["a", "b", "c", "d", "f", "g"]
};

const dialTicks = Array.from({ length: 61 }, (_, index) => ({
  index,
  angle: -132 + index * 4.4,
  zone: index >= 56 ? "alarm-zone" : index >= 43 ? "warning-zone" : "normal-zone"
}));

function normalizeValue(value, minimum, maximum) {
  const numericValue = Number(value);
  if (!Number.isFinite(numericValue)) return minimum;
  return Math.min(maximum, Math.max(minimum, numericValue));
}

function pointerAngle(value, minimum, maximum) {
  return -132 + ((normalizeValue(value, minimum, maximum) - minimum) / (maximum - minimum)) * 264;
}

function displayValue(value) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue.toFixed(1) : "0.0";
}

function numberPosition(index, count) {
  const angle = 228 + (index * 264) / (count - 1);
  const radians = (angle * Math.PI) / 180;
  return {
    left: `${50 + Math.sin(radians) * 39}%`,
    top: `${50 - Math.cos(radians) * 39}%`
  };
}

const gauges = computed(() => [
  {
    kind: "temperature",
    label: "温度",
    subtitle: "TEMPERATURE",
    displayValue: displayValue(props.temperature),
    characters: [...displayValue(props.temperature)],
    unit: "°C",
    readings: ["-40", "-20", "0", "20", "40", "60", "80", "100"],
    pointerAngle: pointerAngle(props.temperature, -40, 100)
  },
  {
    kind: "humidity",
    label: "湿度",
    subtitle: "HUMIDITY",
    displayValue: displayValue(props.humidity),
    characters: [...displayValue(props.humidity)],
    unit: "%RH",
    readings: ["0", "20", "40", "60", "80", "100"],
    pointerAngle: pointerAngle(props.humidity, 0, 100)
  }
]);

function statusTone(status) {
  const text = String(status || "");
  const orangeKeywords = ["\u505c\u6b62", "\u4e2d\u6b62", "\u4fdd\u6301", "\u6682\u505c"];
  const redKeywords = ["\u79bb\u7ebf", "\u5f02\u5e38", "\u62a5\u8b66", "\u6545\u969c", "\u5931\u8d25"];
  const greenKeywords = ["\u8fd0\u884c", "\u6b63\u5e38", "\u5728\u7ebf", "\u5df2\u8fde\u63a5"];
  if (orangeKeywords.some((keyword) => text.includes(keyword))) return "orange";
  if (redKeywords.some((keyword) => text.includes(keyword))) return "red";
  if (greenKeywords.some((keyword) => text.includes(keyword))) return "green";
  return "";
}

const statusItems = computed(() => [
  { icon: ServerCog, label: "设备状态", value: props.deviceStatus, tone: "green" },
  { icon: Clock3, label: "更新时间", value: props.updatedAt, tone: "" },
  { icon: Network, label: "通讯状态", value: props.communicationStatus, tone: props.communicationStatus === "在线" ? "green" : "" },
  { icon: Database, label: "数据来源", value: props.dataSource, tone: "blue" }
]);
</script>

<style scoped>
.hmi-dashboard {
  --hmi-cyan: #26e7ef;
  --hmi-blue: #249fff;
  --hmi-green: #25d89a;
  --hmi-red: #ff4650;
  box-sizing: border-box;
  min-height: 0;
  flex: 1 1 auto;
  overflow: hidden;
  color: #e8f2ff;
  display: grid;
  grid-template-rows: 72px minmax(0, 1fr) 74px;
  border-radius: 7px;
  background:
    radial-gradient(ellipse 70% 68% at 50% 45%, rgba(25, 55, 83, .35), transparent 72%),
    linear-gradient(120deg, #07121d 0%, #0b1724 48%, #06111c 100%);
}

.hmi-header {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.header-title {
  z-index: 1;
  padding: 0 24px 6px;
  border-bottom: 1px solid rgba(111, 153, 187, .45);
  text-align: center;
}

.header-title h3 {
  margin: 0;
  color: #eef6ff;
  font-size: clamp(20px, 2vw, 30px);
  font-weight: 650;
  letter-spacing: .12em;
  line-height: 1.15;
}

.header-title p {
  margin: 4px 0 0;
  color: #97abc4;
  font-family: "Rajdhani", "Segoe UI", sans-serif;
  font-size: clamp(10px, 1vw, 14px);
  font-weight: 600;
  letter-spacing: .08em;
}

.header-line {
  position: absolute;
  top: 57%;
  width: 28%;
  height: 25px;
  border-top: 1px solid rgba(113, 151, 185, .36);
}

.header-line-left { left: 0; }
.header-line-right { right: 0; transform: scaleX(-1); }
.header-line::after {
  content: "";
  position: absolute;
  top: -3px;
  right: 0;
  width: 16%;
  height: 23px;
  border-top: 1px solid rgba(113, 151, 185, .5);
  border-right: 1px solid rgba(113, 151, 185, .5);
  transform: skewX(43deg);
}
.header-line i { position: absolute; top: 4px; right: 20px; width: 18px; height: 1px; background: #50657b; transform: rotate(42deg); }
.header-line b { position: relative; display: inline-block; width: 10px; height: 5px; margin: 3px 2px 0; background: #52677d; opacity: .65; transform: skewX(35deg); }

.gauge-stage {
  --gauge-size: min(42cqw, 96cqh, 560px);
  min-height: 0;
  container-type: size;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: clamp(32px, 5vw, 72px);
  padding: 0 4% 2px;
}

.gauge-card {
  --accent: var(--hmi-cyan);
  position: relative;
  width: var(--gauge-size);
  height: var(--gauge-size);
  max-width: 100%;
  flex: 0 0 var(--gauge-size);
  container-type: size;
  border-radius: 50%;
  isolation: isolate;
  filter: drop-shadow(0 14px 18px rgba(0, 0, 0, .38));
}
.gauge-card.humidity { --accent: var(--hmi-blue); }

.metal-ring {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(135deg, #435260 0%, #b6c2cc 13%, #5d6b76 20%, #1e2b36 43%, #697883 73%, #101b26 100%);
  box-shadow: inset 0 0 0 2px rgba(205, 221, 232, .5), inset 0 0 0 8px rgba(9, 18, 28, .7), 0 0 0 1px rgba(152, 183, 204, .45);
}
.metal-ring::after { content: ""; position: absolute; inset: clamp(8px, 3cqw, 16px); border-radius: inherit; background: #09141f; box-shadow: inset 0 0 clamp(18px, 6.5cqw, 34px) #01070c; }

.gauge-ticks { position: absolute; inset: clamp(10px, 3.4cqw, 18px); z-index: 4; overflow: hidden; border-radius: 50%; pointer-events: none; }
.gauge-tick { position: absolute; inset: 0; transform: rotate(var(--tick-angle)); }
.gauge-tick::after { content: ""; position: absolute; top: 2.5%; left: 50%; width: clamp(2px, .45cqw, 3px); height: clamp(8px, 2.4cqw, 14px); background: var(--accent); box-shadow: 0 0 clamp(4px, 1.3cqw, 7px) color-mix(in srgb, var(--accent) 38%, transparent); transform: translateX(-50%); }
.gauge-tick:nth-child(5n + 1)::after { width: clamp(3px, .65cqw, 4px); height: clamp(14px, 4cqw, 24px); }
.gauge-tick.warning-zone::after { background: #ffb32e; box-shadow: 0 0 5px rgba(255, 179, 46, .35); }
.gauge-tick.alarm-zone::after { background: #ff4650; box-shadow: 0 0 5px rgba(255, 70, 80, .35); }

.gauge-numbers { position: absolute; inset: 0; z-index: 3; }
.gauge-numbers span { position: absolute; color: #dce7f4; font-family: "Rajdhani", "Segoe UI", sans-serif; font-size: clamp(10px, 3.4cqw, 19px); font-weight: 600; line-height: 1; text-shadow: 0 1px 4px #000; transform: translate(-50%, -50%); }

.gauge-face { position: absolute; inset: 22%; z-index: 6; overflow: hidden; border: clamp(2px, .55cqw, 3px) solid #1b4156; border-radius: 50%; background: radial-gradient(circle at 50% 45%, #101f2d 0%, #08131f 60%, #040b13 100%); box-shadow: inset 0 0 0 clamp(4px, 1.25cqw, 7px) rgba(2, 10, 17, .65), 0 0 0 1px rgba(72, 129, 164, .22); }
.gauge-face::after { content: ""; position: absolute; inset: clamp(3px, 1cqw, 6px); border-radius: 50%; border-bottom: 1px solid var(--accent); opacity: .75; }

.pointer { position: absolute; inset: 0; z-index: 5; transform-origin: 50% 50%; transition: transform .35s ease; pointer-events: none; }
.pointer i { position: absolute; top: 7%; left: calc(50% - clamp(5px, 1.45cqw, 8px)); display: block; width: clamp(10px, 2.9cqw, 16px); height: 16%; background: linear-gradient(90deg, transparent 0 25%, var(--accent) 40% 60%, transparent 75%); clip-path: polygon(50% 0, 94% 100%, 6% 100%); filter: drop-shadow(0 0 clamp(4px, 1.2cqw, 7px) color-mix(in srgb, var(--accent) 35%, transparent)); }

.dial-content { position: absolute; inset: 0; z-index: 2; display: flex; flex-direction: column; align-items: center; padding-top: 12%; text-align: center; }
.gauge-label { color: #c2d1e1; font-size: clamp(12px, 4.6cqw, 24px); font-weight: 500; letter-spacing: .12em; }
.gauge-subtitle { margin-top: clamp(2px, .6cqw, 4px); color: #91a4bc; font-family: "Rajdhani", "Segoe UI", sans-serif; font-size: clamp(8px, 2.5cqw, 14px); font-weight: 600; letter-spacing: .04em; }

.digital-value { margin-top: clamp(6px, 3cqw, 16px); display: flex; flex-direction: column; align-items: center; transform: translateY(-4%); }
.digital-value strong { display: flex; align-items: flex-end; gap: clamp(2px, .55cqw, 4px); height: clamp(42px, 17cqw, 94px); }
.digital-value > span { margin-top: clamp(3px, 1.5cqw, 8px); color: #f8fbff; font-family: "Rajdhani", "Segoe UI", sans-serif; font-size: clamp(12px, 4.6cqw, 25px); font-weight: 700; line-height: 1; text-shadow: 0 0 8px rgba(248, 251, 255, .42); }
.seven-digit { position: relative; display: inline-block; width: clamp(23px, 9.6cqw, 54px); height: clamp(41px, 17cqw, 94px); filter: drop-shadow(0 0 clamp(5px, 1.5cqw, 9px) rgba(248, 251, 255, .28)); }
.seven-digit i { position: absolute; display: block; background: color-mix(in srgb, var(--accent) 18%, transparent); opacity: .28; clip-path: polygon(8% 0, 92% 0, 100% 50%, 92% 100%, 8% 100%, 0 50%); }
.seven-digit i.on { opacity: 1; background: #f8fbff; box-shadow: 0 0 8px rgba(248, 251, 255, .62), 0 0 14px color-mix(in srgb, var(--accent) 24%, transparent); }
.seven-digit .a, .seven-digit .g, .seven-digit .d { left: 14%; width: 72%; height: 7%; }
.seven-digit .a { top: 0; }
.seven-digit .g { top: 46.5%; }
.seven-digit .d { bottom: 0; }
.seven-digit .b, .seven-digit .c, .seven-digit .e, .seven-digit .f { width: 10%; height: 41%; }
.seven-digit .b { top: 5%; right: 0; }
.seven-digit .c { right: 0; bottom: 5%; }
.seven-digit .e { bottom: 5%; left: 0; }
.seven-digit .f { top: 5%; left: 0; }
.seven-dot { width: clamp(5px, 1.5cqw, 8px); height: clamp(5px, 1.5cqw, 8px); margin: 0 1px clamp(3px, .8cqw, 5px) 0; border-radius: 50%; background: #f8fbff; box-shadow: 0 0 8px rgba(248, 251, 255, .62), 0 0 14px color-mix(in srgb, var(--accent) 24%, transparent); }
.seven-minus { align-self: center; width: clamp(16px, 4cqw, 24px); height: clamp(4px, 1cqw, 6px); margin: 0 1px; background: #f8fbff; box-shadow: 0 0 8px rgba(248, 251, 255, .62), 0 0 14px color-mix(in srgb, var(--accent) 24%, transparent); clip-path: polygon(8% 0, 92% 0, 100% 50%, 92% 100%, 8% 100%, 0 50%); }

.status-bar { min-width: 0; margin: 0 22px 12px; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border: 1px solid rgba(91, 143, 181, .35); border-radius: 10px; background: linear-gradient(100deg, rgba(10, 25, 40, .84), rgba(7, 19, 31, .64)); }
.status-item { position: relative; min-width: 0; display: flex; align-items: center; justify-content: center; gap: 12px; padding: 10px 14px; }
.status-item:not(:first-child)::before { content: ""; position: absolute; left: 0; height: 48%; border-left: 1px solid rgba(101, 138, 169, .28); }
.status-icon { flex: 0 0 auto; color: #a7bed5; }
.status-copy { min-width: 0; }
.status-copy > span { display: block; color: #b9c9da; font-size: 11px; letter-spacing: .06em; white-space: nowrap; }
.status-copy strong { display: block; overflow: hidden; margin-top: 3px; color: #f2f6fb; font-family: "Rajdhani", "Segoe UI", sans-serif; font-size: 13px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.status-copy strong.green { color: var(--hmi-green); }
.status-copy strong.red { color: var(--hmi-red); }
.status-copy strong.orange { color: #ffb12b; }
.status-copy strong.blue { color: #2caeff; }
.status-copy strong i { display: inline-block; width: 7px; height: 7px; margin-left: 7px; border-radius: 50%; background: currentColor; box-shadow: 0 0 7px currentColor; opacity: .9; }

/* Match the compact monitoring cards with the same industrial cockpit language. */
.hmi-dashboard {
  position: relative;
  border: 1px solid rgba(39, 157, 228, .58);
  border-radius: 0;
  background:
    radial-gradient(ellipse 64% 72% at 50% 46%, rgba(5, 87, 143, .18), transparent 70%),
    linear-gradient(90deg, rgba(14, 76, 116, .12) 1px, transparent 1px) 0 0 / 32px 32px,
    linear-gradient(rgba(14, 76, 116, .09) 1px, transparent 1px) 0 0 / 32px 32px,
    linear-gradient(125deg, #041321 0%, #061a2b 50%, #03101c 100%);
  box-shadow: inset 0 0 34px rgba(0, 119, 199, .10), 0 10px 28px rgba(0, 0, 0, .22);
  clip-path: polygon(11px 0, calc(100% - 11px) 0, 100% 11px, 100% calc(100% - 11px), calc(100% - 11px) 100%, 11px 100%, 0 calc(100% - 11px), 0 11px);
}

.hmi-dashboard::before,
.hmi-dashboard::after {
  content: "";
  position: absolute;
  z-index: 8;
  pointer-events: none;
}

.hmi-dashboard::before {
  top: 3px;
  left: 18px;
  right: 18px;
  height: 5px;
  border-top: 1px solid rgba(76, 197, 255, .72);
  background: linear-gradient(90deg, #2ed2ff 0 7%, transparent 7% 80%, rgba(62, 176, 238, .28) 80% 91%, #29d9ff 91% 93%, transparent 93%);
}

.hmi-dashboard::after {
  left: 9%;
  right: 9%;
  bottom: 2px;
  height: 2px;
  background: linear-gradient(90deg, transparent, #148cff 12%, #2bd8ff 50%, #148cff 88%, transparent);
  box-shadow: 0 -2px 11px rgba(26, 160, 255, .72);
}

.header-title { border-bottom-color: rgba(45, 185, 255, .58); }
.header-title h3 { color: #e1f5ff; text-shadow: 0 0 12px rgba(38, 174, 242, .28); }
.header-title p { color: #83b4d3; }
.header-line { border-top-color: rgba(45, 166, 231, .42); }
.header-line::after { border-color: rgba(62, 183, 242, .52); }
.header-line b { background: #2b9fd8; opacity: .55; }

.gauge-stage {
  background: radial-gradient(circle at 50% 48%, rgba(0, 118, 202, .10), transparent 62%);
}

.gauge-card {
  filter: drop-shadow(0 12px 18px rgba(0, 0, 0, .42)) drop-shadow(0 0 10px color-mix(in srgb, var(--accent) 14%, transparent));
}

.metal-ring {
  background:
    radial-gradient(circle, transparent 64%, rgba(34, 174, 235, .18) 64.5% 66%, transparent 66.5%),
    linear-gradient(135deg, #102d42 0%, #39718d 12%, #10273a 24%, #061522 48%, #2b5b75 76%, #06121e 100%);
  box-shadow:
    inset 0 0 0 2px rgba(88, 190, 239, .56),
    inset 0 0 0 7px rgba(2, 13, 23, .86),
    inset 0 0 24px rgba(0, 134, 216, .22),
    0 0 0 1px rgba(75, 166, 213, .50),
    0 0 16px color-mix(in srgb, var(--accent) 18%, transparent);
}

.metal-ring::after {
  background: radial-gradient(circle at 50% 42%, #0a2438, #03101b 70%);
  box-shadow: inset 0 0 clamp(20px, 7cqw, 38px) #01060b, inset 0 0 0 1px rgba(45, 159, 218, .20);
}

.gauge-face {
  border-color: color-mix(in srgb, var(--accent) 54%, #17394d);
  background: radial-gradient(circle at 50% 43%, #0a2a42 0%, #061827 60%, #020a12 100%);
  box-shadow:
    inset 0 0 0 clamp(4px, 1.25cqw, 7px) rgba(1, 8, 14, .72),
    inset 0 0 24px rgba(0, 108, 184, .16),
    0 0 0 1px rgba(54, 174, 229, .30),
    0 0 13px color-mix(in srgb, var(--accent) 16%, transparent);
}

.gauge-numbers span { color: #d7edfb; text-shadow: 0 0 6px rgba(35, 163, 226, .30); }
.gauge-label { color: #cae6f7; }
.gauge-subtitle { color: #78acd0; }

.status-bar {
  position: relative;
  overflow: hidden;
  border-color: rgba(38, 159, 226, .52);
  border-radius: 0;
  background: linear-gradient(100deg, rgba(4, 25, 42, .96), rgba(4, 16, 29, .92));
  box-shadow: inset 0 0 18px rgba(0, 117, 190, .08);
  clip-path: polygon(8px 0, calc(100% - 8px) 0, 100% 8px, 100% calc(100% - 8px), calc(100% - 8px) 100%, 8px 100%, 0 calc(100% - 8px), 0 8px);
}
.status-bar::before { content: ""; position: absolute; top: 0; left: 28px; width: 72px; height: 2px; background: #28cfff; box-shadow: 0 0 8px #159bdf; }
.status-icon { color: #67c7f2; filter: drop-shadow(0 0 4px rgba(34, 168, 226, .34)); }
.status-item:not(:first-child)::before { border-left-color: rgba(44, 154, 213, .30); }

@media (max-width: 900px) {
  .hmi-dashboard { overflow: visible; grid-template-rows: auto auto auto; clip-path: none; }
  .hmi-header { min-height: 76px; }
  .gauge-stage { --gauge-size: min(46cqw, 92cqh, 340px); gap: 20px; padding: 12px 16px; }
  .status-bar { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .status-item:nth-child(3)::before { display: none; }
}

@media (max-width: 620px) {
  .header-line { display: none; }
  .gauge-stage { --gauge-size: min(88cqw, 46cqh, 340px); flex-direction: column; }
  .status-bar { grid-template-columns: 1fr; }
  .status-item { justify-content: flex-start; padding-left: 18%; }
  .status-item:not(:first-child)::before { top: 0; left: 10%; width: 80%; height: 0; border-top: 1px solid rgba(101, 138, 169, .28); border-left: 0; }
}
</style>
