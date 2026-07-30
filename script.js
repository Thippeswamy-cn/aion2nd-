document.addEventListener("DOMContentLoaded", () => {
  const page = window.location.pathname.split("/").pop() || "index.html";

  if (page === "index.html" || page === "") {
    window.location.replace("home.html");
    return;
  }

  const header = document.querySelector("[data-header]");
  const menuButton = document.querySelector(".menu-toggle");
  const navigation = document.querySelector(".header-actions");

  let previousScrollY = window.scrollY;
  let headerTicking = false;

  const updateHeader = () => {
    if (!header) return;

    const currentScrollY = Math.max(window.scrollY, 0);
    const scrollingDown = currentScrollY > previousScrollY;
    const menuOpen = navigation?.classList.contains("open");

    header.classList.toggle("scrolled", currentScrollY > 12);
    header.classList.toggle(
      "header-hidden",
      scrollingDown && currentScrollY > 120 && !menuOpen
    );

    previousScrollY = currentScrollY;
    headerTicking = false;
  };

  const requestHeaderUpdate = () => {
    if (!headerTicking) {
      window.requestAnimationFrame(updateHeader);
      headerTicking = true;
    }
  };

  updateHeader();
  window.addEventListener("scroll", requestHeaderUpdate, { passive: true });

  menuButton?.addEventListener("click", () => {
    const open = menuButton.getAttribute("aria-expanded") !== "true";
    menuButton.setAttribute("aria-expanded", String(open));
    menuButton.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    navigation?.classList.toggle("open", open);
    header?.classList.remove("header-hidden");
  });

  navigation?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menuButton?.setAttribute("aria-expanded", "false");
      menuButton?.setAttribute("aria-label", "Open navigation");
      navigation.classList.remove("open");
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && navigation?.classList.contains("open")) {
      menuButton?.click();
      menuButton?.focus();
    }
  });

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const revealItems = document.querySelectorAll(".reveal, .reveal-card");

  if (reducedMotion || !("IntersectionObserver" in window)) {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  } else {
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    revealItems.forEach((item) => revealObserver.observe(item));
  }

  const timeline = document.querySelector("[data-timeline]");
  if (timeline) {
    const showTimeline = () => {
      timeline.classList.add("is-visible");
      timeline.style.setProperty("--progress", "100%");
    };
    if (reducedMotion || !("IntersectionObserver" in window)) {
      showTimeline();
    } else {
      const timelineObserver = new IntersectionObserver((entries, observer) => {
        if (entries[0].isIntersecting) {
          showTimeline();
          observer.disconnect();
        }
      }, { threshold: 0.3 });
      timelineObserver.observe(timeline);
    }
  }

  const countElements = document.querySelectorAll("[data-count]");
  const animateCount = (element) => {
    const target = Number(element.dataset.count);
    const suffix = element.dataset.suffix || "";
    const duration = 1100;
    const started = performance.now();
    const format = new Intl.NumberFormat("en-IN");

    const tick = (now) => {
      const progress = Math.min((now - started) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = `${format.format(Math.round(target * eased))}${suffix}`;
      if (progress < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  };

  if (reducedMotion || !("IntersectionObserver" in window)) {
    countElements.forEach((element) => {
      element.textContent = `${new Intl.NumberFormat("en-IN").format(Number(element.dataset.count))}${element.dataset.suffix || ""}`;
    });
  } else {
    const countObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCount(entry.target);
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.65 });
    countElements.forEach((element) => countObserver.observe(element));
  }

  const educationSelect = document.querySelector('select[name="education"]');
  const cards = [...document.querySelectorAll(".eligibility-card")];
  const educationMap = {
    "Graduate": 0,
    "Skilled graduate": 1,
    "Postgraduate": 2,
    "Skilled postgraduate": 3
  };

  educationSelect?.addEventListener("change", () => {
    const selectedIndex = educationMap[educationSelect.value];
    cards.forEach((card, index) => {
      const matches = selectedIndex === undefined || index === selectedIndex;
      card.hidden = !matches;
    });
  });
});
