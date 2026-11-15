import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

export function useSelectionIndicator(container, selectedKey, { resizeDebounceMs = 0 } = {}) {
  const style = ref(null);
  let observer;
  let frame;
  let resizeTimer;

  function update() {
    window.cancelAnimationFrame(frame);
    frame = window.requestAnimationFrame(() => {
      const root = container.value;
      const button = root && [...root.querySelectorAll(":scope > button[data-motion-key]")]
        .find(item => item.dataset.motionKey === String(selectedKey.value));
      if (!button || !root.clientWidth) {
        style.value = null;
        return;
      }
      const parent = root.getBoundingClientRect();
      const target = button.getBoundingClientRect();
      style.value = {
        width: `${target.width}px`,
        height: `${target.height}px`,
        transform: `translate(${target.left - parent.left - root.clientLeft + root.scrollLeft}px, ${target.top - parent.top - root.clientTop + root.scrollTop}px)`
      };
    });
  }

  function scheduleResizeUpdate() {
    if (!resizeDebounceMs) {
      update();
      return;
    }
    window.clearTimeout(resizeTimer);
    resizeTimer = window.setTimeout(update, resizeDebounceMs);
  }

  watch([container, selectedKey], async () => {
    await nextTick();
    observer?.disconnect();
    if (container.value) observer?.observe(container.value);
    update();
  }, { flush: "post" });
  onMounted(() => {
    observer = new ResizeObserver(scheduleResizeUpdate);
    if (container.value) observer.observe(container.value);
    window.addEventListener("resize", update);
    update();
  });
  onBeforeUnmount(() => {
    observer?.disconnect();
    window.clearTimeout(resizeTimer);
    window.cancelAnimationFrame(frame);
    window.removeEventListener("resize", update);
  });
  return style;
}
