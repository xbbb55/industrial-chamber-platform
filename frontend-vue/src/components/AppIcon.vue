<template>
  <component :is="iconComponent" :size="size" :stroke-width="strokeWidth" aria-hidden="true" />
</template>

<script setup>
import {
  Activity,
  AlertTriangle,
  Bell,
  Box,
  ChartNoAxesCombined,
  Check,
  ChevronsLeft,
  ChevronsRight,
  Database,
  X,
  Factory,
  FileText,
  Gauge,
  History,
  LayoutDashboard,
  Lightbulb,
  Network,
  RotateCcw,
  RefreshCw,
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
  Plus,
  UserRound,
  Wifi,
  WifiOff
} from "lucide-vue-next";
import { computed } from "vue";

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  strokeWidth: { type: [Number, String], default: 1.8 }
});

const icons = {
  activity: Activity,
  check: Check,
  alarms: AlertTriangle,
  bell: Bell,
  box: Box,
  chart: ChartNoAxesCombined,
  collapse: ChevronsLeft,
  database: Database,
  dashboard: LayoutDashboard,
  factory: Factory,
  humidity: Droplets,
  light: Lightbulb,
  gauge: Gauge,
  history: History,
  network: Network,
  reports: FileText,
  reset: RotateCcw,
  refresh: RefreshCw,
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
  plus: Plus,
  user: UserRound,
  wifi: Wifi,
  wifiOff: WifiOff
};

const iconComponent = computed(() => icons[props.name] || Activity);
</script>
