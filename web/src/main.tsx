import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

function App() {
  return <main>FlightMind</main>;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
