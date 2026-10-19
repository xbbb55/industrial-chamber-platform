import { onBeforeUnmount, reactive } from "vue";

export function useRefreshTask({ delay = 150, timeout = 10000 } = {}) {
  const state = reactive({ pending: false, visible: false, error: "", updatedAt: null });
  let controller;
  let indicatorTimer;
  let timeoutTimer;
  let revision = 0;

  function clearTimers() {
    window.clearTimeout(indicatorTimer);
    window.clearTimeout(timeoutTimer);
  }

  function cancel() {
    revision += 1;
    controller?.abort();
    clearTimers();
    state.pending = false;
    state.visible = false;
  }

  function dismissError() {
    state.error = "";
  }

  async function run(load, apply) {
    cancel();
    const requestRevision = revision;
    const requestController = new AbortController();
    controller = requestController;
    let timedOut = false;
    state.pending = true;
    state.error = "";
    indicatorTimer = window.setTimeout(() => { state.visible = true; }, delay);
    timeoutTimer = window.setTimeout(() => {
      timedOut = true;
      requestController.abort();
    }, timeout);
    try {
      const value = await load(requestController.signal);
      if (requestRevision !== revision) return;
      if (timedOut) throw new Error("读取超时，请重试");
      apply(value);
      state.updatedAt = Date.now();
    } catch (error) {
      if (requestRevision !== revision) return;
      state.error = timedOut ? "读取超时，请重试" : error.message || "读取失败，请重试";
    } finally {
      if (requestRevision === revision) {
        clearTimers();
        state.pending = false;
        state.visible = false;
      }
    }
  }

  onBeforeUnmount(cancel);
  return { state, run, cancel, dismissError };
}
