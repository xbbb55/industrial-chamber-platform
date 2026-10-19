import { computed, shallowReactive } from "vue";

const dialogs = shallowReactive([]);
export const hasOpenDialogs = computed(() => dialogs.length > 0);

export function useDialogStack() {
  const id = Symbol("dialog");
  const isTop = computed(() => dialogs.at(-1) === id);
  const layer = computed(() => 40 + Math.max(0, dialogs.indexOf(id)) * 2);

  function register() {
    if (!dialogs.includes(id)) dialogs.push(id);
  }

  function release() {
    const index = dialogs.indexOf(id);
    if (index >= 0) dialogs.splice(index, 1);
  }

  return { isTop, layer, register, release };
}
