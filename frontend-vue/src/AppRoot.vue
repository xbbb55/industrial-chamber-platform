<template><LoginView v-if="!authenticated" @authenticated="handleAuthenticated" /><DashboardApp v-else @logout="handleLogout" /></template>

<script setup>
import { ref } from "vue";
import DashboardApp from "./DashboardApp.vue";
import LoginView from "./LoginView.vue";

const authenticated = ref(Boolean(localStorage.getItem("industrial-auth-token")));
function handleAuthenticated() { authenticated.value = true; }
function handleLogout() { authenticated.value = false; }
</script>
