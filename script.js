document.addEventListener("DOMContentLoaded", () => {
  const page = window.location.pathname.split("/").pop() || "index.html";
  const splashSeen = sessionStorage.getItem("splashSeen") === "true";

  if (page === "index.html") {
    if (!splashSeen) {
      sessionStorage.setItem("splashSeen", "true");
    }
    setTimeout(() => {
      window.location.href = "eligibility.html";
    }, 4000);
    return;
  }

  if (!splashSeen) {
    window.location.replace("index.html");
  }
});