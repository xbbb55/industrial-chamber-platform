<template>
  <section class="workspace-identity" aria-labelledby="workspace-identity-title">
    <div class="identity-copy">
      <p class="identity-eyebrow">HARDY ENVIRONMENT <span></span> 环境试验智控</p>
      <h2 id="workspace-identity-title">试验设备运行总览</h2>
      <p class="identity-promise">让每一次环境试验，都可追溯。</p>
    </div>

    <dl class="identity-status" aria-label="设备运行概况">
      <div>
        <dt>接入设备</dt>
        <dd>{{ total }}</dd>
      </div>
      <div>
        <dt>在线设备</dt>
        <dd class="online">{{ online }}</dd>
      </div>
      <div>
        <dt>运行中</dt>
        <dd>{{ running }}</dd>
      </div>
      <div>
        <dt>报警设备</dt>
        <dd :class="{ alarm: alarms > 0 }">{{ alarms }}</dd>
      </div>
    </dl>
  </section>
</template>

<script setup>
defineProps({
  total: { type: Number, required: true },
  online: { type: Number, required: true },
  running: { type: Number, required: true },
  alarms: { type: Number, required: true }
});
</script>

<style scoped>
.workspace-identity {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  min-width: 0;
  padding: 2px 4px 4px;
  color: var(--system-ink, #202326);
}

.identity-copy { min-width: 0; }
.identity-eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 5px;
  color: var(--brand-blue, #263a9b);
  font-size: 10px;
  font-weight: 700;
}
.identity-eyebrow span { width: 3px; height: 3px; border-radius: 50%; background: var(--brand-green, #08734a); }
.identity-copy h2 { margin: 0; font-size: 20px; font-weight: 700; line-height: 1.3; }
.identity-promise { margin: 3px 0 0; color: var(--system-ink-soft, #626d74); font-size: 12px; }

.identity-status {
  display: grid;
  grid-template-columns: repeat(4, minmax(64px, auto));
  gap: 20px;
  margin: 0;
}
.identity-status div { display: grid; gap: 3px; min-width: 0; }
.identity-status dt { color: var(--system-ink-muted, #727c83); font-size: 11px; }
.identity-status dd { margin: 0; color: var(--system-ink, #202326); font-size: 17px; font-weight: 700; font-variant-numeric: tabular-nums; }
.identity-status dd.online { color: #36866c; }
.identity-status dd.alarm { color: #b34949; }

@media (max-width: 760px) {
  .workspace-identity { align-items: flex-start; flex-direction: column; gap: 14px; padding-inline: 0; }
  .identity-copy h2 { font-size: 18px; }
  .identity-status { grid-template-columns: repeat(4, minmax(0, 1fr)); width: 100%; gap: 10px; }
}
</style>
