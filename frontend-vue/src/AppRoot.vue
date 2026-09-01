<template><LoginView v-if="!authenticated" @authenticated="handleAuthenticated" /><DashboardApp v-else :initial-user="currentUser" @logout="handleLogout" /></template>

<script setup>
import { ref } from "vue";
import DashboardApp from "./DashboardApp.vue";
import LoginView from "./LoginView.vue";

const authenticated = ref(Boolean(localStorage.getItem("industrial-auth-token")));
const fallbackUser = { username: "admin", display_name: "Admin User", role: "ADMIN", role_label: "管理员" };
const currentUser = ref(readStoredUser());

function normalizeUser(user) {
  const role = ["ADMIN", "工程师", "ENGINEER", "销售", "SALES"].includes(user?.role) ? user.role : "ADMIN";
  const normalizedRole = role === "工程师" ? "ENGINEER" : role === "销售" ? "SALES" : role;
  const labels = { ADMIN: "管理员", ENGINEER: "工程师", SALES: "销售" };
  return { ...fallbackUser, ...user, role: normalizedRole, role_label: labels[normalizedRole] };
}

function readStoredUser() {
  try {
    return normalizeUser(JSON.parse(localStorage.getItem("industrial-auth-user") || "{}"));
  } catch {
    return fallbackUser;
  }
}

function handleAuthenticated(user) {
  currentUser.value = normalizeUser(user);
  authenticated.value = true;
}

function handleLogout() {
  localStorage.removeItem("industrial-auth-token");
  localStorage.removeItem("industrial-auth-user");
  currentUser.value = fallbackUser;
  authenticated.value = false;
}
</script>
