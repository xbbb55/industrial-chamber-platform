import { createApp } from "vue";
import App from "./AppRoot.vue";
import "./styles.css";
import "./enterprise.css";
import "./motion.css";
import "./system-theme.css";
import "./parameter-theme.css";
import "./shell-theme.css";

if (window.desktopWindow) document.documentElement.classList.add("desktop-app");

createApp(App).mount("#app");
