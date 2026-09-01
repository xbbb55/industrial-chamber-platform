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
  Lightbulb,
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
  ZoomOut,
  Pause,
  SkipForward,
  Square,
  LogOut,
  KeyRound,
  UsersRound,
  Plus
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
  light: Lightbulb,
  gauge: Gauge,
  history: History,
  reports: FileText,
  reset: RotateCcw,
  expand: ChevronsRight,
  settings: Settings2,
  sliders: SlidersHorizontal,
  shield: ShieldCheck,
  play: Play,
  pause: Pause,
  skip: SkipForward,
  stop: Square,
  chevronDown: ChevronDown,
  chevronRight: ChevronRight,
  chevronUp: ChevronUp,
  temperature: Thermometer,
  tools: Wrench,
  zoomIn: ZoomIn,
  zoomOut: ZoomOut,
  close: X,
  logout: LogOut,
  key: KeyRound,
  users: UsersRound,
  plus: Plus
};

const iconComponent = computed(() => icons[props.name] || Activity);
</script>
