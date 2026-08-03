document.addEventListener("DOMContentLoaded", () => {
  const page = window.location.pathname.split("/").pop() || "index.html";

  const root = document.documentElement;
  const themeButtons = document.querySelectorAll("[data-theme-toggle]");
  const systemTheme = window.matchMedia("(prefers-color-scheme: light)");
  let savedTheme = null;
  try { savedTheme = window.localStorage.getItem("aion-theme"); } catch (_) {}

  const applyTheme = (theme) => {
    root.dataset.theme = theme;
    const nextTheme = theme === "dark" ? "light" : "dark";
    themeButtons.forEach((button) => {
      button.setAttribute("aria-label", `Switch to ${nextTheme} mode`);
      button.setAttribute("title", `Switch to ${nextTheme} mode`);
      button.setAttribute("aria-pressed", String(theme === "light"));
    });
  };

  applyTheme(savedTheme || (systemTheme.matches ? "light" : "dark"));
  themeButtons.forEach((button) => button.addEventListener("click", () => {
    const theme = root.dataset.theme === "light" ? "dark" : "light";
    applyTheme(theme);
    savedTheme = theme;
    try { window.localStorage.setItem("aion-theme", theme); } catch (_) {}
  }));
  systemTheme.addEventListener?.("change", (event) => {
    if (!savedTheme) applyTheme(event.matches ? "light" : "dark");
  });

  const flippingWord = document.querySelector("[data-flipping-word]");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const createLetterNodes = (text) => Array.from(text, (letter, index) => {
    const character = document.createElement("span");
    character.className = "flip-letter";
    character.style.setProperty("--letter-index", index);
    character.textContent = letter === " " ? "\u00a0" : letter;
    return character;
  });

  if (flippingWord && !reduceMotion) {
    const words = ["deserve.", "envision.", "choose."];
    let wordIndex = 0;
    const renderWord = (word) => {
      flippingWord.replaceChildren(...createLetterNodes(word));
    };

    renderWord(words[wordIndex]);
    window.setInterval(() => {
      flippingWord.classList.add("is-exiting");
      window.setTimeout(() => {
        wordIndex = (wordIndex + 1) % words.length;
        renderWord(words[wordIndex]);
        flippingWord.classList.remove("is-exiting");
        flippingWord.classList.add("is-entering");
        window.setTimeout(() => {
          flippingWord.classList.remove("is-entering");
        }, 580);
      }, 480);
    }, 2200);
  }

  const staticFlipText = document.querySelectorAll("[data-letter-flip-static]");
  staticFlipText.forEach((element) => {
    const text = element.textContent;
    if (reduceMotion) return;
    element.setAttribute("aria-label", text);
    element.replaceChildren(...createLetterNodes(text));
  });
  if (!reduceMotion && staticFlipText.length) {
    const flipObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.45 });
    staticFlipText.forEach((element) => flipObserver.observe(element));
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
    menuButton.setAttribute("aria-label", open ? "Close header controls" : "Open header controls");
    navigation?.classList.toggle("open", open);
    header?.classList.remove("header-hidden");
  });

  navigation?.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menuButton?.setAttribute("aria-expanded", "false");
      menuButton?.setAttribute("aria-label", "Open header controls");
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

  const applicationModal = document.querySelector("[data-application-modal]");
  const applicationForm = document.querySelector("[data-application-form]");
  const applicationSuccess = document.querySelector("[data-application-success]");
  const roleInput = document.querySelector("[data-role-input]");
  const qualificationInput = applicationForm?.querySelector('select[name="qualification"]');
  let applicationTrigger = null;

  const openApplication = (trigger, role = "", qualification = "") => {
    if (!applicationModal) return;
    applicationTrigger = trigger;
    applicationForm.reset();
    roleInput.value = role;
    qualificationInput.value = qualification;
    const previousError = applicationForm.querySelector("[data-form-error]");
    if (previousError) previousError.hidden = true;
    applicationForm.hidden = false;
    applicationSuccess.hidden = true;
    applicationModal.hidden = false;
    document.body.classList.add("modal-open");
    window.requestAnimationFrame(() => applicationModal.classList.add("is-open"));
    applicationModal.querySelector(role ? 'input[name="fullName"]' : 'select[name="role"]')?.focus();
  };

  const closeApplication = () => {
    if (!applicationModal) return;
    applicationModal.classList.remove("is-open");
    document.body.classList.remove("modal-open");
    window.setTimeout(() => { applicationModal.hidden = true; }, 220);
    applicationTrigger?.focus();
  };

  document.querySelectorAll("[data-apply-role]").forEach((button) => {
    button.addEventListener("click", () => openApplication(button, button.dataset.applyRole));
  });

  document.querySelectorAll("[data-apply-qualification]").forEach((button) => {
    button.addEventListener("click", () => {
      openApplication(button, "", button.dataset.applyQualification);
    });
  });

  document.querySelectorAll("[data-open-application]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      openApplication(button);
    });
  });

  if (new URLSearchParams(window.location.search).get("apply") === "1") {
    openApplication(null);
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash}`);
  }

  const enquiryForm = document.querySelector("[data-enquiry-form]");
  enquiryForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = enquiryForm.querySelector('button[type="submit"]');
    const errorMessage = enquiryForm.querySelector("[data-enquiry-error]");
    const successMessage = enquiryForm.querySelector("[data-enquiry-success]");
    errorMessage.hidden = true;
    successMessage.hidden = true;
    submitButton.disabled = true;
    submitButton.firstChild.textContent = "Sending… ";
    try {
      const fields = Object.fromEntries(new FormData(enquiryForm));
      const response = await fetch("/api/enquiries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(fields)
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "Unable to send your enquiry. Please try again.");
      enquiryForm.reset();
      successMessage.textContent = `Thank you. Your enquiry reference is ${result.enquiryId}.`;
      successMessage.hidden = false;
      successMessage.focus();
    } catch (error) {
      errorMessage.textContent = error.message;
      errorMessage.hidden = false;
      errorMessage.focus();
    } finally {
      submitButton.disabled = false;
      submitButton.firstChild.textContent = "Send enquiry ";
    }
  });

  document.querySelectorAll("[data-close-application]").forEach((button) => button.addEventListener("click", closeApplication));
  applicationForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submitButton = applicationForm.querySelector('button[type="submit"]');
    const formError = applicationForm.querySelector("[data-form-error]");
    const resume = applicationForm.elements.resume?.files?.[0];
    if (resume && resume.size > 5 * 1024 * 1024) {
      applicationForm.elements.resume.setCustomValidity("Please upload a file smaller than 5 MB.");
      applicationForm.reportValidity();
      return;
    }
    applicationForm.elements.resume?.setCustomValidity("");
    formError.hidden = true;
    submitButton.disabled = true;
    submitButton.firstChild.textContent = "Submitting… ";
    try {
      const response = await fetch("/api/applications", {
        method: "POST",
        body: new FormData(applicationForm)
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "Unable to submit your application. Please try again.");
      applicationForm.hidden = true;
      applicationSuccess.hidden = false;
      const reference = applicationSuccess.querySelector("[data-application-reference]");
      if (reference) reference.textContent = `Application reference: ${result.applicationId}`;
      applicationSuccess.querySelector("button")?.focus();
      applicationForm.reset();
    } catch (error) {
      formError.textContent = error.message;
      formError.hidden = false;
      formError.focus();
    } finally {
      submitButton.disabled = false;
      submitButton.firstChild.textContent = "Submit application ";
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && applicationModal && !applicationModal.hidden) closeApplication();
  });
});
