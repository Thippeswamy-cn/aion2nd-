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
  const roleInput = applicationForm?.querySelector("[data-role-input]");
  const qualificationInput = applicationForm?.querySelector('select[name="qualification"]');
  const rolesByQualification = {
    "Graduate": ["Branch Operations Executive", "Customer Success Associate", "Business Development Associate", "Other"],
    "Skilled graduate": ["Software Engineer", "Data Analyst", "Healthcare Administration Associate", "Customer Success Associate", "Quality Assurance Executive", "Other"],
    "Postgraduate": ["Data Analyst", "Branch Operations Executive", "Customer Success Associate", "Business Development Associate", "Other"],
    "Skilled postgraduate": ["Software Engineer", "Data Analyst", "Branch Operations Executive", "Customer Success Associate", "Quality Assurance Executive", "Business Development Associate", "Other"],
    "Diploma / Other": ["Customer Success Associate", "Quality Assurance Executive", "Other"]
  };
  const roleGroups = roleInput ? [...roleInput.querySelectorAll("optgroup")].map((group) => ({
    label: group.label,
    roles: [...group.querySelectorAll("option")].map((option) => option.value)
  })) : [];
  let modalTrigger = null;

  const setRoleOptions = (qualification = "", preferredRole = "") => {
    if (!roleInput) return;
    const allowedRoles = qualification ? new Set(rolesByQualification[qualification] || ["Other"]) : null;
    roleInput.replaceChildren(new Option("Select a role", ""));
    roleGroups.forEach((group) => {
      const roles = allowedRoles ? group.roles.filter((role) => allowedRoles.has(role)) : group.roles;
      if (!roles.length) return;
      const optgroup = document.createElement("optgroup");
      optgroup.label = group.label;
      roles.forEach((role) => optgroup.append(new Option(role, role)));
      roleInput.append(optgroup);
    });
    roleInput.value = preferredRole;
    if (roleInput.value !== preferredRole) roleInput.value = "";
  };

  const openApplication = (trigger, role = "", qualification = "") => {
    if (!modal || !applicationForm || !applicationSuccess) return;
    modalTrigger = trigger;
    applicationForm.reset();
    if (qualificationInput) qualificationInput.value = qualification;
    setRoleOptions(qualification, role);
    const formError = applicationForm.querySelector("[data-form-error]");
    if (formError) formError.hidden = true;
    applicationForm.hidden = false;
    applicationSuccess.hidden = true;
    modal.hidden = false;
    document.body.classList.add("modal-open");
    window.requestAnimationFrame(() => modal.classList.add("is-open"));
    window.setTimeout(() => (role ? applicationForm.querySelector('input[name="fullName"]') : roleInput)?.focus(), 120);
  };
  const closeApplication = () => {
    if (!modal) return;
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
    openApplication(trigger, trigger.dataset.applyRole || "");
  }));
  document.querySelectorAll("[data-apply-qualification]").forEach((trigger) => trigger.addEventListener("click", () => {
    openApplication(trigger, "", trigger.dataset.applyQualification || "");
  }));
  qualificationInput?.addEventListener("change", () => {
    setRoleOptions(qualificationInput.value, roleInput?.value || "");
  });
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
    if (resume && resume.size > 5 * 1024 * 1024) {
      applicationForm.elements.resume.setCustomValidity("Please upload a file smaller than 5 MB.");
      applicationForm.reportValidity();
      return;
    }
    applicationForm.elements.resume?.setCustomValidity("");
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
    if (modal && !modal.hidden) closeApplication();
    else if (navPanel?.classList.contains("open")) closeMenu();
  });
});
