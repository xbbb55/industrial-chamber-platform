<template>
  <component :is="iconComponent" :size="size" :stroke-width="strokeWidth" aria-hidden="true" />
</template>

<script setup>
import {
  Activity,
  AlertTriangle,
  Bell,
  ChartNoAxesCombined,
  ChevronsLeft,
  ChevronsRight,
  X,
  FileText,
  Gauge,
  History,
  LayoutDashboard,
  RotateCcw,
  Settings2,
  SlidersHorizontal,
  ShieldCheck,
  Play,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Thermometer,
  Droplets,
  Wrench,
  ZoomIn,
  ZoomOut
} from "lucide-vue-next";
import { computed } from "vue";

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  strokeWidth: { type: [Number, String], default: 1.8 }
});

const icons = {
  activity: Activity,
  alarms: AlertTriangle,
  bell: Bell,
  chart: ChartNoAxesCombined,
  collapse: ChevronsLeft,
  dashboard: LayoutDashboard,
  humidity: Droplets,
  gauge: Gauge,
  history: History,
  reports: FileText,
  reset: RotateCcw,
  expand: ChevronsRight,
  settings: Settings2,
  sliders: SlidersHorizontal,
  shield: ShieldCheck,
  play: Play,
  chevronDown: ChevronDown,
  chevronRight: ChevronRight,
  chevronUp: ChevronUp,
  temperature: Thermometer,
  tools: Wrench,
  zoomIn: ZoomIn,
  zoomOut: ZoomOut,
  close: X
};

const iconComponent = computed(() => icons[props.name] || Activity);
</script>
