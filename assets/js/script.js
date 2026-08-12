document.addEventListener("DOMContentLoaded", () => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const header = document.querySelector("[data-header]");
  const menuToggle = document.querySelector("[data-menu-toggle]");
  const navPanel = document.querySelector("[data-nav-panel]");

  let previousY = window.scrollY;
  let ticking = false;
  const updateHeader = () => {
    const currentY = Math.max(window.scrollY, 0);
    header?.classList.toggle("scrolled", currentY > 20);
    header?.classList.toggle("header-hidden", currentY > 180 && currentY > previousY && !navPanel?.classList.contains("open"));
    previousY = currentY;
    ticking = false;
  };
  window.addEventListener("scroll", () => {
    if (!ticking) {
      window.requestAnimationFrame(updateHeader);
      ticking = true;
    }
  }, { passive: true });
  updateHeader();

  const closeMenu = () => {
    menuToggle?.setAttribute("aria-expanded", "false");
    menuToggle?.setAttribute("aria-label", "Open navigation");
    navPanel?.classList.remove("open");
  };
  menuToggle?.addEventListener("click", () => {
    const open = menuToggle.getAttribute("aria-expanded") !== "true";
    menuToggle.setAttribute("aria-expanded", String(open));
    menuToggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    navPanel?.classList.toggle("open", open);
    header?.classList.remove("header-hidden");
  });
  navPanel?.querySelectorAll("a").forEach((link) => link.addEventListener("click", closeMenu));

  const revealItems = [...document.querySelectorAll(".reveal, .reveal-card")];
  if (!reduceMotion && "IntersectionObserver" in window) {
    document.body.classList.add("motion-ready");
    const revealObserver = new IntersectionObserver((entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add("is-visible");
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.08, rootMargin: "0px 0px -5% 0px" });
    revealItems.forEach((item) => revealObserver.observe(item));
    window.setTimeout(() => revealItems.forEach((item) => item.classList.add("is-visible")), 1800);
  } else {
    revealItems.forEach((item) => item.classList.add("is-visible"));
  }

  document.querySelectorAll("[data-count]").forEach((counter) => {
    const suffix = counter.dataset.suffix || "";
    counter.textContent = `${new Intl.NumberFormat("en-IN").format(Number(counter.dataset.count))}${suffix}`;
  });

  const modal = document.querySelector("[data-application-modal]");
  const applicationForm = document.querySelector("[data-application-form]");
  const applicationSuccess = document.querySelector("[data-application-success]");
  const educationField = applicationForm?.querySelector("[data-education-field]");
  const educationLabel = applicationForm?.querySelector("#education-label");
  const educationSelect = applicationForm?.querySelector("[data-education-select]");
  const qualificationInput = applicationForm?.querySelector("[data-education-input]");
  const educationTrigger = applicationForm?.querySelector("[data-education-trigger]");
  const educationValue = applicationForm?.querySelector("[data-education-value]");
  const educationOptions = applicationForm?.querySelector("[data-education-options]");
  const educationError = applicationForm?.querySelector("[data-education-error]");
  const educationOptionButtons = [];
  const educationPlaceholder = qualificationInput?.options[0]?.textContent || "Select your highest qualification";
  let educationEnhanced = false;
  let modalTrigger = null;

  const closeEducationOptions = () => {
    if (!educationEnhanced || !educationSelect || !educationTrigger || !educationOptions) return;
    educationSelect.classList.remove("is-open");
    educationTrigger.setAttribute("aria-expanded", "false");
    educationOptions.hidden = true;
  };

  const syncEducationValue = (value = "") => {
    if (!qualificationInput || !educationValue || !educationTrigger) return;
    qualificationInput.value = value;
    qualificationInput.setCustomValidity("");
    const selected = [...qualificationInput.options].find((option) => option.value === qualificationInput.value && option.value);
    educationValue.textContent = selected?.textContent || educationPlaceholder;
    educationTrigger.classList.toggle("has-value", Boolean(selected));
    educationTrigger.setAttribute("aria-invalid", "false");
    educationField?.classList.remove("is-invalid");
    if (educationError) educationError.hidden = true;
    educationOptionButtons.forEach((option) => option.setAttribute("aria-selected", String(option.dataset.value === qualificationInput.value)));
  };

  const openEducationOptions = (focusPosition = "") => {
    if (!educationEnhanced || !educationSelect || !educationTrigger || !educationOptions || !educationOptionButtons.length) return;
    educationOptions.hidden = false;
    educationSelect.classList.add("is-open");
    educationTrigger.setAttribute("aria-expanded", "true");
    if (!focusPosition) return;
    const selected = educationOptionButtons.find((option) => option.getAttribute("aria-selected") === "true");
    const target = focusPosition === "last" ? educationOptionButtons.at(-1) : selected || educationOptionButtons[0];
    target?.focus();
    target?.scrollIntoView({ block: "nearest" });
  };

  const chooseEducation = (value, restoreFocus = true) => {
    syncEducationValue(value);
    closeEducationOptions();
    if (restoreFocus) educationTrigger?.focus();
  };

  if (qualificationInput && educationOptions) {
    const addEducationOption = (option, container) => {
      const choice = document.createElement("button");
      choice.type = "button";
      choice.className = "education-option";
      choice.dataset.value = option.value;
      choice.setAttribute("role", "option");
      choice.setAttribute("aria-selected", "false");
      choice.tabIndex = -1;
      choice.textContent = option.textContent;
      container.append(choice);
      educationOptionButtons.push(choice);
    };
    [...qualificationInput.children].forEach((item) => {
      if (item.tagName === "OPTGROUP") {
        const group = document.createElement("div");
        group.className = "education-option-group";
        group.setAttribute("role", "group");
        group.setAttribute("aria-label", item.label);
        const groupLabel = document.createElement("div");
        groupLabel.className = "education-group-label";
        groupLabel.setAttribute("aria-hidden", "true");
        groupLabel.textContent = item.label;
        group.append(groupLabel);
        [...item.querySelectorAll("option")].forEach((option) => addEducationOption(option, group));
        educationOptions.append(group);
      } else if (item.value) {
        addEducationOption(item, educationOptions);
      }
    });
    const customStylesReady = getComputedStyle(educationSelect).getPropertyValue("--education-select-ready").trim() === "1";
    if (customStylesReady && educationTrigger) {
      educationEnhanced = true;
      educationSelect.classList.add("is-enhanced");
      qualificationInput.hidden = true;
      educationTrigger.hidden = false;
    }
    syncEducationValue();
  }

  qualificationInput?.addEventListener("change", () => syncEducationValue(qualificationInput.value));
  educationLabel?.addEventListener("click", (event) => {
    if (!educationEnhanced) return;
    event.preventDefault();
    educationTrigger?.focus();
  });

  educationTrigger?.addEventListener("click", () => {
    if (educationSelect?.classList.contains("is-open")) closeEducationOptions();
    else openEducationOptions();
  });
  educationTrigger?.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      openEducationOptions(event.key === "ArrowUp" ? "last" : "selected");
    } else if (event.key === "Escape") {
      event.stopPropagation();
      closeEducationOptions();
    }
  });
  educationOptionButtons.forEach((option, index) => {
    option.addEventListener("click", () => chooseEducation(option.dataset.value || ""));
    option.addEventListener("keydown", (event) => {
      if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
        event.preventDefault();
        let nextIndex = event.key === "Home" ? 0 : event.key === "End" ? educationOptionButtons.length - 1 : index + (event.key === "ArrowDown" ? 1 : -1);
        nextIndex = (nextIndex + educationOptionButtons.length) % educationOptionButtons.length;
        educationOptionButtons[nextIndex]?.focus();
        educationOptionButtons[nextIndex]?.scrollIntoView({ block: "nearest" });
      } else if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        closeEducationOptions();
        educationTrigger?.focus();
      } else if (event.key === "Tab") {
        closeEducationOptions();
      }
    });
  });
  document.addEventListener("pointerdown", (event) => {
    if (educationSelect && !educationSelect.contains(event.target)) closeEducationOptions();
  });

  const openApplication = (trigger, qualification = "") => {
    if (!modal || !applicationForm || !applicationSuccess) return;
    modalTrigger = trigger;
    applicationForm.reset();
    syncEducationValue(qualification);
    const formError = applicationForm.querySelector("[data-form-error]");
    if (formError) formError.hidden = true;
    applicationForm.hidden = false;
    applicationSuccess.hidden = true;
    modal.hidden = false;
    document.body.classList.add("modal-open");
    window.requestAnimationFrame(() => modal.classList.add("is-open"));
    window.setTimeout(() => {
      const educationControl = educationEnhanced ? educationTrigger : qualificationInput;
      (qualificationInput?.value ? applicationForm.querySelector('input[name="fullName"]') : educationControl)?.focus();
    }, 120);
  };
  const closeApplication = () => {
    if (!modal) return;
    closeEducationOptions();
    modal.classList.remove("is-open");
    document.body.classList.remove("modal-open");
    window.setTimeout(() => { modal.hidden = true; }, 230);
    modalTrigger?.focus();
  };

  document.querySelectorAll("[data-open-application]").forEach((trigger) => trigger.addEventListener("click", (event) => {
    event.preventDefault();
    openApplication(trigger);
  }));
  document.querySelectorAll("[data-apply-role]").forEach((trigger) => trigger.addEventListener("click", (event) => {
    event.preventDefault();
    openApplication(trigger);
  }));
  document.querySelectorAll("[data-apply-qualification]").forEach((trigger) => trigger.addEventListener("click", () => {
    openApplication(trigger, trigger.dataset.applyQualification || "");
  }));
  document.querySelectorAll("[data-close-application]").forEach((trigger) => trigger.addEventListener("click", closeApplication));

  if (new URLSearchParams(window.location.search).get("apply") === "1") {
    openApplication(null);
    window.history.replaceState({}, "", `${window.location.pathname}${window.location.hash}`);
  }

  const enquiryForm = document.querySelector("[data-enquiry-form]");
  enquiryForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = enquiryForm.querySelector('button[type="submit"]');
    const error = enquiryForm.querySelector("[data-enquiry-error]");
    const success = enquiryForm.querySelector("[data-enquiry-success]");
    error.hidden = true;
    success.hidden = true;
    submit.disabled = true;
    const original = submit.innerHTML;
    submit.textContent = "Sending…";
    try {
      const response = await fetch("/api/enquiries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(Object.fromEntries(new FormData(enquiryForm)))
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "Unable to send your enquiry. Please try again.");
      enquiryForm.reset();
      success.textContent = `Thank you. Your enquiry reference is ${result.enquiryId}.`;
      success.hidden = false;
      success.focus();
    } catch (requestError) {
      error.textContent = requestError.message;
      error.hidden = false;
      error.focus();
    } finally {
      submit.disabled = false;
      submit.innerHTML = original;
    }
  });

  applicationForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = applicationForm.querySelector('button[type="submit"]');
    const error = applicationForm.querySelector("[data-form-error]");
    const resume = applicationForm.elements.resume?.files?.[0];
    const photo = applicationForm.elements.photo?.files?.[0];
    if (!qualificationInput?.value) {
      if (educationEnhanced) {
        educationField?.classList.add("is-invalid");
        educationTrigger?.setAttribute("aria-invalid", "true");
        if (educationError) educationError.hidden = false;
        openEducationOptions();
        educationTrigger?.focus();
      } else {
        qualificationInput?.setCustomValidity("Please select your highest degree or qualification.");
        qualificationInput?.reportValidity();
        qualificationInput?.focus();
      }
      return;
    }
    qualificationInput.setCustomValidity("");
    if (!applicationForm.reportValidity()) return;
    if (resume && resume.size > 5 * 1024 * 1024) {
      applicationForm.elements.resume.setCustomValidity("Please upload a file smaller than 5 MB.");
      applicationForm.reportValidity();
      return;
    }
    applicationForm.elements.resume?.setCustomValidity("");
    if (photo && photo.size > 3 * 1024 * 1024) {
      applicationForm.elements.photo.setCustomValidity("Please upload a photo smaller than 3 MB.");
      applicationForm.reportValidity();
      return;
    }
    applicationForm.elements.photo?.setCustomValidity("");
    error.hidden = true;
    submit.disabled = true;
    const original = submit.innerHTML;
    submit.textContent = "Submitting…";
    try {
      const response = await fetch("/api/applications", { method: "POST", body: new FormData(applicationForm) });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || "Unable to submit your application. Please try again.");
      applicationForm.hidden = true;
      applicationSuccess.hidden = false;
      const reference = applicationSuccess.querySelector("[data-application-reference]");
      if (reference) reference.textContent = `Application reference: ${result.applicationId}`;
      applicationSuccess.querySelector("button")?.focus();
      applicationForm.reset();
      syncEducationValue();
    } catch (requestError) {
      error.textContent = requestError.message;
      error.hidden = false;
      error.focus();
    } finally {
      submit.disabled = false;
      submit.innerHTML = original;
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (educationSelect?.classList.contains("is-open")) {
      closeEducationOptions();
      educationTrigger?.focus();
    } else if (modal && !modal.hidden) closeApplication();
    else if (navPanel?.classList.contains("open")) closeMenu();
  });
});
