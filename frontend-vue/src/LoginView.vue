<template>
  <main class="login-page">
    <div class="login-grid-mark" aria-hidden="true"></div>
    <section class="login-aside">
      <div class="login-brand"><span>IC</span><div><strong>环境试验箱平台</strong><small>Industrial Chamber QC</small></div></div>
      <div class="login-intro">
        <h1>让每一次环境试验，<em>都可追溯。</em></h1>
      </div>
    </section>

    <section class="login-panel" aria-labelledby="login-title">
      <div class="login-copy"><h2 id="login-title">欢迎回来</h2><p>请输入您的账户信息以继续访问控制中心</p></div>
      <form class="login-form" @submit.prevent="submit">
        <label><span>账户名</span><div class="login-input"><UserRound :size="18" /><input v-model.trim="username" autocomplete="username" placeholder="请输入账户名" required /></div></label>
        <label><span>密码</span><div class="login-input"><LockKeyhole :size="18" /><input v-model="password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="请输入密码" required /><button type="button" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword"><EyeOff v-if="showPassword" :size="17" /><Eye v-else :size="17" /></button></div></label>
        <p v-if="error" class="login-error" role="alert">{{ error }}</p>
        <button class="login-submit" type="submit" :disabled="loading"><span>{{ loading ? '验证中…' : '登录控制中心' }}</span><ArrowRight :size="18" /></button>
      </form>
      <div class="login-foot"><ShieldCheck :size="16" /><span>账户信息由系统数据库统一管理 · 会话采用安全令牌</span></div>
    </section>
  </main>
</template>

<script setup>
import { ref } from "vue";
import { ArrowRight, Eye, EyeOff, LockKeyhole, ShieldCheck, UserRound } from "lucide-vue-next";

const emit = defineEmits(["authenticated"]);
const username = ref("");
const password = ref("");
const showPassword = ref(false);
const loading = ref(false);
const error = ref("");

async function submit() {
  error.value = "";
  loading.value = true;
  try {
    const response = await fetch("/api/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username: username.value, password: password.value }) });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || "登录失败，请稍后重试");
    localStorage.setItem("industrial-auth-token", payload.access_token);
    localStorage.setItem("industrial-auth-user", JSON.stringify(payload.user));
    emit("authenticated", payload.user);
  } catch (cause) {
    error.value = cause.message || "网络连接失败，请检查服务状态";
  } finally {
    loading.value = false;
  }
}
</script>
