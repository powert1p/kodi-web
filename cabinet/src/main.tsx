import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { HashRouter } from "react-router-dom";

// Шрифты self-host: WebView никогда не падает на системный фолбэк
import "@fontsource-variable/lexend";
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource-variable/space-grotesk";
// KaTeX-стили
import "katex/dist/katex.min.css";
import "./index.css";

import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </StrictMode>,
);
