import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./index.css";
import { StaffKeyProvider } from "./context/StaffKeyContext";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <StaffKeyProvider>
        <App />
      </StaffKeyProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
