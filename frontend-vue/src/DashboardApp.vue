<template>
  <div class="app-shell" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">IC</div>
        <div>
          <h1>环境试验箱平台</h1>
          <p>Industrial Chamber QC</p>
        </div>
      </div>

      <nav class="nav-list" aria-label="主导航">
        <button
          v-for="item in sidebarItems"
          :key="item.key"
          :class="{ active: activeSidebarKey === item.key }"
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

    <section class="main-shell">
      <header class="topbar">
        <div class="top-title">
          <template v-if="activeView === 'device-detail'">
            <div>
              <h2>{{ selectedDevice?.name || selectedDeviceId }}</h2>
              <div class="device-title-meta">
                <span>{{ selectedDeviceId }}</span>
                <span>{{ selectedDevice?.ip_address || selectedDevice?.ip || "暂无 IP" }}</span>
                <strong
                  v-if="selectedDevice"
                  :class="stateClass(selectedDevice)"
                >
                  {{ stateLabel(selectedDevice.run_state) }}
                </strong>
              </div>
            </div>
          </template>
          <h2 v-else>{{ currentTitle }}</h2>
        </div>
        <div class="top-actions">
          <button class="notify" type="button" :title="notificationTitle" :aria-label="notificationTitle" @click="isNotificationOpen = true">
            <AppIcon name="bell" :size="18" />
            <span v-if="notificationCount > 0">{{ notificationCountText }}</span>
          </button>
          <button class="user-card" type="button" aria-label="打开个人中心" @click="openProfile">
            <div>
              <strong>Admin User</strong>
              <span>系统管理员</span>
            </div>
            <div class="avatar">A</div>
          </button>
        </div>
      </header>

      <main class="content">
        <section v-if="activeView === 'dashboard'" class="page-stack">
          <section class="panel overview-panel">
            <div class="panel-title">
              <h3>试验箱实时列表</h3>
              <div class="panel-actions">
                <span class="live-pill"><i></i>实时数据流</span>
                <div class="view-toggle" aria-label="切换设备展示形式">
                  <button
                    type="button"
                    :class="{ active: deviceDisplayMode === 'list' }"
                    @click="deviceDisplayMode = 'list'"
                  >
                    列表
                  </button>
                  <button
                    type="button"
                    :class="{ active: deviceDisplayMode === 'card' }"
                    @click="deviceDisplayMode = 'card'"
                  >
                    卡片
                  </button>
                </div>
              </div>
            </div>
            <DeviceOverviewList
              v-if="deviceDisplayMode === 'list'"
              :devices="devices"
              @select="openDeviceDetail"
            />
            <div v-else class="machine-detail-grid device-card-list">
              <LiveDeviceDetailCard
                v-for="device in devices"
                :key="device.device_id"
                :device="device"
                @select="openDeviceDetail"
              />
            </div>
          </section>
        </section>

        <section v-else-if="activeView === 'profile'" class="page-stack profile-page">
          <div class="section-head profile-section-head">
            <div>
              <h2>个人中心</h2>
              <span>管理个人资料、账号状态与安全信息</span>
            </div>
            <button class="profile-back-button" type="button" @click="returnToDashboard">
              <AppIcon name="dashboard" :size="16" />
              <span>返回设备看板</span>
            </button>
          </div>

          <section class="profile-hero panel">
            <div class="profile-avatar">A</div>
            <div class="profile-identity">
              <div class="profile-name-row">
                <h3>Admin User</h3>
                <span class="profile-status"><i></i>在线</span>
              </div>
              <p>系统管理员 · 工业试验箱平台</p>
              <span class="profile-id">账号 ID：ADMIN-001</span>
            </div>
            <div class="profile-hero-meta">
              <span>当前会话</span>
              <strong>{{ currentTimeText }}</strong>
            </div>
          </section>

          <div class="profile-grid">
            <section class="panel profile-info-panel">
              <div class="panel-title">
                <h3>基本资料</h3>
                <span>账户信息</span>
              </div>
              <div class="profile-fields">
                <div><span>姓名</span><strong>Admin User</strong></div>
                <div><span>角色</span><strong>系统管理员</strong></div>
                <div><span>所属组织</span><strong>工业试验箱控制中心</strong></div>
                <div><span>工作邮箱</span><strong>admin@industrial-chamber.local</strong></div>
                <div><span>联系电话</span><strong>未设置</strong></div>
                <div><span>时区</span><strong>Asia/Shanghai (UTC+8)</strong></div>
              </div>
            </section>

            <section class="panel profile-security-panel">
              <div class="panel-title">
                <h3>账号安全</h3>
                <span>安全等级：良好</span>
              </div>
              <div class="security-item"><AppIcon name="settings" :size="17" /><div><strong>登录密码</strong><span>建议定期更新密码</span></div><button type="button" @click="profileActionText = '密码修改功能即将开放'">修改</button></div>
              <div class="security-item"><AppIcon name="bell" :size="17" /><div><strong>通知偏好</strong><span>接收设备报警与运行通知</span></div><button type="button" @click="profileActionText = '通知偏好已保持为默认设置'">管理</button></div>
              <p v-if="profileActionText" class="profile-action-feedback">{{ profileActionText }}</p>
            </section>
          </div>

          <section class="panel profile-activity-panel">
            <div class="panel-title">
              <h3>最近操作</h3>
              <span>当前浏览器会话</span>
            </div>
            <div v-if="operationLogs.length" class="profile-activity-list">
              <div v-for="item in operationLogs.slice(0, 5)" :key="item.id" class="profile-activity-item">
                <i :class="item.tone"></i>
                <div><strong>{{ item.title }}</strong><span>{{ item.message }}</span></div>
                <time>{{ item.timeText }}</time>
              </div>
            </div>
            <div v-else class="profile-empty-activity">暂无操作记录，设备控制操作会显示在这里。</div>
          </section>
        </section>

        <section v-else-if="activeView === 'device-detail'" class="page-stack">
          <section
            v-if="selectedDevice && selectedDeviceSection === 'monitor'"
            class="monitor-layout"
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
                    :disabled="!selectedDevice || startingDeviceIds[selectedDeviceId]"
                    @click="startSelectedDevice"
                  >
                    {{ startingDeviceIds[selectedDeviceId] ? "启动下发中" : "启动运行" }}
                  </button>
                  <button
                    class="hold-command-button"
                    type="button"
                    :disabled="!selectedDevice || holdingDeviceIds[selectedDeviceId]"
                    @click="holdSelectedDevice"
                  >
                    {{ holdingDeviceIds[selectedDeviceId] ? "保持下发中" : "保持" }}
                  </button>
                  <button
                    class="skip-command-button"
                    type="button"
                    :disabled="!selectedDevice || skippingDeviceIds[selectedDeviceId]"
                    @click="skipSelectedDeviceStep"
                  >
                    {{ skippingDeviceIds[selectedDeviceId] ? "跳步下发中" : "跳步" }}
                  </button>
                  <button
                    class="danger-command-button"
                    type="button"
                    :disabled="!selectedDevice || stoppingDeviceIds[selectedDeviceId]"
                    @click="stopSelectedDevice"
                  >
                    {{ stoppingDeviceIds[selectedDeviceId] ? "停止下发中" : "停止运行" }}
                  </button>
                </div>
                <div class="command-status">
                  <h3>远程控制</h3>
                  <p>{{ commandStatusText }}</p>
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
                :device-status="stateLabel(selectedDevice.run_state)"
                :updated-at="formatSnapshotTime(selectedDevice.updated_at || snapshot?.written_at)"
                :communication-status="selectedDevice.online ? '正常' : '离线'"
                :data-source="sourceName"
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

                <section v-if="visibleMonitorCards.includes('status')" class="monitor-card info-monitor-card">
                  <div class="monitor-card-title"><AppIcon name="activity" :size="17" /><h3>运行状态</h3></div>
                  <strong class="monitor-status-value" :class="stateClass(selectedDevice)">{{ stateLabel(selectedDevice.run_state) }}</strong>
                  <span>当前设备运行状态</span>
                </section>
                <section v-if="visibleMonitorCards.includes('communication')" class="monitor-card info-monitor-card">
                  <div class="monitor-card-title"><AppIcon name="chart" :size="17" /><h3>通讯信息</h3></div>
                  <div class="monitor-data-row"><span>设备 IP</span><strong>{{ selectedDevice.ip_address || selectedDevice.ip || "--" }}</strong></div>
                  <div class="monitor-data-row"><span>连接状态</span><strong>{{ selectedDevice.online ? "在线" : "离线" }}</strong></div>
                </section>
                <section v-if="visibleMonitorCards.includes('updated')" class="monitor-card info-monitor-card">
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

            <div v-if="isLayoutEditorOpen" class="layout-modal-backdrop" @click.self="isLayoutEditorOpen = false">
              <section class="layout-modal" role="dialog" aria-modal="true" aria-labelledby="layout-modal-title">
                <div class="layout-modal-header">
                  <div>
                    <h3 id="layout-modal-title">选择显示卡片</h3>
                    <span>配置仅保存在当前浏览器</span>
                  </div>
                  <button class="layout-modal-close" type="button" title="关闭" aria-label="关闭" @click="isLayoutEditorOpen = false">
                    <AppIcon name="close" :size="17" />
                  </button>
                </div>
                <div class="layout-editor">
                  <label v-for="card in optionalMonitorCards" :key="card.key" class="layout-option">
                    <input
                      type="checkbox"
                      :checked="visibleMonitorCards.includes(card.key)"
                      @change="toggleMonitorCard(card.key)"
                    />
                    <AppIcon :name="card.icon" :size="15" />
                    <span>{{ card.label }}</span>
                  </label>
                </div>
                <div class="layout-modal-footer">
                  <span>{{ visibleMonitorCards.length }} 项已显示</span>
                  <button class="layout-modal-confirm" type="button" @click="isLayoutEditorOpen = false">完成</button>
                </div>
              </section>
            </div>
          </section>

          <section v-else-if="selectedDevice && selectedDeviceSection === 'operation'" class="operation-settings">
            <div class="operation-layout">
              <nav class="operation-nav panel" aria-label="操作设定分类">
                <button v-for="item in operationTabs" :key="item.key" type="button" :class="{ active: operationTab === item.key }" @click="operationTab = item.key">
                  <AppIcon :name="item.icon" :size="17" />
                  <span><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span>
                  <AppIcon name="chevronRight" :size="14" />
                </button>
              </nav>

              <section class="operation-editor panel">
                <div class="operation-editor-head">
                  <div>
                    <span class="eyebrow-label">CONFIGURATION</span>
                    <h3>{{ activeOperationTab.label }}</h3>
                  </div>
                  <span class="operation-save-state"><i></i>{{ operationFeedback || '未修改' }}</span>
                </div>

                <div v-if="operationTab === 'protection'" class="protection-settings-grid">
                  <section v-for="item in protectionItems" :key="item.key" class="protection-card" :class="{ 'protection-card-empty': item.empty, 'protection-card-enabled': !item.empty && operationForm[item.enabled] }">
                    <header>
                      <span>{{ item.label }}</span>
                      <label v-if="!item.empty" class="protection-switch">
                        <input v-model="operationForm[item.enabled]" type="checkbox" :aria-label="`${item.label}开关`">
                        <i></i><small>{{ operationForm[item.enabled] ? '已启用' : '未启用' }}</small>
                      </label>
                    </header>
                    <div v-if="!item.empty" class="protection-fields" :class="{ disabled: !operationForm[item.enabled] }">
                      <label><span>上限值</span><b>=</b><span class="hmi-number-control"><input v-model="operationForm[item.upper]" :disabled="!operationForm[item.enabled]" type="number" min="-32768" max="32768" step="0.1" :aria-label="`${item.label}上限值`" @blur="clampOperationNumber(item.upper, -32768, 32768)"><span class="hmi-number-steps"><button type="button" :disabled="!operationForm[item.enabled]" :title="`调高${item.label}上限值`" :aria-label="`调高${item.label}上限值`" @click.stop.prevent="stepOperationNumber(item.upper, 0.1, -32768, 32768)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" :disabled="!operationForm[item.enabled]" :title="`调低${item.label}上限值`" :aria-label="`调低${item.label}上限值`" @click.stop.prevent="stepOperationNumber(item.upper, -0.1, -32768, 32768)"><AppIcon name="chevronDown" :size="12" /></button></span></span></label>
                      <label><span>下限值</span><b>=</b><span class="hmi-number-control"><input v-model="operationForm[item.lower]" :disabled="!operationForm[item.enabled]" type="number" min="-32768" max="32768" step="0.1" :aria-label="`${item.label}下限值`" @blur="clampOperationNumber(item.lower, -32768, 32768)"><span class="hmi-number-steps"><button type="button" :disabled="!operationForm[item.enabled]" :title="`调高${item.label}下限值`" :aria-label="`调高${item.label}下限值`" @click.stop.prevent="stepOperationNumber(item.lower, 0.1, -32768, 32768)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" :disabled="!operationForm[item.enabled]" :title="`调低${item.label}下限值`" :aria-label="`调低${item.label}下限值`" @click.stop.prevent="stepOperationNumber(item.lower, -0.1, -32768, 32768)"><AppIcon name="chevronDown" :size="12" /></button></span></span></label>
                    </div>
                  </section>
                </div>

                <div v-else-if="operationTab === 'setpoint'" class="setpoint-module-grid">
                  <section class="setpoint-module-card setpoint-temperature-card">
                    <header><span><AppIcon name="temperature" :size="16" />温度</span><small>CH-01 / TEMP</small></header>
                    <div class="setpoint-module-fields">
                      <label class="field-control field-control-large"><span>目标值</span><div><span class="hmi-number-control"><input v-model="operationForm.targetTemp" type="number" step="0.1"><span class="hmi-number-steps"><button type="button" title="调高温度目标值" aria-label="调高温度目标值" @click.stop.prevent="stepOperationNumber('targetTemp', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="调低温度目标值" aria-label="调低温度目标值" @click.stop.prevent="stepOperationNumber('targetTemp', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>°C</b></div></label>
                      <label class="field-control field-control-large"><span>斜率值</span><div><span class="hmi-number-control"><input v-model="operationForm.tempRamp" type="number" step="0.1"><span class="hmi-number-steps"><button type="button" title="调高温度斜率值" aria-label="调高温度斜率值" @click.stop.prevent="stepOperationNumber('tempRamp', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="调低温度斜率值" aria-label="调低温度斜率值" @click.stop.prevent="stepOperationNumber('tempRamp', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>°C/min</b></div></label>
                    </div>
                  </section>
                  <section class="setpoint-module-card setpoint-humidity-card">
                    <header><span><AppIcon name="humidity" :size="16" />湿度</span><small>CH-02 / HUM</small></header>
                    <div class="setpoint-module-fields">
                      <label class="field-control field-control-large"><span>目标值</span><div><span class="hmi-number-control"><input v-model="operationForm.targetHum" type="number" step="0.1"><span class="hmi-number-steps"><button type="button" title="调高湿度目标值" aria-label="调高湿度目标值" @click.stop.prevent="stepOperationNumber('targetHum', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="调低湿度目标值" aria-label="调低湿度目标值" @click.stop.prevent="stepOperationNumber('targetHum', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>%RH</b></div></label>
                      <label class="field-control field-control-large"><span>斜率值</span><div><span class="hmi-number-control"><input v-model="operationForm.humRamp" type="number" step="0.1"><span class="hmi-number-steps"><button type="button" title="调高湿度斜率值" aria-label="调高湿度斜率值" @click.stop.prevent="stepOperationNumber('humRamp', 0.1)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="调低湿度斜率值" aria-label="调低湿度斜率值" @click.stop.prevent="stepOperationNumber('humRamp', -0.1)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>%/min</b></div></label>
                    </div>
                  </section>
                  <section class="setpoint-module-card setpoint-runtime-card">
                    <header><span><AppIcon name="history" :size="16" />运行时间</span><small>CH-03 / H:M:S</small></header>
                    <div class="runtime-time-control" aria-label="运行时间，格式为小时分钟秒">
                      <span class="runtime-time-segment"><span class="hmi-number-control"><input v-model="operationForm.runtimeHours" type="number" min="0" step="1" aria-label="运行时间小时" @blur="clampOperationNumber('runtimeHours', 0, 999)"><span class="hmi-number-steps"><button type="button" title="增加小时" aria-label="增加小时" @click.stop.prevent="stepOperationNumber('runtimeHours', 1, 0, 999)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少小时" aria-label="减少小时" @click.stop.prevent="stepOperationNumber('runtimeHours', -1, 0, 999)"><AppIcon name="chevronDown" :size="12" /></button></span></span><em>H</em></span>
                      <b>:</b>
                      <span class="runtime-time-segment"><span class="hmi-number-control"><input v-model="operationForm.runtimeMinutes" type="number" min="0" max="59" step="1" aria-label="运行时间分钟" @blur="clampOperationNumber('runtimeMinutes', 0, 59)"><span class="hmi-number-steps"><button type="button" title="增加分钟" aria-label="增加分钟" @click.stop.prevent="stepOperationNumber('runtimeMinutes', 1, 0, 59)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少分钟" aria-label="减少分钟" @click.stop.prevent="stepOperationNumber('runtimeMinutes', -1, 0, 59)"><AppIcon name="chevronDown" :size="12" /></button></span></span><em>M</em></span>
                      <b>:</b>
                      <span class="runtime-time-segment"><span class="hmi-number-control"><input v-model="operationForm.runtimeSeconds" type="number" min="0" max="59" step="1" aria-label="运行时间秒" @blur="clampOperationNumber('runtimeSeconds', 0, 59)"><span class="hmi-number-steps"><button type="button" title="增加秒" aria-label="增加秒" @click.stop.prevent="stepOperationNumber('runtimeSeconds', 1, 0, 59)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="减少秒" aria-label="减少秒" @click.stop.prevent="stepOperationNumber('runtimeSeconds', -1, 0, 59)"><AppIcon name="chevronDown" :size="12" /></button></span></span><em>S</em></span>
                    </div>
                  </section>
                </div>

                <div v-else-if="operationTab === 'program'" class="program-settings">
                  <div class="program-toolbar"><div><span class="setting-section-title inline"><span>程序模式</span><small>选择需要下发的试验程序</small></span></div><button class="secondary-action" type="button" @click="operationFeedback = '程序新建功能即将开放'">＋ 新建程序</button></div>
                  <div class="program-list"><button v-for="program in programs" :key="program.id" type="button" class="program-card" :class="{ active: operationForm.programId === program.id }" @click="operationForm.programId = program.id"><div class="program-card-mark">{{ program.id }}</div><div><strong>{{ program.name }}</strong><span>{{ program.steps }} 个步骤 · {{ program.duration }}</span></div><i>{{ operationForm.programId === program.id ? '已选择' : '选择' }}</i></button></div>
                  <div class="program-summary"><span>选中程序</span><strong>{{ selectedProgram.name }}</strong><small>执行前请确认保护设定与目标定值</small></div>
                </div>

                <div v-else class="settings-form-grid">
                  <div class="setting-section-title"><span>运行偏好</span><small>设备提示与执行行为</small></div>
                  <label class="setting-toggle-row"><span><strong>运行完成提示音</strong><small>程序结束时播放提示音</small></span><input v-model="operationForm.soundEnabled" type="checkbox"><i></i></label>
                  <label class="setting-toggle-row"><span><strong>自动锁定箱门</strong><small>运行期间禁止打开箱门</small></span><input v-model="operationForm.doorLock" type="checkbox"><i></i></label>
                  <label class="setting-toggle-row"><span><strong>保存运行数据</strong><small>自动保存每次试验的过程数据</small></span><input v-model="operationForm.autoSave" type="checkbox"><i></i></label>
                  <div class="setting-section-title"><span>界面显示</span><small>当前设备本地显示偏好</small></div>
                  <label class="field-control"><span>温度显示精度</span><select v-model="operationForm.precision"><option value="0.1">0.1 °C</option><option value="1">1 °C</option></select></label>
                  <label class="field-control"><span>待机亮度</span><div><span class="hmi-number-control"><input v-model="operationForm.brightness" type="number" min="10" max="100"><span class="hmi-number-steps"><button type="button" title="提高待机亮度" aria-label="提高待机亮度" @click.stop.prevent="stepOperationNumber('brightness', 1, 10, 100)"><AppIcon name="chevronUp" :size="12" /></button><button type="button" title="降低待机亮度" aria-label="降低待机亮度" @click.stop.prevent="stepOperationNumber('brightness', -1, 10, 100)"><AppIcon name="chevronDown" :size="12" /></button></span></span><b>%</b></div></label>
                </div>

                <div class="operation-editor-footer"><span>最后保存：{{ operationLastSaved }}</span><div><button class="ghost-action" type="button" @click="resetOperationForm">恢复默认</button><button class="primary-action" type="button" @click="saveOperationSettings">保存设定</button></div></div>
              </section>
            </div>
          </section>

          <section v-else-if="selectedDevice" class="panel empty-panel">
            <h3>{{ currentDeviceSectionLabel }}</h3>
            <p>{{ currentDeviceSectionDescription }}</p>
          </section>

          <section v-else class="panel empty-panel">
            <h3>设备暂未找到</h3>
            <p>请返回实时列表，重新选择一台在线试验箱。</p>
          </section>
        </section>

        <section v-else-if="activeView === 'memory'" class="page-stack">
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

        <section v-else class="page-stack">
          <div class="section-head">
            <h2>{{ currentTitle }}</h2>
            <span>预留模块</span>
          </div>
          <section class="panel empty-panel">
            <h3>模块待接入</h3>
            <p>这里将接入历史曲线、试验报告、报警处理、配方管理和权限审批。</p>
          </section>
        </section>
      </main>
    </section>

    <div v-if="isNotificationOpen" class="notification-modal-backdrop" @click.self="isNotificationOpen = false">
      <section class="notification-modal" role="dialog" aria-modal="true" aria-labelledby="notification-modal-title">
        <div class="notification-modal-header">
          <div>
            <h3 id="notification-modal-title">{{ notificationTitle }}</h3>
            <span>{{ notificationSubtitle }}</span>
          </div>
          <button class="notification-modal-close" type="button" title="关闭" aria-label="关闭" @click="isNotificationOpen = false">
            <AppIcon name="close" :size="17" />
          </button>
        </div>
        <div class="notification-list">
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
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import LiveMetricCard from "./components/LiveMetricCard.vue";
import LiveDeviceDetailCard from "./components/LiveDeviceDetailCard.vue";
import DeviceOverviewList from "./components/DeviceOverviewList.vue";
import AppIcon from "./components/AppIcon.vue";
import HmiDashboard from "./components/HmiDashboard.vue";

const TREND_PAST_MS = 5 * 60 * 1000;
const TREND_FUTURE_MS = 5 * 60 * 1000;
const TREND_DEFAULT_WINDOW_MS = TREND_PAST_MS + TREND_FUTURE_MS;
const TREND_MIN_WINDOW_MS = 30 * 1000;
const TREND_MAX_WINDOW_MS = 60 * 60 * 1000;
const TREND_HISTORY_RETENTION_MS = 2 * 60 * 60 * 1000;
const TREND_Y_MIN_SCALE = 0.18;
const TREND_Y_MAX_SCALE = 3.5;
const MONITOR_LAYOUT_STORAGE_KEY = "industrial-chamber-monitor-layout-v1";

const activeView = ref("dashboard");
const devices = ref([]);
const snapshot = ref(null);
const routerReadAt = ref(null);
const connectionText = ref("连接中");
const selectedDeviceId = ref(null);
const selectedDeviceSection = ref("monitor");
const operationTab = ref("protection");
const operationFeedback = ref("");
const operationLastSaved = ref("尚未保存");
const operationForm = ref({
  overTempEnabled: true,
  overHumEnabled: true,
  powerMemory: true,
  tempLimit: 85,
  humLimit: 95,
  airTempUpper: 0,
  airTempLower: 0,
  airTempProtectionEnabled: true,
  dutTempUpper: 0,
  dutTempLower: 0,
  dutTempProtectionEnabled: true,
  dutControlAirUpper: 0,
  dutControlAirLower: 0,
  dutControlAirProtectionEnabled: true,
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
  brightness: 80
});
const deviceDisplayMode = ref("list");
const selectedTrendCanvas = ref(null);
const trendHistory = ref({});
const currentTimeText = ref(new Date().toLocaleTimeString());
const commandStatusText = ref("等待操作");
const profileActionText = ref("");
const stoppingDeviceIds = ref({});
const startingDeviceIds = ref({});
const holdingDeviceIds = ref({});
const skippingDeviceIds = ref({});
const trendClockMs = ref(Date.now());
const trendWindowMs = ref(TREND_DEFAULT_WINDOW_MS);
const trendCenterOffsetMs = ref(0);
const trendYScale = ref(1);
const trendYOffsetRatio = ref(0);
const isTrendDragging = ref(false);
const isSidebarCollapsed = ref(false);
const isLayoutEditorOpen = ref(false);
const isNotificationOpen = ref(false);
const visibleMonitorCards = ref(["trend", "status", "communication", "updated"]);
const deviceNotifications = ref([]);
const operationLogs = ref([]);
const previousDeviceStates = ref({});

let socket = null;
let reconnectTimer = null;
let clockTimer = null;
let lastTrendDragX = 0;

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
  { key: "status", label: "运行状态", icon: "activity" },
  { key: "communication", label: "通讯信息", icon: "settings" },
  { key: "updated", label: "数据更新时间", icon: "history" },
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
const defaultMonitorCardKeys = ["trend", "status", "communication", "updated"];
const operationTabs = [
  { key: "protection", label: "保护设定", description: "安全联锁与阈值", icon: "shield" },
  { key: "setpoint", label: "定值模式", description: "温湿度目标控制", icon: "sliders" },
  { key: "program", label: "程序模式", description: "试验程序与步骤", icon: "play" },
  { key: "other", label: "其他设定", description: "设备偏好与显示", icon: "settings" }
];
const protectionItems = [
  { key: "air-temperature", label: "空气温度保护", upper: "airTempUpper", lower: "airTempLower", enabled: "airTempProtectionEnabled" },
  { key: "dut-temperature", label: "试品温度保护", upper: "dutTempUpper", lower: "dutTempLower", enabled: "dutTempProtectionEnabled" },
  { key: "dut-control-air", label: "试品控温空气温度", upper: "dutControlAirUpper", lower: "dutControlAirLower", enabled: "dutControlAirProtectionEnabled" },
  { key: "empty", label: "", empty: true }
];
const controlModes = [
  { key: "precise", label: "精准控制", description: "优先保持目标稳定" },
  { key: "balanced", label: "平衡模式", description: "稳定性与响应速度平衡" },
  { key: "rapid", label: "快速响应", description: "优先快速达到目标" }
];
const programs = [
  { id: "P-01", name: "高低温循环 A", steps: 8, duration: "02:30:00" },
  { id: "P-02", name: "恒温恒湿验证", steps: 4, duration: "08:00:00" },
  { id: "P-03", name: "快速温变测试", steps: 6, duration: "01:45:00" }
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
const activeOperationTab = computed(() => operationTabs.find(item => item.key === operationTab.value) || operationTabs[0]);
const selectedProgram = computed(() => programs.find(item => item.id === operationForm.value.programId) || programs[0]);
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
const sourceName = computed(() => snapshot.value?.source ?? "--");
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
const activeNotifications = computed(() => {
  if (activeView.value === "device-detail") {
    return operationLogs.value.filter(item => !selectedDeviceId.value || item.deviceId === selectedDeviceId.value);
  }
  return deviceNotifications.value;
});
const notificationCount = computed(() => activeNotifications.value.length);
const notificationCountText = computed(() => notificationCount.value > 99 ? "99+" : String(notificationCount.value));
const notificationTitle = computed(() => activeView.value === "device-detail" ? "操作日志" : "设备运行通知");
const notificationSubtitle = computed(() => {
  if (activeView.value === "device-detail") return `${selectedDevice.value?.name || selectedDeviceId.value} 的远程控制记录`;
  return "记录设备启动、停止、断开连接等运行状态变化";
});
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
  if (["STOPPED", "STOPPING", "ABORTING", "OFFLINE"].includes(device.run_state)) return "stopped";
  if (device.run_state === "IDLE") return "idle";
  return "running";
}

function formatNumber(value) {
  return Number(value ?? 0).toFixed(1);
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
  selectedDeviceSection.value = "monitor";
  activeView.value = "device-detail";
}

function returnToDashboard() {
  activeView.value = "dashboard";
  isSidebarCollapsed.value = false;
}

function openProfile() {
  profileActionText.value = "";
  activeView.value = "profile";
  isSidebarCollapsed.value = false;
}

function handleSidebarSelect(item) {
  if (item.scope === "device") {
    selectedDeviceSection.value = item.key;
    return;
  }
  activeView.value = item.key;
}

function saveOperationSettings() {
  operationLastSaved.value = new Date().toLocaleTimeString("zh-CN", { hour12: false });
  operationFeedback.value = "已保存";
  addOperationLog({ title: "保存操作设定", message: `${selectedDevice.value?.name || selectedDeviceId.value} 已更新${activeOperationTab.value.label}`, tone: "success" });
  window.setTimeout(() => { operationFeedback.value = ""; }, 2200);
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

function resetOperationForm() {
  operationForm.value = {
    ...operationForm.value,
    overTempEnabled: true, overHumEnabled: true, powerMemory: true,
    tempLimit: 85, humLimit: 95, airTempUpper: 0, airTempLower: 0, airTempProtectionEnabled: true, dutTempUpper: 0, dutTempLower: 0, dutTempProtectionEnabled: true, dutControlAirUpper: 0, dutControlAirLower: 0, dutControlAirProtectionEnabled: true, targetTemp: 25, targetHum: 50,
    tempRamp: 1.5, humRamp: 2, runtimeHours: 0, runtimeMinutes: 30, runtimeSeconds: 0, controlMode: "balanced", programId: "P-01",
    soundEnabled: true, doorLock: true, autoSave: true, precision: "0.1", brightness: 80
  };
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

async function stopSelectedDevice() {
  if (!selectedDevice.value) return;
  const deviceId = selectedDevice.value.device_id;
  const deviceName = selectedDevice.value.name || deviceId;
  stoppingDeviceIds.value = { ...stoppingDeviceIds.value, [deviceId]: true };
  commandStatusText.value = "正在下发停止命令";
  addOperationLog({ title: "停止运行", message: `${deviceName} 正在下发停止命令`, tone: "warning", deviceId });

  try {
    const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/stop-requests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        operator_id: "web-admin",
        reason: "stop requested from Vue dashboard"
      })
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || result.message || "停止命令下发失败");
    }
    commandStatusText.value = "停止命令已下发";
    addOperationLog({ title: "停止运行", message: `${deviceName} 停止命令已下发`, tone: "danger", deviceId });
  } catch (error) {
    commandStatusText.value = error.message || "停止命令下发失败";
    addOperationLog({ title: "停止运行", message: `${deviceName} 停止命令下发失败`, tone: "danger", deviceId });
  } finally {
    stoppingDeviceIds.value = { ...stoppingDeviceIds.value, [deviceId]: false };
  }
}

async function startSelectedDevice() {
  if (!selectedDevice.value) return;
  const deviceId = selectedDevice.value.device_id;
  const deviceName = selectedDevice.value.name || deviceId;
  startingDeviceIds.value = { ...startingDeviceIds.value, [deviceId]: true };
  commandStatusText.value = "正在下发启动命令";
  addOperationLog({ title: "启动运行", message: `${deviceName} 正在下发启动命令`, tone: "warning", deviceId });

  try {
    const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/start-requests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        operator_id: "web-admin",
        reason: "start requested from Vue dashboard",
        target_temperature: Number(selectedDevice.value.target_temperature ?? selectedDevice.value.current_temperature ?? 25),
        target_humidity: Number(selectedDevice.value.target_humidity ?? selectedDevice.value.current_humidity ?? 60)
      })
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || result.message || "启动命令下发失败");
    }
    commandStatusText.value = "启动命令已下发";
    addOperationLog({ title: "启动运行", message: `${deviceName} 启动命令已下发`, tone: "success", deviceId });
  } catch (error) {
    commandStatusText.value = error.message || "启动命令下发失败";
    addOperationLog({ title: "启动运行", message: `${deviceName} 启动命令下发失败`, tone: "danger", deviceId });
  } finally {
    startingDeviceIds.value = { ...startingDeviceIds.value, [deviceId]: false };
  }
}

async function holdSelectedDevice() {
  if (!selectedDevice.value) return;
  const deviceId = selectedDevice.value.device_id;
  const deviceName = selectedDevice.value.name || deviceId;
  holdingDeviceIds.value = { ...holdingDeviceIds.value, [deviceId]: true };
  commandStatusText.value = "正在下发保持命令";
  addOperationLog({ title: "保持", message: `${deviceName} 正在下发保持命令`, tone: "warning", deviceId });

  try {
    const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/hold-requests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        operator_id: "web-admin",
        reason: "hold requested from Vue dashboard"
      })
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || result.message || "保持命令下发失败");
    }
    commandStatusText.value = "保持命令已下发";
    addOperationLog({ title: "保持", message: `${deviceName} 保持命令已下发`, tone: "success", deviceId });
  } catch (error) {
    commandStatusText.value = error.message || "保持命令下发失败";
    addOperationLog({ title: "保持", message: `${deviceName} 保持命令下发失败`, tone: "danger", deviceId });
  } finally {
    holdingDeviceIds.value = { ...holdingDeviceIds.value, [deviceId]: false };
  }
}

async function skipSelectedDeviceStep() {
  if (!selectedDevice.value) return;
  const deviceId = selectedDevice.value.device_id;
  const deviceName = selectedDevice.value.name || deviceId;
  skippingDeviceIds.value = { ...skippingDeviceIds.value, [deviceId]: true };
  commandStatusText.value = "正在下发跳步命令";
  addOperationLog({ title: "跳步", message: `${deviceName} 正在下发跳步命令`, tone: "warning", deviceId });

  try {
    const response = await fetch(`/api/devices/${encodeURIComponent(deviceId)}/skip-step-requests`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        operator_id: "web-admin",
        reason: "step skip requested from Vue dashboard"
      })
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(result.detail || result.message || "跳步命令下发失败");
    }
    commandStatusText.value = "跳步命令已下发";
    addOperationLog({ title: "跳步", message: `${deviceName} 跳步命令已下发`, tone: "success", deviceId });
  } catch (error) {
    commandStatusText.value = error.message || "跳步命令下发失败";
    addOperationLog({ title: "跳步", message: `${deviceName} 跳步命令下发失败`, tone: "danger", deviceId });
  } finally {
    skippingDeviceIds.value = { ...skippingDeviceIds.value, [deviceId]: false };
  }
}

function connectSocket() {
  const protocol = location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(`${protocol}://${location.host}/ws/memory`);

  socket.onopen = () => {
    connectionText.value = "已连接";
  };

  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.type === "memory_not_ready") {
      connectionText.value = "共享内存未就绪";
      return;
    }

    snapshot.value = message.snapshot;
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

  socket.onclose = () => {
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
    ctx.fillStyle = "#0b1020";
    ctx.fillRect(0, 0, width, height);

    ctx.strokeStyle = "#293142";
    ctx.lineWidth = 1;
    ctx.font = "12px Microsoft YaHei";
    ctx.fillStyle = "#94a3b8";

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
      ctx.fillStyle = "#64748b";
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
  ctx.fillStyle = "#94a3b8";
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

    ctx.fillStyle = "#60a5fa";
    ctx.textAlign = "right";
    ctx.fillText(`${tempValue.toFixed(1)}C`, padLeft - 8, y + 4);

    ctx.fillStyle = "#34d399";
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
  connectSocket();
  window.addEventListener("resize", handleTrendResize);
  clockTimer = window.setInterval(() => {
    currentTimeText.value = new Date().toLocaleTimeString();
    trendClockMs.value = Date.now();
    drawSelectedTrend();
  }, 1000);
});

onBeforeUnmount(() => {
  if (socket) socket.close();
  if (reconnectTimer) window.clearTimeout(reconnectTimer);
  if (clockTimer) window.clearInterval(clockTimer);
  window.removeEventListener("resize", handleTrendResize);
});

watch([activeView, selectedDeviceId, selectedDeviceSection, visibleMonitorCards], () => nextTick(drawSelectedTrend));
</script>
