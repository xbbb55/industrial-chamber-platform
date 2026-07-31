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
