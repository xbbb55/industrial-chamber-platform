export function stateLabel(state) {
  const map = {
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
  return map[state] || state;
}

export function runStateLabel(state) {
  return state === "OFFLINE" ? "未知" : stateLabel(state);
}

export function communicationLabel(online) {
  return online ? "在线" : "离线";
}

export function communicationClass(online) {
  return online ? "online" : "offline";
}

export function deviceCommunicationLabel(device) {
  const state = device?.communication_state;
  if (state === "ONLINE") return "在线";
  if (state === "DATA_STALE") return "数据陈旧";
  if (state === "DEVICE_OFFLINE") return "设备离线";
  if (state === "GATEWAY_OFFLINE") return "网关离线";
  return communicationLabel(device?.online);
}

export function deviceCommunicationClass(device) {
  const state = device?.communication_state;
  if (state === "ONLINE") return "online";
  if (state === "DATA_STALE") return "stale";
  if (state === "DEVICE_OFFLINE" || state === "GATEWAY_OFFLINE") return "offline";
  return communicationClass(device?.online);
}

export function communicationHealthLabel(device) {
  const gateway = device?.gateway_online === false ? "网关离线" : "网关在线";
  const quality = device?.data_quality === "FRESH" ? "数据实时"
    : device?.data_quality === "STALE" ? "数据陈旧" : "数据未知";
  return `${gateway} · ${quality}`;
}
