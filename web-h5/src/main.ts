import { createApp } from "vue";
import {
  Button,
  Cell,
  CellGroup,
  Empty,
  Field,
  Loading,
  NavBar,
  Popup,
  Tag,
  Toast,
} from "vant";
import "vant/lib/index.css";

import App from "./App.vue";
import "./styles.css";

const app = createApp(App);
app.use(NavBar);
app.use(Popup);
app.use(Cell);
app.use(CellGroup);
app.use(Button);
app.use(Field);
app.use(Empty);
app.use(Loading);
app.use(Tag);
app.use(Toast);
app.mount("#app");
