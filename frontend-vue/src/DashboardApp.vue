<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">
    <aside class="sidebar" :inert="hasOpenDialogs">
      <div class="brand">
        <div class="brand-mark" aria-hidden="true">
          <AppIcon name="factory" :size="22" :stroke-width="1.75" />
        </div>
        <div class="brand-copy">
          <h1>哈丁环境试验箱数据平台</h1>
        </div>
      </div>

      <nav ref="sidebarNav" class="nav-list motion-nav" :class="{ 'motion-ready': sidebarIndicator }" aria-label="主导航">
        <span v-if="sidebarIndicator" class="motion-selection" :style="sidebarIndicator" aria-hidden="true"></span>
        <button
          v-for="item in sidebarItems"
          :key="item.key"
          :data-motion-key="item.key"
          :class="{ active: activeSidebarKey === item.key }"
          :aria-current="activeSidebarKey === item.key ? 'page' : undefined"
          type="button"
          @click="handleSidebarSelect(item)"
        >
          <span class="nav-icon"><AppIcon :name="iconFor(item.key)" :size="18" /></span>
          <span class="nav-label">{{ item.label }}</span>
        </button>
      </nav>

      <div class="sidebar-foot">
        <div v-if="activeView === 'device-detail'" class="sidebar-device-actions">
          <button
            class="sidebar-return-button"
            type="button"
            title="返回设备列表"
            aria-label="返回设备列表"
            @click="returnToDashboard"
          >
            <AppIcon name="dashboard" :size="18" />
            <span>返回设备列表</span>
          </button>
          <button
            class="sidebar-collapse-button"
            type="button"
            :title="isSidebarCollapsed ? '展开侧边栏' : '收缩侧边栏'"
            :aria-label="isSidebarCollapsed ? '展开侧边栏' : '收缩侧边栏'"
            @click="isSidebarCollapsed = !isSidebarCollapsed"
          >
            <AppIcon :name="isSidebarCollapsed ? 'expand' : 'collapse'" :size="18" />
            <span>{{ isSidebarCollapsed ? "展开" : "收缩" }}</span>
          </button>
        </div>
        <template v-else>
          <p>总控服务</p>
          <strong>{{ connectionText }}</strong>
        </template>
      </div>
    </aside>

    <section class="main-shell" :inert="hasOpenDialogs">
      <header class="topbar">
        <div class="top-title">
          <Transition name="settings-tab" mode="out-in">
          <div v-if="activeView === 'device-detail'" key="device" class="device-title-copy">
              <div class="device-heading">
                <AppIcon class="device-heading-icon" name="box" :size="20" :stroke-width="1.7" />
                <h2>{{ selectedDevice?.name || selectedDeviceId }}</h2>
              </div>
              <div class="device-title-meta">
                <span class="device-meta-item device-meta-ip" title="设备 IP 地址">
                  <AppIcon name="network" :size="14" :stroke-width="1.8" />
                  <span class="device-meta-label">IP</span>
                  <strong>{{ selectedDevice?.device_ip || selectedDevice?.ip_address || selectedDevice?.ip || "未配置" }}</strong>
                </span>
                <span
                  v-if="selectedDevice"
                  :class="['device-meta-item', 'device-status-item', communicationClass(selectedDevice.online)]"
                  title="设备连接状态"
                >
                  <AppIcon :name="selectedDevice.online ? 'wifi' : 'wifiOff'" :size="14" :stroke-width="1.9" />
                  <span class="device-meta-label">连接</span>
                  <strong>{{ communicationLabel(selectedDevice.online) }}</strong>
                </span>
                <span
                  v-if="selectedDevice"
                  :class="['device-meta-item', 'device-status-item', stateClass(selectedDevice)]"
                  title="设备运行状态"
                >
                  <AppIcon :name="runStateIcon(selectedDevice.run_state)" :size="14" :stroke-width="1.9" />
                  <span class="device-meta-label">运行</span>
                  <strong>{{ runStateLabel(selectedDevice.run_state) }}</strong>
                </span>
                <span v-if="isPilotWorkspace" class="workspace-refresh-status" :class="{ 'has-error': pilotRefresh.state.error }">
                  <AppIcon
                    :class="{ 'status-icon-spin': pilotRefresh.state.pending }"
                    :name="pilotRefresh.state.error ? 'alarms' : pilotRefresh.state.pending ? 'refresh' : 'database'"
                    :size="14"
                    :stroke-width="1.8"
                  />
                  <span>{{ pilotStatusText }}</span>
                </span>
              </div>
          </div>
          <h2 v-else :key="activeView">{{ currentTitle }}</h2>
          </Transition>
        </div>
        <div class="top-actions">
          <button
            class="light-toggle"
            :class="{ active: isLightOn }"
            type="button"
            :title="isLightOn ? '关灯' : '开灯'"
            :aria-label="isLightOn ? '关灯' : '开灯'"
            :aria-pressed="isLightOn"
            :disabled="!selectedDevice || isLightCommandPending"
            @click="toggleSelectedDeviceLight"
          >
            <AppIcon name="light" :size="18" />
          </button>
          <button class="notify" type="button" :title="notificationTitle" :aria-label="notificationTitle" @click="isNotificationOpen = true">
            <AppIcon name="bell" :size="18" />
            <span v-if="notificationCount > 0">{{ notificationCountText }}</span>
          </button>
          <button class="user-card" type="button" aria-label="打开个人中心" @click="openProfile">
            <div>
              <strong>{{ sessionUser.display_name }}</strong>
              <span>{{ sessionUser.role_label }}</span>
            </div>
            <div class="avatar" aria-hidden="true">
              <AppIcon name="user" :size="18" :stroke-width="1.8" />
            </div>
          </button>
        </div>
      </header>

      <main ref="workspaceContent" class="content">
        <Transition name="workspace" mode="out-in" @before-leave="prepareWorkspaceLeave" @after-enter="finishWorkspaceEnter">
        <section v-if="activeView === 'dashboard'" key="dashboard" class="page-stack">
          <section class="panel overview-panel">
            <div class="panel-title">
              <h3>试验箱实时列表</h3>
              <div class="panel-actions">
                <span class="live-pill"><i></i>实时数据流</span>
                <div ref="displayModeNav" class="view-toggle motion-nav" :class="{ 'motion-ready': displayModeIndicator }" aria-label="切换设备展示形式">
                  <span v-if="displayModeIndicator" class="motion-selection" :style="displayModeIndicator" aria-hidden="true"></span>
                  <button
                    type="button"
                    data-motion-key="list"
                    :class="{ active: deviceDisplayMode === 'list' }"
                    @click="deviceDisplayMode = 'list'"
                  >
                    列表
                  </button>
                  <button
                    type="button"
                    data-motion-key="card"
                    :class="{ active: deviceDisplayMode === 'card' }"
                    @click="deviceDisplayMode = 'card'"
                  >
                    卡片
                  </button>
                </div>
              </div>
            </div>
            <Transition name="settings-tab" mode="out-in" @before-leave="prepareWorkspaceLeave">
            <DeviceOverviewList
              v-if="deviceDisplayMode === 'list'"
              key="list"
              :devices="devices"
              @select="openDeviceDetail"
            />
            <div v-else key="card" class="machine-detail-grid device-card-list">
              <LiveDeviceDetailCard
                v-for="device in devices"
                :key="device.device_id"
                :device="device"
                @select="openDeviceDetail"
              />
            </div>
            </Transition>
          </section>
        </section>

        <ProfileCenter
          v-else-if="activeView === 'profile'"
          key="profile"
          :user="sessionUser"
          :current-time="currentTimeText"
          :refresh-target="workspaceContent"
          @back="returnToMonitoring"
          @logout="logoutToLogin"
          @user-updated="updateSessionUser"
        />

        <section v-else-if="activeView === 'device-detail'" key="device-detail" class="page-stack device-workspace">
          <Transition name="workspace" mode="out-in" @before-leave="prepareWorkspaceLeave" @after-enter="finishWorkspaceEnter">
          <section
            v-if="selectedDevice && selectedDeviceSection === 'monitor'"
            key="monitor"
            class="monitor-layout"
            :aria-busy="monitorRefresh.state.pending"
            :class="{
              'wallboard-mode': visibleMonitorCards.length === 0,
              'dut-only-mode': visibleMonitorCards.length === 1 && visibleMonitorCards[0] === 'dut-temperatures',
              'event-only-mode': visibleMonitorCards.length === 1 && visibleMonitorCards[0] === 'user-events'
            }"
          >
            <section v-if="visibleMonitorCards.length > 0" class="panel realtime-overview-panel">
              <div class="realtime-tile temperature">
                <div class="current-reading">
                  <span>当前温度</span>
                  <div class="reading-value-row">
                    <AppIcon class="realtime-icon" name="temperature" :size="48" :stroke-width="1.45" />
                    <strong>{{ formatNumber(selectedDevice.current_temperature) }}<small>°C</small></strong>
                  </div>
                </div>
                <div class="target-value">
                  <span>目标温度</span>
                  <b>{{ selectedDevice.target_temperature }}°C</b>
                </div>
              </div>

              <div class="realtime-tile humidity">
                <div class="current-reading">
                  <span>当前湿度</span>
                  <div class="reading-value-row">
                    <AppIcon class="realtime-icon" name="humidity" :size="48" :stroke-width="1.45" />
                    <strong>{{ formatNumber(selectedDevice.current_humidity) }}<small>%</small></strong>
                  </div>
                </div>
                <div class="target-value">
                  <span>目标湿度</span>
                  <b>{{ selectedDevice.target_humidity }}%</b>
                </div>
              </div>
            </section>

            <section class="panel command-panel">
              <div class="command-main-row">
                <div class="command-actions">
                  <button
                    class="start-command-button"
                    type="button"
                    :disabled="!selectedDevice"
                    @click="startSelectedDevice"
                  >
                    <AppIcon name="play" :size="15" :stroke-width="2.1" />
                    <span>{{ startingDeviceIds[selectedDeviceId] ? "启动下发中" : isDeviceRunning ? "已启动" : "启动运行" }}</span>
                  </button>
                  <button
                    class="hold-command-button"
                    type="button"
                    :disabled="!selectedDevice"
                    @click="holdSelectedDevice"
                  >
                    <AppIcon :name="heldDeviceIds[selectedDeviceId] ? 'play' : 'pause'" :size="15" :stroke-width="2.1" />
                    <span>{{ holdingDeviceIds[selectedDeviceId] ? `${heldDeviceIds[selectedDeviceId] ? "继续" : "保持"}下发中` : heldDeviceIds[selectedDeviceId] ? "继续" : "保持" }}</span>
                  </button>
                  <button
                    class="skip-command-button"
                    type="button"
                    :disabled="!selectedDevice"
                    @click="skipSelectedDeviceStep"
                  >
                    <AppIcon name="skip" :size="15" :stroke-width="2.1" />
                    <span>{{ skippingDeviceIds[selectedDeviceId] ? "跳步下发中" : "跳步" }}</span>
                  </button>
                  <button
                    class="danger-command-button"
                    type="button"
                    :disabled="!selectedDevice"
                    @click="stopSelectedDevice"
                  >
                    <AppIcon name="stop" :size="15" :stroke-width="2.1" />
                    <span>{{ stoppingDeviceIds[selectedDeviceId] ? "停止下发中" : isDeviceStopped ? "已停止" : "停止运行" }}</span>
                  </button>
                </div>
                <button
                  class="layout-config-button command-layout-button"
                  type="button"
                  :class="{ active: isLayoutEditorOpen }"
                  title="更多部件"
                  aria-label="更多部件"
                  @click="isLayoutEditorOpen = true"
                >
                  <AppIcon name="sliders" :size="16" />
                  <span>更多部件</span>
                </button>
              </div>
            </section>

            <section class="panel runtime-panel">
              <div class="runtime-tags">
                <div class="runtime-tag">
                  <span>运行时间:</span>
                  <strong>{{ runtimeDisplay.running }}</strong>
                </div>
                <i aria-hidden="true"></i>
                <div class="runtime-tag">
                  <span>设定时间:</span>
                  <strong>{{ runtimeDisplay.setting }}</strong>
                </div>
                <i aria-hidden="true"></i>
                <div class="runtime-tag">
                  <span>总运行时间:</span>
                  <strong>{{ runtimeDisplay.total }}</strong>
                </div>
              </div>
            </section>

            <section class="panel custom-layout-panel">
              <HmiDashboard
                v-if="visibleMonitorCards.length === 0"
                :temperature="Number(selectedDevice.current_temperature ?? 0)"
                :humidity="Number(selectedDevice.current_humidity ?? 0)"
                :device-status="runStateLabel(selectedDevice.run_state)"
                :running-mode="selectedDeviceRunningMode"
                :communication-status="communicationLabel(selectedDevice.online)"
                :start-time="selectedDeviceStartTime"
              />
              <div v-else class="custom-monitor-grid" :class="{ 'single-card': visibleMonitorCards.length === 1 }">
                <section v-if="visibleMonitorCards.includes('trend')" class="monitor-card trend-panel monitor-card-wide">
                  <div class="trend-header">
                    <div class="trend-title-block">
                      <h3>实时温湿度曲线</h3>
                      <span>过去 5 分钟 / 未来 5 分钟</span>
                    </div>
                    <div class="chart-legend" aria-label="曲线图例">
                      <span><i class="temp-line"></i>温度</span>
                      <span><i class="hum-line"></i>湿度</span>
                      <span class="now-label">当前时刻</span>
                    </div>
                    <div class="trend-toolbar" aria-label="曲线缩放控制">
                      <span>{{ trendWindowText }}</span>
                      <span class="trend-toolbar-label">时间轴</span>
                      <button type="button" title="放大曲线" aria-label="放大曲线" @click="zoomTrend(0.72)"><AppIcon name="zoomIn" :size="16" /></button>
                      <button type="button" title="缩小曲线" aria-label="缩小曲线" @click="zoomTrend(1.38)"><AppIcon name="zoomOut" :size="16" /></button>
                      <button type="button" title="复位时间窗口" aria-label="复位时间窗口" @click="resetTrendZoom"><AppIcon name="reset" :size="16" /></button>
                      <span class="trend-toolbar-label">纵轴</span>
                      <button type="button" title="放大纵轴" aria-label="放大纵轴" @click="zoomTrendY(0.78)"><AppIcon name="zoomIn" :size="16" /></button>
                      <button type="button" title="缩小纵轴" aria-label="缩小纵轴" @click="zoomTrendY(1.28)"><AppIcon name="zoomOut" :size="16" /></button>
                      <button type="button" title="复位纵轴" aria-label="复位纵轴" @click="resetTrendY"><AppIcon name="reset" :size="16" /></button>
                    </div>
                  </div>
                  <canvas ref="selectedTrendCanvas" width="1080" height="220" @mousedown="handleTrendPointerDown" @mousemove="handleTrendPointerMove" @mouseup="handleTrendPointerUp" @mouseleave="handleTrendPointerUp" @dblclick="resetTrendZoom"></canvas>
                  <div class="trend-time-axis" aria-label="曲线时间刻度"><span v-for="label in trendAxisLabels" :key="label">{{ label }}</span></div>
                  <div class="trend-hint">左右拖拽平移时间轴，使用按钮缩放或复位</div>
                </section>

                <section v-if="false && visibleMonitorCards.includes('status')" class="monitor-card info-monitor-card">
                  <div class="monitor-card-title"><AppIcon name="activity" :size="17" /><h3>运行状态</h3></div>
                  <strong class="monitor-status-value" :class="stateClass(selectedDevice)">{{ runStateLabel(selectedDevice.run_state) }}</strong>
                  <span>当前设备运行状态</span>
                </section>
                <section v-if="false && visibleMonitorCards.includes('communication')" class="monitor-card info-monitor-card">
                  <div class="monitor-card-title"><AppIcon name="chart" :size="17" /><h3>通讯信息</h3></div>
                  <div class="monitor-data-row"><span>设备 IP</span><strong>{{ selectedDevice.device_ip || selectedDevice.ip_address || selectedDevice.ip || "--" }}</strong></div>
                  <div class="monitor-data-row"><span>连接状态</span><strong>{{ selectedDevice.online ? "在线" : "离线" }}</strong></div>
                </section>
                <section v-if="false && visibleMonitorCards.includes('updated')" class="monitor-card info-monitor-card">
                  <div class="monitor-card-title"><AppIcon name="history" :size="17" /><h3>数据更新时间</h3></div>
                  <strong class="monitor-number-value">{{ formatSnapshotTime(selectedDevice.updated_at || snapshot?.written_at) }}</strong>
                  <span>最近一次总服务端接收时间</span>
                </section>
                <section v-if="visibleMonitorCards.includes('dut-temperatures')" class="monitor-card monitor-card-wide dut-temperature-panel">
                  <div class="trend-header dut-temperature-header">
                    <div class="trend-title-block">
                      <h3>试品温度</h3>
                    </div>
                    <span class="dut-selected-caption">当前选中：{{ selectedDutLabel }}</span>
                  </div>
                  <div class="dut-temperature-grid">
                    <div
                      v-for="card in dutMonitorCards"
                      :key="card.key"
                      class="dut-temperature-item"
                      :class="{ 'dut-selected-card': isDutSelected(card.number) }"
                    >
                      <span>试品温度{{ card.number }}</span>
                      <strong>{{ formatNumber(dutValue(card.number)) }}<small>°C</small></strong>
                    </div>
                  </div>
                </section>
                <section v-if="visibleMonitorCards.includes('user-events')" class="monitor-card monitor-card-wide event-panel">
                  <div class="trend-header event-panel-header">
                    <div class="trend-title-block">
                      <h3>用户事件</h3>
                    </div>
                    <span class="event-count-caption">16 个事件通道</span>
                  </div>
                  <div class="event-grid">
                    <div v-for="event in eventMonitorCards" :key="event.key" class="event-item" :class="{ 'event-active': eventState(event.number) === 'ON' }">
                      <div class="event-item-head"><span>用户事件{{ event.number }}</span><i></i></div>
                      <strong>{{ eventText(event.number) }}</strong>
                    </div>
                  </div>
                </section>
              </div>
            </section>

          </section>

          <section v-else-if="selectedDevice && selectedDeviceSection === 'operation'" key="operation" class="operation-settings">
            <div class="operation-layout">
              <nav ref="operationNav" class="operation-nav panel motion-nav" :class="{ 'motion-ready': operationIndicator }" aria-label="操作设定分类">
                <span v-if="operationIndicator" class="motion-selection" :style="operationIndicator" aria-hidden="true"></span>
                <button v-for="item in operationTabs" :key="item.key" :data-motion-key="item.key" type="button" :class="{ active: operationTab === item.key }" :aria-current="operationTab === item.key ? 'page' : undefined" @click="operationTab = item.key">
                  <AppIcon :name="item.icon" :size="17" />
                  <span><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span>
                  <AppIcon name="chevronRight" :size="14" />
                </button>
              </nav>

              <section class="operation-editor" :aria-busy="operationRefresh.state.pending || operationSaving">
                <Transition name="settings-tab" mode="out-in" @before-leave="prepareTabLeave" @after-enter="finishTabEnter">
                <div :key="operationTab" class="operation-tab-content" :class="{ 'is-refreshing': operationRefresh.state.visible || operationRefresh.state.error }" :inert="operationRefresh.state.pending || !!operationRefresh.state.error || operationSaving">
                <div v-if="operationTab === 'protection'" class="protection-settings-grid">
                  <section v-for="item in protectionItems" :key="item.key" class="protection-card protection-card-enabled">
                    <header>
                      <span>{{ item.label }}</span>
                    </header>
                    <div class="protection-fields">
                      <label><span>上限值</span><span class="hmi-number-control"><input v-model="operationForm[item.upper]" type="number" min="-32768" max="32768" step="0.1" :aria-label="`${item.label}上限值`" @blur="clampOperationNumber(item.upper, -32768, 32768)"><span class="hmi-number-steps"><button type="button" :title="`调高${item.label}上限值`" :aria-label="`调高${item.label}上限值`" @click.stop.prevent="stepOperationNumber(item.upper, 0.1, -32768, 32768)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" :title="`调低${item.label}上限值`" :aria-label="`调低${item.label}上限值`" @click.stop.prevent="stepOperationNumber(item.upper, -0.1, -32768, 32768)"><AppIcon name="chevronDown" :size="12" /></button></span></span></label>
                      <label><span>下限值</span><span class="hmi-number-control"><input v-model="operationForm[item.lower]" type="number" min="-32768" max="32768" step="0.1" :aria-label="`${item.label}下限值`" @blur="clampOperationNumber(item.lower, -32768, 32768)"><span class="hmi-number-steps"><button type="button" :title="`调高${item.label}下限值`" :aria-label="`调高${item.label}下限值`" @click.stop.prevent="stepOperationNumber(item.lower, 0.1, -32768, 32768)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" :title="`调低${item.label}下限值`" :aria-label="`调低${item.label}下限值`" @click.stop.prevent="stepOperationNumber(item.lower, -0.1, -32768, 32768)"><AppIcon name="chevronDown" :size="12" /></button></span></span></label>
                    </div>
                  </section>
                </div>

                <div v-else-if="operationTab === 'setpoint'" class="setpoint-module-grid">
                  <section class="setpoint-module-card setpoint-temperature-card">
                    <header><span><AppIcon name="temperature" :size="16" />温度</span></header>
                    <div class="setpoint-module-fields">
                      <label class="setpoint-inline-field"><span>目标值</span><div><span class="hmi-number-control"><input v-model="operationForm.targetTemp" type="number" step="0.1"><span class="hmi-number-steps"><button type="button" title="调高温度目标值" aria-label="调高温度目标值" @click.stop.prevent="stepOperationNumber('targetTemp', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="调低温度目标值" aria-label="调低温度目标值" @click.stop.prevent="stepOperationNumber('targetTemp', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>°C</b></div></label>
                      <label class="setpoint-inline-field"><span>斜率值</span><div><span class="hmi-number-control"><input v-model="operationForm.tempRamp" type="number" step="0.1"><span class="hmi-number-steps"><button type="button" title="调高温度斜率值" aria-label="调高温度斜率值" @click.stop.prevent="stepOperationNumber('tempRamp', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="调低温度斜率值" aria-label="调低温度斜率值" @click.stop.prevent="stepOperationNumber('tempRamp', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>°C/min</b></div></label>
                    </div>
                  </section>
                  <section class="setpoint-module-card setpoint-humidity-card">
                    <header><span><AppIcon name="humidity" :size="16" />湿度</span></header>
                    <div class="setpoint-module-fields">
                      <label class="setpoint-inline-field"><span>目标值</span><div><span class="hmi-number-control"><input v-model="operationForm.targetHum" type="number" step="0.1"><span class="hmi-number-steps"><button type="button" title="调高湿度目标值" aria-label="调高湿度目标值" @click.stop.prevent="stepOperationNumber('targetHum', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="调低湿度目标值" aria-label="调低湿度目标值" @click.stop.prevent="stepOperationNumber('targetHum', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>%RH</b></div></label>
                      <label class="setpoint-inline-field"><span>斜率值</span><div><span class="hmi-number-control"><input v-model="operationForm.humRamp" type="number" step="0.1"><span class="hmi-number-steps"><button type="button" title="调高湿度斜率值" aria-label="调高湿度斜率值" @click.stop.prevent="stepOperationNumber('humRamp', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="调低湿度斜率值" aria-label="调低湿度斜率值" @click.stop.prevent="stepOperationNumber('humRamp', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>%/min</b></div></label>
                    </div>
                  </section>
                  <section class="setpoint-module-card setpoint-runtime-card">
                    <header><span><AppIcon name="history" :size="16" />运行时间</span></header>
                    <div class="runtime-time-control" aria-label="运行时间，格式为小时分钟秒">
                      <label class="runtime-time-field"><span>小时</span><div><span class="hmi-number-control"><input v-model="operationForm.runtimeHours" type="number" min="0" step="1" aria-label="运行时间小时" @blur="clampOperationNumber('runtimeHours', 0, 999)"><span class="hmi-number-steps"><button type="button" title="增加小时" aria-label="增加小时" @click.stop.prevent="stepOperationNumber('runtimeHours', 1, 0, 999)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少小时" aria-label="减少小时" @click.stop.prevent="stepOperationNumber('runtimeHours', -1, 0, 999)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>H</b></div></label>
                      <label class="runtime-time-field"><span>分钟</span><div><span class="hmi-number-control"><input v-model="operationForm.runtimeMinutes" type="number" min="0" max="59" step="1" aria-label="运行时间分钟" @blur="clampOperationNumber('runtimeMinutes', 0, 59)"><span class="hmi-number-steps"><button type="button" title="增加分钟" aria-label="增加分钟" @click.stop.prevent="stepOperationNumber('runtimeMinutes', 1, 0, 59)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少分钟" aria-label="减少分钟" @click.stop.prevent="stepOperationNumber('runtimeMinutes', -1, 0, 59)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>M</b></div></label>
                      <label class="runtime-time-field"><span>秒</span><div><span class="hmi-number-control"><input v-model="operationForm.runtimeSeconds" type="number" min="0" max="59" step="1" aria-label="运行时间秒" @blur="clampOperationNumber('runtimeSeconds', 0, 59)"><span class="hmi-number-steps"><button type="button" title="增加秒" aria-label="增加秒" @click.stop.prevent="stepOperationNumber('runtimeSeconds', 1, 0, 59)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少秒" aria-label="减少秒" @click.stop.prevent="stepOperationNumber('runtimeSeconds', -1, 0, 59)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>S</b></div></label>
                    </div>
                  </section>
                </div>

                <div v-else-if="operationTab === 'program'" class="program-settings">
                  <div class="program-toolbar"><div><span class="setting-section-title inline"><span>程序模式</span><small>从数据库读取并维护试验程序</small></span></div><button class="secondary-action" type="button" @click="openProgramEditor()">＋ 新建程序</button></div>
                  <div v-if="programs.length" class="program-workspace">
                    <div class="program-list">
                      <div class="program-list-header"><span>程序名</span><span>总运行时间</span><span>预览</span><span>维护</span><span>状态</span></div>
                      <article v-for="program in programs" :key="program.pro_no" class="program-card" :class="{ active: operationForm.programId === String(program.pro_no) }">
                        <button class="program-card-select" type="button" @click="selectProgram(program.pro_no)"><strong>{{ program.name }}</strong></button>
                        <span class="program-card-duration">{{ program.display_total_time == null ? '--' : formatDuration(program.display_total_time) }}</span>
                        <button class="program-preview-button" type="button" @click="openProgramPreview(program.pro_no)">预览</button>
                        <div class="program-card-actions"><button type="button" title="编辑程序" @click="openProgramEditor(program.pro_no)">编辑</button><button type="button" title="删除程序" @click="deleteProgram(program.pro_no)">删除</button></div>
                        <span class="program-card-selection" :class="{ selected: operationForm.programId === String(program.pro_no) }">{{ operationForm.programId === String(program.pro_no) ? '已选中' : '未选中' }}</span>
                      </article>
                    </div>
                  </div>
                  <section v-else class="program-empty-state"><strong>暂无程序组</strong><span>数据库中还没有程序，点击“新建程序”开始配置。</span><button class="primary-action" type="button" @click="openProgramEditor()">新建程序</button></section>
                </div>

                <section v-else class="other-settings-section">
                  <div class="other-settings-grid">
                  <section class="other-settings-card">
                    <header>断电后启动方式</header>
                    <div class="other-radio-list">
                      <label><input v-model="operationForm.powerOnMode" type="radio" value="stop"><span>停机</span></label>
                      <label><input v-model="operationForm.powerOnMode" type="radio" value="cold"><span>冷启动</span></label>
                      <label><input v-model="operationForm.powerOnMode" type="radio" value="warm"><span>热启动</span></label>
                    </div>
                  </section>

                  <section class="other-settings-card">
                    <header>停机后启动方式</header>
                    <div class="other-radio-list">
                      <label><input v-model="operationForm.stopResumeMode" type="radio" value="reset"><span>清零复位启动</span></label>
                      <label><input v-model="operationForm.stopResumeMode" type="radio" value="continue"><span>继续启动</span></label>
                    </div>
                  </section>

                  <section class="other-settings-card">
                    <header>温度控制方式</header>
                    <div class="other-radio-list other-temperature-options">
                      <label><input v-model="operationForm.temperatureControlMode" type="radio" value="air"><span>空气控温</span></label>
                      <label><input v-model="operationForm.temperatureControlMode" type="radio" value="dut"><span>试品控温</span><select v-model="operationForm.dutTemperatureSource" :disabled="operationForm.temperatureControlMode !== 'dut'" aria-label="试品温度来源"><option v-for="index in 8" :key="index" :value="`dut${index}`">试品温度{{ index }}</option></select></label>
                    </div>
                  </section>

                  <section class="other-settings-card">
                    <header>运行等待设定</header>
                    <div class="other-value-list">
                      <label><span>温度等待区域</span><input v-model.number="operationForm.waitTemperatureUpper" type="number" step="0.1" aria-label="温度等待区域上限"></label>
                      <label><span>湿度等待区域</span><input v-model.number="operationForm.waitHumidityUpper" type="number" step="0.1" aria-label="湿度等待区域上限"></label>
                    </div>
                  </section>

                  <section class="other-settings-card">
                    <header>事件</header>
                    <div class="other-value-list single-value">
                      <label><span>事件</span><input :value="operationForm.eventCode" type="text" maxlength="16" readonly aria-label="事件代码，点击选择事件" title="点击选择事件" @click="openEventDialog" @keydown.enter.prevent="openEventDialog" @keydown.space.prevent="openEventDialog"></label>
                    </div>
                  </section>

                  <section class="other-settings-card">
                    <header>数据保存时间</header>
                    <div class="other-value-list single-value">
                      <label><span>温湿度历史数据</span><select v-model.number="operationForm.historyRetentionDays" aria-label="温湿度历史数据保存时间"><option :value="30">30天</option><option :value="60">60天</option><option :value="90">90天</option><option :value="200">200天</option><option :value="300">300天</option></select></label>
                    </div>
                  </section>

                  <section class="other-settings-card">
                    <header>预约启动设定</header>
                    <div class="schedule-list">
                      <label class="schedule-row"><input v-model="operationForm.scheduledStartEnabled" type="checkbox"><span>启动</span><input v-model="operationForm.scheduledStartDate" type="date" aria-label="预约启动日期"><input v-model="operationForm.scheduledStartTime" type="time" aria-label="预约启动时间"></label>
                      <label class="schedule-row"><input v-model="operationForm.scheduledStopEnabled" type="checkbox"><span>停机</span><input v-model="operationForm.scheduledStopDate" type="date" aria-label="预约停机日期"><input v-model="operationForm.scheduledStopTime" type="time" aria-label="预约停机时间"></label>
                    </div>
                  </section>
                  </div>
                  <div class="operation-editor-footer other-settings-footer"><span class="operation-save-meta"><span>最后保存：{{ operationLastSaved }}</span><span v-if="operationFeedback" class="operation-feedback" role="status">{{ operationFeedback }}</span></span><button class="primary-action" type="button" @click="openSaveConfirm('other')">保存设定</button></div>
                </section>

                <div v-if="operationTab !== 'other'" class="operation-editor-footer"><span class="operation-save-meta"><span>最后保存：{{ operationLastSaved }}</span><span v-if="operationFeedback" class="operation-feedback" role="status">{{ operationFeedback }}</span></span><div v-if="operationTab !== 'program'"><button class="ghost-action" type="button" @click="resetOperationForm">恢复默认</button><button class="primary-action" type="button" @click="openSaveConfirm('operation')">保存设定</button></div></div>
                </div>
                </Transition>
              </section>
            </div>
          </section>

          <section v-else-if="selectedDevice && selectedDeviceSection === 'parameters'" key="parameters" class="system-parameters">
            <nav ref="parameterNav" class="operation-nav panel system-parameter-nav motion-nav" :class="{ 'motion-ready': parameterIndicator }" aria-label="系统参数分类">
              <span v-if="parameterIndicator" class="motion-selection" :style="parameterIndicator" aria-hidden="true"></span>
              <button v-for="item in parameterTabs" :key="item.key" :data-motion-key="item.key" type="button" :class="{ active: parameterTab === item.key }" :aria-current="parameterTab === item.key ? 'page' : undefined" @click="parameterTab = item.key">
                <AppIcon :name="item.icon" :size="17" />
                <span><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span>
                <AppIcon name="chevronRight" :size="14" />
              </button>
            </nav>
            <Transition name="settings-tab" mode="out-in" @before-leave="prepareTabLeave" @after-enter="finishTabEnter">
            <div :key="parameterTab" class="parameter-tab-content" :aria-busy="parameterRefresh.state.pending || parameterSaving" :inert="parameterRefresh.state.pending || !!parameterRefresh.state.error || parameterSaving">
            <div class="system-parameters-grid" :class="{ 'basic-parameter-grid': parameterTab === 'basic', 'calibration-parameter-grid': parameterTab === 'calibration' }">
              <section v-if="parameterTab === 'basic'" class="system-parameter-card product-info-card">
                <header><span>产品信息</span></header>
                <div class="parameter-fields">
                  <label><span>产品编号</span><input :value="selectedDevice.device_id" type="text" disabled></label>
                  <label><span>产品型号</span><input v-model="parameterForm.model" type="text"></label>
                  <label><span>配置 IP</span><input :value="selectedDevice.device_ip || selectedDevice.ip_address || selectedDevice.ip || '--'" type="text" disabled></label>
                </div>
              </section>

              <template v-if="parameterTab === 'calibration'">
                <section v-for="card in calibrationCards" :key="card.key" class="system-parameter-card calibration-card measurement-calibration-card">
                  <header><span>{{ card.title }}</span></header>
                  <div class="calibration-card-content">
                    <div class="calibration-readings" :aria-label="`当前${card.title}测量值`">
                      <div v-for="reading in calibrationReadings(card)" :key="reading.label" class="calibration-reading">
                        <span>{{ reading.label }}</span>
                        <output>{{ formatCalibrationValue(reading.value) }}<small>{{ card.unit }}</small></output>
                      </div>
                    </div>

                    <div class="calibration-matrix" role="group" :aria-label="`${card.title}校正参数`">
                      <div class="calibration-matrix-head" aria-hidden="true">
                        <span></span><span>区间</span><span>修正值</span><span>定校</span>
                      </div>
                      <div v-for="row in card.rows" :key="row.area.key" class="calibration-matrix-row">
                        <strong>{{ row.number }}</strong>
                        <label :title="row.area.key">
                          <span class="hmi-number-control"><input v-model.number="parameterForm[row.area.key]" type="number" step="any" :aria-label="`${row.number}号${card.title}区间（${row.area.key}）`"><span class="hmi-number-steps"><button type="button" :title="`增加${row.number}号${card.title}区间`" :aria-label="`增加${row.number}号${card.title}区间`" @click.stop.prevent="stepParameterNumber(row.area.key, 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" :title="`减少${row.number}号${card.title}区间`" :aria-label="`减少${row.number}号${card.title}区间`" @click.stop.prevent="stepParameterNumber(row.area.key, -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span>
                        </label>
                        <label :title="row.corrected.key">
                          <span class="hmi-number-control"><input v-model.number="parameterForm[row.corrected.key]" type="number" step="any" :aria-label="`${row.number}号${card.title}修正值（${row.corrected.key}）`"><span class="hmi-number-steps"><button type="button" :title="`增加${row.number}号${card.title}修正值`" :aria-label="`增加${row.number}号${card.title}修正值`" @click.stop.prevent="stepParameterNumber(row.corrected.key, 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" :title="`减少${row.number}号${card.title}修正值`" :aria-label="`减少${row.number}号${card.title}修正值`" @click.stop.prevent="stepParameterNumber(row.corrected.key, -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span>
                        </label>
                        <label v-if="row.number === 1" :title="card.correction.key">
                          <span class="hmi-number-control"><input v-model.number="parameterForm[card.correction.key]" type="number" step="any" :aria-label="`${card.title}定校（${card.correction.key}）`"><span class="hmi-number-steps"><button type="button" :title="`增加${card.title}定校`" :aria-label="`增加${card.title}定校`" @click.stop.prevent="stepParameterNumber(card.correction.key, 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" :title="`减少${card.title}定校`" :aria-label="`减少${card.title}定校`" @click.stop.prevent="stepParameterNumber(card.correction.key, -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span>
                        </label>
                        <span v-else aria-hidden="true"></span>
                      </div>
                    </div>
                  </div>
                </section>
              </template>

              <section v-if="parameterTab === 'calibration'" class="system-parameter-card calibration-card dut-calibration-card">
                <header><span>试品温度</span></header>
                <div class="dut-calibration-content" role="table" aria-label="试品温度测量值">
                  <div v-for="(group, groupIndex) in dutCalibrationGroups" :key="groupIndex" class="dut-calibration-group" role="rowgroup">
                    <div class="dut-calibration-head" role="row">
                      <span role="columnheader"></span>
                      <span role="columnheader">采集值</span>
                      <span role="columnheader">修正值</span>
                      <span role="columnheader">最终值</span>
                    </div>
                    <div v-for="channel in group" :key="channel" class="dut-calibration-row" role="row">
                      <strong role="rowheader">试品温度{{ channel }}</strong>
                      <output role="cell" :aria-label="`试品温度${channel}采集值`">{{ formatCalibrationValue(dutCalibrationValue(channel, 'collected')) }}</output>
                      <label class="dut-correction-value" role="cell">
                        <span class="hmi-number-control"><input v-model.number="parameterForm[`DUT${channel}_Corrected`]" type="number" step="any" :aria-label="`试品温度${channel}修正值`"><span class="hmi-number-steps"><button type="button" :title="`增加试品温度${channel}修正值`" :aria-label="`增加试品温度${channel}修正值`" @click.stop.prevent="stepParameterNumber(`DUT${channel}_Corrected`, 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" :title="`减少试品温度${channel}修正值`" :aria-label="`减少试品温度${channel}修正值`" @click.stop.prevent="stepParameterNumber(`DUT${channel}_Corrected`, -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span>
                      </label>
                      <output role="cell" :aria-label="`试品温度${channel}最终值`">{{ formatCalibrationValue(dutCalibrationValue(channel, 'final')) }}</output>
                    </div>
                  </div>
                </div>
              </section>

              <section v-if="parameterTab === 'pid'" class="system-parameter-card pid-setting-card">
                <header><span>PID 设定</span></header>
                <div class="pid-setting-layout">
                  <div class="pid-coordinate-modes">
                    <fieldset v-for="mode in pidModes" :key="mode.key" class="pid-coordinate-panel" :class="{ active: selectedPidMode === mode.key }">
                      <legend>{{ mode.title }}</legend>
                      <div class="pid-coordinate-map" :class="`pid-coordinate-map-${mode.key}`">
                        <label v-for="(axis, axisIndex) in mode.yAxes" :key="axis.key" class="pid-axis-input pid-axis-y" :style="{ gridRow: axisIndex + 1, gridColumn: 1 }">
                          <span>{{ axis.label }}</span>
                          <input v-model.number="parameterForm[axis.key]" type="number" step="any" :aria-label="`${mode.title}${axis.label}坐标`">
                        </label>
                        <button
                          v-for="group in mode.groupCount"
                          :key="group"
                          type="button"
                          class="pid-coordinate-point"
                          :class="{ active: selectedPidMode === mode.key && selectedPidGroup === group }"
                          :style="pidGroupPosition(mode.key, group)"
                          :aria-label="`编辑${mode.title}${pidDisplayGroupNumber(mode, group)}组参数`"
                          @click="selectPidGroup(mode.key, group)"
                        >{{ pidDisplayGroupNumber(mode, group) }}</button>
                        <label v-for="(axis, axisIndex) in mode.xAxes" :key="axis.key" class="pid-axis-input pid-axis-x" :style="{ gridRow: 5, gridColumn: axisIndex + 2 }">
                          <span>{{ axis.label }}</span>
                          <input v-model.number="parameterForm[axis.key]" type="number" step="any" :aria-label="`${mode.title}${axis.label}坐标`">
                        </label>
                      </div>
                    </fieldset>
                  </div>

                  <Transition name="settings-tab" mode="out-in" @before-leave="prepareWorkspaceLeave">
                  <fieldset :key="`${selectedPidMode}-${selectedPidGroup}`" class="pid-group-editor">
                    <legend>设定序号：{{ selectedPidDisplayNumber }}</legend>
                    <div class="pid-editor-head" aria-hidden="true">
                      <span></span>
                      <strong v-for="category in pidCategories" :key="category.key">{{ category.label }}</strong>
                    </div>
                    <div v-for="metric in pidMetrics" :key="metric.key" class="pid-editor-row">
                      <span>{{ metric.label }}<small v-if="metric.unit">（{{ metric.unit }}）</small></span>
                      <label v-for="category in pidCategories" :key="category.key">
                        <span class="pid-equals" aria-hidden="true">=</span>
                        <span v-if="selectedPidModeConfig.categories.some(item => item.key === category.key)" class="hmi-number-control"><input v-model.number="parameterForm[pidParameterKey(selectedPidMode, selectedPidGroup, category.key, metric.key)]" type="number" step="any" :aria-label="`${selectedPidModeConfig.title}${selectedPidDisplayNumber}组${category.label}${metric.label}`"><span class="hmi-number-steps"><button type="button" :title="`增加${category.label}${metric.label}`" :aria-label="`增加${category.label}${metric.label}`" @click.stop.prevent="stepParameterNumber(pidParameterKey(selectedPidMode, selectedPidGroup, category.key, metric.key), 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" :title="`减少${category.label}${metric.label}`" :aria-label="`减少${category.label}${metric.label}`" @click.stop.prevent="stepParameterNumber(pidParameterKey(selectedPidMode, selectedPidGroup, category.key, metric.key), -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span>
                        <output v-else class="pid-unavailable" :aria-label="`${selectedPidModeConfig.title}无${category.label}${metric.label}参数`">---</output>
                      </label>
                    </div>
                  </fieldset>
                  </Transition>
                </div>
              </section>

              <section v-if="parameterTab === 'basic'" class="system-parameter-card">
                <header><span>电机频率</span></header>
                <div class="parameter-fields">
                  <label><span>升降温频率</span><div><span class="hmi-number-control"><input v-model.number="parameterForm.compressorFrequency" type="number" min="0" max="100" step="0.1"><span class="hmi-number-steps"><button type="button" title="提高升降温频率" aria-label="提高升降温频率" @click.stop.prevent="stepParameterNumber('compressorFrequency', 0.1, 0, 100)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="降低升降温频率" aria-label="降低升降温频率" @click.stop.prevent="stepParameterNumber('compressorFrequency', -0.1, 0, 100)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>Hz</b></div></label>
                  <label><span>恒温频率</span><div><span class="hmi-number-control"><input v-model.number="parameterForm.circulationFanFrequency" type="number" min="0" max="100" step="0.1"><span class="hmi-number-steps"><button type="button" title="提高恒温频率" aria-label="提高恒温频率" @click.stop.prevent="stepParameterNumber('circulationFanFrequency', 0.1, 0, 100)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="降低恒温频率" aria-label="降低恒温频率" @click.stop.prevent="stepParameterNumber('circulationFanFrequency', -0.1, 0, 100)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>Hz</b></div></label>
                  <label><span>湿度频率</span><div><span class="hmi-number-control"><input v-model.number="parameterForm.humidifierFrequency" type="number" min="0" max="100" step="0.1"><span class="hmi-number-steps"><button type="button" title="提高湿度频率" aria-label="提高湿度频率" @click.stop.prevent="stepParameterNumber('humidifierFrequency', 0.1, 0, 100)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="降低湿度频率" aria-label="降低湿度频率" @click.stop.prevent="stepParameterNumber('humidifierFrequency', -0.1, 0, 100)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>Hz</b></div></label>
                  <label><span>其他频率</span><div><span class="hmi-number-control"><input v-model.number="parameterForm.frequencyLimit" type="number" min="0" max="100" step="0.1"><span class="hmi-number-steps"><button type="button" title="提高其他频率" aria-label="提高其他频率" @click.stop.prevent="stepParameterNumber('frequencyLimit', 0.1, 0, 100)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="降低其他频率" aria-label="降低其他频率" @click.stop.prevent="stepParameterNumber('frequencyLimit', -0.1, 0, 100)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>Hz</b></div></label>
                </div>
              </section>

              <section v-if="parameterTab === 'basic'" class="system-parameter-card">
                <header><span>温度操作范围</span></header>
                <div class="parameter-fields">
                  <label><span>操作下限</span><div><span class="hmi-number-control"><input v-model.number="parameterForm.temperatureRangeMin" type="number" step="0.1"><span class="hmi-number-steps"><button type="button" title="增加温度操作下限" aria-label="增加温度操作下限" @click.stop.prevent="stepParameterNumber('temperatureRangeMin', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少温度操作下限" aria-label="减少温度操作下限" @click.stop.prevent="stepParameterNumber('temperatureRangeMin', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>°C</b></div></label>
                  <label><span>操作上限</span><div><span class="hmi-number-control"><input v-model.number="parameterForm.temperatureRangeMax" type="number" step="0.1"><span class="hmi-number-steps"><button type="button" title="增加温度操作上限" aria-label="增加温度操作上限" @click.stop.prevent="stepParameterNumber('temperatureRangeMax', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少温度操作上限" aria-label="减少温度操作上限" @click.stop.prevent="stepParameterNumber('temperatureRangeMax', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>°C</b></div></label>
                </div>
              </section>

              <section v-if="parameterTab === 'basic'" class="system-parameter-card">
                <header><span>湿度操作范围</span></header>
                <div class="parameter-fields stacked-limit-fields">
                  <label><span>湿度操作上限</span><div><span class="hmi-number-control"><input v-model.number="parameterForm.humidityRangeMax" type="number" min="0" max="100" step="0.1" aria-label="湿度操作上限"><span class="hmi-number-steps"><button type="button" title="增加湿度操作上限" aria-label="增加湿度操作上限" @click.stop.prevent="stepParameterNumber('humidityRangeMax', 0.1, 0, 100)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少湿度操作上限" aria-label="减少湿度操作上限" @click.stop.prevent="stepParameterNumber('humidityRangeMax', -0.1, 0, 100)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>%RH</b></div></label>
                  <label><span>湿度操作下限</span><div><span class="hmi-number-control"><input v-model.number="parameterForm.humidityRangeMin" type="number" min="0" max="100" step="0.1" aria-label="湿度操作下限"><span class="hmi-number-steps"><button type="button" title="增加湿度操作下限" aria-label="增加湿度操作下限" @click.stop.prevent="stepParameterNumber('humidityRangeMin', 0.1, 0, 100)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少湿度操作下限" aria-label="减少湿度操作下限" @click.stop.prevent="stepParameterNumber('humidityRangeMin', -0.1, 0, 100)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>%RH</b></div></label>
                </div>
              </section>

              <section v-if="parameterTab === 'basic'" class="system-parameter-card">
                <header><span>湿度模式温度操作范围</span></header>
                <div class="parameter-fields stacked-limit-fields">
                  <label><span>温度操作上限值</span><div><span class="hmi-number-control"><input v-model.number="parameterForm.temperatureTransmissionMax" type="number" step="0.1" aria-label="温度操作上限值"><span class="hmi-number-steps"><button type="button" title="增加温度操作上限值" aria-label="增加温度操作上限值" @click.stop.prevent="stepParameterNumber('temperatureTransmissionMax', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少温度操作上限值" aria-label="减少温度操作上限值" @click.stop.prevent="stepParameterNumber('temperatureTransmissionMax', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>°C</b></div></label>
                  <label><span>温度操作下限值</span><div><span class="hmi-number-control"><input v-model.number="parameterForm.temperatureTransmissionMin" type="number" step="0.1" aria-label="温度操作下限值"><span class="hmi-number-steps"><button type="button" title="增加温度操作下限值" aria-label="增加温度操作下限值" @click.stop.prevent="stepParameterNumber('temperatureTransmissionMin', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少温度操作下限值" aria-label="减少温度操作下限值" @click.stop.prevent="stepParameterNumber('temperatureTransmissionMin', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>°C</b></div></label>
                </div>
              </section>

            </div>
            <div class="system-parameters-footer"><span>参数修改仅作用于当前设备</span><div><button class="ghost-action" type="button" @click="resetParameterForm">恢复默认</button><button class="primary-action" type="button" @click="openSaveConfirm('parameters')">保存参数</button></div></div>
            </div>
            </Transition>
          </section>

          <section v-else-if="selectedDevice && selectedDeviceSection === 'history'" key="history" class="history-page page-stack" :aria-busy="historyLoading">
            <div class="section-head history-page-head">
              <div><h2>历史记录</h2><span>{{ selectedDevice.name || selectedDevice.device_id }} · 温湿度历史曲线</span></div>
              <span class="history-record-count">{{ historyItems.length }} 条记录</span>
            </div>
            <section class="panel history-query-panel">
              <div class="history-query-row">
                <label><span>快捷范围</span><select v-model="historyQuery.range" @change="applyHistoryRange"><option value="1h">最近1小时</option><option value="6h">最近6小时</option><option value="24h">最近24小时</option><option value="7d">最近7天</option><option value="custom">自定义</option></select></label>
                <label><span>开始时间</span><input v-model="historyQuery.startTime" type="datetime-local" :disabled="historyQuery.range !== 'custom'"></label>
                <label><span>结束时间</span><input v-model="historyQuery.endTime" type="datetime-local" :disabled="historyQuery.range !== 'custom'"></label>
                <label><span>运行状态</span><select v-model="historyQuery.runState"><option value="">全部状态</option><option value="RUNNING">运行中</option><option value="HOLDING">保持中</option><option value="PAUSED">已暂停</option><option value="STOPPED">已停止</option><option value="IDLE">空闲</option><option value="ALARM">报警</option></select></label>
                <button class="primary-action history-query-button" type="button" :disabled="historyLoading" @click="loadEnvironmentalHistory">{{ historyLoading ? '查询中…' : '查询历史' }}</button>
              </div>
              <p v-if="historyError" class="history-error" role="alert">{{ historyError }}</p>
            </section>
            <section class="panel history-chart-panel">
              <div class="panel-title"><div><h3>温湿度曲线</h3><span>{{ historyRangeLabel }}</span></div><div class="history-legend"><span><i class="history-temp-line"></i>温度 °C</span><span><i class="history-hum-line"></i>湿度 %RH</span></div></div>
              <div v-if="!historyItems.length" class="history-state">{{ historyLoading ? '' : '当前时间范围内暂无历史数据。' }}</div>
              <svg v-else class="history-chart" viewBox="0 0 1000 320" role="img" aria-label="温湿度历史曲线">
                <g class="history-grid-lines"><line v-for="y in historyGridLines" :key="`y-${y}`" x1="58" :y1="y" x2="978" :y2="y"></line><line v-for="x in historyXAxis" :key="`x-${x}`" :x1="x" y1="20" :x2="x" y2="268"></line></g>
                <polyline class="history-temp-path" :points="historyTempPoints"></polyline><polyline class="history-hum-path" :points="historyHumPoints"></polyline>
                <g class="history-axis-labels"><text v-for="label in historyYAxisLabels" :key="label.text" :x="label.x" :y="label.y">{{ label.text }}</text><text v-for="label in historyXAxisLabels" :key="label.text" :x="label.x" y="294" text-anchor="middle">{{ label.text }}</text></g>
              </svg>
            </section>
            <section class="panel history-table-panel">
              <div class="panel-title"><div><h3>采样明细</h3><span>按采样时间倒序显示最近 50 条</span></div><span>{{ historyItems.length ? formatHistoryTime(historyItems[historyItems.length - 1].recorded_at) : '--' }} 至 {{ historyItems.length ? formatHistoryTime(historyItems[0].recorded_at) : '--' }}</span></div>
              <div v-if="historyItems.length" class="history-table-wrap"><table class="history-table"><thead><tr><th>采样时间</th><th>温度（°C）</th><th>湿度（%RH）</th><th>温度目标</th><th>湿度目标</th><th>运行状态</th></tr></thead><tbody><tr v-for="item in historyRecentItems" :key="`${item.recorded_at}-${item.device_id}`"><td>{{ formatHistoryTime(item.recorded_at) }}</td><td>{{ formatHistoryNumber(item.temperature) }}</td><td>{{ formatHistoryNumber(item.humidity) }}</td><td>{{ formatHistoryNumber(item.temperature_target) }}</td><td>{{ formatHistoryNumber(item.humidity_target) }}</td><td>{{ historyRunStateLabel(item.run_state) }}</td></tr></tbody></table></div>
              <div v-else-if="!historyLoading" class="history-state history-table-empty">暂无可展示的采样明细。</div>
            </section>
          </section>

          <section v-else-if="selectedDevice" :key="selectedDeviceSection" class="panel empty-panel">
            <h3>{{ currentDeviceSectionLabel }}</h3>
            <p>{{ currentDeviceSectionDescription }}</p>
          </section>

          <section v-else key="missing-device" class="panel empty-panel">
            <h3>设备暂未找到</h3>
            <p>请返回实时列表，重新选择一台在线试验箱。</p>
          </section>
          </Transition>
        </section>

        <section v-else-if="activeView === 'memory'" key="memory" class="page-stack">
          <div class="section-head">
            <h2>共享内存检查</h2>
            <a class="link-button" href="/debug" target="_blank">打开调试页</a>
          </div>
          <div class="kpi-grid">
            <LiveMetricCard label="共享内存名称" :value="memoryName" unit="固定映射名" tone="blue" />
            <LiveMetricCard label="总容量" :value="memoryTotal" unit="共享内存大小" tone="green" />
            <LiveMetricCard label="数据长度" :value="payloadLength" unit="当前 JSON" tone="purple" />
            <LiveMetricCard label="可读状态" :value="memoryStableText" unit="版本号机制" tone="red" />
          </div>
          <section class="panel">
            <div class="panel-title">
              <h3>完整快照 JSON</h3>
              <span>{{ currentTimeText }}</span>
            </div>
            <pre class="json-view">{{ formattedSnapshot }}</pre>
          </section>
        </section>

        <section v-else :key="activeView" class="page-stack">
          <div class="section-head">
            <h2>{{ currentTitle }}</h2>
            <span>预留模块</span>
          </div>
          <section class="panel empty-panel">
            <h3>模块待接入</h3>
            <p>这里将接入历史曲线、试验报告、报警处理、配方管理和权限审批。</p>
          </section>
        </section>
        </Transition>
      </main>
      <WorkspaceRefresh
        v-if="workspaceRefresh"
        :key="`${activeView}-${selectedDeviceId}-${selectedDeviceSection}-${operationTab}-${parameterTab}`"
        :target="workspaceContent"
        :pending="workspaceRefresh.state.pending"
        :visible="workspaceRefresh.state.visible"
        :error="workspaceRefresh.state.error"
        :title="workspaceRefreshTitle"
        complete-title="最新数据已就绪"
        :error-title="workspaceErrorTitle"
        @retry="retryWorkspace"
        @dismiss="dismissWorkspaceRefresh"
      />
    </section>

    <MotionDialog :open="isLayoutEditorOpen" backdrop-class="layout-modal-backdrop" panel-class="layout-modal" labelledby="layout-modal-title" @close="isLayoutEditorOpen = false">
      <div class="layout-modal-header">
        <div><h3 id="layout-modal-title">选择显示卡片</h3><span>配置仅保存在当前浏览器</span></div>
        <button class="layout-modal-close" type="button" title="关闭" aria-label="关闭" @click="isLayoutEditorOpen = false"><AppIcon name="close" :size="17" /></button>
      </div>
      <div class="layout-editor">
        <label v-for="card in optionalMonitorCards" :key="card.key" class="layout-option">
          <input type="checkbox" :checked="visibleMonitorCards.includes(card.key)" @change="toggleMonitorCard(card.key)" />
          <AppIcon :name="card.icon" :size="15" /><span>{{ card.label }}</span>
        </label>
      </div>
      <div class="layout-modal-footer"><span>{{ visibleMonitorCards.length }} 项已显示</span><button class="layout-modal-confirm" type="button" @click="isLayoutEditorOpen = false">完成</button></div>
    </MotionDialog>

    <MotionDialog :open="isSaveConfirmOpen" backdrop-class="save-confirm-backdrop" panel-class="save-confirm-modal" labelledby="save-confirm-title" return-focus=".operation-nav button.active" @close="closeSaveConfirm">
        <div class="save-confirm-header">
          <div>
            <h3 id="save-confirm-title">确认修改设置</h3>
            <span>保存后将更新当前设备的设定，是否继续？</span>
          </div>
        </div>
        <div class="save-confirm-footer">
          <button class="ghost-action" type="button" data-dialog-autofocus @click="closeSaveConfirm">取消</button>
          <button class="primary-action" type="button" @click="confirmSaveSettings">确认修改</button>
        </div>
    </MotionDialog>

    <MotionDialog :open="isProgramEditorOpen" backdrop-class="program-editor-backdrop" panel-class="program-editor-modal" labelledby="program-editor-title" @close="closeProgramEditor">
        <div class="program-editor-header"><div><h3 id="program-editor-title">{{ programEditorMode === 'create' ? '新建程序' : '编辑程序' }}</h3></div><button class="program-editor-close" type="button" title="关闭" aria-label="关闭" @click="closeProgramEditor"><AppIcon name="close" :size="17" /></button></div>
        <form class="program-editor-form" @submit.prevent="saveProgram">
          <div class="program-editor-group-fields"><label class="program-editor-name"><span>程序名称</span><input v-model.trim="programDraft.name" type="text" maxlength="128" required></label></div>
          <div class="program-steps-editor-header"><h4>步骤明细</h4><button class="ghost-action" type="button" @click="addProgramStep">＋ 添加步骤</button></div>
          <div class="program-steps-editor-wrap"><table class="program-steps-editor"><thead><tr><th>段号</th><th>时间（时:分:秒）</th><th>温度</th><th>湿度</th><th>气压</th><th>事件</th><th></th></tr></thead><tbody><tr v-for="(step, index) in programDraft.steps" :key="index"><td><span class="program-step-number">{{ index + 1 }}</span></td><td><input v-model.trim="step.timeText" type="time" step="1" required aria-label="步骤时间（时:分:秒）"></td><td><span class="program-step-value-with-unit"><input v-model.number="step.temp" type="number" step="0.1" required><small>°C</small></span></td><td><span class="program-step-value-with-unit"><input v-model.number="step.humi" type="number" step="0.1" required><small>%RH</small></span></td><td><input v-model.number="step.pressure" type="number" step="0.1" required aria-label="步骤气压"></td><td><input class="program-step-event-input" type="text" :value="formatEventBits(step.event_bits)" readonly @click="openProgramStepEventDialog(index)" @keydown.enter.prevent="openProgramStepEventDialog(index)" @keydown.space.prevent="openProgramStepEventDialog(index)" :aria-label="`步骤${index + 1}事件，点击选择`"></td><td><button class="table-icon-button" type="button" title="删除步骤" :disabled="programDraft.steps.length <= 1" @click="removeProgramStep(index)">×</button></td></tr><tr v-if="!programDraft.steps.length"><td colspan="7" class="program-empty-cell">请添加至少一个步骤</td></tr></tbody></table></div>
          <section class="program-loop-section" aria-labelledby="program-loop-title">
            <div class="program-loop-section-header"><h4 id="program-loop-title">循环</h4><div><button class="ghost-action" type="button" :disabled="programDraft.loopCount >= 4" @click="addProgramLoop">＋ 添加循环</button></div></div>
            <div class="program-loop-layout">
              <div class="program-loop-list">
                <div class="program-loop-heading"><span>循环</span><span>起始段</span><span>结束段</span><span>次数</span><span></span></div>
                <label v-for="loopIndex in programDraft.loopCount" :key="loopIndex" class="program-loop-row"><strong>循环{{ loopIndex }}</strong><select v-model.number="programDraft[`loop${loopIndex}_start`]" :aria-label="`循环${loopIndex}起始段`"><option :value="0">选择段号</option><option v-for="step in programDraft.steps" :key="`loop-${loopIndex}-start-${step.step_no}`" :value="Number(step.step_no)">{{ step.step_no }}</option></select><select v-model.number="programDraft[`loop${loopIndex}_end`]" :aria-label="`循环${loopIndex}结束段`"><option :value="0">选择段号</option><option v-for="step in programDraft.steps" :key="`loop-${loopIndex}-end-${step.step_no}`" :value="Number(step.step_no)">{{ step.step_no }}</option></select><input v-model.number="programDraft[`loop${loopIndex}_times`]" type="number" min="0" step="1" :aria-label="`循环${loopIndex}次数`"><button class="program-loop-remove" type="button" title="删除循环" :disabled="programDraft.loopCount <= 1" @click="removeProgramLoop(loopIndex)">×</button></label>
              </div>
              <div class="program-loop-extra">
                <label class="program-loop-total-time"><span>总运行时间</span><output>{{ formatDuration(programCalculatedTotalTime) }}</output></label>
                <label><span>总循环次数</span><input v-model.number="programDraft.full_cycle" type="number" min="0" step="1" aria-label="总循环次数"></label>
                <label><span>链接</span><select v-model.number="programDraft.link_no" aria-label="链接程序号"><option :value="0">不链接</option><template v-for="program in programs" :key="`link-program-${program.pro_no}`"><option v-if="Number(program.pro_no) !== Number(programDraft.pro_no)" :value="Number(program.pro_no)">程序{{ program.pro_no }}：{{ program.name || '未命名程序' }}</option></template></select></label>
              </div>
            </div>
          </section>
          <div class="program-editor-footer"><span v-if="programFeedback" class="program-editor-feedback">{{ programFeedback }}</span><div><button class="ghost-action" type="button" @click="closeProgramEditor">取消</button><button class="primary-action" type="submit" :disabled="programSaving">{{ programSaving ? '保存中…' : '保存程序' }}</button></div></div>
        </form>
    </MotionDialog>

    <MotionDialog :open="isProgramPreviewOpen" backdrop-class="program-preview-backdrop" panel-class="program-preview-modal" labelledby="program-preview-title" @close="closeProgramPreview">
        <header class="program-preview-header"><div><h3 id="program-preview-title">{{ programPreview?.name || '程序预览' }}</h3><span>程序组 {{ programPreview?.pro_no }}</span></div><button class="program-preview-close" type="button" title="关闭预览" aria-label="关闭预览" @click="closeProgramPreview"><AppIcon name="close" :size="17" /></button></header>
        <div v-if="programPreview" class="program-preview-content">
          <div class="program-detail-meta"><span>总运行时间 <strong>{{ formatDuration(programPreview.display_total_time) }}</strong></span><span>总循环次数 <strong>{{ programPreview.full_cycle || 0 }} 次</strong></span><span>链接 <strong>{{ programPreview.link_no || 0 }}</strong></span></div>
          <section v-if="programPreviewChart.points.length" class="program-chart-panel" aria-label="程序运行趋势图">
            <div class="program-chart-legend" aria-label="曲线图例">
              <span v-for="series in programPreviewChart.series" :key="series.key"><i :style="{ backgroundColor: series.color }"></i>{{ series.label }}<b>{{ series.unit }}</b></span>
            </div>
            <svg class="program-preview-chart" viewBox="0 0 900 390" role="img" :aria-label="`${programPreview.name || '程序'}温度、湿度、气压随时间变化曲线`" @pointermove="handleProgramChartPointerMove" @pointerleave="handleProgramChartPointerLeave" @pointerdown="handleProgramChartPointerDown" @pointerup="handleProgramChartPointerUp" @pointercancel="handleProgramChartPointerUp">
              <g class="program-chart-grid">
                <line v-for="tick in programPreviewChart.yTicks" :key="`y-${tick.value}`" x1="72" :y1="tick.y" x2="866" :y2="tick.y"></line>
                <line v-for="(tick, index) in programPreviewChart.xTicks" :key="`x-${index}`" :x1="tick.x" y1="28" :x2="tick.x" y2="322"></line>
              </g>
              <line class="program-chart-axis" x1="72" y1="322" x2="866" y2="322"></line>
              <line class="program-chart-axis" x1="72" y1="28" x2="72" y2="322"></line>
              <text class="program-chart-axis-title" x="72" y="17">温度 / 湿度 / 气压</text>
              <text v-for="tick in programPreviewChart.yTicks" :key="`yl-${tick.value}`" class="program-chart-tick-label" x="60" :y="tick.y + 4" text-anchor="end">{{ tick.label }}</text>
              <text v-for="(tick, index) in programPreviewChart.xTicks" :key="`xl-${index}`" class="program-chart-tick-label" :x="tick.x" y="344" text-anchor="middle">{{ tick.label }}</text>
              <text class="program-chart-x-title" x="469" y="374" text-anchor="middle">时间（时:分:秒）</text>
              <g v-for="series in programPreviewChart.series" :key="series.key">
                <polyline v-for="(segment, segmentIndex) in series.segments" :key="`${series.key}-segment-${segmentIndex}`" class="program-chart-line" :stroke="series.color" :points="segment"></polyline>
                <template v-for="point in series.coordinates" :key="`${series.key}-${point.index}`">
                  <circle v-if="point.showPoint" class="program-chart-point" :fill="series.color" :cx="point.x" :cy="point.y" r="3.5"></circle>
                </template>
              </g>
              <g v-if="programChartCursor" class="program-chart-cursor-group" aria-live="polite">
                <line class="program-chart-cursor" :x1="programChartCursor.x" y1="28" :x2="programChartCursor.x" y2="322"></line>
                <circle v-for="series in programPreviewChart.series" :key="`cursor-${series.key}`" class="program-chart-cursor-point" :fill="series.color" :cx="programChartCursor.x" :cy="programChartCursor.values[series.key].y" r="5"></circle>
                <g :transform="`translate(${programChartCursor.tooltipX}, 40)`">
                  <rect class="program-chart-tooltip" width="172" height="112" rx="5"></rect>
                  <text class="program-chart-tooltip-title" x="12" y="20">时间 {{ programChartCursor.timeLabel }}</text>
                  <text class="program-chart-tooltip-value temp" x="12" y="43">温度 {{ programChartCursor.values.temp.label }} °C</text>
                  <text class="program-chart-tooltip-value humi" x="12" y="66">湿度 {{ programChartCursor.values.humi.label }} %RH</text>
                  <text class="program-chart-tooltip-value pressure" x="12" y="89">气压 {{ programChartCursor.values.pressure.label }}</text>
                </g>
              </g>
            </svg>
            <div v-if="programPreviewChart.totalTime > programPreviewChart.windowDuration" class="program-chart-range">
              <div class="program-chart-range-header"><span>时间范围</span><strong>{{ formatDuration(programPreviewChart.windowStart) }} - {{ formatDuration(programPreviewChart.windowEnd) }}</strong><small>拖动滑块查看更多</small></div>
              <input v-model.number="programChartScrollStart" class="program-chart-range-slider" type="range" min="0" :max="programPreviewChart.maxScroll" step="1" aria-label="预览时间范围" @input="programChartCursor = null">
              <div class="program-chart-range-labels"><span>00:00:00</span><span>{{ formatDuration(programPreviewChart.totalTime) }}</span></div>
            </div>
            <div class="program-chart-hint">移动或拖动图中的竖线，可查看任意时间点的温度、湿度和气压数据</div>
          </section>
          <section v-else class="program-chart-empty">该程序尚未配置可绘制的步骤数据</section>
        </div>
    </MotionDialog>

    <MotionDialog :open="isEventDialogOpen" backdrop-class="event-dialog-backdrop" panel-class="event-dialog" labelledby="event-dialog-title" @close="cancelEventDialog">
        <div class="event-dialog-header">
          <div>
            <h3 id="event-dialog-title">{{ eventDialogStepIndex === null ? '选择事件' : `步骤${eventDialogStepIndex + 1}事件` }}</h3>
            <span>点击按钮启用或关闭对应事件</span>
          </div>
          <button class="event-dialog-close" type="button" title="关闭" aria-label="关闭" @click="cancelEventDialog">
            <AppIcon name="close" :size="17" />
          </button>
        </div>
        <div class="event-dialog-grid" role="group" aria-label="16 个事件开关">
          <button
            v-for="eventIndex in 16"
            :key="eventIndex"
            type="button"
            class="event-toggle"
            :class="{ active: eventDraft[eventIndex - 1] === '1' }"
            :aria-pressed="eventDraft[eventIndex - 1] === '1'"
            @click="toggleEvent(eventIndex - 1)"
          >
            <span class="event-toggle-indicator" aria-hidden="true"></span>
            <strong>事件{{ eventIndex }}</strong>
            <small>{{ eventDraft[eventIndex - 1] === '1' ? '开启' : '关闭' }}</small>
          </button>
        </div>
        <div class="event-dialog-footer">
          <span>当前值：{{ eventDraft }}</span>
          <div>
            <button class="ghost-action" type="button" @click="cancelEventDialog">取消</button>
            <button class="primary-action" type="button" @click="confirmEventDialog">确认</button>
          </div>
        </div>
    </MotionDialog>

    <MotionDialog :open="isRunModeDialogOpen" backdrop-class="run-mode-backdrop" panel-class="run-mode-modal" labelledby="run-mode-title" return-focus=".operation-nav button.active" @close="cancelRunModeSelection">
        <div class="run-mode-header">
          <div>
            <h3 id="run-mode-title">选择运行模式</h3>
          </div>
          <button class="run-mode-close" type="button" title="关闭" aria-label="关闭" data-dialog-autofocus @click="cancelRunModeSelection">
            <AppIcon name="close" :size="17" />
          </button>
        </div>
        <div class="run-mode-options">
          <button
            v-for="mode in runModeOptions"
            :key="mode.value"
            type="button"
            class="run-mode-option"
            :class="{ active: runModeSelection === mode.value }"
            :aria-pressed="runModeSelection === mode.value"
            @click="runModeSelection = mode.value"
          >
            <span class="run-mode-option-icon"><AppIcon :name="mode.icon" :size="21" /></span>
            <span><strong>{{ mode.label }}</strong></span>
            <i>{{ runModeSelection === mode.value ? "已选择" : "选择" }}</i>
          </button>
        </div>
        <div class="run-mode-preview" aria-live="polite">
          <div class="run-mode-preview-heading"><span>当前模式预览</span><button v-if="runModeSelection === '1'" class="run-mode-preview-link" type="button" @click="openSetpointSettings">定制修改</button></div>
          <Transition name="settings-tab" mode="out-in" @before-leave="prepareWorkspaceLeave">
          <div v-if="runModeSelection === '1'" key="fixed" class="run-mode-preview-grid">
            <div><span>温度目标</span><strong>{{ operationForm.targetTemp }} °C</strong></div>
            <div><span>湿度目标</span><strong>{{ operationForm.targetHum }} %RH</strong></div>
            <div><span>运行时间</span><strong>{{ String(operationForm.runtimeHours).padStart(2, '0') }}:{{ String(operationForm.runtimeMinutes).padStart(2, '0') }}:{{ String(operationForm.runtimeSeconds).padStart(2, '0') }}</strong></div>
          </div>
          <div v-else key="program" class="run-mode-preview-grid program-mode-preview">
            <div><span>程序名称</span><strong>{{ selectedProgram?.name || "尚未选择程序" }}</strong></div>
            <div><span>总运行时间</span><strong>{{ selectedProgram?.display_total_time == null ? "--" : formatDuration(selectedProgram.display_total_time) }}</strong></div>
          </div>
          </Transition>
        </div>
        <div class="run-mode-footer">
          <div><button class="primary-action" type="button" @click="confirmRunModeSelection">确认启动</button></div>
        </div>
    </MotionDialog>

    <MotionDialog :open="isNotificationOpen" backdrop-class="notification-modal-backdrop" panel-class="notification-modal" labelledby="notification-modal-title" @close="isNotificationOpen = false">
        <div class="notification-modal-header">
          <div>
            <h3 id="notification-modal-title">{{ notificationTitle }}</h3>
            <span v-if="activeView !== 'device-detail'">{{ notificationSubtitle }}</span>
          </div>
          <button class="notification-modal-close" type="button" title="关闭" aria-label="关闭" @click="isNotificationOpen = false">
            <AppIcon name="close" :size="17" />
          </button>
        </div>
        <div v-if="activeView === 'device-detail'" ref="notificationNav" class="notification-tabs motion-nav" :class="{ 'motion-ready': notificationIndicator }" role="tablist" aria-label="设备信息类别">
          <span v-if="notificationIndicator" class="motion-selection" :style="notificationIndicator" aria-hidden="true"></span>
          <button data-motion-key="operations" type="button" :class="{ active: notificationTab === 'operations' }" role="tab" :aria-selected="notificationTab === 'operations'" @click="notificationTab = 'operations'">操作日志</button>
          <button data-motion-key="alarms" type="button" :class="{ active: notificationTab === 'alarms' }" role="tab" :aria-selected="notificationTab === 'alarms'" @click="notificationTab = 'alarms'">报警信息<span v-if="selectedDeviceAlarmItems.length">{{ selectedDeviceAlarmItems.length }}</span></button>
        </div>
        <Transition name="settings-tab" mode="out-in" @before-leave="prepareWorkspaceLeave">
        <div v-if="notificationTab === 'operations' || activeView !== 'device-detail'" key="operations" class="notification-list">
          <div v-if="activeNotifications.length === 0" class="notification-empty">
            <strong>{{ notificationEmptyTitle }}</strong>
            <span>{{ notificationEmptyText }}</span>
          </div>
          <article v-for="item in activeNotifications" :key="item.id" class="notification-item" :class="item.tone">
            <i aria-hidden="true"></i>
            <div>
              <strong>{{ item.title }}</strong>
              <p>{{ item.message }}</p>
            </div>
            <time>{{ item.timeText }}</time>
          </article>
        </div>
        <div v-else key="alarms" class="alarm-info-list">
          <div class="alarm-info-summary">
            <div><span>当前状态</span><strong :class="{ active: selectedDeviceAlarmItems.length > 0 }">{{ selectedDeviceAlarmState }}</strong></div>
            <small>{{ selectedDeviceAlarmItems.length ? `检测到 ${selectedDeviceAlarmItems.length} 条报警` : "当前设备未上报报警" }}</small>
          </div>
          <div v-if="selectedDeviceAlarmItems.length === 0" class="notification-empty">
            <strong>当前无报警</strong>
            <span>设备应用层的 status.alarm 暂无报警内容。</span>
          </div>
          <article v-for="(alarm, index) in selectedDeviceAlarmItems" :key="`${alarm}-${index}`" class="notification-item danger">
            <i aria-hidden="true"></i>
            <div>
              <strong>报警 {{ index + 1 }}</strong>
              <p>{{ alarm }}</p>
            </div>
            <time>{{ selectedDevice?.data_time || selectedDevice?.time || "实时" }}</time>
          </article>
        </div>
        </Transition>
    </MotionDialog>

    <MotionDialog :open="pendingDeleteProgram !== null" backdrop-class="save-confirm-backdrop" panel-class="save-confirm-modal" labelledby="delete-program-title" @close="pendingDeleteProgram = null">
      <div class="save-confirm-header"><div><h3 id="delete-program-title">删除程序</h3><span>确定删除程序组 {{ pendingDeleteProgram }} 及其全部步骤？</span></div></div>
      <div class="save-confirm-footer">
        <button class="ghost-action" type="button" data-dialog-autofocus @click="pendingDeleteProgram = null">取消</button>
        <button class="primary-action" type="button" @click="confirmDeleteProgram">确认删除</button>
      </div>
    </MotionDialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import LiveMetricCard from "./components/LiveMetricCard.vue";
import LiveDeviceDetailCard from "./components/LiveDeviceDetailCard.vue";
import DeviceOverviewList from "./components/DeviceOverviewList.vue";
import AppIcon from "./components/AppIcon.vue";
import HmiDashboard from "./components/HmiDashboard.vue";
import ProfileCenter from "./components/ProfileCenter.vue";
import MotionDialog from "./components/MotionDialog.vue";
import WorkspaceRefresh from "./components/WorkspaceRefresh.vue";
import { useRefreshTask } from "./composables/useRefreshTask";
import { useSelectionIndicator } from "./composables/useSelectionIndicator";
import { hasOpenDialogs } from "./composables/useDialogStack";
import { communicationClass, communicationLabel, runStateLabel } from "./utils/state";

const emit = defineEmits(["logout"]);
const props = defineProps({
  initialUser: {
    type: Object,
    default: () => ({ username: "admin", display_name: "Admin User", role: "ADMIN", role_label: "管理员" })
  }
});

const TREND_PAST_MS = 5 * 60 * 1000;
const TREND_FUTURE_MS = 5 * 60 * 1000;
const TREND_DEFAULT_WINDOW_MS = TREND_PAST_MS + TREND_FUTURE_MS;
const TREND_MIN_WINDOW_MS = 30 * 1000;
const TREND_MAX_WINDOW_MS = 60 * 60 * 1000;
const TREND_HISTORY_RETENTION_MS = 2 * 60 * 60 * 1000;
const TREND_Y_MIN_SCALE = 0.18;
const TREND_Y_MAX_SCALE = 3.5;
const MONITOR_LAYOUT_STORAGE_KEY = "industrial-chamber-monitor-layout-v1";
const CORRECTION_REFRESH_MS = 1000;
const pidMetrics = [
  { key: "P", label: "比例", unit: "%" },
  { key: "I", label: "积分", unit: "S" },
  { key: "D", label: "微分", unit: "S" },
  { key: "LBL", label: "冷比例", unit: "%" },
  { key: "MQ", label: "盲区", unit: "" }
];
const pidCategories = [{ key: "T", label: "温度" }, { key: "H", label: "湿度" }];
const pidModes = [
  {
    key: "humidity",
    title: "湿热模式",
    groupCount: 7,
    displayOffset: 0,
    xAxes: Array.from({ length: 3 }, (_, index) => ({ key: `HUMI_T${index + 1}`, label: `X${index + 1}` })),
    yAxes: Array.from({ length: 4 }, (_, index) => ({ key: `HUMI_H${index + 1}`, label: `Y${index + 1}` })),
    categories: pidCategories
  },
  {
    key: "temperature",
    title: "温度模式",
    groupCount: 4,
    displayOffset: 7,
    xAxes: [],
    yAxes: Array.from({ length: 4 }, (_, index) => ({ key: `TEMP_T${index + 1}`, label: `Y${index + 1}` })),
    categories: [{ key: "T", label: "温度" }]
  }
];
const pidGroupPositions = {
  humidity: {
    1: [4, 2], 2: [3, 2], 3: [2, 2],
    4: [4, 3], 5: [3, 3], 6: [2, 3], 7: [3, 4]
  },
  temperature: {
    1: [4, 2], 2: [3, 2], 3: [2, 2], 4: [3, 3]
  }
};
const pidSettingFieldKeys = [
  ...pidModes.flatMap(mode => [...mode.xAxes, ...mode.yAxes].map(axis => axis.key)),
  ...Array.from({ length: 4 }, (_, index) => pidMetrics.map(metric => `TEMP${index + 1}_${metric.key}`)).flat(),
  ...Array.from({ length: 7 }, (_, index) =>
    ["T", "H"].flatMap(category => pidMetrics.map(metric => `HUMI${index + 1}_${category}_${metric.key}`))
  ).flat()
];

const activeView = ref("device-detail");
const devices = ref([{
  device_id: "EDGE-CHAMBER-001",
  name: "环境试验箱（本机）",
  online: false,
  run_state: "IDLE",
  status_text: "等待控制器数据",
  current_temperature: 0,
  target_temperature: 0,
  current_humidity: 0,
  target_humidity: 0,
  current_step: 0,
  total_steps: 0,
  alarms: []
}]);
const snapshot = ref(null);
const routerReadAt = ref(null);
const connectionText = ref("连接中");
const selectedDeviceId = ref("EDGE-CHAMBER-001");
const selectedDeviceSection = ref("monitor");
const operationTab = ref("protection");
const parameterTab = ref("basic");
const selectedPidMode = ref("humidity");
const selectedPidGroup = ref(1);
const operationFeedback = ref("");
const operationLastSaved = ref("尚未保存");
const operationForm = ref({
  overTempEnabled: true,
  overHumEnabled: true,
  powerMemory: true,
  tempLimit: 85,
  humLimit: 95,
  airTEMP_H: 0,
  airTEMP_L: 0,
  dutTEMP_H: 0,
  dutTEMP_L: 0,
  dutModeAir_H: 0,
  dutModeAir_L: 0,
  targetTemp: 25,
  targetHum: 50,
  tempRamp: 1.5,
  humRamp: 2,
  runtimeHours: 0,
  runtimeMinutes: 30,
  runtimeSeconds: 0,
  controlMode: "balanced",
  programId: "P-01",
  soundEnabled: true,
  doorLock: true,
  autoSave: true,
  precision: "0.1",
  brightness: 80,
  powerOnMode: "stop",
  stopResumeMode: "reset",
  temperatureControlMode: "air",
  dutTemperatureSource: "dut1",
  waitTemperatureUpper: 0,
  waitHumidityUpper: 0,
  historyRetentionDays: 90,
  eventCode: "0000000000000000",
  scheduledStartEnabled: false,
  scheduledStartDate: "2026-07-31",
  scheduledStartTime: "16:34",
  scheduledStopEnabled: false,
  scheduledStopDate: "2026-07-31",
  scheduledStopTime: "16:34"
});
const operationFieldGroups = {
  protection: ["airTEMP_H", "airTEMP_L", "dutTEMP_H", "dutTEMP_L", "dutModeAir_H", "dutModeAir_L"],
  setpoint: ["targetTemp", "targetHum", "tempRamp", "humRamp", "runtimeHours", "runtimeMinutes", "runtimeSeconds"],
  other: ["powerOnMode", "stopResumeMode", "temperatureControlMode", "dutTemperatureSource", "waitTemperatureUpper", "waitHumidityUpper", "eventCode"],
  retention: ["historyRetentionDays"]
};
const operationBaselines = ref(Object.fromEntries(Object.keys(operationFieldGroups).map(key => [key, operationSignature(key)])));
const operationSaving = ref(false);
const monitorRefresh = useRefreshTask();
const operationRefresh = useRefreshTask();
const parameterRefresh = useRefreshTask();
const historyRefresh = useRefreshTask();
const programRead = useRefreshTask();
const parameterSaving = ref(false);
const sidebarNav = ref(null);
const operationNav = ref(null);
const parameterNav = ref(null);
const displayModeNav = ref(null);
const notificationNav = ref(null);
const workspaceContent = ref(null);
const parameterForm = ref({
  deviceName: "",
  model: "IC-1000",
  firmwareVersion: "0.1.0",
  temperatureOffset: 0,
  temperatureGain: 1,
  humidityOffset: 0,
  humidityGain: 1,
  TEMP_Area1: 0,
  TEMP_Area2: 0,
  TEMP_Area3: 0,
  TEMP_Area4: 0,
  TEMP_Corrected1: 0,
  TEMP_Corrected2: 0,
  TEMP_Corrected3: 0,
  TEMP_Corrected4: 0,
  TEMP_Correction: 0,
  HUMI_Area1: 0,
  HUMI_Area2: 0,
  HUMI_Area3: 0,
  HUMI_Area4: 0,
  HUMI_Corrected1: 0,
  HUMI_Corrected2: 0,
  HUMI_Corrected3: 0,
  HUMI_Corrected4: 0,
  HUMI_Correction: 0,
  TEMP_Collected: 0,
  TEMP_Corrected: 0,
  TEMP_Final: 0,
  HUMI_Collected: 0,
  HUMI_Corrected: 0,
  HUMI_Final: 0,
  ...Object.fromEntries(
    Array.from({ length: 10 }, (_, index) =>
      ["Collected", "Corrected", "Final"].map(stage => [`DUT${index + 1}_${stage}`, 0])
    ).flat()
  ),
  ...Object.fromEntries(pidSettingFieldKeys.map(key => [key, 0])),
  compressorFrequency: 50,
  circulationFanFrequency: 50,
  humidifierFrequency: 50,
  frequencyLimit: 60,
  temperatureRangeMin: -40,
  temperatureRangeMax: 100,
  humidityRangeMin: 0,
  humidityRangeMax: 100,
  temperatureTransmissionMin: -40,
  temperatureTransmissionMax: 100,
  humidityTransmissionMin: 0,
  humidityTransmissionMax: 100
});
const deviceDisplayMode = ref("list");
const selectedTrendCanvas = ref(null);
const trendHistory = ref({});
const historyItems = ref([]);
const historyLoading = computed(() => historyRefresh.state.pending);
const historyError = computed(() => historyRefresh.state.error);
const historyQuery = ref({ range: "24h", startTime: toDateTimeInput(Date.now() - 24 * 60 * 60 * 1000), endTime: toDateTimeInput(Date.now()), runState: "" });
const currentTimeText = ref(new Date().toLocaleTimeString());
const commandStatusById = ref({});
const sessionUser = ref({ ...props.initialUser });
const stoppingDeviceIds = ref({});
const stoppedDeviceIds = ref({});
const startingDeviceIds = ref({});
const startCommandLockedIds = ref({});
const holdingDeviceIds = ref({});
const heldDeviceIds = ref({});
const skippingDeviceIds = ref({});
const trendClockMs = ref(Date.now());
const trendWindowMs = ref(TREND_DEFAULT_WINDOW_MS);
const trendCenterOffsetMs = ref(0);
const trendYScale = ref(1);
const trendYOffsetRatio = ref(0);
const isTrendDragging = ref(false);
const isSidebarCollapsed = ref(false);
const isLayoutEditorOpen = ref(false);
const isLightOn = ref(true);
const isLightCommandPending = ref(false);
const isNotificationOpen = ref(false);
const notificationTab = ref("operations");
const isSaveConfirmOpen = ref(false);
const isEventDialogOpen = ref(false);
const eventDraft = ref("0000000000000000");
const eventDialogStepIndex = ref(null);
const isRunModeDialogOpen = ref(false);
const runModeSelection = ref("1");
const programs = ref([]);
const selectedProgramDetail = ref(null);
const isProgramPreviewOpen = ref(false);
const programPreview = ref(null);
const programChartCursor = ref(null);
const isProgramChartPointerDown = ref(false);
const programChartScrollStart = ref(0);
const isProgramEditorOpen = ref(false);
const pendingDeleteProgram = ref(null);
const programEditorMode = ref("create");
const programSaving = ref(false);
const programFeedback = ref("");
const programDraft = ref(createProgramDraft());
const pendingSaveTarget = ref(null);
const deviceStartTimes = ref({});
const visibleMonitorCards = ref(["trend"]);
const deviceNotifications = ref([]);
const operationLogs = ref([]);
const previousDeviceStates = ref({});

let socket = null;
let reconnectTimer = null;
let clockTimer = null;
let correctionRefreshTimer = null;
let correctionRequestPending = false;
let correctionController;
let correctionRevision = 0;
let lastTrendDragX = 0;
let socketSnapshotRevision = 0;
let programRequestRevision = 0;
let programSelectionRevision = 0;
let feedbackTimer;
let retryProgramRead = null;

const navItems = [
  { key: "dashboard", label: "设备列表", icon: "D" }
];

const deviceNavItems = [
  { key: "monitor", label: "数据监控", icon: "监", scope: "device" },
  { key: "operation", label: "操作设定", icon: "操", scope: "device" },
  { key: "parameters", label: "系统参数", icon: "参", scope: "device" },
  { key: "history", label: "历史记录", icon: "史", scope: "device" },
  { key: "faults", label: "故障查询", icon: "故", scope: "device" }
];

const optionalMonitorCards = [
  { key: "trend", label: "温湿度趋势", icon: "chart" },
  { key: "dut-temperatures", label: "试品温度", icon: "temperature" },
  { key: "user-events", label: "用户事件", icon: "activity" }
];
const dutMonitorCards = Array.from({ length: 24 }, (_, index) => ({
  key: `dut-${index + 1}`,
  number: index + 1
}));
const eventMonitorCards = Array.from({ length: 16 }, (_, index) => ({
  key: `event-${index + 1}`,
  number: index + 1
}));
const defaultMonitorCardKeys = ["trend"];
const operationTabs = [
  { key: "protection", label: "保护设定", description: "安全联锁与阈值", icon: "shield" },
  { key: "setpoint", label: "定值模式", description: "温湿度目标控制", icon: "sliders" },
  { key: "program", label: "程序模式", description: "试验程序与步骤", icon: "play" },
  { key: "other", label: "其他设定", description: "设备偏好与显示", icon: "settings" }
];
const runModeOptions = [
  { value: "1", label: "定值模式", description: "按当前温湿度目标值运行", icon: "sliders" },
  { value: "2", label: "程序模式", description: "按已选择的试验程序运行", icon: "play" }
];
const parameterTabs = [
  { key: "basic", label: "基础信息", description: "设备身份与版本", icon: "settings" },
  { key: "calibration", label: "测量校正", description: "温湿度测量修正", icon: "sliders" },
  { key: "pid", label: "PID 设定", description: "温湿度控制参数", icon: "activity" }
];
const calibrationFields = {
  temperature: [
    { key: "TEMP_Area1", label: "温度区间1", unit: "°C" },
    { key: "TEMP_Area2", label: "温度区间2", unit: "°C" },
    { key: "TEMP_Area3", label: "温度区间3", unit: "°C" },
    { key: "TEMP_Area4", label: "温度区间4", unit: "°C" },
    { key: "TEMP_Corrected1", label: "温度校正1", unit: "°C" },
    { key: "TEMP_Corrected2", label: "温度校正2", unit: "°C" },
    { key: "TEMP_Corrected3", label: "温度校正3", unit: "°C" },
    { key: "TEMP_Corrected4", label: "温度校正4", unit: "°C" },
    { key: "TEMP_Correction", label: "温度定校", unit: "°C" }
  ],
  humidity: [
    { key: "HUMI_Area1", label: "湿度区间1", unit: "%RH" },
    { key: "HUMI_Area2", label: "湿度区间2", unit: "%RH" },
    { key: "HUMI_Area3", label: "湿度区间3", unit: "%RH" },
    { key: "HUMI_Area4", label: "湿度区间4", unit: "%RH" },
    { key: "HUMI_Corrected1", label: "湿度校正1", unit: "%RH" },
    { key: "HUMI_Corrected2", label: "湿度校正2", unit: "%RH" },
    { key: "HUMI_Corrected3", label: "湿度校正3", unit: "%RH" },
    { key: "HUMI_Corrected4", label: "湿度校正4", unit: "%RH" },
    { key: "HUMI_Correction", label: "湿度定校", unit: "%RH" }
  ]
};
const calibrationCards = [
  { key: "temperature", title: "温度", unit: "°C", prefix: "TEMP" },
  { key: "humidity", title: "湿度", unit: "%RH", prefix: "HUMI" }
].map(card => ({
  ...card,
  correction: calibrationFields[card.key][8],
  rows: calibrationFields[card.key].slice(0, 4).map((area, index) => ({
    number: index + 1,
    area,
    corrected: calibrationFields[card.key][index + 4]
  }))
}));
const dutCalibrationGroups = [
  Array.from({ length: 5 }, (_, index) => index + 1),
  Array.from({ length: 5 }, (_, index) => index + 6)
];
const correctionReadingFieldKeys = ["TEMP", "HUMI"].flatMap(prefix =>
  ["Collected", "Corrected", "Final"].map(stage => `${prefix}_${stage}`)
).concat(Array.from({ length: 10 }, (_, index) => ["Collected", "Final"].map(stage => `DUT${index + 1}_${stage}`)).flat());
const correctionFieldKeys = [
  ...calibrationFields.temperature.map(({ key }) => key),
  ...calibrationFields.humidity.map(({ key }) => key),
  ...correctionReadingFieldKeys,
  ...Array.from({ length: 10 }, (_, index) =>
    ["Collected", "Corrected", "Final"].map(stage => `DUT${index + 1}_${stage}`)
  ).flat()
];
const parameterFieldGroups = {
  basic: ["temperatureRangeMax", "temperatureRangeMin", "humidityRangeMax", "humidityRangeMin", "temperatureTransmissionMax", "temperatureTransmissionMin", "compressorFrequency", "circulationFanFrequency", "humidifierFrequency", "frequencyLimit"],
  calibration: correctionFieldKeys.filter(key => !correctionReadingFieldKeys.includes(key)),
  pid: pidSettingFieldKeys
};
const parameterBaselines = ref(Object.fromEntries(Object.values(parameterFieldGroups).flat().map(key => [key, String(parameterForm.value[key])])));
const protectionItems = [
  { key: "air-temperature", label: "空气温度保护", upper: "airTEMP_H", lower: "airTEMP_L" },
  { key: "dut-temperature", label: "试品温度保护", upper: "dutTEMP_H", lower: "dutTEMP_L" },
  { key: "dut-control-air", label: "试品控温空气温度", upper: "dutModeAir_H", lower: "dutModeAir_L" }
];
const controlModes = [
  { key: "precise", label: "精准控制", description: "优先保持目标稳定" },
  { key: "balanced", label: "平衡模式", description: "稳定性与响应速度平衡" },
  { key: "rapid", label: "快速响应", description: "优先快速达到目标" }
];
const titleMap = {
  dashboard: "设备列表",
  profile: "个人中心",
  "device-detail": "设备实时详情",
  memory: "共享内存检查",
  alarms: "报警中心",
  reports: "试验报告",
  settings: "系统设置"
};

const stateTextMap = {
  OFFLINE: "离线",
  IDLE: "空闲",
  READY: "就绪",
  WAIT_LOCAL_CONFIRM: "等待本机确认",
  RUNNING: "运行中",
  HOLDING: "保持中",
  PAUSED: "已暂停",
  COMPLETED: "已完成",
  STOPPED: "已停止",
  STOPPING: "停止中",
  ABORTING: "中止中",
  ALARM: "报警",
  MAINTENANCE: "维护中"
};

const sidebarItems = computed(() => {
  if (activeView.value === "device-detail") return deviceNavItems;
  return navItems;
});
const activeSidebarKey = computed(() => {
  if (activeView.value === "device-detail") return selectedDeviceSection.value;
  return activeView.value;
});
const sidebarIndicator = useSelectionIndicator(sidebarNav, activeSidebarKey);
const operationIndicator = useSelectionIndicator(operationNav, operationTab);
const parameterIndicator = useSelectionIndicator(parameterNav, parameterTab);
const displayModeIndicator = useSelectionIndicator(displayModeNav, deviceDisplayMode);
const notificationIndicator = useSelectionIndicator(notificationNav, notificationTab);
const isPilotWorkspace = computed(() => activeView.value === "device-detail" && ["monitor", "operation"].includes(selectedDeviceSection.value));
const pilotRefresh = computed(() => selectedDeviceSection.value === "operation" ? operationRefresh : monitorRefresh);
const workspaceRefresh = computed(() => {
  if (programRead.state.pending || programRead.state.error) return programRead;
  if (["dashboard", "memory"].includes(activeView.value)) return monitorRefresh;
  if (activeView.value !== "device-detail") return null;
  return ({ monitor: monitorRefresh, operation: operationRefresh, parameters: parameterRefresh, history: historyRefresh })[selectedDeviceSection.value] || null;
});
const workspaceRefreshTitle = computed(() => {
  if (workspaceRefresh.value === programRead) return "正在读取程序";
  if (activeView.value !== "device-detail") return "正在读取实时数据";
  return ({ operation: "正在读取最新设置", parameters: "正在读取系统参数", history: "正在读取历史记录" })[selectedDeviceSection.value] || "正在读取实时数据";
});
const workspaceErrorTitle = computed(() => {
  if (workspaceRefresh.value === programRead) return "程序读取失败";
  if (activeView.value === "device-detail") {
    return ({ operation: "设置读取失败", monitor: "实时数据读取失败", parameters: "参数读取失败", history: "历史记录读取失败" })[selectedDeviceSection.value] || "数据读取失败";
  }
  return activeView.value === "memory" ? "快照读取失败" : "设备数据读取失败";
});
const operationHasDraft = computed(() => Object.keys(operationFieldGroups).some(key => operationSignature(key) !== operationBaselines.value[key]));
const pilotStatusText = computed(() => {
  const state = pilotRefresh.value.state;
  if (state.error) return selectedDeviceSection.value === "operation" ? "设置读取失败" : snapshot.value ? "实时数据暂不可用，保留上次快照" : "等待控制器数据";
  if (selectedDeviceSection.value === "operation") {
    if (operationSaving.value) return "正在保存设置";
    if (operationHasDraft.value) return "未保存的修改已保留";
    return state.updatedAt ? `设置读取于 ${formatRefreshTime(state.updatedAt)}` : "等待读取设置";
  }
  if (connectionText.value !== "已连接" || !selectedDevice.value?.online) return snapshot.value ? "当前为最近一次设备数据" : "等待控制器数据";
  return snapshot.value?.written_at ? `数据时间 ${formatRefreshTime(snapshot.value.written_at * 1000)}` : "等待设备数据";
});
const currentDeviceSectionLabel = computed(() => {
  return deviceNavItems.find(item => item.key === selectedDeviceSection.value)?.label || "数据监控";
});
const currentDeviceSectionDescription = computed(() => {
  const descriptionMap = {
    operation: "这里将用于下发启动、停止、暂停、恢复等操作申请，并等待本机工控端审核确认。",
    parameters: "这里将展示和维护当前试验箱的设备参数、通讯参数、保护阈值和校准信息。",
    history: "这里将查询当前试验箱的历史曲线、运行记录、报警记录和试验批次。",
    faults: "这里将用于查询当前试验箱的故障代码、故障时间、处理状态和维修记录。"
  };
  return descriptionMap[selectedDeviceSection.value] || "这里展示当前试验箱的实时温度、湿度、步骤、报警等运行数据。";
});
const selectedProgram = computed(() => programs.value.find(item => String(item.pro_no) === operationForm.value.programId) || programs.value[0] || null);
const programCalculatedTotalTime = computed(() => calculateProgramTotalTime(programDraft.value));
const programPreviewChart = computed(() => buildProgramPreviewChart(programPreview.value, programChartScrollStart.value));
const selectedDeviceRunningMode = computed(() => {
  const mode = Number(firstDefined(selectedDevice.value?.run_mode, selectedDevice.value?.mainData?.runMode));
  return runModeOptions.find(item => item.value === String(mode))?.label || "未知";
});
const currentTitle = computed(() => {
  if (activeView.value === "device-detail") return currentDeviceSectionLabel.value;
  return titleMap[activeView.value];
});
const selectedDevice = computed(() => {
  return devices.value.find(device => device.device_id === selectedDeviceId.value) || null;
});
const onlineCount = computed(() => devices.value.filter(device => device.online).length);
const runningCount = computed(() => devices.value.filter(device => device.run_state === "RUNNING").length);
const alarmCount = computed(() => devices.value.filter(device => device.run_state === "ALARM" || device.alarm).length);
const sequence = computed(() => snapshot.value?.sequence ?? "--");
const readLatency = computed(() => {
  if (!snapshot.value || !routerReadAt.value || !snapshot.value.written_at) return "--";
  return `${Math.max(0, (routerReadAt.value - snapshot.value.written_at) * 1000).toFixed(0)}ms`;
});

const avgTempDelta = computed(() => averageDelta("current_temperature", "target_temperature"));
const avgHumDelta = computed(() => averageDelta("current_humidity", "target_humidity"));
const payloadUsage = computed(() => {
  const bytes = new Blob([JSON.stringify(snapshot.value || {})]).size;
  return `${(bytes / 1024).toFixed(1)}KB`;
});
const payloadLength = computed(() => payloadUsage.value);
const memoryName = computed(() => "industrial_chamber_realtime_v1");
const memoryTotal = computed(() => "256KB");
const memoryStableText = computed(() => snapshot.value ? "稳定可读" : "等待数据");
const formattedSnapshot = computed(() => JSON.stringify(snapshot.value, null, 2));
const trendAxisLabels = computed(() => {
  const range = getTrendTimeRange(trendClockMs.value);
  return [0, 0.25, 0.5, 0.75, 1].map(ratio => {
    return formatTimeLabel(range.startMs + (range.endMs - range.startMs) * ratio);
  });
});
const trendWindowText = computed(() => {
  const totalSeconds = Math.round(trendWindowMs.value / 1000);
  if (totalSeconds < 60) return `当前窗口 ${totalSeconds} 秒`;
  const minutes = totalSeconds / 60;
  if (minutes < 60) return `当前窗口 ${minutes.toFixed(minutes >= 10 ? 0 : 1)} 分钟`;
  return `当前窗口 ${(minutes / 60).toFixed(1)} 小时`;
});
const runtimeDisplay = computed(() => {
  const device = selectedDevice.value || {};
  const timeData = device.timeData || {};
  return {
    running: formatDurationValue(firstDefined(timeData.runTime, device.running_time, device.run_time, device.elapsed_time, device.elapsed_seconds)),
    setting: formatDurationValue(firstDefined(timeData.setTime, device.setting_time, device.set_time, device.target_time, device.duration_seconds)),
    total: formatDurationValue(firstDefined(timeData.totalTime, device.total_running_time, device.total_run_time, device.total_time, device.total_seconds))
  };
});
const selectedDeviceStartTime = computed(() => {
  return formatStartTimeMinute(deviceStartTimes.value[selectedDeviceId.value] || selectedDevice.value?.timeData?.startTime || "--");
});
const activeRunStates = ["RUNNING", "HOLDING", "PAUSED", "STOPPING", "ABORTING"];
const stoppedRunStates = ["STOPPED", "IDLE", "COMPLETED"];
const selectedRunState = computed(() => String(selectedDevice.value?.run_state || "").toUpperCase());
const isDeviceRunning = computed(() => activeRunStates.includes(selectedRunState.value));
const isDeviceStopped = computed(() => stoppedRunStates.includes(selectedRunState.value));
const activeNotifications = computed(() => {
  if (activeView.value === "device-detail") {
    return operationLogs.value.filter(item => !selectedDeviceId.value || item.deviceId === selectedDeviceId.value);
  }
  return deviceNotifications.value;
});
const historyRangeLabel = computed(() => `${historyQuery.value.startTime.replace("T", " ")} 至 ${historyQuery.value.endTime.replace("T", " ")}`);
const historyRecentItems = computed(() => [...historyItems.value].reverse().slice(0, 50));
const historyChartValues = computed(() => {
  const values = historyItems.value.flatMap(item => [Number(item.temperature), Number(item.humidity)]).filter(Number.isFinite);
  if (!values.length) return { min: 0, max: 100 };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = Math.max((max - min) * 0.12, 1);
  return { min: min - padding, max: max + padding };
});
const historyTempPoints = computed(() => historySeriesPoints("temperature"));
const historyHumPoints = computed(() => historySeriesPoints("humidity"));
const historyGridLines = [20, 82, 144, 206, 268];
const historyXAxis = [58, 288, 518, 748, 978];
const historyYAxisLabels = computed(() => {
  const { min, max } = historyChartValues.value;
  return historyGridLines.map((y, index) => ({ x: 50, y: y + 4, text: formatHistoryNumber(max - (max - min) * index / 4) }));
});
const historyXAxisLabels = computed(() => {
  const times = historyItems.value.map(item => historyTimestamp(item.recorded_at)).filter(Number.isFinite);
  if (!times.length) return [];
  const start = Math.min(...times);
  const end = Math.max(...times);
  return historyXAxis.map((x, index) => ({ x, text: formatHistoryTime(new Date(start + (end - start) * index / 4).toISOString()) }));
});
const selectedDeviceAlarmState = computed(() => {
  const status = selectedDevice.value?.status || {};
  return String(status.state || selectedDevice.value?.status_text || "正常").trim() || "正常";
});
const selectedDeviceAlarmItems = computed(() => {
  const device = selectedDevice.value || {};
  const status = device.status || {};
  const rawAlarms = status.alarm ?? device.alarms ?? device.alarm;
  const alarms = (Array.isArray(rawAlarms) ? rawAlarms : rawAlarms ? [rawAlarms] : [])
    .map(item => String(item).trim())
    .filter(Boolean);
  const statusText = selectedDeviceAlarmState.value;
  if (!alarms.length && ["报警", "故障", "保护", "异常"].some(keyword => statusText.includes(keyword))) {
    alarms.push(statusText);
  }
  return [...new Set(alarms)];
});

watch(() => selectedDevice.value?.timeData?.startTime, startTime => {
  if (!selectedDeviceId.value || !startTime || deviceStartTimes.value[selectedDeviceId.value]) return;
  deviceStartTimes.value = { ...deviceStartTimes.value, [selectedDeviceId.value]: startTime };
}, { immediate: true });
watch(() => props.initialUser, user => {
  if (user?.username) updateSessionUser(user);
}, { deep: true });
const notificationCount = computed(() => activeNotifications.value.length);
const notificationCountText = computed(() => notificationCount.value > 99 ? "99+" : String(notificationCount.value));
const notificationTitle = computed(() => activeView.value === "device-detail" ? "操作日志" : "设备运行通知");
const notificationSubtitle = computed(() => "记录设备启动、停止、断开连接等运行状态变化");
const notificationEmptyTitle = computed(() => activeView.value === "device-detail" ? "暂无操作记录" : "暂无设备通知");
const notificationEmptyText = computed(() => activeView.value === "device-detail" ? "当前设备还没有远程控制操作。" : "设备状态变化会显示在这里。");

function averageDelta(currentKey, targetKey) {
  if (!devices.value.length) return "0.0";
  const total = devices.value.reduce((sum, device) => {
    return sum + Math.abs(Number(device[currentKey] ?? 0) - Number(device[targetKey] ?? 0));
  }, 0);
  return (total / devices.value.length).toFixed(1);
}

function stateLabel(state) {
  return stateTextMap[state] || state || "未知";
}

function stateClass(device) {
  if (device.run_state === "ALARM" || device.alarm) return "alarm";
  if (["STOPPED", "STOPPING", "ABORTING"].includes(device.run_state)) return "stopped";
  if (device.run_state === "IDLE") return "idle";
  if (device.online === false) return "idle";
  return "running";
}

function runStateIcon(state) {
  const iconMap = {
    RUNNING: "play",
    HOLDING: "pause",
    PAUSED: "pause",
    STOPPED: "stop",
    STOPPING: "stop",
    ABORTING: "stop",
    ALARM: "alarms",
    MAINTENANCE: "settings",
    READY: "check",
    COMPLETED: "check",
    IDLE: "gauge"
  };
  return iconMap[String(state || "").toUpperCase()] || "gauge";
}

function formatNumber(value) {
  return Number(value ?? 0).toFixed(1);
}

function formatCalibrationValue(value) {
  const numericValue = Number(value);
  return Number.isFinite(numericValue) ? numericValue.toFixed(2) : "--";
}

function calibrationReadings(card) {
  return [
    { label: "采集值", value: parameterForm.value[`${card.prefix}_Collected`] },
    { label: "修正值", value: parameterForm.value[`${card.prefix}_Corrected`] },
    { label: "最终值", value: parameterForm.value[`${card.prefix}_Final`] }
  ];
}

const dutChannelOffset = computed(() => {
  const dut = selectedDevice.value?.DUT;
  if (!dut || typeof dut !== "object") return 1;
  return Object.prototype.hasOwnProperty.call(dut, "DUT24") ? 0 : 1;
});

function dutValue(cardNumber) {
  const dut = selectedDevice.value?.DUT;
  if (!dut || typeof dut !== "object") return 0;
  const key = `DUT${cardNumber - dutChannelOffset.value}`;
  return dut[key] ?? 0;
}

function dutCalibrationValue(channel, stage) {
  const suffix = stage.charAt(0).toUpperCase() + stage.slice(1);
  return parameterForm.value[`DUT${channel}_${suffix}`];
}

function isDutSelected(cardNumber) {
  const selected = Number(selectedDevice.value?.DUT_SEL ?? selectedDevice.value?.dut_selected);
  if (!Number.isFinite(selected)) return false;
  return cardNumber - dutChannelOffset.value === selected;
}

const eventChannelOffset = computed(() => {
  const events = selectedDevice.value?.event;
  if (!events || typeof events !== "object") return 1;
  return Object.prototype.hasOwnProperty.call(events, "event16") ? 0 : 1;
});

function eventText(eventNumber) {
  const events = selectedDevice.value?.event;
  if (!events || typeof events !== "object") return "--";
  return events[`event${eventNumber - eventChannelOffset.value}`] ?? "--";
}

function eventState(eventNumber) {
  const value = String(eventText(eventNumber)).trim().toUpperCase();
  const separatorIndex = value.lastIndexOf("=");
  return separatorIndex >= 0 ? value.slice(separatorIndex + 1).trim() : value;
}

const selectedDutLabel = computed(() => {
  const selected = Number(selectedDevice.value?.DUT_SEL ?? selectedDevice.value?.dut_selected);
  if (!Number.isFinite(selected)) return "--";
  return `试品温度${selected + dutChannelOffset.value}`;
});

function firstDefined(...values) {
  return values.find(value => value !== undefined && value !== null && value !== "");
}

function formatDurationValue(value) {
  if (value === undefined) return "00:00:00";
  if (typeof value === "string") {
    if (/^\d{1,2}:\d{2}:\d{2}$/.test(value)) return value.padStart(8, "0");
    const numericString = Number(value);
    if (!Number.isNaN(numericString)) return formatDurationSeconds(numericString);
    return value;
  }
  const numericValue = Number(value);
  return Number.isNaN(numericValue) ? "00:00:00" : formatDurationSeconds(numericValue);
}

function formatDurationSeconds(value) {
  const totalSeconds = Math.max(0, Math.floor(value));
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds].map(part => String(part).padStart(2, "0")).join(":");
}

function formatDuration(value) {
  return formatDurationValue(value);
}

function calculateProgramTotalTime(program) {
  const steps = Array.isArray(program?.steps) ? program.steps : [];
  const durations = steps.map(step => {
    const parsed = parseDuration(step.timeText);
    return parsed === null ? Math.max(0, Number(step.time) || 0) : parsed;
  });
  const loopCount = [1, 2, 3, 4].reduce((last, index) => ["start", "end", "times"].some(field => Number(program?.[`loop${index}_${field}`] ?? 0) !== 0) ? index : last, 1);
  let cycleDuration = 0;
  for (let loopIndex = 1; loopIndex <= loopCount; loopIndex += 1) {
    const start = Number(program?.[`loop${loopIndex}_start`]) || 0;
    const end = Number(program?.[`loop${loopIndex}_end`]) || 0;
    const times = Number(program?.[`loop${loopIndex}_times`]) || 0;
    if (start < 1 || end < 1 || times <= 0) continue;
    const first = Math.max(0, Math.min(start, end) - 1);
    const last = Math.min(durations.length - 1, Math.max(start, end) - 1);
    if (last < first) continue;
    cycleDuration += durations.slice(first, last + 1).reduce((sum, value) => sum + value, 0) * times;
  }
  return cycleDuration * Math.max(0, Number(program?.full_cycle) || 0);
}

function buildProgramPreviewChart(program, requestedWindowStart = 0) {
  const PROGRAM_CHART_WINDOW_SECONDS = 2 * 60 * 60;
  const steps = Array.isArray(program?.steps) ? program.steps : [];
  const stepDuration = step => {
    const parsed = parseDuration(step?.timeText);
    return parsed === null ? Math.max(0, Number(step?.time) || 0) : parsed;
  };
  const loopDefinitions = [];
  for (let loopIndex = 1; loopIndex <= 4; loopIndex += 1) {
    const start = Number(program?.[`loop${loopIndex}_start`]) || 0;
    const end = Number(program?.[`loop${loopIndex}_end`]) || 0;
    const times = Number(program?.[`loop${loopIndex}_times`]) || 0;
    if (start < 1 || end < 1 || times <= 0) continue;
    const first = Math.max(0, Math.min(start, end) - 1);
    const last = Math.min(steps.length - 1, Math.max(start, end) - 1);
    if (last < first) continue;
    loopDefinitions.push({ first, last, times });
  }
  const cycleSteps = [];
  if (loopDefinitions.length) {
    let cursor = 0;
    for (const loop of loopDefinitions) {
      cycleSteps.push(...steps.slice(cursor, loop.first));
      for (let repeat = 0; repeat < loop.times; repeat += 1) cycleSteps.push(...steps.slice(loop.first, loop.last + 1));
      cursor = Math.max(cursor, loop.last + 1);
    }
    cycleSteps.push(...steps.slice(cursor));
  } else {
    cycleSteps.push(...steps);
  }
  // ponytail: cap preview expansion at 100 cycles; add downsampling if very
  // large programs need an exact visualisation without rendering thousands of points.
  const cycleCount = Math.min(100, Math.max(1, Number(program?.full_cycle) || 0));
  const timelineSteps = Array.from({ length: cycleCount }, () => cycleSteps).flat();
  if (!timelineSteps.length) return { points: [], series: [], xTicks: [], yTicks: [], totalTime: 0, windowStart: 0, windowEnd: 0, windowDuration: PROGRAM_CHART_WINDOW_SECONDS, maxScroll: 0 };

  const points = [];
  let elapsed = 0;
  timelineSteps.forEach((step, index) => {
    const values = {
      temp: Number(step?.temp) || 0,
      humi: Number(step?.humi) || 0,
      pressure: Number(step?.pressure) || 0
    };
    // Keep each step value flat for its duration.  Adding the next value at
    // the same timestamp creates a vertical jump instead of an interpolated
    // diagonal between two step targets.
    if (index === 0) points.push({ time: 0, ...values });
    else points.push({ time: elapsed, ...values });
    elapsed += stepDuration(step);
    points.push({ time: elapsed, ...values });
  });

  const totalTime = Math.max(0, elapsed);
  const windowDuration = Math.min(PROGRAM_CHART_WINDOW_SECONDS, Math.max(1, totalTime));
  const maxScroll = Math.max(0, totalTime - windowDuration);
  const windowStart = Math.min(maxScroll, Math.max(0, Number(requestedWindowStart) || 0));
  const windowEnd = Math.min(totalTime, windowStart + windowDuration);
  let startIndex = 0;
  points.forEach((point, index) => {
    if (point.time <= windowStart) startIndex = index;
  });
  const visiblePoints = [{ ...points[startIndex], time: windowStart }];
  points.forEach(point => {
    if (point.time > windowStart && point.time < windowEnd) visiblePoints.push(point);
  });
  let endIndex = startIndex;
  points.forEach((point, index) => {
    if (point.time <= windowEnd) endIndex = index;
  });
  visiblePoints.push({ ...points[endIndex], time: windowEnd });

  const values = visiblePoints.flatMap(point => [point.temp, point.humi, point.pressure]);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  let min = Math.floor(rawMin / 10) * 10;
  let max = Math.ceil(rawMax / 10) * 10;
  if (min === max) {
    min -= 10;
    max += 10;
  }
  const maxTime = Math.max(1, windowDuration);
  const plot = { left: 72, right: 866, top: 28, bottom: 322 };
  const xFor = time => plot.left + ((time - windowStart) / maxTime) * (plot.right - plot.left);
  const yFor = value => plot.bottom - ((value - min) / (max - min)) * (plot.bottom - plot.top);
  const series = [
    { key: "temp", label: "温度", unit: "°C", color: "#ef6c67" },
    { key: "humi", label: "湿度", unit: "%RH", color: "#25b887" },
    { key: "pressure", label: "气压", unit: "", color: "#4f8df7" }
  ].map(definition => {
    const coordinates = visiblePoints.map((point, index) => {
      const previous = visiblePoints[index - 1];
      const valueChangedAtBoundary = index > 0 && point.time === previous.time && point[definition.key] !== previous[definition.key];
      return { index, x: xFor(point.time), y: yFor(point[definition.key]), showPoint: index === 0 || index === visiblePoints.length - 1 || valueChangedAtBoundary };
    });
    const segments = coordinates.slice(0, -1).flatMap((point, index) => {
      const next = coordinates[index + 1];
      return next.x > point.x && Math.abs(next.y - point.y) < 0.01
        ? [`${point.x.toFixed(2)},${point.y.toFixed(2)} ${next.x.toFixed(2)},${next.y.toFixed(2)}`]
        : [];
    });
    return { ...definition, coordinates, segments, points: segments.join(" ") };
  });
  const yTicks = [];
  for (let value = max; value >= min; value -= 10) {
    const ratio = (max - value) / (max - min);
    yTicks.push({ value: String(value), label: String(value), y: plot.top + (plot.bottom - plot.top) * ratio });
  }
  const xStep = chooseProgramChartTimeStep(windowDuration);
  const tickCandidates = [{ time: windowStart, priority: 3 }, { time: windowEnd, priority: 3 }];
  for (let offset = xStep; offset < windowDuration; offset += xStep) tickCandidates.push({ time: windowStart + offset, priority: 1 });
  visiblePoints.forEach((point, index) => {
    if (index > 0 && point.time === visiblePoints[index - 1].time) tickCandidates.push({ time: point.time, priority: 2 });
  });
  const minimumLabelGap = 64;
  const xTicks = tickCandidates
    .map(tick => ({ ...tick, x: xFor(tick.time) }))
    .sort((left, right) => right.priority - left.priority || left.time - right.time)
    .reduce((selected, tick) => {
      if (selected.every(item => Math.abs(item.x - tick.x) >= minimumLabelGap)) selected.push(tick);
      return selected;
    }, [])
    .sort((left, right) => left.time - right.time)
    .map(tick => ({ label: formatDuration(tick.time), x: tick.x }));
  return { points: visiblePoints, series, xTicks, yTicks, min, max, maxTime, plot, totalTime, windowStart, windowEnd, windowDuration, maxScroll };
}

function chooseProgramChartTimeStep(totalSeconds) {
  const base = 10 * 60;
  if (totalSeconds <= base * 7) return base;
  const target = totalSeconds / 7;
  const candidates = [base, base * 2, base * 3, base * 6, base * 12, base * 24, base * 72];
  return candidates.find(step => step >= target) || candidates[candidates.length - 1];
}

function formatEventBits(value) {
  return Number(value ?? 0).toString(2).padStart(16, "0");
}

function parseDuration(value) {
  const text = String(value ?? "").trim();
  const match = /^(\d{1,4}):([0-5]\d):([0-5]\d)$/.exec(text);
  if (!match) return null;
  return Number(match[1]) * 3600 + Number(match[2]) * 60 + Number(match[3]);
}

function createProgramStep(stepNo = 1) {
  return { step_no: String(stepNo), timeText: "00:00:00", time: 0, temp: 0, humi: 0, pressure: 0, event_bits: 0, space: 0 };
}

function createProgramDraft(program = null) {
  const source = program || {};
  const steps = Array.isArray(source.steps) && source.steps.length
    ? source.steps.map((step, index) => ({ ...step, step_no: String(index + 1), timeText: formatDuration(step.time) }))
    : [createProgramStep()];
  return {
    pro_no: source.pro_no == null ? null : Number(source.pro_no),
    name: source.name || "",
    total_time: Number(source.total_time ?? 0),
    loop1_start: Number(source.loop1_start ?? 0), loop1_end: Number(source.loop1_end ?? 0), loop1_times: Number(source.loop1_times ?? 0),
    loop2_start: Number(source.loop2_start ?? 0), loop2_end: Number(source.loop2_end ?? 0), loop2_times: Number(source.loop2_times ?? 0),
    loop3_start: Number(source.loop3_start ?? 0), loop3_end: Number(source.loop3_end ?? 0), loop3_times: Number(source.loop3_times ?? 0),
    loop4_start: Number(source.loop4_start ?? 0), loop4_end: Number(source.loop4_end ?? 0), loop4_times: Number(source.loop4_times ?? 0),
    full_cycle: Number(source.full_cycle ?? 0),
    link_no: Number(source.link_no ?? 0),
    loopCount: [1, 2, 3, 4].reduce((last, index) => ["start", "end", "times"].some(field => Number(source[`loop${index}_${field}`] ?? 0) !== 0) ? index : last, 1),
    steps
  };
}

function formatStartTime(value = new Date()) {
  const pad = number => String(number).padStart(2, "0");
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())} ${pad(value.getHours())}:${pad(value.getMinutes())}:${pad(value.getSeconds())}`;
}

function formatStartTimeMinute(value) {
  const text = String(value || "--");
  return /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(text) ? text.slice(0, 16) : text;
}

function makeLogItem({ title, message, tone = "info", deviceId = selectedDeviceId.value }) {
  const now = Date.now();
  return {
    id: `${now}-${Math.random().toString(16).slice(2)}`,
    title,
    message,
    tone,
    deviceId,
    time: now,
    timeText: new Date(now).toLocaleTimeString("zh-CN", { hour12: false })
  };
}

function trimLogs(items, limit = 80) {
  return items.slice(0, limit);
}

function addDeviceNotification(item) {
  deviceNotifications.value = trimLogs([makeLogItem(item), ...deviceNotifications.value]);
}

function addOperationLog(item) {
  operationLogs.value = trimLogs([makeLogItem(item), ...operationLogs.value]);
}

function updateDeviceNotifications(deviceList) {
  const previous = previousDeviceStates.value;
  const next = {};

  deviceList.forEach(device => {
    const deviceId = device.device_id;
    const name = device.name || deviceId;
    const state = {
      online: Boolean(device.online),
      runState: device.run_state || "UNKNOWN"
    };
    const oldState = previous[deviceId];

    if (!oldState) {
      addDeviceNotification({
        title: name,
        message: `${name} 当前状态：${state.online ? stateLabel(state.runState) : "离线"}`,
        tone: state.online ? stateTone(state.runState) : "danger",
        deviceId
      });
    } else {
      if (oldState.online !== state.online) {
        addDeviceNotification({
          title: name,
          message: `${name} ${state.online ? "恢复连接" : "断开连接"}`,
          tone: state.online ? "success" : "danger",
          deviceId
        });
      }
      if (oldState.runState !== state.runState) {
        addDeviceNotification({
          title: name,
          message: `${name} 由${stateLabel(oldState.runState)}变为${stateLabel(state.runState)}`,
          tone: stateTone(state.runState),
          deviceId
        });
      }
    }

    next[deviceId] = state;
  });

  previousDeviceStates.value = next;
}

function stateTone(runState) {
  if (runState === "ALARM" || ["STOPPED", "STOPPING", "ABORTING", "OFFLINE"].includes(runState)) return "danger";
  if (runState === "HOLDING" || runState === "PAUSED" || runState === "WAIT_LOCAL_CONFIRM") return "warning";
  if (runState === "RUNNING" || runState === "READY" || runState === "COMPLETED") return "success";
  return "info";
}

function formatSnapshotTime(value) {
  if (!value) return "--";
  const numericValue = Number(value);
  const date = new Date(numericValue < 100000000000 ? numericValue * 1000 : numericValue);
  return Number.isNaN(date.getTime()) ? "--" : date.toLocaleTimeString("zh-CN", { hour12: false });
}

function toggleMonitorCard(cardKey) {
  const current = visibleMonitorCards.value;
  visibleMonitorCards.value = current.includes(cardKey)
    ? current.filter(key => key !== cardKey)
    : [...current, cardKey];
  saveMonitorLayout();
  nextTick(drawSelectedTrend);
}

function saveMonitorLayout() {
  window.localStorage.setItem(MONITOR_LAYOUT_STORAGE_KEY, JSON.stringify(visibleMonitorCards.value));
}

function loadMonitorLayout() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(MONITOR_LAYOUT_STORAGE_KEY) || "null");
    if (Array.isArray(saved)) {
      const allowed = new Set(optionalMonitorCards.map(card => card.key));
      visibleMonitorCards.value = saved.filter(key => allowed.has(key));
    }
  } catch {
    visibleMonitorCards.value = [...defaultMonitorCardKeys];
  }
}

function openDeviceDetail(deviceId) {
  selectedDeviceId.value = deviceId;
  const device = devices.value.find(item => item.device_id === deviceId);
  parameterForm.value.deviceName = device?.name || "";
  selectedDeviceSection.value = "monitor";
  activeView.value = "device-detail";
}

function returnToDashboard() {
  activeView.value = "dashboard";
  isSidebarCollapsed.value = false;
}

function openProfile() {
  activeView.value = "profile";
  isSidebarCollapsed.value = false;
}

function updateSessionUser(user) {
  sessionUser.value = { ...user };
  window.localStorage.setItem("industrial-auth-user", JSON.stringify(sessionUser.value));
}

function returnToMonitoring() {
  selectedDeviceSection.value = "monitor";
  activeView.value = "device-detail";
  isSidebarCollapsed.value = false;
}

function forceLogout() {
  window.localStorage.removeItem("industrial-auth-token");
  window.localStorage.removeItem("industrial-auth-user");
  emit("logout");
}

async function logoutToLogin() {
  try {
    await fetch("/api/auth/logout", { method: "POST", headers: authHeaders() });
  } catch {
  } finally {
    forceLogout();
  }
}

function authHeaders() {
  const token = window.localStorage.getItem("industrial-auth-token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function formatRefreshTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString("zh-CN", { hour12: false });
}

function operationSignature(group) {
  return JSON.stringify(operationFieldGroups[group].map(key => String(operationForm.value[key] ?? "")));
}

function markOperationSaved(groups = Object.keys(operationFieldGroups)) {
  for (const group of groups) operationBaselines.value[group] = operationSignature(group);
}

function applyRefreshedOperationData({ fixed, operation, retention, programList }) {
  // Refresh clean groups while keeping in-session edits intact across navigation.
  const drafts = Object.fromEntries(Object.entries(operationFieldGroups)
    .filter(([group]) => operationSignature(group) !== operationBaselines.value[group])
    .flatMap(([, keys]) => keys.map(key => [key, operationForm.value[key]])));
  applyFixedValueSettings(fixed.value);
  applyOperationSettings(operation.value);
  operationForm.value.historyRetentionDays = Number(retention.retention_days || 90);
  const cleanGroups = Object.keys(operationFieldGroups)
    .filter(group => !operationFieldGroups[group].some(key => Object.hasOwn(drafts, key)));
  markOperationSaved(cleanGroups);
  Object.assign(operationForm.value, drafts);
  if (programList) applyProgramList(programList);
}

async function readPageJson(url, signal) {
  const response = await fetch(url, { headers: authHeaders(), signal, cache: "no-store" });
  if (response.status === 401) {
    // P0-8: an expired or revoked session must leave the dashboard instead of
    // showing a read error on a page nobody can operate.
    forceLogout();
    throw new Error("登录已失效，请重新登录");
  }
  if (!response.ok) throw new Error("暂时无法读取，请检查连接后重试");
  return response.json();
}

function refreshOperationData() {
  if (operationSaving.value) return;
  const includePrograms = selectedDeviceSection.value === "operation" && operationTab.value === "program";
  if (includePrograms) programRequestRevision += 1;
  return operationRefresh.run(async signal => {
    const [fixed, operation, retention, programList] = await Promise.all([
      readPageJson("/api/settings/fixed-value", signal),
      readPageJson("/api/settings/operation", signal),
      readPageJson("/api/settings/history-retention", signal),
      includePrograms ? fetchProgramList(signal) : Promise.resolve(null)
    ]);
    return { fixed, operation, retention, programList };
  }, applyRefreshedOperationData);
}

function refreshPilotPage() {
  monitorRefresh.cancel();
  operationRefresh.cancel();
  if (activeView.value === "device-detail" && selectedDeviceSection.value === "operation") {
    refreshOperationData();
    return;
  }
  if (!["dashboard", "memory"].includes(activeView.value) && !(isPilotWorkspace.value && selectedDeviceSection.value === "monitor")) return;
  const socketRevision = socketSnapshotRevision;
  monitorRefresh.run(async signal => {
    try {
      return await readPageJson("/api/memory/snapshot", signal);
    } catch (error) {
      if (socketSnapshotRevision !== socketRevision) return null;
      throw error;
    }
  }, value => {
    // The live stream can advance while the HTTP snapshot is in flight.
    if (!value || socketSnapshotRevision !== socketRevision) return;
    if (Number(value.written_at || 0) < Number(snapshot.value?.written_at || 0)) return;
    snapshot.value = value;
    devices.value = value.devices || [];
    if (!devices.value.some(device => device.device_id === selectedDeviceId.value)) {
      selectedDeviceId.value = devices.value[0]?.device_id || null;
    }
    updateDeviceNotifications(devices.value);
    drawSelectedTrend();
  });
  if (isPilotWorkspace.value) refreshOperationData();
}

function refreshWorkspace() {
  monitorRefresh.cancel();
  operationRefresh.cancel();
  parameterRefresh.cancel();
  historyRefresh.cancel();
  programRead.cancel();
  programRead.state.error = "";
  retryProgramRead = null;
  programSelectionRevision += 1;
  programRequestRevision += 1;
  if (activeView.value === "device-detail" && selectedDeviceSection.value === "parameters") loadParameterSettings();
  else if (activeView.value === "device-detail" && selectedDeviceSection.value === "history") {
    if (historyQuery.value.range !== "custom") updateHistoryRange();
    loadEnvironmentalHistory();
  } else refreshPilotPage();
}

function retryWorkspace() {
  if (programRead.state.error && retryProgramRead) retryProgramRead();
  else refreshWorkspace();
}

function dismissWorkspaceRefresh() {
  workspaceRefresh.value?.dismissError?.();
}

function prepareWorkspaceLeave(element) {
  element.inert = true;
}

function finishWorkspaceEnter() {
  drawSelectedTrend();
}

function prepareTabLeave(element) {
  element.inert = true;
  const editor = element.parentElement;
  if (window.innerWidth <= 760) editor.style.minHeight = `${editor.offsetHeight}px`;
}

function finishTabEnter(element) {
  element.parentElement.style.minHeight = "";
}

function openSaveConfirm(target) {
  if (target === "parameters" && (parameterRefresh.state.pending || parameterRefresh.state.error || parameterSaving.value)) return;
  if (target !== "parameters" && (operationRefresh.state.pending || operationRefresh.state.error || operationSaving.value)) return;
  pendingSaveTarget.value = target;
  isSaveConfirmOpen.value = true;
}

function closeSaveConfirm() {
  isSaveConfirmOpen.value = false;
  pendingSaveTarget.value = null;
}

function normalizeEventCode(value) {
  const text = String(value ?? "").trim();
  return /^[01]{1,16}$/.test(text) ? text.padStart(16, "0") : "0000000000000000";
}

function openEventDialog() {
  eventDialogStepIndex.value = null;
  eventDraft.value = normalizeEventCode(operationForm.value.eventCode);
  isEventDialogOpen.value = true;
}

function openProgramStepEventDialog(index) {
  const step = programDraft.value.steps[index];
  if (!step) return;
  eventDialogStepIndex.value = index;
  eventDraft.value = normalizeEventCode(formatEventBits(step.event_bits));
  isEventDialogOpen.value = true;
}

function cancelEventDialog() {
  isEventDialogOpen.value = false;
  eventDialogStepIndex.value = null;
}

function toggleEvent(index) {
  if (index < 0 || index >= 16) return;
  const bits = eventDraft.value.split("");
  bits[index] = bits[index] === "1" ? "0" : "1";
  eventDraft.value = bits.join("");
}

function confirmEventDialog() {
  if (eventDialogStepIndex.value === null) {
    operationForm.value.eventCode = eventDraft.value;
  } else {
    const step = programDraft.value.steps[eventDialogStepIndex.value];
    if (step) step.event_bits = parseInt(eventDraft.value, 2) || 0;
  }
  isEventDialogOpen.value = false;
  eventDialogStepIndex.value = null;
}

function confirmSaveSettings() {
  const target = pendingSaveTarget.value;
  closeSaveConfirm();
  if (target === "operation") saveOperationSettings();
  if (target === "other") saveOtherSettings();
  if (target === "parameters") saveParameterSettings();
}

async function fetchProgramList(signal) {
  const result = await readPageJson("/api/programs", signal);
  const summaries = Array.isArray(result.programs) ? result.programs : [];
  return Promise.all(summaries.map(async summary => {
    try {
      const detail = await readPageJson(`/api/programs/${encodeURIComponent(summary.pro_no)}`, signal);
      return { ...summary, display_total_time: detail.program ? calculateProgramTotalTime(detail.program) : null };
    } catch (error) {
      if (signal?.aborted) throw error;
      return { ...summary, display_total_time: null };
    }
  }));
}

function applyProgramList(list, selectFirst = true) {
  programs.value = list;
  if (!list.length) {
    operationForm.value.programId = "";
    selectedProgramDetail.value = null;
    return;
  }
  if (selectFirst && !list.some(item => String(item.pro_no) === operationForm.value.programId)) {
    operationForm.value.programId = String(list[0].pro_no);
  }
}

async function loadPrograms(selectFirst = true) {
  const revision = ++programRequestRevision;
  try {
    const list = await fetchProgramList();
    if (revision !== programRequestRevision) return;
    applyProgramList(list, selectFirst);
    if (operationForm.value.programId) await selectProgram(Number(operationForm.value.programId), true);
  } catch (error) {
    if (revision !== programRequestRevision) return;
    if (operationTab.value === "program") operationFeedback.value = `程序读取失败：${error.message || "数据库不可用"}`;
  }
}

async function selectProgram(proNo, quiet = false) {
  const number = Number(proNo);
  if (!Number.isFinite(number)) return;
  operationForm.value.programId = String(number);
  if (!quiet) return readProgram(number, program => { selectedProgramDetail.value = program; });
  const revision = ++programSelectionRevision;
  try {
    const response = await fetch(`/api/programs/${encodeURIComponent(number)}`, { headers: authHeaders() });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "程序读取失败");
    if (revision === programSelectionRevision) selectedProgramDetail.value = normalizeProgramDetail(result.program);
  } catch (error) {
    if (revision !== programSelectionRevision) return;
    selectedProgramDetail.value = null;
    operationFeedback.value = `程序读取失败：${error.message || "数据库不可用"}`;
  }
}

function readProgram(proNo, apply) {
  retryProgramRead = () => readProgram(proNo, apply);
  return programRead.run(async signal => {
    const result = await readPageJson(`/api/programs/${encodeURIComponent(proNo)}`, signal);
    const program = normalizeProgramDetail(result.program);
    if (!program) throw new Error("程序不存在，请刷新列表");
    return program;
  }, apply);
}

function normalizeProgramDetail(program) {
  if (!program) return null;
  const normalized = { ...program, steps: (program.steps || []).map((step, index) => ({ ...step, step_no: String(index + 1) })) };
  // The UI derives runtime from step durations and loop configuration.  The
  // persisted total_time remains a database value, but is not used as the
  // display source so stale records cannot make the list/preview misleading.
  normalized.display_total_time = calculateProgramTotalTime(normalized);
  return normalized;
}

async function openProgramPreview(proNo) {
  return readProgram(proNo, program => {
    programPreview.value = program;
    programChartCursor.value = null;
    programChartScrollStart.value = 0;
    isProgramPreviewOpen.value = true;
  });
}

function closeProgramPreview() {
  isProgramPreviewOpen.value = false;
  programChartCursor.value = null;
  programChartScrollStart.value = 0;
  isProgramChartPointerDown.value = false;
}

function updateProgramChartCursor(clientX, svg) {
  const chart = programPreviewChart.value;
  const coordinates = chart.series[0]?.coordinates || [];
  if (!coordinates.length) return;
  if (!svg) return;
  const rect = svg.getBoundingClientRect();
  const viewBoxX = ((clientX - rect.left) / Math.max(1, rect.width)) * 900;
  const plotWidth = chart.plot.right - chart.plot.left;
  const cursorX = Math.min(chart.plot.right, Math.max(chart.plot.left, viewBoxX));
  const cursorTime = chart.windowStart + ((cursorX - chart.plot.left) / plotWidth) * chart.windowDuration;
  let pointIndex = 0;
  chart.points.forEach((candidate, index) => {
    if (candidate.time <= cursorTime) pointIndex = index;
  });
  const point = chart.points[pointIndex];
  if (!point) return;
  const values = Object.fromEntries(chart.series.map(series => {
    const value = Number(point[series.key]) || 0;
    const y = chart.plot.bottom - ((value - chart.min) / (chart.max - chart.min)) * (chart.plot.bottom - chart.plot.top);
    return [series.key, { y, label: value.toFixed(1) }];
  }));
  const x = cursorX;
  programChartCursor.value = {
    x,
    timeLabel: formatDuration(cursorTime),
    tooltipX: Math.min(682, Math.max(78, x + 12)),
    values
  };
}

function handleProgramChartPointerMove(event) {
  updateProgramChartCursor(event.clientX, event.currentTarget);
}

function handleProgramChartPointerLeave() {
  if (!isProgramChartPointerDown.value) programChartCursor.value = null;
}

function handleProgramChartPointerDown(event) {
  isProgramChartPointerDown.value = true;
  event.currentTarget?.setPointerCapture?.(event.pointerId);
  updateProgramChartCursor(event.clientX, event.currentTarget);
}

function handleProgramChartPointerUp(event) {
  isProgramChartPointerDown.value = false;
  event.currentTarget?.releasePointerCapture?.(event.pointerId);
}

async function openProgramEditor(proNo = null) {
  programFeedback.value = "";
  if (proNo !== null && proNo !== undefined && proNo !== "") {
    return readProgram(proNo, program => {
      programDraft.value = createProgramDraft(program);
      programEditorMode.value = "edit";
      isProgramEditorOpen.value = true;
    });
  } else {
    programRead.cancel();
    programRead.state.error = "";
    programDraft.value = createProgramDraft({ pro_no: null });
    programEditorMode.value = "create";
  }
  isProgramEditorOpen.value = true;
}

function closeProgramEditor() {
  if (programSaving.value) return;
  isProgramEditorOpen.value = false;
  programFeedback.value = "";
}

function addProgramStep() {
  programDraft.value.steps.push(createProgramStep(programDraft.value.steps.length + 1));
}

function removeProgramStep(index) {
  if (programDraft.value.steps.length <= 1) return;
  programDraft.value.steps.splice(index, 1);
}

function addProgramLoop() {
  if (programDraft.value.loopCount >= 4) return;
  programDraft.value.loopCount += 1;
}

function removeProgramLoop(loopIndex) {
  const count = programDraft.value.loopCount;
  if (count <= 1 || loopIndex < 1 || loopIndex > count) return;
  for (let index = loopIndex; index < count; index += 1) {
    for (const field of ["start", "end", "times"]) {
      programDraft.value[`loop${index}_${field}`] = Number(programDraft.value[`loop${index + 1}_${field}`]) || 0;
    }
  }
  for (const field of ["start", "end", "times"]) programDraft.value[`loop${count}_${field}`] = 0;
  programDraft.value.loopCount = count - 1;
}

async function saveProgram() {
  programFeedback.value = "";
  const draft = programDraft.value;
  if (!String(draft.name || "").trim()) {
    programFeedback.value = "请输入程序名称";
    return;
  }
  const steps = [];
  const seenStepNumbers = new Set();
  for (const [index, step] of draft.steps.entries()) {
    const stepNo = String(index + 1);
    const seconds = parseDuration(step.timeText);
    if (seconds === null) {
      programFeedback.value = `步骤 ${stepNo} 的时间格式应为时:分:秒`;
      return;
    }
    seenStepNumbers.add(stepNo);
    steps.push({ step_no: stepNo, time: seconds, temp: Number(step.temp) || 0, humi: Number(step.humi) || 0, pressure: Number(step.pressure) || 0, event_bits: Math.min(65535, Math.max(0, Number(step.event_bits) || 0)), space: Number(step.space) || 0 });
  }
  const payload = {
    pro_no: draft.pro_no == null ? null : Number(draft.pro_no), name: String(draft.name).trim(), total_time: programCalculatedTotalTime.value,
    loop1_start: Number(draft.loop1_start) || 0, loop1_end: Number(draft.loop1_end) || 0, loop1_times: Number(draft.loop1_times) || 0,
    loop2_start: Number(draft.loop2_start) || 0, loop2_end: Number(draft.loop2_end) || 0, loop2_times: Number(draft.loop2_times) || 0,
    loop3_start: Number(draft.loop3_start) || 0, loop3_end: Number(draft.loop3_end) || 0, loop3_times: Number(draft.loop3_times) || 0,
    loop4_start: Number(draft.loop4_start) || 0, loop4_end: Number(draft.loop4_end) || 0, loop4_times: Number(draft.loop4_times) || 0,
    full_cycle: Number(draft.full_cycle) || 0, link_no: Number(draft.link_no) || 0, steps
  };
  programSaving.value = true;
  try {
    const path = programEditorMode.value === "create" ? "/api/programs" : `/api/programs/${encodeURIComponent(payload.pro_no)}`;
    const response = await fetch(path, { method: programEditorMode.value === "create" ? "POST" : "PUT", headers: { "Content-Type": "application/json", ...authHeaders() }, body: JSON.stringify(payload) });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "程序保存失败");
    const savedProgram = result.program || {};
    operationForm.value.programId = String(savedProgram.pro_no ?? payload.pro_no);
    isProgramEditorOpen.value = false;
    operationFeedback.value = "程序已保存到数据库";
    await loadPrograms(false);
  } catch (error) {
    programFeedback.value = error.message || "程序保存失败";
  } finally {
    programSaving.value = false;
  }
}

function deleteProgram(proNo) {
  pendingDeleteProgram.value = proNo;
}

async function confirmDeleteProgram() {
  const proNo = pendingDeleteProgram.value;
  if (proNo === null) return;
  pendingDeleteProgram.value = null;
  try {
    const response = await fetch(`/api/programs/${encodeURIComponent(proNo)}`, { method: "DELETE", headers: authHeaders() });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "程序删除失败");
    await loadPrograms(true);
    operationFeedback.value = "程序已删除";
  } catch (error) {
    operationFeedback.value = `程序删除失败：${error.message || "数据库不可用"}`;
  }
}

function handleSidebarSelect(item) {
  if (item.scope === "device") {
    selectedDeviceSection.value = item.key;
    return;
  }
  activeView.value = item.key;
}

async function saveOperationSettings() {
  if (operationSaving.value || operationRefresh.state.pending || operationRefresh.state.error) return;
  operationSaving.value = true;
  operationRefresh.cancel();
  window.clearTimeout(feedbackTimer);
  const savedTab = operationTab.value;
  operationFeedback.value = "保存中…";
  const payload = {
    temperature_target: Number(operationForm.value.targetTemp),
    temperature_slope: Number(operationForm.value.tempRamp),
    humidity_target: Number(operationForm.value.targetHum),
    humidity_slope: Number(operationForm.value.humRamp),
    runtime_hours: Number(operationForm.value.runtimeHours),
    runtime_minutes: Number(operationForm.value.runtimeMinutes),
    runtime_seconds: Number(operationForm.value.runtimeSeconds)
  };
  const protectionPayload = {
    airTEMP_H: Number(operationForm.value.airTEMP_H),
    airTEMP_L: Number(operationForm.value.airTEMP_L),
    dutTEMP_H: Number(operationForm.value.dutTEMP_H),
    dutTEMP_L: Number(operationForm.value.dutTEMP_L),
    dutModeAir_H: Number(operationForm.value.dutModeAir_H),
    dutModeAir_L: Number(operationForm.value.dutModeAir_L)
  };
  const selectedDutSensor = Number(String(operationForm.value.dutTemperatureSource || "dut1").replace(/^dut/, "")) - 1;
  const eventBits = normalizeEventCode(operationForm.value.eventCode);
  const otherPayload = {
    dutControl: operationForm.value.temperatureControlMode === "dut" ? 1 : 0,
    dutSel: Math.min(7, Math.max(0, Number.isFinite(selectedDutSensor) ? selectedDutSensor : 0)),
    waitTEMP: Number(operationForm.value.waitTemperatureUpper),
    waitHUMI: Number(operationForm.value.waitHumidityUpper),
    event: Number.parseInt(eventBits, 2) || 0,
    powerRestoration: ({ stop: 0, cold: 1, warm: 2 })[operationForm.value.powerOnMode] ?? 0,
    afterShutdow: ({ reset: 0, continue: 1 })[operationForm.value.stopResumeMode] ?? 0
  };
  try {
    const shouldNotifyFixedValue = savedTab === "setpoint";
    const shouldNotifyOperation = savedTab === "protection" || savedTab === "other";
    const response = await fetch(`/api/settings/fixed-value?notify_memory=${shouldNotifyFixedValue}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "数据库保存失败");
    applyFixedValueSettings(result.value || payload);
    markOperationSaved(["setpoint"]);
    const protectionResponse = await fetch(`/api/settings/operation?notify_memory=${shouldNotifyOperation}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ ...protectionPayload, ...otherPayload })
    });
    const protectionResult = await protectionResponse.json().catch(() => ({}));
    if (!protectionResponse.ok) throw new Error(protectionResult.detail || "保护设定保存失败");
    applyOperationSettings(protectionResult.value || protectionPayload);
    markOperationSaved(["protection", "other"]);
    operationLastSaved.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    operationFeedback.value = "已保存到数据库";
    addOperationLog({ title: "保存操作设定", message: `${selectedDevice.value?.name || selectedDeviceId.value} 已更新${operationTabs.find(item => item.key === savedTab)?.label || "操作设定"}`, tone: "success" });
  } catch (error) {
    operationFeedback.value = `保存失败：${error.message || "数据库不可用"}`;
  }
  operationSaving.value = false;
  feedbackTimer = window.setTimeout(() => { operationFeedback.value = ""; }, 3000);
}

async function saveOtherSettings() {
  if (operationSaving.value || operationRefresh.state.pending || operationRefresh.state.error) return;
  operationSaving.value = true;
  operationRefresh.cancel();
  window.clearTimeout(feedbackTimer);
  operationFeedback.value = "保存中…";
  const selectedDutSensor = Number(String(operationForm.value.dutTemperatureSource || "dut1").replace(/^dut/, "")) - 1;
  const eventBits = normalizeEventCode(operationForm.value.eventCode);
  const payload = {
    dutControl: operationForm.value.temperatureControlMode === "dut" ? 1 : 0,
    dutSel: Math.min(7, Math.max(0, Number.isFinite(selectedDutSensor) ? selectedDutSensor : 0)),
    waitTEMP: Number(operationForm.value.waitTemperatureUpper),
    waitHUMI: Number(operationForm.value.waitHumidityUpper),
    history_retention_days: Number(operationForm.value.historyRetentionDays),
    event: Number.parseInt(eventBits, 2) || 0,
    powerRestoration: ({ stop: 0, cold: 1, warm: 2 })[operationForm.value.powerOnMode] ?? 0,
    afterShutdow: ({ reset: 0, continue: 1 })[operationForm.value.stopResumeMode] ?? 0
  };
  try {
    const response = await fetch("/api/settings/operation/other", {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "其他设定保存失败");
    applyOperationSettings(result.value || payload);
    markOperationSaved(["other", "retention"]);
    operationLastSaved.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    operationFeedback.value = "已保存到数据库并通知应用层";
    addOperationLog({ title: "保存其他设定", message: `${selectedDevice.value?.name || selectedDeviceId.value} 已更新其他设定`, tone: "success" });
  } catch (error) {
    operationFeedback.value = `保存失败：${error.message || "数据库不可用"}`;
  }
  operationSaving.value = false;
  feedbackTimer = window.setTimeout(() => { operationFeedback.value = ""; }, 3000);
}

function applyOperationSettings(value) {
  if (!value) return;
  const dutSelection = Number(value.dutSel);
  const dutIndex = Number.isFinite(dutSelection) ? Math.min(7, Math.max(0, dutSelection)) + 1 : 1;
  operationForm.value = {
    ...operationForm.value,
    airTEMP_H: value.airTEMP_H == null ? operationForm.value.airTEMP_H : Number(value.airTEMP_H),
    airTEMP_L: value.airTEMP_L == null ? operationForm.value.airTEMP_L : Number(value.airTEMP_L),
    dutTEMP_H: value.dutTEMP_H == null ? operationForm.value.dutTEMP_H : Number(value.dutTEMP_H),
    dutTEMP_L: value.dutTEMP_L == null ? operationForm.value.dutTEMP_L : Number(value.dutTEMP_L),
    dutModeAir_H: value.dutModeAir_H == null ? operationForm.value.dutModeAir_H : Number(value.dutModeAir_H),
    dutModeAir_L: value.dutModeAir_L == null ? operationForm.value.dutModeAir_L : Number(value.dutModeAir_L),
    temperatureControlMode: value.dutControl == null ? operationForm.value.temperatureControlMode : (Number(value.dutControl) === 1 ? "dut" : "air"),
    dutTemperatureSource: value.dutSel == null ? operationForm.value.dutTemperatureSource : `dut${dutIndex}`,
    waitTemperatureUpper: value.waitTEMP == null ? operationForm.value.waitTemperatureUpper : Number(value.waitTEMP),
    waitHumidityUpper: value.waitHUMI == null ? operationForm.value.waitHumidityUpper : Number(value.waitHUMI),
    historyRetentionDays: value.history_retention_days == null ? operationForm.value.historyRetentionDays : Number(value.history_retention_days),
    eventCode: value.event == null ? operationForm.value.eventCode : Number(value.event).toString(2).padStart(16, "0"),
    powerOnMode: value.powerRestoration == null ? operationForm.value.powerOnMode : (({ 0: "stop", 1: "cold", 2: "warm" })[Number(value.powerRestoration)] || operationForm.value.powerOnMode),
    stopResumeMode: value.afterShutdow == null ? operationForm.value.stopResumeMode : (({ 0: "reset", 1: "continue" })[Number(value.afterShutdow)] || operationForm.value.stopResumeMode)
  };
}

function applyFixedValueSettings(value) {
  if (!value) return;
  operationForm.value = {
    ...operationForm.value,
    targetTemp: Number(value.temperature_target),
    tempRamp: Number(value.temperature_slope),
    targetHum: Number(value.humidity_target),
    humRamp: Number(value.humidity_slope),
    runtimeHours: Number(value.runtime_hours),
    runtimeMinutes: Number(value.runtime_minutes),
    runtimeSeconds: Number(value.runtime_seconds)
  };
}

function loadParameterSettings() {
  if (parameterSaving.value) return;
  const group = parameterTab.value;
  const endpoint = { basic: "system-basic", calibration: "correction", pid: "pid" }[group];
  return parameterRefresh.run(signal => readPageJson(`/api/settings/${endpoint}`, signal), result => {
    const drafts = Object.fromEntries(parameterFieldGroups[group]
      .filter(key => String(parameterForm.value[key]) !== parameterBaselines.value[key])
      .map(key => [key, parameterForm.value[key]]));
    if (group === "basic") applySystemBasicSettings(result.value);
    else if (group === "pid") applyPidSettings(result.value);
    else applyCorrectionSettings(result.value);
    markParametersSaved(group);
    Object.assign(parameterForm.value, drafts);
  });
}

function markParametersSaved(group) {
  for (const key of parameterFieldGroups[group]) parameterBaselines.value[key] = String(parameterForm.value[key]);
}

function toDateTimeInput(timestamp) {
  const date = new Date(timestamp);
  const pad = value => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function applyHistoryRange() {
  if (historyQuery.value.range === "custom") return;
  updateHistoryRange();
  loadEnvironmentalHistory();
}

function updateHistoryRange() {
  const durations = { "1h": 60 * 60 * 1000, "6h": 6 * 60 * 60 * 1000, "24h": 24 * 60 * 60 * 1000, "7d": 7 * 24 * 60 * 60 * 1000 };
  const end = Date.now();
  historyQuery.value.startTime = toDateTimeInput(end - (durations[historyQuery.value.range] || durations["24h"]));
  historyQuery.value.endTime = toDateTimeInput(end);
}

function historyTimestamp(value) {
  if (value == null) return NaN;
  const text = String(value).trim().replace(" ", "T");
  const timestamp = Date.parse(/Z$|[+-]\d\d:?\d\d$/.test(text) ? text : `${text}Z`);
  return Number.isFinite(timestamp) ? timestamp : NaN;
}

function formatHistoryTime(value) {
  const timestamp = historyTimestamp(value);
  return Number.isFinite(timestamp) ? new Date(timestamp).toLocaleString("zh-CN", { hour12: false }) : "--";
}

function formatHistoryNumber(value) {
  return value == null || value === "" || !Number.isFinite(Number(value)) ? "--" : Number(value).toFixed(2);
}

function historyRunStateLabel(value) {
  return stateTextMap[String(value || "").toUpperCase()] || value || "--";
}

function historySeriesPoints(field) {
  const items = historyItems.value;
  if (!items.length) return "";
  const times = items.map(item => historyTimestamp(item.recorded_at));
  const validTimes = times.filter(Number.isFinite);
  const start = Math.min(...validTimes);
  const end = Math.max(...validTimes);
  const range = Math.max(end - start, 1);
  const { min, max } = historyChartValues.value;
  return items.map((item, index) => {
    const time = times[index];
    const value = Number(item[field]);
    if (!Number.isFinite(time) || !Number.isFinite(value)) return null;
    const x = 58 + ((time - start) / range) * 920;
    const y = 268 - ((value - min) / Math.max(max - min, 1)) * 248;
    return `${x.toFixed(1)},${Math.max(20, Math.min(268, y)).toFixed(1)}`;
  }).filter(Boolean).join(" ");
}

async function loadEnvironmentalHistory() {
  if (!selectedDeviceId.value) return;
  return historyRefresh.run(async signal => {
    const start = new Date(historyQuery.value.startTime).getTime();
    const end = new Date(historyQuery.value.endTime).getTime();
    if (!Number.isFinite(start) || !Number.isFinite(end) || end <= start) throw new Error("请选择有效的时间范围");
    const params = new URLSearchParams({ device_id: selectedDeviceId.value, start_time: String(start / 1000), end_time: String(end / 1000), limit: "20000" });
    if (historyQuery.value.runState) params.set("run_state", historyQuery.value.runState);
    return readPageJson(`/api/environmental-history?${params}`, signal);
  }, result => {
    historyItems.value = Array.isArray(result.items) ? result.items : [];
  });
}

function applyPidSettings(value) {
  if (!value) return;
  for (const key of pidSettingFieldKeys) {
    if (value[key] != null) parameterForm.value[key] = Number(value[key]);
  }
}

function pidPayload() {
  return Object.fromEntries(
    pidSettingFieldKeys.map(key => [key, Number(parameterForm.value[key])])
  );
}

async function loadCorrectionSettings() {
  if (correctionRequestPending || parameterRefresh.state.pending || parameterSaving.value) return;
  correctionRequestPending = true;
  const revision = correctionRevision;
  const controller = new AbortController();
  correctionController = controller;
  const timeout = window.setTimeout(() => controller.abort(), 7000);
  try {
    const result = await readPageJson("/api/settings/correction", controller.signal);
    if (revision === correctionRevision && !controller.signal.aborted) applyCorrectionSettings(result.value, correctionReadingFieldKeys);
  } catch {
  } finally {
    window.clearTimeout(timeout);
    if (revision === correctionRevision) correctionRequestPending = false;
  }
}

function syncCorrectionRefresh() {
  correctionRevision += 1;
  correctionController?.abort();
  correctionRequestPending = false;
  if (correctionRefreshTimer) {
    window.clearInterval(correctionRefreshTimer);
    correctionRefreshTimer = null;
  }
  if (activeView.value !== "device-detail" || selectedDeviceSection.value !== "parameters" || parameterTab.value !== "calibration") return;
  correctionRefreshTimer = window.setInterval(
    loadCorrectionSettings,
    CORRECTION_REFRESH_MS
  );
}

function stepOperationNumber(field, delta, min = null, max = null) {
  const currentValue = Number(operationForm.value[field]);
  const baseValue = Number.isFinite(currentValue) ? currentValue : 0;
  const decimals = String(Math.abs(delta)).split(".")[1]?.length || 0;
  let nextValue = Number((baseValue + delta).toFixed(decimals));
  if (min !== null) nextValue = Math.max(min, nextValue);
  if (max !== null) nextValue = Math.min(max, nextValue);
  operationForm.value[field] = nextValue;
}

function clampOperationNumber(field, min, max) {
  const currentValue = Number(operationForm.value[field]);
  if (!Number.isFinite(currentValue)) {
    operationForm.value[field] = min;
    return;
  }
  operationForm.value[field] = Math.min(max, Math.max(min, currentValue));
}

function stepParameterNumber(field, delta, min = null, max = null) {
  const currentValue = Number(parameterForm.value[field]);
  const baseValue = Number.isFinite(currentValue) ? currentValue : 0;
  const decimals = String(Math.abs(delta)).split(".")[1]?.length || 0;
  let nextValue = Number((baseValue + delta).toFixed(decimals));
  if (min !== null) nextValue = Math.max(min, nextValue);
  if (max !== null) nextValue = Math.min(max, nextValue);
  parameterForm.value[field] = nextValue;
}

const selectedPidModeConfig = computed(() =>
  pidModes.find(mode => mode.key === selectedPidMode.value) || pidModes[0]
);
const selectedPidDisplayNumber = computed(() =>
  pidDisplayGroupNumber(selectedPidModeConfig.value, selectedPidGroup.value)
);

function selectPidGroup(mode, group) {
  selectedPidMode.value = mode;
  selectedPidGroup.value = group;
}

function pidDisplayGroupNumber(mode, group) {
  return mode.displayOffset + group;
}

function pidGroupPosition(mode, group) {
  const [row, column] = pidGroupPositions[mode][group];
  return { gridRow: row, gridColumn: column };
}

function pidParameterKey(mode, group, category, metric) {
  return mode === "temperature"
    ? `TEMP${group}_${metric}`
    : `HUMI${group}_${category}_${metric}`;
}

function applySystemBasicSettings(value) {
  if (!value) return;
  parameterForm.value = {
    ...parameterForm.value,
    temperatureRangeMax: Number(value.TEMP_OP_H ?? parameterForm.value.temperatureRangeMax),
    temperatureRangeMin: Number(value.TEMP_OP_L ?? parameterForm.value.temperatureRangeMin),
    humidityRangeMax: Number(value.HUMI_OP_H ?? parameterForm.value.humidityRangeMax),
    humidityRangeMin: Number(value.HUMI_OP_L ?? parameterForm.value.humidityRangeMin),
    temperatureTransmissionMax: Number(value.HUMI_AirOP_H ?? parameterForm.value.temperatureTransmissionMax),
    temperatureTransmissionMin: Number(value.HUMI_AirOP_L ?? parameterForm.value.temperatureTransmissionMin),
    compressorFrequency: Number(value.heatingUpDownHz ?? parameterForm.value.compressorFrequency),
    circulationFanFrequency: Number(value.constantTEMPHz ?? parameterForm.value.circulationFanFrequency),
    humidifierFrequency: Number(value.HumiHeatHz ?? parameterForm.value.humidifierFrequency),
    frequencyLimit: Number(value.otherHz ?? parameterForm.value.frequencyLimit)
  };
}

function correctionPayload() {
  return Object.fromEntries(
    correctionFieldKeys.map(key => [key, Number(parameterForm.value[key])])
  );
}

function applyCorrectionSettings(value, fields = correctionFieldKeys) {
  if (!value) return;
  for (const key of fields) {
    if (value[key] != null) parameterForm.value[key] = Number(value[key]);
  }
}

async function saveParameterSettings() {
  if (parameterSaving.value || parameterRefresh.state.pending || parameterRefresh.state.error) return;
  const tab = parameterTab.value;
  parameterSaving.value = true;
  parameterRefresh.cancel();
  correctionRevision += 1;
  correctionController?.abort();
  correctionRequestPending = false;
  try {
    await persistParameterSettings(tab);
  } finally {
    parameterSaving.value = false;
    if (activeView.value === "device-detail" && selectedDeviceSection.value === "parameters" && parameterTab.value !== tab) loadParameterSettings();
  }
}

async function persistParameterSettings(tab) {
  if (tab === "calibration") {
    await saveCorrectionSettings();
    return;
  }
  if (tab === "pid") {
    await savePidSettings();
    return;
  }
  const payload = {
    TEMP_OP_H: Number(parameterForm.value.temperatureRangeMax),
    TEMP_OP_L: Number(parameterForm.value.temperatureRangeMin),
    HUMI_OP_H: Number(parameterForm.value.humidityRangeMax),
    HUMI_OP_L: Number(parameterForm.value.humidityRangeMin),
    HUMI_AirOP_H: Number(parameterForm.value.temperatureTransmissionMax),
    HUMI_AirOP_L: Number(parameterForm.value.temperatureTransmissionMin),
    heatingUpDownHz: Number(parameterForm.value.compressorFrequency),
    constantTEMPHz: Number(parameterForm.value.circulationFanFrequency),
    HumiHeatHz: Number(parameterForm.value.humidifierFrequency),
    otherHz: Number(parameterForm.value.frequencyLimit)
  };
  const deviceName = selectedDevice.value?.name || selectedDeviceId.value;
  try {
    const response = await fetch("/api/settings/system-basic", {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "系统参数保存失败");
    applySystemBasicSettings(result.value || payload);
    markParametersSaved("basic");
    operationLastSaved.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    addOperationLog({ title: "保存系统参数", message: `${deviceName} 已保存基础信息并通知应用层`, tone: "success" });
  } catch (error) {
    addOperationLog({ title: "保存系统参数失败", message: `${deviceName}：${error.message || "数据库不可用"}`, tone: "danger" });
  }
}

async function savePidSettings() {
  const payload = pidPayload();
  const deviceName = selectedDevice.value?.name || selectedDeviceId.value;
  try {
    const response = await fetch("/api/settings/pid", {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "PID 参数保存失败");
    applyPidSettings(result.value || payload);
    markParametersSaved("pid");
    operationLastSaved.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    addOperationLog({ title: "保存 PID 参数", message: `${deviceName} 已保存温度及湿热模式参数并通知应用层`, tone: "success" });
  } catch (error) {
    addOperationLog({ title: "保存 PID 参数失败", message: `${deviceName}：${error.message || "数据库不可用"}`, tone: "danger" });
  }
}

async function saveCorrectionSettings() {
  const payload = correctionPayload();
  const deviceName = selectedDevice.value?.name || selectedDeviceId.value;
  try {
    const response = await fetch("/api/settings/correction", {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify(payload)
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || "测量校正参数保存失败");
    applyCorrectionSettings(result.value || payload);
    markParametersSaved("calibration");
    operationLastSaved.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
    addOperationLog({ title: "保存测量校正", message: `${deviceName} 已保存温湿度及试品温度校正参数并通知应用层`, tone: "success" });
  } catch (error) {
    addOperationLog({ title: "保存测量校正失败", message: `${deviceName}：${error.message || "数据库不可用"}`, tone: "danger" });
  }
}

function resetParameterForm() {
  parameterForm.value = {
    ...parameterForm.value,
    model: "IC-1000",
    firmwareVersion: "0.1.0",
    temperatureOffset: 0,
    temperatureGain: 1,
    humidityOffset: 0,
    humidityGain: 1,
    TEMP_Area1: 0,
    TEMP_Area2: 0,
    TEMP_Area3: 0,
    TEMP_Area4: 0,
    TEMP_Corrected1: 0,
    TEMP_Corrected2: 0,
    TEMP_Corrected3: 0,
    TEMP_Corrected4: 0,
    TEMP_Correction: 0,
    HUMI_Area1: 0,
    HUMI_Area2: 0,
    HUMI_Area3: 0,
    HUMI_Area4: 0,
    HUMI_Corrected1: 0,
    HUMI_Corrected2: 0,
    HUMI_Corrected3: 0,
    HUMI_Corrected4: 0,
    HUMI_Correction: 0,
    TEMP_Collected: 0,
    TEMP_Corrected: 0,
    TEMP_Final: 0,
    HUMI_Collected: 0,
    HUMI_Corrected: 0,
    HUMI_Final: 0,
    ...Object.fromEntries(
      Array.from({ length: 10 }, (_, index) =>
        ["Collected", "Corrected", "Final"].map(stage => [`DUT${index + 1}_${stage}`, 0])
      ).flat()
    ),
    ...Object.fromEntries(pidSettingFieldKeys.map(key => [key, 0])),
    compressorFrequency: 50,
    circulationFanFrequency: 50,
    humidifierFrequency: 50,
    frequencyLimit: 60,
    temperatureRangeMin: -40,
    temperatureRangeMax: 100,
    humidityRangeMin: 0,
    humidityRangeMax: 100,
    temperatureTransmissionMin: -40,
    temperatureTransmissionMax: 100,
    humidityTransmissionMin: 0,
    humidityTransmissionMax: 100
  };
  selectedPidMode.value = "humidity";
  selectedPidGroup.value = 1;
  operationLastSaved.value = "已恢复默认";
}

function resetOperationForm() {
  operationForm.value = {
    ...operationForm.value,
    overTempEnabled: true, overHumEnabled: true, powerMemory: true,
    tempLimit: 85, humLimit: 95, airTEMP_H: 0, airTEMP_L: 0, dutTEMP_H: 0, dutTEMP_L: 0, dutModeAir_H: 0, dutModeAir_L: 0, targetTemp: 25, targetHum: 50,
    tempRamp: 1.5, humRamp: 2, runtimeHours: 0, runtimeMinutes: 30, runtimeSeconds: 0, controlMode: "balanced", programId: programs.value[0] ? String(programs.value[0].pro_no) : "",
    soundEnabled: true, doorLock: true, autoSave: true, precision: "0.1", brightness: 80,
    powerOnMode: "stop", stopResumeMode: "reset", temperatureControlMode: "air", dutTemperatureSource: "dut1",
    waitTemperatureUpper: 0, waitHumidityUpper: 0, eventCode: "0000000000000000",
    scheduledStartEnabled: false, scheduledStartDate: "2026-07-31", scheduledStartTime: "16:34",
    scheduledStopEnabled: false, scheduledStopDate: "2026-07-31", scheduledStopTime: "16:34"
  };
  if (operationTab.value === "program" && programs.value[0]) selectProgram(programs.value[0].pro_no);
  operationFeedback.value = "已恢复默认值";
  window.setTimeout(() => { operationFeedback.value = ""; }, 2200);
}

function iconFor(key) {
  const icons = {
    dashboard: "dashboard",
    memory: "gauge",
    alarms: "alarms",
    reports: "reports",
    settings: "settings",
    monitor: "activity",
    operation: "sliders",
    parameters: "settings",
    history: "history",
    faults: "tools"
  };
  return icons[key] || "activity";
}

function trackQueuedCommand(result, commandLabel, deviceId) {
  if (!result?.command_id) return;
  const existing = commandStatusById.value[result.command_id];
  const trackedCommand = {
    ...existing,
    command_id: result.command_id,
    device_id: deviceId,
    label: commandLabel,
    status: existing?.status || "QUEUED",
    message: existing?.message || "等待工控机执行"
  };
  commandStatusById.value = {
    ...commandStatusById.value,
    [result.command_id]: trackedCommand
  };
  // The edge can execute and report a command before the HTTP response that
  // created it reaches the browser. Re-process an already terminal result
  // after attaching the command label so the button state is finalized.
  if (existing && ["EXECUTED", "SUCCESS", "SUCCEEDED", "COMPLETED", "FAILED", "ERROR", "REJECTED", "TIMEOUT"].includes(String(existing.status || "").toUpperCase())) {
    handleCommandStatus(trackedCommand);
  }
}

function commandExecutionText(status) {
  const normalizedStatus = String(status || "").toUpperCase();
  if (["EXECUTED", "SUCCESS", "SUCCEEDED", "COMPLETED"].includes(normalizedStatus)) return "已完成";
  if (["FAILED", "ERROR", "REJECTED", "TIMEOUT"].includes(normalizedStatus)) return "执行失败";
  return "等待工控机执行";
}

function handleCommandStatus(event) {
  if (!event?.command_id) {
    const nextStatus = commandExecutionText(event?.status);
    return;
  }
  const current = commandStatusById.value[event.command_id] || {};
  const nextStatus = commandExecutionText(event.status);
  commandStatusById.value = {
    ...commandStatusById.value,
    [event.command_id]: { ...current, ...event, message: event.message || nextStatus }
  };
  const deviceId = event.device_id;
  const commandLabel = current.label;
  const normalizedStatus = String(event.status || "").toUpperCase();
  const succeeded = ["EXECUTED", "SUCCESS", "SUCCEEDED", "COMPLETED"].includes(normalizedStatus);
  const failed = ["FAILED", "ERROR", "REJECTED", "TIMEOUT"].includes(normalizedStatus);

  if (commandLabel === "启动") {
    if (succeeded) {
      startingDeviceIds.value = { ...startingDeviceIds.value, [deviceId]: false };
      startCommandLockedIds.value = { ...startCommandLockedIds.value, [deviceId]: true };
      delete stoppedDeviceIds.value[deviceId];
      stoppedDeviceIds.value = { ...stoppedDeviceIds.value };
      deviceStartTimes.value = { ...deviceStartTimes.value, [deviceId]: formatStartTime() };
    } else if (failed) {
      startingDeviceIds.value = { ...startingDeviceIds.value, [deviceId]: false };
      delete startCommandLockedIds.value[deviceId];
      startCommandLockedIds.value = { ...startCommandLockedIds.value };
    }
  }

  if (commandLabel === "停止") {
    if (succeeded) {
      stoppingDeviceIds.value = { ...stoppingDeviceIds.value, [deviceId]: false };
      stoppedDeviceIds.value = { ...stoppedDeviceIds.value, [deviceId]: true };
      delete startCommandLockedIds.value[deviceId];
      startCommandLockedIds.value = { ...startCommandLockedIds.value };
    } else if (failed) {
      stoppingDeviceIds.value = { ...stoppingDeviceIds.value, [deviceId]: false };
    }
  }
}

async function stopSelectedDevice() {
  if (!selectedDevice.value) return;
  const deviceId = selectedDevice.value.device_id;
  const deviceName = selectedDevice.value.name || deviceId;
  stoppingDeviceIds.value = { ...stoppingDeviceIds.value, [deviceId]: true };
  addOperationLog({ title: "停止运行", message: `${deviceName} 正在下发停止命令`, tone: "warning", deviceId });

  try {
    const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        command: "Stop",
        reason: "stop requested from Vue dashboard"
      })
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || result.message || "停止命令下发失败");
    }
    trackQueuedCommand(result, "停止", deviceId);
    stoppingDeviceIds.value = { ...stoppingDeviceIds.value, [deviceId]: false };
    addOperationLog({ title: "停止运行", message: `${deviceName} 停止命令已排队，等待工控机确认`, tone: "warning", deviceId });
  } catch (error) {
    stoppingDeviceIds.value = { ...stoppingDeviceIds.value, [deviceId]: false };
    addOperationLog({ title: "停止运行", message: `${deviceName} 停止命令下发失败`, tone: "danger", deviceId });
  }
}

async function startSelectedDevice() {
  if (!selectedDevice.value) return;
  const currentMode = Number(firstDefined(selectedDevice.value.run_mode, selectedDevice.value.mainData?.runMode));
  runModeSelection.value = runModeOptions.some(item => item.value === String(currentMode))
    ? String(currentMode)
    : "1";
  isRunModeDialogOpen.value = true;
}

function cancelRunModeSelection() {
  isRunModeDialogOpen.value = false;
}

function openSetpointSettings() {
  isRunModeDialogOpen.value = false;
  activeView.value = "device-detail";
  selectedDeviceSection.value = "operation";
  operationTab.value = "setpoint";
}

function waitForCommandPollingWindow() {
  return new Promise(resolve => window.setTimeout(resolve, 350));
}

async function postDeviceCommand(deviceId, command, reason, payload = {}) {
  const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/commands`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ command, time: formatStartTime(), reason, payload })
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || result.message || `${command}命令下发失败`);
  return result;
}

async function toggleSelectedDeviceLight() {
  if (!selectedDevice.value || isLightCommandPending.value) return;
  const deviceId = selectedDevice.value.device_id;
  const deviceName = selectedDevice.value.name || deviceId;
  const nextLightState = !isLightOn.value;
  const command = nextLightState ? "LightON" : "LightOFF";
  const commandLabel = nextLightState ? "开灯" : "关灯";
  isLightCommandPending.value = true;
  addOperationLog({ title: commandLabel, message: `${deviceName} 正在下发${commandLabel}命令`, tone: "warning", deviceId });

  try {
    const result = await postDeviceCommand(deviceId, command, `${commandLabel} requested from Vue dashboard`);
    isLightOn.value = nextLightState;
    trackQueuedCommand(result, commandLabel, deviceId);
    addOperationLog({ title: commandLabel, message: `${deviceName} ${commandLabel}命令已排队，等待工控机确认`, tone: "success", deviceId });
  } catch (error) {
    addOperationLog({ title: commandLabel, message: `${deviceName} ${commandLabel}命令下发失败：${error.message || "未知错误"}`, tone: "danger", deviceId });
  } finally {
    isLightCommandPending.value = false;
  }
}

async function confirmRunModeSelection() {
  if (!selectedDevice.value) return;
  const deviceId = selectedDevice.value.device_id;
  const deviceName = selectedDevice.value.name || deviceId;
  const mode = runModeOptions.find(item => item.value === runModeSelection.value) || runModeOptions[0];
  isRunModeDialogOpen.value = false;
  startingDeviceIds.value = { ...startingDeviceIds.value, [deviceId]: true };
  addOperationLog({ title: "启动运行", message: `${deviceName} 正在切换至${mode.label}`, tone: "warning", deviceId });

  try {
    await postDeviceCommand(deviceId, `RunMode=${mode.value}`, `运行模式选择：${mode.label}`);
    await waitForCommandPollingWindow();
    const result = await postDeviceCommand(deviceId, "Run", "start requested from Vue dashboard", {
      target_temperature: Number(selectedDevice.value.target_temperature ?? selectedDevice.value.current_temperature ?? 25),
      target_humidity: Number(selectedDevice.value.target_humidity ?? selectedDevice.value.current_humidity ?? 60)
    });
    trackQueuedCommand(result, "启动", deviceId);
    startingDeviceIds.value = { ...startingDeviceIds.value, [deviceId]: false };
    addOperationLog({ title: "启动运行", message: `${deviceName} 启动命令已排队，等待工控机确认`, tone: "warning", deviceId });
  } catch (error) {
    startingDeviceIds.value = { ...startingDeviceIds.value, [deviceId]: false };
    addOperationLog({ title: "启动运行", message: `${deviceName} 启动命令下发失败`, tone: "danger", deviceId });
  }
}

async function holdSelectedDevice() {
  if (!selectedDevice.value) return;
  const deviceId = selectedDevice.value.device_id;
  const deviceName = selectedDevice.value.name || deviceId;
  const isHeld = Boolean(heldDeviceIds.value[deviceId]);
  const command = isHeld ? "HoldOFF" : "HoldON";
  const commandLabel = isHeld ? "继续" : "保持";
  holdingDeviceIds.value = { ...holdingDeviceIds.value, [deviceId]: true };
  addOperationLog({ title: commandLabel, message: `${deviceName} 正在下发${commandLabel}命令`, tone: "warning", deviceId });

  try {
    const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        command,
        time: formatStartTime(),
        reason: `${commandLabel} requested from Vue dashboard`
      })
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || result.message || `${commandLabel}命令下发失败`);
    }
    heldDeviceIds.value = { ...heldDeviceIds.value, [deviceId]: !isHeld };
    trackQueuedCommand(result, commandLabel, deviceId);
    addOperationLog({ title: commandLabel, message: `${deviceName} ${commandLabel}命令已下发`, tone: "success", deviceId });
  } catch (error) {
    addOperationLog({ title: commandLabel, message: `${deviceName} ${commandLabel}命令下发失败`, tone: "danger", deviceId });
  } finally {
    holdingDeviceIds.value = { ...holdingDeviceIds.value, [deviceId]: false };
  }
}

async function skipSelectedDeviceStep() {
  if (!selectedDevice.value) return;
  const deviceId = selectedDevice.value.device_id;
  const deviceName = selectedDevice.value.name || deviceId;
  skippingDeviceIds.value = { ...skippingDeviceIds.value, [deviceId]: true };
  addOperationLog({ title: "跳步", message: `${deviceName} 正在下发跳步命令`, tone: "warning", deviceId });

  try {
    const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/commands`, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({
        command: "Jump",
        reason: "step skip requested from Vue dashboard"
      })
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || result.message || "跳步命令下发失败");
    }
    trackQueuedCommand(result, "跳步", deviceId);
    addOperationLog({ title: "跳步", message: `${deviceName} 跳步命令已下发`, tone: "success", deviceId });
  } catch (error) {
    addOperationLog({ title: "跳步", message: `${deviceName} 跳步命令下发失败`, tone: "danger", deviceId });
  } finally {
    skippingDeviceIds.value = { ...skippingDeviceIds.value, [deviceId]: false };
  }
}

function connectSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  const token = window.localStorage.getItem("industrial-auth-token");
  socket = new WebSocket(`${protocol}://${location.host}/ws/memory?access_token=${encodeURIComponent(token || "")}`);

  socket.onopen = () => {
    connectionText.value = "已连接";
  };

  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.type === "command_status") {
      handleCommandStatus(message);
      return;
    }
    if (message.type === "memory_not_ready") {
      connectionText.value = "共享内存未就绪";
      return;
    }

    snapshot.value = message.snapshot;
    socketSnapshotRevision += 1;
    monitorRefresh.cancel();
    monitorRefresh.state.error = "";
    monitorRefresh.state.updatedAt = Date.now();
    routerReadAt.value = message.router_read_at;
    devices.value = message.snapshot?.devices || [];
    if (!devices.value.some(device => device.device_id === selectedDeviceId.value)) {
      selectedDeviceId.value = devices.value[0]?.device_id || null;
    }
    updateDeviceNotifications(devices.value);
    pushTrendSamples(devices.value, message.snapshot?.written_at);
    drawSelectedTrend();
  };

  socket.onerror = () => {
    connectionText.value = "连接异常";
  };

  socket.onclose = event => {
    if (event?.code === 1008) {
      // Session revoked: rebuilding the socket with a dead token only creates a
      // reconnect storm, so leave the dashboard instead.
      forceLogout();
      return;
    }
    connectionText.value = "重连中";
    reconnectTimer = window.setTimeout(connectSocket, 1200);
  };
}

function pushTrendSamples(deviceList, writtenAt) {
  const nowMs = Number(writtenAt ? writtenAt * 1000 : Date.now());
  const nextHistory = { ...trendHistory.value };

  deviceList.forEach(device => {
    const deviceId = device.device_id;
    const samples = nextHistory[deviceId] ? [...nextHistory[deviceId]] : [];
    samples.push({
      time: nowMs,
      temp: Number(device.current_temperature ?? 0),
      hum: Number(device.current_humidity ?? 0)
    });
    nextHistory[deviceId] = samples.filter(sample => sample.time >= nowMs - TREND_HISTORY_RETENTION_MS);
  });

  trendHistory.value = nextHistory;
}

function drawSelectedTrend() {
  nextTick(() => {
    const canvas = selectedTrendCanvas.value;
    if (!canvas) return;

    const metrics = prepareTrendCanvas(canvas);
    const ctx = metrics.ctx;
    const width = metrics.width;
    const height = metrics.height;
    const padLeft = 72;
    const padRight = 72;
    const padTop = 24;
    const padBottom = 54;
    const plotWidth = width - padLeft - padRight;
    const plotHeight = height - padTop - padBottom;
    const nowMs = Date.now();
    const { startMs, endMs } = getTrendTimeRange(nowMs);
    const yRanges = getTrendYRanges();
    const samples = trendHistory.value[selectedDeviceId.value] || [];

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "#f8fbfc";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "#d8e2e8";
    ctx.lineWidth = 1;
    ctx.font = "12px Microsoft YaHei";
    ctx.fillStyle = "#1f2933";

    for (let index = 0; index <= 5; index += 1) {
      const y = padTop + index * (plotHeight / 5);
      ctx.beginPath();
      ctx.setLineDash([4, 4]);
      ctx.moveTo(padLeft, y);
      ctx.lineTo(width - padRight, y);
      ctx.stroke();
    }

    drawValueAxis(ctx, yRanges.temp, yRanges.hum, padLeft, width - padRight, padTop, plotHeight);

    for (let index = 0; index <= 10; index += 1) {
      const x = padLeft + index * (plotWidth / 10);
      ctx.beginPath();
      ctx.setLineDash([4, 4]);
      ctx.moveTo(x, padTop);
      ctx.lineTo(x, height - padBottom);
      ctx.stroke();
    }

    const nowX = timeToX(nowMs, startMs, endMs, padLeft, plotWidth);
    ctx.setLineDash([]);
    ctx.strokeStyle = "#f59e0b";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(nowX, padTop);
    ctx.lineTo(nowX, height - padBottom);
    ctx.stroke();

    drawTimeAxis(ctx, startMs, endMs, padLeft, plotWidth, height - 26);

    drawTimeSeries(ctx, samples, "temp", "#3b82f6", yRanges.temp.min, yRanges.temp.max, startMs, endMs, padLeft, padTop, plotWidth, plotHeight);
    drawTimeSeries(ctx, samples, "hum", "#22c55e", yRanges.hum.min, yRanges.hum.max, startMs, endMs, padLeft, padTop, plotWidth, plotHeight);

    if (samples.length === 0) {
      ctx.fillStyle = "#35596d";
      ctx.font = "14px Microsoft YaHei";
      ctx.fillText("等待实时数据写入曲线", padLeft + 18, padTop + 34);
    }
  });
}

function prepareTrendCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.max(1, window.devicePixelRatio || 1);
  const width = Math.max(320, Math.round(rect.width || canvas.clientWidth || 1080));
  const height = Math.max(220, Math.round(rect.height || canvas.clientHeight || 320));
  const pixelWidth = Math.round(width * dpr);
  const pixelHeight = Math.round(height * dpr);

  if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
    canvas.width = pixelWidth;
    canvas.height = pixelHeight;
  }

  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, width, height };
}

function drawTimeAxis(ctx, startMs, endMs, padLeft, plotWidth, y) {
  ctx.setLineDash([]);
  ctx.fillStyle = "#1f2933";
  ctx.font = "12px Microsoft YaHei";
  ctx.textAlign = "center";

  [0, 0.25, 0.5, 0.75, 1].forEach(ratio => {
    const x = padLeft + plotWidth * ratio;
    const label = formatTimeLabel(startMs + (endMs - startMs) * ratio);
    ctx.fillText(label, x, y);
  });

  ctx.textAlign = "left";
}

function drawValueAxis(ctx, tempRange, humRange, padLeft, axisRight, padTop, plotHeight) {
  ctx.setLineDash([]);
  ctx.font = "11px Microsoft YaHei";

  for (let index = 0; index <= 5; index += 1) {
    const ratio = index / 5;
    const y = padTop + plotHeight * ratio;
    const tempValue = tempRange.max - (tempRange.max - tempRange.min) * ratio;
    const humValue = humRange.max - (humRange.max - humRange.min) * ratio;

    ctx.fillStyle = "#1f2933";
    ctx.textAlign = "right";
    ctx.fillText(`${tempValue.toFixed(1)}C`, padLeft - 8, y + 4);

    ctx.fillStyle = "#1f2933";
    ctx.textAlign = "left";
    ctx.fillText(`${humValue.toFixed(1)}%`, axisRight + 8, y + 4);
  }

  ctx.textAlign = "left";
}

function drawTimeSeries(ctx, samples, key, color, min, max, startMs, endMs, padLeft, padTop, plotWidth, plotHeight) {
  const visibleSamples = samples.filter(sample => sample.time >= startMs && sample.time <= endMs);
  if (visibleSamples.length === 0) return;

  ctx.strokeStyle = color;
  ctx.lineWidth = 2.5;
  ctx.beginPath();

  visibleSamples.forEach((sample, index) => {
    const value = sample[key];
    const x = timeToX(sample.time, startMs, endMs, padLeft, plotWidth);
    const y = padTop + plotHeight - ((value - min) / (max - min)) * plotHeight;
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });

  ctx.stroke();

  if (visibleSamples.length === 1) {
    const sample = visibleSamples[0];
    const value = sample[key];
    const x = timeToX(sample.time, startMs, endMs, padLeft, plotWidth);
    const y = padTop + plotHeight - ((value - min) / (max - min)) * plotHeight;
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, 3.5, 0, Math.PI * 2);
    ctx.fill();
  }
}

function timeToX(time, startMs, endMs, padLeft, plotWidth) {
  return padLeft + ((time - startMs) / (endMs - startMs)) * plotWidth;
}

function getTrendTimeRange(baseMs = Date.now()) {
  const centerMs = baseMs + trendCenterOffsetMs.value;
  const halfWindow = trendWindowMs.value / 2;
  return {
    startMs: centerMs - halfWindow,
    endMs: centerMs + halfWindow
  };
}

function getTrendYRanges() {
  return {
    temp: getScaledRange(-40, 100),
    hum: getScaledRange(0, 100)
  };
}

function getScaledRange(baseMin, baseMax) {
  const baseSpan = baseMax - baseMin;
  const span = baseSpan * trendYScale.value;
  const center = (baseMin + baseMax) / 2 + trendYOffsetRatio.value * baseSpan;
  return {
    min: center - span / 2,
    max: center + span / 2
  };
}

function formatTimeLabel(valueMs) {
  return new Date(valueMs).toLocaleTimeString("zh-CN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function getTrendCanvasRatio(event) {
  const canvas = selectedTrendCanvas.value;
  if (!canvas) return 0.5;
  const rect = canvas.getBoundingClientRect();
  const x = Math.min(Math.max(event.clientX - rect.left, 0), rect.width);
  return rect.width ? x / rect.width : 0.5;
}

function zoomTrend(factor, anchorRatio = 0.5) {
  const oldWindow = trendWindowMs.value;
  const nextWindow = Math.min(Math.max(oldWindow * factor, TREND_MIN_WINDOW_MS), TREND_MAX_WINDOW_MS);
  const nowMs = Date.now();
  const range = getTrendTimeRange(nowMs);
  const anchorTime = range.startMs + oldWindow * anchorRatio;
  const nextStart = anchorTime - nextWindow * anchorRatio;
  const nextCenter = nextStart + nextWindow / 2;

  trendWindowMs.value = nextWindow;
  trendCenterOffsetMs.value = nextCenter - nowMs;
  trendClockMs.value = nowMs;
  drawSelectedTrend();
}

function zoomTrendY(factor, anchorRatio = 0.5) {
  const oldScale = trendYScale.value;
  const nextScale = Math.min(Math.max(oldScale * factor, TREND_Y_MIN_SCALE), TREND_Y_MAX_SCALE);
  const oldTopOffset = trendYOffsetRatio.value - oldScale / 2;
  const anchorOffset = oldTopOffset + oldScale * anchorRatio;
  trendYScale.value = nextScale;
  trendYOffsetRatio.value = anchorOffset - nextScale * anchorRatio + nextScale / 2;
  drawSelectedTrend();
}

function resetTrendZoom() {
  trendWindowMs.value = TREND_DEFAULT_WINDOW_MS;
  trendCenterOffsetMs.value = 0;
  resetTrendY(false);
  trendClockMs.value = Date.now();
  drawSelectedTrend();
}

function resetTrendY(shouldDraw = true) {
  trendYScale.value = 1;
  trendYOffsetRatio.value = 0;
  if (shouldDraw) drawSelectedTrend();
}

function handleTrendPointerDown(event) {
  isTrendDragging.value = true;
  lastTrendDragX = event.clientX;
}

function handleTrendPointerMove(event) {
  if (!isTrendDragging.value) return;
  const canvas = selectedTrendCanvas.value;
  const rect = canvas?.getBoundingClientRect();
  const width = rect?.width || 1;
  const deltaX = event.clientX - lastTrendDragX;
  lastTrendDragX = event.clientX;
  trendCenterOffsetMs.value -= (deltaX / width) * trendWindowMs.value;
  trendClockMs.value = Date.now();
  drawSelectedTrend();
}

function handleTrendPointerUp() {
  isTrendDragging.value = false;
}

function handleTrendResize() {
  drawSelectedTrend();
}

onMounted(() => {
  loadMonitorLayout();
  loadPrograms();
  connectSocket();
  refreshWorkspace();
  syncCorrectionRefresh();
  window.addEventListener("resize", handleTrendResize);
  clockTimer = window.setInterval(() => {
    currentTimeText.value = new Date().toLocaleTimeString();
    trendClockMs.value = Date.now();
    drawSelectedTrend();
  }, 1000);
});

onBeforeUnmount(() => {
  if (socket) {
    socket.onclose = null;
    socket.close();
  }
  if (reconnectTimer) window.clearTimeout(reconnectTimer);
  if (clockTimer) window.clearInterval(clockTimer);
  if (correctionRefreshTimer) window.clearInterval(correctionRefreshTimer);
  correctionController?.abort();
  window.clearTimeout(feedbackTimer);
  window.removeEventListener("resize", handleTrendResize);
});

watch([activeView, selectedDeviceId, selectedDeviceSection, visibleMonitorCards], () => nextTick(drawSelectedTrend));
watch([activeView, selectedDeviceId, selectedDeviceSection, operationTab, parameterTab], (current, previous) => {
  if (current.slice(0, 3).some((value, index) => value !== previous?.[index])
    || (current[2] === "operation" && current[3] !== previous?.[3])
    || (current[2] === "parameters" && current[4] !== previous?.[4])) refreshWorkspace();
});
watch([activeView, selectedDeviceSection, parameterTab], syncCorrectionRefresh);
</script>
