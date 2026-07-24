// Silence benign ResizeObserver loop warning that triggers webpack-dev-server error overlay
// This is a known harmless warning from Radix UI components and does not affect production builds.
if (typeof window !== "undefined") {
  const RO_MSGS = [
    "ResizeObserver loop completed with undelivered notifications.",
    "ResizeObserver loop limit exceeded",
  ];
  const shouldIgnore = (msg) =>
    typeof msg === "string" && RO_MSGS.some((m) => msg.includes(m));

  window.addEventListener("error", (e) => {
    if (shouldIgnore(e.message)) {
      e.stopImmediatePropagation();
      e.preventDefault();
    }
  });
  window.addEventListener("unhandledrejection", (e) => {
    if (shouldIgnore(e?.reason?.message)) {
      e.stopImmediatePropagation();
      e.preventDefault();
    }
  });
}
