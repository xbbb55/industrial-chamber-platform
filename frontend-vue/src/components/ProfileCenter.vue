<template>
  <div class="profile-center">
  <section class="page-stack profile-page">
    <div class="section-head profile-section-head profile-page-head">
      <div>
        <h2>个人中心</h2>
        <span>查看账户资料、维护登录凭据和管理平台账户</span>
      </div>
      <nav ref="profileTabNav" class="profile-tabs motion-nav" :class="{ 'motion-ready': profileIndicator }" aria-label="个人中心页面">
        <span v-if="profileIndicator" class="motion-selection" :style="profileIndicator" aria-hidden="true"></span>
        <button data-motion-key="profile" type="button" :class="{ active: activeTab === 'profile' }" @click="selectTab('profile')">个人中心</button>
        <button data-motion-key="logs" type="button" :class="{ active: activeTab === 'logs' }" @click="selectTab('logs')">操作日志</button>
      </nav>
      <button class="profile-back-button" type="button" @click="emit('back')">
        <AppIcon name="gauge" :size="16" />
        <span>返回</span>
      </button>
    </div>

    <Transition name="settings-tab" mode="out-in">
    <div v-if="activeTab === 'profile'" key="profile" class="profile-tab-content">
    <section class="profile-hero panel" aria-label="当前账户概览">
      <div class="profile-identity-block">
        <div class="profile-avatar">{{ avatarText }}</div>
        <div class="profile-identity">
          <div class="profile-name-row">
            <h3>{{ user.display_name }}</h3>
            <span class="profile-status"><i></i>在线</span>
          </div>
          <p>{{ user.role_label }} · 工业试验箱平台</p>
          <span class="profile-id">账户：{{ user.username }}</span>
        </div>
      </div>
      <div class="profile-hero-summary">
        <div class="profile-summary-item">
          <span>权限组</span>
          <strong>{{ user.role_label }}</strong>
        </div>
        <div class="profile-summary-item">
          <span>会话状态</span>
          <strong class="profile-online-value">已验证</strong>
        </div>
        <div class="profile-summary-item profile-session-time">
          <span>当前会话</span>
          <strong>{{ currentTime }}</strong>
        </div>
      </div>
    </section>

    <div class="profile-grid">
      <section class="panel profile-info-panel">
        <div class="panel-title profile-panel-heading">
          <div><h3>个人资料</h3><span>账户登记信息</span></div>
          <AppIcon name="users" :size="18" />
        </div>
        <dl class="profile-fields">
          <div><dt>姓名</dt><dd>{{ user.display_name }}</dd></div>
          <div><dt>权限组</dt><dd>{{ user.role_label }}</dd></div>
          <div><dt>账户名</dt><dd>{{ user.username }}</dd></div>
          <div><dt>所属组织</dt><dd>工业试验箱控制中心</dd></div>
          <div><dt>联系电话</dt><dd class="profile-empty-value">未设置</dd></div>
          <div><dt>时区</dt><dd>Asia/Shanghai (UTC+8)</dd></div>
        </dl>
      </section>

      <section class="panel profile-security-panel">
        <div class="panel-title profile-panel-heading">
          <div><h3>账户安全</h3><span>密码规则：至少 5 位数字</span></div>
          <AppIcon name="shield" :size="18" />
        </div>
        <div class="security-item security-item-primary">
          <AppIcon name="key" :size="17" />
          <div><strong>登录密码</strong><span>更新后将退出当前账户并要求重新登录</span></div>
          <button type="button" @click="openPasswordDialog">修改</button>
        </div>
        <div class="security-item">
          <AppIcon name="shield" :size="17" />
          <div><strong>权限组</strong><span>权限在登录后按权限组统一生效</span></div>
          <strong class="role-value">{{ user.role_label }}</strong>
        </div>
        <div v-if="canManageUsers" class="security-item">
          <AppIcon name="users" :size="17" />
          <div><strong>用户管理</strong><span>可创建用户并调整权限组</span></div>
          <button type="button" @click="loadUsers">刷新</button>
        </div>
      </section>
    </div>

    <section v-if="canManageUsers" class="panel profile-users-panel">
      <div class="panel-title profile-users-title">
        <div><h3>用户管理</h3><span>当前所有权限组均可访问；可调整账户权限组</span></div>
        <div class="profile-users-actions">
          <div class="profile-user-count" aria-label="账户统计"><strong>{{ users.length }}</strong><span>个账户</span></div>
        <button class="profile-primary-button" type="button" @click="openCreateUserDialog">
          <AppIcon name="plus" :size="16" />
          <span>新增用户</span>
        </button>
        </div>
      </div>
      <div class="profile-role-note"><AppIcon name="shield" :size="15" /><span>当前管理员、工程师与销售拥有相同业务权限。</span></div>
      <p v-if="usersError" class="profile-error" role="alert">{{ usersError }}</p>
      <div v-if="users.length" class="user-list" role="table" aria-label="用户列表">
        <div class="user-list-head" role="row"><span>用户</span><span>账户名</span><span>权限组</span><span>操作</span></div>
        <div v-for="account in users" :key="account.username" class="user-list-row" role="row">
          <div><strong>{{ account.display_name }}</strong><small>{{ account.username === user.username ? '当前账户' : '平台用户' }}</small></div>
          <span class="user-login-name">{{ account.username }}</span>
          <label class="role-select"><span class="sr-only">{{ account.display_name }} 的权限组</span><select v-model="account.role" :disabled="updatingUsername === account.username"><option v-for="role in roles" :key="role.value" :value="role.value">{{ role.label }}</option></select></label>
          <button class="user-save-button" type="button" :disabled="updatingUsername === account.username" @click="saveRole(account)">{{ updatingUsername === account.username ? '保存中' : '保存' }}</button>
        </div>
      </div>
      <div v-else-if="!usersLoading" class="profile-loading">暂无账户，可使用“新增用户”创建。</div>
    </section>

    <div class="profile-logout-row">
      <button class="profile-logout-button" type="button" @click="emit('logout')">
        <AppIcon name="logout" :size="16" />
        <span>退出登录</span>
      </button>
    </div>
    </div>

    <section v-else key="logs" class="panel operation-log-panel" aria-labelledby="operation-log-title">
      <div class="panel-title operation-log-title">
        <div><h3 id="operation-log-title">操作日志</h3><span>记录账户登录、设备控制与参数修改等操作</span></div>
        <button class="profile-secondary-button" type="button" :disabled="logsLoading" @click="loadOperationLogs(1)">刷新</button>
      </div>

      <form class="operation-log-filters" @submit.prevent="loadOperationLogs(1)">
        <label v-if="canViewAllLogs"><span>用户</span><input v-model.trim="logFilters.username" type="search" placeholder="全部用户"></label>
        <label><span>操作分类</span><select v-model="logFilters.category"><option value="">全部分类</option><option v-for="category in logCategories" :key="category.value" :value="category.value">{{ category.label }}</option></select></label>
        <label><span>操作结果</span><select v-model="logFilters.status"><option value="">全部结果</option><option value="SUCCESS">成功</option><option value="FAILED">失败</option><option value="PENDING">处理中</option></select></label>
        <label><span>开始时间</span><input v-model="logFilters.startTime" type="datetime-local"></label>
        <label><span>结束时间</span><input v-model="logFilters.endTime" type="datetime-local"></label>
        <div class="operation-log-filter-actions"><button class="profile-secondary-button" type="button" @click="resetLogFilters">重置</button><button class="profile-primary-button" type="submit">查询</button></div>
      </form>

      <p v-if="logsError" class="profile-error" role="alert">{{ logsError }}</p>
      <div v-if="operationLogs.length" class="operation-log-table-wrap">
        <div class="operation-log-table" role="table" aria-label="用户操作日志">
          <div class="operation-log-head" role="row"><span role="columnheader">用户</span><span role="columnheader">时间</span><span role="columnheader">操作</span><span role="columnheader">结果</span></div>
          <div v-for="log in operationLogs" :key="log.id" class="operation-log-row" role="row">
            <div role="cell"><strong>{{ log.display_name }}</strong><small>{{ log.username }}</small></div>
            <time role="cell" :datetime="new Date(log.created_at * 1000).toISOString()">{{ formatLogTime(log.created_at) }}</time>
            <div class="operation-log-action" role="cell">
              <strong>{{ log.action_summary }}</strong>
              <small>{{ log.action_category_label }}</small>
              <details v-if="log.details"><summary>查看详情</summary><pre>{{ formatLogDetails(log.details) }}</pre></details>
            </div>
            <span role="cell" class="operation-log-status" :class="log.result_status.toLowerCase()">{{ logStatusLabel(log.result_status) }}</span>
          </div>
        </div>
      </div>
      <div v-else-if="!logsLoading" class="profile-loading operation-log-state">当前筛选条件下暂无操作日志。</div>

      <footer class="operation-log-pagination">
        <span>共 {{ logsTotal }} 条，第 {{ logsPage }} / {{ logsTotalPages }} 页</span>
        <div><button class="profile-secondary-button" type="button" :disabled="logsLoading || logsPage <= 1" @click="loadOperationLogs(logsPage - 1)">上一页</button><button class="profile-secondary-button" type="button" :disabled="logsLoading || logsPage >= logsTotalPages" @click="loadOperationLogs(logsPage + 1)">下一页</button></div>
      </footer>
    </section>
    </Transition>
  </section>

  <MotionDialog :open="isPasswordDialogOpen" backdrop-class="profile-modal-backdrop" panel-class="profile-dialog-shell" labelledby="password-modal-title" @close="closePasswordDialog">
    <form class="profile-modal" aria-labelledby="password-modal-title" @submit.prevent="changePassword">
      <div class="profile-modal-header"><div><h3 id="password-modal-title">修改登录密码</h3><span>新密码必须至少为 5 位数字。</span></div><button type="button" aria-label="关闭" @click="closePasswordDialog"><AppIcon name="close" :size="17" /></button></div>
      <div class="profile-form-fields">
        <label>当前密码<input v-model="passwordForm.current_password" type="password" autocomplete="current-password" data-dialog-autofocus required /></label>
        <label>新密码<input v-model="passwordForm.new_password" type="password" inputmode="numeric" pattern="[0-9]{5,}" autocomplete="new-password" required /></label>
        <label>确认新密码<input v-model="passwordForm.confirm_password" type="password" inputmode="numeric" pattern="[0-9]{5,}" autocomplete="new-password" required /></label>
      </div>
      <p v-if="passwordError" class="profile-error" role="alert">{{ passwordError }}</p>
      <p v-if="passwordSuccess" class="profile-success" role="status">{{ passwordSuccess }}</p>
      <div class="profile-modal-footer"><button class="profile-secondary-button" type="button" :disabled="passwordSaving" @click="closePasswordDialog">取消</button><button class="profile-primary-button" type="submit" :disabled="passwordSaving">{{ passwordSaving ? '保存中…' : '确认修改' }}</button></div>
    </form>
  </MotionDialog>

  <MotionDialog :open="isCreateUserDialogOpen" backdrop-class="profile-modal-backdrop" panel-class="profile-dialog-shell" labelledby="create-user-modal-title" @close="closeCreateUserDialog">
    <form class="profile-modal" aria-labelledby="create-user-modal-title" @submit.prevent="createUser">
      <div class="profile-modal-header"><div><h3 id="create-user-modal-title">新增用户</h3><span>初始密码必须至少为 5 位数字。</span></div><button type="button" aria-label="关闭" @click="closeCreateUserDialog"><AppIcon name="close" :size="17" /></button></div>
      <div class="profile-form-fields">
        <label>姓名<input v-model.trim="newUserForm.display_name" autocomplete="name" data-dialog-autofocus required /></label>
        <label>账户名<input v-model.trim="newUserForm.username" autocomplete="username" pattern="[A-Za-z0-9_.-]+" required /></label>
        <label>初始密码<input v-model="newUserForm.password" type="password" inputmode="numeric" pattern="[0-9]{5,}" autocomplete="new-password" required /></label>
        <label>权限组<select v-model="newUserForm.role"><option v-for="role in roles" :key="role.value" :value="role.value">{{ role.label }}</option></select></label>
      </div>
      <p v-if="createUserError" class="profile-error" role="alert">{{ createUserError }}</p>
      <div class="profile-modal-footer"><button class="profile-secondary-button" type="button" :disabled="creatingUser" @click="closeCreateUserDialog">取消</button><button class="profile-primary-button" type="submit" :disabled="creatingUser">{{ creatingUser ? '创建中…' : '创建用户' }}</button></div>
    </form>
  </MotionDialog>
  <WorkspaceRefresh
    :target="refreshTarget"
    :pending="activeTab === 'logs' ? logsRefresh.state.pending : usersRefresh.state.pending"
    :visible="activeTab === 'logs' ? logsRefresh.state.visible : usersRefresh.state.visible"
    :error="activeTab === 'logs' ? logsRefresh.state.error : usersRefresh.state.error"
    title="正在读取个人中心"
    complete-title="个人中心已更新"
    error-title="个人中心读取失败"
    @retry="activeTab === 'logs' ? loadOperationLogs(logsPage) : loadUsers()"
    @dismiss="dismissRefreshNotice"
  />
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import AppIcon from "./AppIcon.vue";
import MotionDialog from "./MotionDialog.vue";
import { useSelectionIndicator } from "../composables/useSelectionIndicator";
import WorkspaceRefresh from "./WorkspaceRefresh.vue";
import { useRefreshTask } from "../composables/useRefreshTask";

const props = defineProps({
  user: { type: Object, required: true },
  currentTime: { type: String, required: true },
  refreshTarget: { type: Object, default: null }
});
const emit = defineEmits(["back", "logout", "user-updated"]);
const roles = [
  { value: "ADMIN", label: "管理员" },
  { value: "ENGINEER", label: "工程师" },
  { value: "SALES", label: "销售" }
];
const users = ref([]);
const usersLoading = ref(false);
const usersError = ref("");
const updatingUsername = ref("");
const isPasswordDialogOpen = ref(false);
const passwordSaving = ref(false);
const passwordError = ref("");
const passwordSuccess = ref("");
const passwordForm = ref({ current_password: "", new_password: "", confirm_password: "" });
const isCreateUserDialogOpen = ref(false);
const creatingUser = ref(false);
const createUserError = ref("");
const newUserForm = ref({ display_name: "", username: "", password: "", role: "ENGINEER" });
const activeTab = ref("profile");
const profileTabNav = ref(null);
const profileIndicator = useSelectionIndicator(profileTabNav, activeTab);
const operationLogs = ref([]);
const logsLoading = ref(false);
const logsError = ref("");
const logsPage = ref(1);
const logsTotal = ref(0);
const logsTotalPages = ref(1);
const logCategories = ref([
  { value: "AUTH", label: "登录认证" },
  { value: "DEVICE", label: "设备控制" },
  { value: "SETTINGS", label: "参数设置" },
  { value: "PROGRAM", label: "程序管理" },
  { value: "DOWNLOAD", label: "下载导出" },
  { value: "ACCOUNT", label: "账户管理" }
]);
const logFilters = ref({ username: "", category: "", status: "", startTime: "", endTime: "" });
const usersRefresh = useRefreshTask();
const logsRefresh = useRefreshTask();

const canManageUsers = computed(() => props.user.permissions?.includes("user.manage") ?? true);
const canViewAllLogs = computed(() => props.user.role === "ADMIN");
const avatarText = computed(() => String(props.user.display_name || props.user.username || "A").slice(0, 1).toUpperCase());

function authHeaders() {
  return { "Content-Type": "application/json", Authorization: `Bearer ${window.localStorage.getItem("industrial-auth-token") || ""}` };
}

async function request(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { ...authHeaders(), ...(options.headers || {}) } });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) emit("logout");
    throw new Error(body.detail || "请求失败，请稍后重试");
  }
  return body;
}

function selectTab(tab) {
  activeTab.value = tab;
  if (tab === "logs") loadOperationLogs(1);
  else if (canManageUsers.value) loadUsers();
}

async function loadOperationLogs(page = logsPage.value) {
  if (logsLoading.value) logsRefresh.cancel();
  logsLoading.value = true;
  logsError.value = "";
  const parameters = new URLSearchParams({ page: String(page), page_size: "20" });
  if (canViewAllLogs.value && logFilters.value.username) parameters.set("username", logFilters.value.username);
  if (logFilters.value.category) parameters.set("category", logFilters.value.category);
  if (logFilters.value.status) parameters.set("status", logFilters.value.status);
  if (logFilters.value.startTime) parameters.set("start_time", String(new Date(logFilters.value.startTime).getTime() / 1000));
  if (logFilters.value.endTime) parameters.set("end_time", String(new Date(logFilters.value.endTime).getTime() / 1000));
  await logsRefresh.run(
    signal => request(`/api/operation-logs?${parameters}`, { signal }),
    result => {
      operationLogs.value = result.items || [];
      logsPage.value = result.page || page;
      logsTotal.value = result.total || 0;
      logsTotalPages.value = result.total_pages || 1;
      if (result.categories?.length) logCategories.value = result.categories;
    }
  );
  logsError.value = logsRefresh.state.error;
  logsLoading.value = false;
}

function resetLogFilters() {
  logFilters.value = { username: "", category: "", status: "", startTime: "", endTime: "" };
  loadOperationLogs(1);
}

function formatLogTime(timestamp) {
  return new Date(Number(timestamp) * 1000).toLocaleString("zh-CN", { hour12: false });
}

function formatLogDetails(details) {
  return JSON.stringify(details, null, 2);
}

function logStatusLabel(status) {
  return ({ SUCCESS: "成功", FAILED: "失败", PENDING: "处理中" })[status] || status;
}

function resetPasswordForm() {
  passwordForm.value = { current_password: "", new_password: "", confirm_password: "" };
  passwordError.value = "";
  passwordSuccess.value = "";
}

function openPasswordDialog() {
  resetPasswordForm();
  isPasswordDialogOpen.value = true;
}

function closePasswordDialog() {
  if (passwordSaving.value) return;
  isPasswordDialogOpen.value = false;
}

async function changePassword() {
  passwordError.value = "";
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    passwordError.value = "两次输入的新密码不一致";
    return;
  }
  passwordSaving.value = true;
  try {
    const result = await request("/api/auth/password", { method: "PUT", body: JSON.stringify({ current_password: passwordForm.value.current_password, new_password: passwordForm.value.new_password }) });
    passwordSuccess.value = result.message;
    window.setTimeout(() => emit("logout"), 900);
  } catch (error) {
    passwordError.value = error.message;
  } finally {
    passwordSaving.value = false;
  }
}

async function loadUsers() {
  if (!canManageUsers.value) return;
  usersRefresh.cancel();
  usersLoading.value = true;
  usersError.value = "";
  await usersRefresh.run(
    signal => request("/api/auth/users", { signal }),
    result => { users.value = result.users || []; }
  );
  usersError.value = usersRefresh.state.error;
  usersLoading.value = false;
}

function dismissRefreshNotice() {
  const refresh = activeTab.value === "logs" ? logsRefresh : usersRefresh;
  refresh.dismissError();
}

async function saveRole(account) {
  updatingUsername.value = account.username;
  usersError.value = "";
  try {
    const result = await request(`/api/auth/users/${encodeURIComponent(account.username)}/role`, { method: "PUT", body: JSON.stringify({ role: account.role }) });
    Object.assign(account, result.user);
    if (account.username === props.user.username) {
      emit("user-updated", result.user);
      window.setTimeout(() => emit("logout"), 500);
    }
  } catch (error) {
    usersError.value = error.message;
    await loadUsers();
  } finally {
    updatingUsername.value = "";
  }
}

function openCreateUserDialog() {
  createUserError.value = "";
  newUserForm.value = { display_name: "", username: "", password: "", role: "ENGINEER" };
  isCreateUserDialogOpen.value = true;
}

function closeCreateUserDialog() {
  if (!creatingUser.value) isCreateUserDialogOpen.value = false;
}

async function createUser() {
  createUserError.value = "";
  creatingUser.value = true;
  try {
    const result = await request("/api/auth/users", { method: "POST", body: JSON.stringify(newUserForm.value) });
    users.value = [...users.value, result.user];
    isCreateUserDialogOpen.value = false;
  } catch (error) {
    createUserError.value = error.message;
  } finally {
    creatingUser.value = false;
  }
}

watch(canManageUsers, allowed => {
  if (allowed) loadUsers();
}, { immediate: true });
</script>

<style scoped>
.profile-center { display: flex; flex: 1 0 auto; flex-direction: column; min-width: 0; }
.profile-page { gap: 16px; padding-bottom: 28px; }
.profile-page-head { min-height: 52px; }
.profile-page-head h2 { margin-top: 2px; }
.profile-tabs { display: flex; align-self: center; gap: 4px; margin-right: auto; margin-left: 28px; padding: 0; border: 1px solid transparent; border-radius: 5px; background: transparent; }
.profile-tabs button { min-width: 92px; min-height: 34px; padding: 7px 14px; border: 1px solid transparent; border-radius: 4px; background: transparent; color: var(--ink-muted, #80a7bd); font-size: 12px; font-weight: 700; cursor: pointer; }
.profile-tabs button:hover { color: var(--ink-strong, #e2f7ff); }
.profile-tabs button.active { border-color: #2787b4; background: transparent; color: var(--ink-strong, #e2f7ff); }
.profile-hero { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 28px; min-height: 154px; padding: 24px 28px; border-color: rgba(65, 196, 255, .5); background: linear-gradient(90deg, rgba(14, 68, 107, .3) 1px, transparent 1px) 0 0 / 36px 36px, linear-gradient(rgba(14, 68, 107, .2) 1px, transparent 1px) 0 0 / 36px 36px, radial-gradient(circle at 10% 0%, rgba(39, 184, 244, .28), transparent 32%), linear-gradient(115deg, #0a2a47, #07192c 66%, #061422); }
.profile-hero::after { left: 28px; right: 28px; bottom: 14px; }
.profile-identity-block { position: relative; z-index: 1; display: flex; align-items: center; gap: 16px; min-width: 0; }
.profile-avatar { width: 76px; height: 76px; border-radius: 12px; background: linear-gradient(145deg, #258fcd, #102f59); }
.profile-identity { gap: 8px; }
.profile-name-row h3 { font-size: 24px; letter-spacing: .02em; }
.profile-hero-summary { position: relative; z-index: 1; display: grid; grid-template-columns: repeat(3, minmax(104px, 1fr)); align-self: stretch; overflow: hidden; border: 1px solid rgba(92, 206, 255, .2); border-radius: 6px; background: rgba(3, 22, 39, .44); }
.profile-summary-item { display: grid; align-content: center; gap: 7px; min-width: 104px; padding: 12px 16px; border-left: 1px solid rgba(92, 206, 255, .16); }
.profile-summary-item:first-child { border-left: 0; }
.profile-summary-item span { color: #79a9c2; font-size: 10px; font-weight: 700; letter-spacing: .08em; }
.profile-summary-item strong { color: #e3f8ff; font-size: 13px; white-space: nowrap; }
.profile-summary-item.profile-session-time strong { color: #9ce8ff; font-family: "Roboto Mono", Consolas, monospace; }
.profile-online-value { color: #70ec91 !important; }
.profile-info-panel, .profile-security-panel, .profile-users-panel { padding: 20px; }
.profile-panel-heading { align-items: flex-start; min-height: 28px; }
.profile-panel-heading > div, .profile-users-title > div:first-child { display: grid; gap: 5px; }
.profile-panel-heading span, .profile-users-title > div > span { color: #7396ad; font-size: 11px; }
.profile-panel-heading > svg { color: #52ceff; }
.profile-fields { margin: 18px 0 0; gap: 10px; }
.profile-fields > div { min-height: 60px; padding: 12px 13px; border-color: rgba(57, 176, 234, .22); background: linear-gradient(135deg, rgba(8, 43, 70, .8), rgba(5, 27, 47, .64)); }
.profile-fields dt { color: #7fa9c0; font-size: 10px; font-weight: 700; letter-spacing: .08em; }
.profile-fields dd { margin: 0; overflow: hidden; color: #d8f2fc; font-size: 13px; font-weight: 700; text-overflow: ellipsis; white-space: nowrap; }
.profile-empty-value { color: #8cadbe !important; font-weight: 500 !important; }
.profile-security-panel { display: flex; flex-direction: column; }
.security-item { min-height: 68px; gap: 12px; padding: 12px 0; }
.security-item-primary { margin-top: 8px; padding: 12px; border: 1px solid rgba(59, 190, 250, .25); border-radius: 6px; background: rgba(7, 40, 66, .54); }
.security-item-primary + .security-item { margin-top: 3px; }
.security-item > svg { width: 34px; height: 34px; padding: 8px; border: 1px solid rgba(70, 195, 250, .24); border-radius: 5px; background: rgba(14, 69, 105, .34); color: #64d8ff; }
.security-item button { min-width: 58px; }
.profile-users-panel { display: grid; gap: 0; }
.profile-users-title { align-items: center; }
.profile-users-actions { display: flex; align-items: center; gap: 10px; }
.profile-user-count { display: flex; align-items: baseline; gap: 4px; padding: 0 10px; color: #7fa7bd; font-size: 11px; }
.profile-user-count strong { color: #83e2ff; font-family: "Roboto Mono", Consolas, monospace; font-size: 17px; }
.profile-role-note { display: flex; align-items: center; gap: 7px; margin-top: 16px; padding: 9px 11px; border-left: 2px solid #3cbdf4; border-radius: 3px; background: rgba(8, 46, 75, .5); color: #8eb7cc; font-size: 11px; }
.profile-role-note svg { flex: 0 0 auto; color: #5cd5ff; }
.profile-primary-button, .profile-secondary-button, .user-save-button { display: inline-flex; align-items: center; justify-content: center; gap: 7px; min-height: 34px; border: 1px solid rgba(42, 164, 239, .44); border-radius: 5px; padding: 7px 11px; font-size: 12px; font-weight: 700; cursor: pointer; }
.profile-primary-button { background: #1768ad; color: #effbff; }
.profile-primary-button:hover:not(:disabled) { background: #2380cb; }
.profile-secondary-button, .user-save-button { background: rgba(8, 39, 67, .86); color: #bfeaff; }
.profile-secondary-button:hover:not(:disabled), .user-save-button:hover:not(:disabled) { border-color: #36c5ff; background: rgba(13, 86, 131, .84); }
.profile-primary-button:disabled, .profile-secondary-button:disabled, .user-save-button:disabled { cursor: not-allowed; opacity: .58; }
.role-value { color: #8adfff; font-size: 12px; }
.user-list { margin-top: 14px; border: 1px solid rgba(42, 164, 239, .24); border-radius: 6px; overflow: hidden; }
.user-list-head, .user-list-row { display: grid; grid-template-columns: minmax(150px, 1.25fr) minmax(120px, 1fr) minmax(120px, .8fr) 64px; gap: 12px; align-items: center; padding: 10px 12px; }
.user-list-head { background: rgba(10, 57, 91, .68); color: #91bad0; font-size: 10px; font-weight: 800; letter-spacing: .06em; }
.user-list-row { border-top: 1px solid rgba(42, 164, 239, .14); color: #cae8f5; font-size: 12px; transition: background .16s ease; }
.user-list-row:hover { background: rgba(20, 94, 137, .18); }
.user-list-row > div { display: grid; gap: 3px; min-width: 0; }
.user-list-row strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.user-list-row small { color: #7396ad; font-size: 10px; }
.user-login-name { color: #8bc3dd; font-family: "Roboto Mono", Consolas, monospace; font-size: 11px; }
.role-select select, .profile-form-fields input, .profile-form-fields select { width: 100%; border: 1px solid rgba(42, 164, 239, .3); border-radius: 4px; background: rgba(4, 26, 45, .9); color: #e5f8ff; outline: none; }
.role-select select { min-height: 32px; padding: 5px 8px; font-size: 12px; }
.role-select select:focus, .profile-form-fields input:focus, .profile-form-fields select:focus { border-color: #36c5ff; box-shadow: 0 0 0 2px rgba(54, 197, 255, .14); }
.profile-loading, .profile-error, .profile-success { margin: 14px 0 0; font-size: 12px; }
.profile-loading { color: #8fb2c9; }
.profile-error { color: #ffadb4; }
.profile-success { color: #72eb92; }
.operation-log-panel { display: grid; gap: 16px; padding: 20px; }
.operation-log-title > div { display: grid; gap: 5px; }
.operation-log-title h3 { margin: 0; }
.operation-log-title span { color: var(--ink-muted, #7396ad); font-size: 11px; }
.operation-log-filters { display: grid; grid-template-columns: repeat(auto-fit, minmax(145px, 1fr)); gap: 12px; align-items: end; padding: 14px; border: 1px solid var(--card-divider, rgba(42, 164, 239, .18)); border-radius: 5px; background: var(--card-surface-muted, rgba(5, 31, 52, .5)); }
.operation-log-filters label { display: grid; gap: 6px; color: var(--ink-muted, #8fb2c9); font-size: 11px; font-weight: 700; }
.operation-log-filters input,
.operation-log-filters select { width: 100%; min-height: 36px; box-sizing: border-box; padding: 7px 9px; border: 1px solid var(--field-border, rgba(42, 164, 239, .3)); border-radius: 4px; outline: none; background: var(--field-surface, rgba(4, 26, 45, .9)); color: var(--ink, #e5f8ff); font: inherit; }
.operation-log-filters input:focus,
.operation-log-filters select:focus { border-color: #36a9d5; box-shadow: 0 0 0 2px rgba(54, 169, 213, .14); }
.operation-log-filter-actions { display: flex; justify-content: flex-end; gap: 8px; }
.operation-log-table-wrap { overflow-x: auto; border: 1px solid var(--card-divider, rgba(42, 164, 239, .22)); border-radius: 5px; }
.operation-log-table { min-width: 760px; }
.operation-log-head,
.operation-log-row { display: grid; grid-template-columns: minmax(150px, .8fr) minmax(180px, .9fr) minmax(260px, 1.7fr) 78px; gap: 16px; align-items: center; padding: 11px 14px; }
.operation-log-head { background: var(--card-surface-muted, rgba(10, 57, 91, .68)); color: var(--ink-muted, #91bad0); font-size: 11px; font-weight: 800; }
.operation-log-row { border-top: 1px solid var(--card-divider, rgba(42, 164, 239, .14)); color: var(--ink, #cae8f5); font-size: 12px; }
.operation-log-row:hover { background: rgba(39, 135, 180, .05); }
.operation-log-row > div:first-child,
.operation-log-action { display: grid; gap: 3px; min-width: 0; }
.operation-log-row strong { color: var(--ink-strong, #d8f2fc); }
.operation-log-row small { color: var(--ink-muted, #7396ad); font-size: 10px; }
.operation-log-row time { color: var(--ink, #8bc3dd); font-family: "Roboto Mono", Consolas, monospace; font-size: 11px; }
.operation-log-action details { margin-top: 4px; }
.operation-log-action summary { width: max-content; color: #2787b4; font-size: 10px; cursor: pointer; }
.operation-log-action pre { max-height: 220px; margin: 7px 0 0; overflow: auto; padding: 10px; border-radius: 4px; background: #eef4f6; color: #35596d; font: 10px/1.55 "Roboto Mono", Consolas, monospace; white-space: pre-wrap; word-break: break-all; }
.operation-log-status { justify-self: start; padding: 4px 7px; border-radius: 3px; font-size: 10px; font-weight: 800; }
.operation-log-status.success { background: #e3f4e8; color: #278245; }
.operation-log-status.failed { background: #fbe7e8; color: #b43c47; }
.operation-log-status.pending { background: #fff3d8; color: #996817; }
.operation-log-state { min-height: 160px; display: grid; place-items: center; margin: 0; }
.operation-log-pagination { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: var(--ink-muted, #7396ad); font-size: 11px; }
.operation-log-pagination > div { display: flex; gap: 8px; }
.profile-modal-backdrop { position: fixed; inset: 0; z-index: 32; display: grid; place-items: center; padding: 24px; background: rgba(4, 10, 20, .72); }
.profile-modal { width: min(440px, 100%); overflow: hidden; border: 1px solid rgba(42, 164, 239, .5); border-radius: 8px; background: #0b1b2f; box-shadow: 0 20px 65px rgba(0, 0, 0, .45); }
.profile-modal-header, .profile-modal-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 15px 18px; }
.profile-modal-header { border-bottom: 1px solid rgba(42, 164, 239, .18); }
.profile-modal-header h3 { margin: 0 0 4px; color: #e6f8ff; font-size: 15px; }
.profile-modal-header span { color: #7ea6bb; font-size: 11px; }
.profile-modal-header button { display: grid; place-items: center; width: 30px; height: 30px; border: 1px solid transparent; border-radius: 4px; background: transparent; color: #8ab8cf; cursor: pointer; }
.profile-modal-header button:hover { border-color: rgba(42, 164, 239, .44); color: #e6f8ff; }
.profile-form-fields { display: grid; gap: 13px; padding: 18px; }
.profile-form-fields label { display: grid; gap: 7px; color: #b9d8e6; font-size: 12px; font-weight: 700; }
.profile-form-fields input, .profile-form-fields select { min-height: 38px; padding: 8px 10px; font: inherit; font-weight: 400; }
.profile-modal .profile-error, .profile-modal .profile-success { padding: 0 18px; }
.profile-modal-footer { justify-content: flex-end; margin-top: 4px; border-top: 1px solid rgba(42, 164, 239, .18); background: rgba(4, 24, 42, .5); }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }
@media (max-width: 960px) { .profile-hero { grid-template-columns: 1fr; gap: 18px; } .profile-hero-summary { grid-template-columns: repeat(3, 1fr); min-height: 74px; } }
@media (max-width: 760px) { .profile-page { gap: 14px; } .profile-page-head { flex-wrap: wrap; } .profile-tabs { order: 3; width: 100%; margin: 8px 0 0; } .profile-tabs button { flex: 1; } .profile-hero { padding: 20px; } .profile-identity-block { align-items: flex-start; } .profile-avatar { width: 62px; height: 62px; font-size: 24px; } .profile-name-row { flex-wrap: wrap; } .profile-name-row h3 { font-size: 20px; } .profile-hero-summary { grid-template-columns: 1fr; } .profile-summary-item { min-height: 54px; grid-template-columns: 1fr auto; align-items: center; padding: 10px 12px; border-top: 1px solid rgba(92, 206, 255, .16); border-left: 0; } .profile-summary-item:first-child { border-top: 0; } .profile-users-title { align-items: flex-start; flex-direction: column; } .profile-users-actions { width: 100%; justify-content: space-between; } .user-list { overflow-x: auto; } .user-list-head, .user-list-row { min-width: 560px; } .profile-logout-row { justify-content: stretch; } .profile-logout-button { width: 100%; } .operation-log-panel { padding: 14px; } .operation-log-pagination { align-items: flex-start; flex-direction: column; } }
@media (prefers-reduced-motion: reduce) { .user-list-row { transition: none; } }
</style>
