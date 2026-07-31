import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { App } from "./App";
import { AuthProvider } from "./lib/auth";
import { queryClient } from "./lib/queryClient";
import "./styles/global.css";
import "./styles/admin.css";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("The root element was not found");

createRoot(rootElement).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
