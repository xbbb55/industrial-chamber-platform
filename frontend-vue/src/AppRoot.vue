<template><LoginView v-if="!authenticated" @authenticated="handleAuthenticated" /><DashboardApp v-else :initial-user="currentUser" @logout="handleLogout" /></template>

<script setup>
import { ref } from "vue";
import DashboardApp from "./DashboardApp.vue";
import LoginView from "./LoginView.vue";

const fallbackUser = { username: "admin", display_name: "Admin User", role: "ADMIN", role_label: "管理员" };

// Authentication is intentionally page-session scoped.  A full page reload
// must never reopen the previous control-center view on a shared industrial
// workstation, even when an old token was left in localStorage.
function clearPersistedSession() {
  localStorage.removeItem("industrial-auth-token");
  localStorage.removeItem("industrial-auth-user");
}

clearPersistedSession();

const authenticated = ref(false);
const currentUser = ref(fallbackUser);

function normalizeUser(user) {
  const role = ["ADMIN", "工程师", "ENGINEER", "销售", "SALES"].includes(user?.role) ? user.role : "ADMIN";
  const normalizedRole = role === "工程师" ? "ENGINEER" : role === "销售" ? "SALES" : role;
  const labels = { ADMIN: "管理员", ENGINEER: "工程师", SALES: "销售" };
  return { ...fallbackUser, ...user, role: normalizedRole, role_label: labels[normalizedRole] };
}

function handleAuthenticated(user) {
  currentUser.value = normalizeUser(user);
  authenticated.value = true;
}

function handleLogout() {
  clearPersistedSession();
  currentUser.value = fallbackUser;
  authenticated.value = false;
}
</script>
