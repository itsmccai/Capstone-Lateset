import { createApp } from 'vue'
import App from './App.vue'
import './main.css'
import 'primeicons/primeicons.css'
import '@google/model-viewer';


import router from './router'

const app = createApp(App);

app.use(router);
app.mount('#app');