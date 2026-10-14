/**
 * TalentPulse — Frontend Controller
 * Minimalist, responsive, Claude & Gemini interaction mechanics.
 * Robust Authentication Gate, Anti-Bot Captcha, & Multi-Tenant User Isolation.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Application State
  let selectedSkills = new Set();
  let allSkillsTaxonomy = {};
  let jobsCache = [];
  
  // Auth State
  let currentUser = null;
  let authToken = localStorage.getItem("talentpulse_token") || null;
  try {
    const storedUser = localStorage.getItem("talentpulse_user");
    if (storedUser) currentUser = JSON.parse(storedUser);
  } catch (e) {
    currentUser = null;
  }
  
  const captchaTokens = {
    login: null,
    register: null
  };

  // DOM Elements - Navigation & Views
  const navItems = document.querySelectorAll(".nav-item");
  const viewSections = document.querySelectorAll(".view-section");
  const activeViewTitle = document.getElementById("active-view-title");
  
  // DOM Elements - Matching Form
  const chipContainer = document.getElementById("skills-chip-container");
  const expSlider = document.getElementById("exp-slider");
  const expDisplay = document.getElementById("exp-display");
  const jobSelect = document.getElementById("target-job-select");
  const candNameInput = document.getElementById("cand-name");
  const resumeTextInput = document.getElementById("resume-text");
  const runMatchBtn = document.getElementById("run-match-btn");
  const resultsWrapper = document.getElementById("results-wrapper");
  const matchResultsList = document.getElementById("match-results-list");
  const inferenceTimeTag = document.getElementById("inference-time-tag");
  const jobsTableBody = document.getElementById("jobs-table-body");
  const retrainBtn = document.getElementById("retrain-btn");

  // DOM Elements - Authenticated Sidebar & Header
  const authAvatar = document.getElementById("auth-avatar");
  const authUserName = document.getElementById("auth-user-name");
  const authUserEmail = document.getElementById("auth-user-email");
  const authUserProvider = document.getElementById("auth-user-provider");
  const logoutBtn = document.getElementById("logout-btn");
  const headerAuthBtn = document.getElementById("header-auth-btn");

  // DOM Elements - Auth Portal Form
  const tabLoginBtn = document.getElementById("tab-login-btn");
  const tabRegisterBtn = document.getElementById("tab-register-btn");
  const formLogin = document.getElementById("form-login");
  const formRegister = document.getElementById("form-register");
  const authAlert = document.getElementById("auth-alert");

  const googleLoginBtn = document.getElementById("google-login-btn");
  const githubLoginBtn = document.getElementById("github-login-btn");
  const switchToRegisterLink = document.getElementById("switch-to-register-link");
  const switchToLoginLink = document.getElementById("switch-to-login-link");

  const loginCaptchaQuestion = document.getElementById("login-captcha-question");
  const refreshLoginCaptchaBtn = document.getElementById("refresh-login-captcha-btn");
  const regCaptchaQuestion = document.getElementById("reg-captcha-question");
  const refreshRegCaptchaBtn = document.getElementById("refresh-reg-captcha-btn");

  // DOM Elements - OAuth Credential Modals
  const googleOAuthModal = document.getElementById("google-oauth-modal");
  const googleOAuthForm = document.getElementById("google-oauth-form");
  const googleEmailInput = document.getElementById("google-email-input");
  const googlePwdInput = document.getElementById("google-pwd-input");
  const googleOAuthCancelBtn = document.getElementById("google-oauth-cancel-btn");
  const googleOAuthAlert = document.getElementById("google-oauth-alert");

  const githubOAuthModal = document.getElementById("github-oauth-modal");
  const githubOAuthForm = document.getElementById("github-oauth-form");
  const githubEmailInput = document.getElementById("github-email-input");
  const githubPwdInput = document.getElementById("github-pwd-input");
  const githubOAuthCancelBtn = document.getElementById("github-oauth-cancel-btn");
  const githubOAuthAlert = document.getElementById("github-oauth-alert");

  // DOM Elements - PDF CV Upload
  const pdfDropzone = document.getElementById("pdf-dropzone");
  const cvPdfInput = document.getElementById("cv-pdf-input");
  const browsePdfBtn = document.getElementById("browse-pdf-btn");
  const pdfStatusBanner = document.getElementById("pdf-status-banner");
  const pdfFileInfo = document.getElementById("pdf-file-info");
  const pdfSkillsSummary = document.getElementById("pdf-skills-summary");

  // DOM Elements - Knowledge Graph
  const graphCanvas = document.getElementById("knowledge-graph-canvas");
  const graphNodeCount = document.getElementById("graph-node-count");
  const graphLinkCount = document.getElementById("graph-link-count");
  const graphSkillsCount = document.getElementById("graph-skills-count");
  const graphJobsSeenCount = document.getElementById("graph-jobs-seen-count");
  const graphHighMatchCount = document.getElementById("graph-high-match-count");
  const graphFilterBtns = document.querySelectorAll(".graph-filter-btn");
  const graphScopeToggleBtn = document.getElementById("graph-scope-toggle-btn");
  const graphSearchInput = document.getElementById("graph-search-input");
  const graphResetBtn = document.getElementById("graph-reset-btn");
  const graphInspectorCard = document.getElementById("graph-inspector-card");
  const inspectorBadge = document.getElementById("inspector-badge");
  const inspectorTitle = document.getElementById("inspector-title");
  const inspectorMeta = document.getElementById("inspector-meta");
  const inspectorDetails = document.getElementById("inspector-details");
  const inspectorActions = document.getElementById("inspector-actions");
  const closeInspectorBtn = document.getElementById("close-inspector-btn");

  async function trackJobView(jobId) {
    if (!authToken || !jobId) return;
    try {
      await fetch(`/api/jobs/${encodeURIComponent(jobId)}/view`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${authToken}` }
      });
    } catch (e) {
      console.warn("Failed to record job view:", e);
    }
  }

  // DOM Elements - AI Assistant
  const assistantToggleBtn = document.getElementById("assistant-toggle-btn");
  const assistantDrawer = document.getElementById("assistant-drawer");
  const closeAssistantBtn = document.getElementById("close-assistant-btn");
  const assistantQuickChips = document.querySelectorAll(".assistant-quick-chip");
  const assistantChatMessages = document.getElementById("assistant-chat-messages");
  const assistantChatForm = document.getElementById("assistant-chat-form");
  const assistantInput = document.getElementById("assistant-input");

  // Demo Profiles for quick-load
  const demoProfiles = {
    junior: {
      name: "Ahmed Raza",
      exp: 0.5,
      skills: ["Python", "NumPy", "Git", "Scikit-Learn"],
      text: "Fresh Computer Science graduate from FAST-NUCES Lahore. Final year project on tabular student churn prediction with Scikit-Learn. Proficient in Python, linear algebra, and data wrangling with Pandas. Eager to break into machine learning engineering."
    },
    rag: {
      name: "Fatima Khan",
      exp: 2.5,
      skills: ["Python", "PyTorch", "LLMs", "RAG", "LangChain", "Vector Databases", "FastAPI", "Docker"],
      text: "AI Engineer with 2.5 years of experience building production Retrieval-Augmented Generation (RAG) pipelines and LLM agents. Hands-on experience fine-tuning models with LoRA, deploying FastAPI microservices with Docker, and building semantic search engines using Qdrant and ChromaDB."
    },
    senior: {
      name: "Bilal Siddiqui",
      exp: 5.0,
      skills: ["Python", "PyTorch", "Deep Learning", "Transformers", "Model Serving", "Docker", "SQL", "MLflow", "AWS SageMaker", "Kubernetes"],
      text: "Senior Deep Learning Specialist with 5 years leading ML solutions. Specialized in custom neural architectures, transformer fine-tuning, metric learning, and low-latency inference deployments. Proven track record scaling ML systems across cloud infrastructures."
    }
  };

  // ==============================================================================
  // 1. AUTHENTICATION & ACCESS CONTROL GATE
  // ==============================================================================

  function updateAuthUI() {
    if (currentUser && authToken) {
      document.body.classList.remove("not-authenticated");
      document.body.classList.add("authenticated");
      
      authUserName.textContent = currentUser.full_name || "User";
      authUserEmail.textContent = currentUser.email || "";

      // Initials avatar
      const initials = (currentUser.full_name || "User")
        .split(" ")
        .map(n => n[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();
      authAvatar.textContent = initials || "U";

      // Provider badge
      let providerLabel = "Verified Account";
      if (currentUser.auth_provider === "google") providerLabel = "Google Account";
      if (currentUser.auth_provider === "github") providerLabel = "GitHub Account";
      authUserProvider.textContent = providerLabel;

      if (candNameInput.value === "Hamza Tariq" && currentUser.full_name) {
        candNameInput.value = currentUser.full_name;
      }

      // Load platform data once authenticated
      loadSkills();
      loadJobs();
      loadKnowledgeGraph();
    } else {
      document.body.classList.remove("authenticated");
      document.body.classList.add("not-authenticated");
      fetchCaptcha("login");
    }
  }

  async function verifyCurrentSession() {
    if (!authToken) {
      updateAuthUI();
      return;
    }
    try {
      const res = await fetch("/api/auth/me", {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      if (res.ok) {
        currentUser = await res.json();
        localStorage.setItem("talentpulse_user", JSON.stringify(currentUser));
      } else {
        localStorage.removeItem("talentpulse_token");
        localStorage.removeItem("talentpulse_user");
        authToken = null;
        currentUser = null;
      }
    } catch (err) {
      console.warn("Session check failed:", err);
    }
    updateAuthUI();
  }

  async function fetchCaptcha(mode = "login") {
    const questionElem = mode === "login" ? loginCaptchaQuestion : regCaptchaQuestion;
    if (!questionElem) return;
    questionElem.textContent = "Loading...";

    try {
      const res = await fetch("/api/auth/captcha");
      if (res.ok) {
        const data = await res.json();
        captchaTokens[mode] = data.captcha_token;
        questionElem.textContent = data.captcha_question;
      } else {
        questionElem.textContent = "Error loading";
      }
    } catch (err) {
      questionElem.textContent = "Connection error";
    }
  }

  function showAuthAlert(message, type = "error") {
    authAlert.textContent = message;
    authAlert.className = `auth-alert ${type}`;
    authAlert.style.display = "block";
  }

  function clearAuthAlert() {
    authAlert.textContent = "";
    authAlert.style.display = "none";
  }

  function switchTab(tab) {
    clearAuthAlert();
    if (tab === "login") {
      tabLoginBtn.classList.add("active");
      tabRegisterBtn.classList.remove("active");
      formLogin.style.display = "flex";
      formRegister.style.display = "none";
      fetchCaptcha("login");
    } else {
      tabRegisterBtn.classList.add("active");
      tabLoginBtn.classList.remove("active");
      formRegister.style.display = "flex";
      formLogin.style.display = "none";
      fetchCaptcha("register");
    }
  }

  tabLoginBtn.addEventListener("click", () => switchTab("login"));
  tabRegisterBtn.addEventListener("click", () => switchTab("register"));
  switchToRegisterLink.addEventListener("click", (e) => { e.preventDefault(); switchTab("register"); });
  switchToLoginLink.addEventListener("click", (e) => { e.preventDefault(); switchTab("login"); });

  refreshLoginCaptchaBtn.addEventListener("click", () => fetchCaptcha("login"));
  refreshRegCaptchaBtn.addEventListener("click", () => fetchCaptcha("register"));

  // Handle Register Form Submission
  formRegister.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAuthAlert();

    const fullName = document.getElementById("reg-fullname").value.trim();
    const email = document.getElementById("reg-email").value.trim().toLowerCase();
    const password = document.getElementById("reg-password").value;
    const confirmPassword = document.getElementById("reg-confirm-password").value;
    const captchaAnswer = document.getElementById("reg-captcha-answer").value.trim();

    if (!fullName) {
      showAuthAlert("Please provide your full name.");
      return;
    }
    const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
    if (!emailRegex.test(email)) {
      showAuthAlert("Please enter a valid email address (e.g. name@domain.com).");
      return;
    }
    if (password.length < 6) {
      showAuthAlert("Password must be at least 6 characters long.");
      return;
    }
    if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) {
      showAuthAlert("Password must contain both letters and numbers.");
      return;
    }
    if (password !== confirmPassword) {
      showAuthAlert("Passwords do not match.");
      return;
    }
    if (!captchaAnswer) {
      showAuthAlert("Please solve the mathematical security challenge.");
      return;
    }

    const submitBtn = document.getElementById("reg-submit-btn");
    submitBtn.disabled = true;
    submitBtn.textContent = "Creating Account...";

    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName,
          email: email,
          password: password,
          captcha_token: captchaTokens.register || "",
          captcha_answer: captchaAnswer
        })
      });

      const data = await res.json();
      if (!res.ok) {
        showAuthAlert(data.detail || "Registration failed. Please try again.");
        fetchCaptcha("register");
        return;
      }

      authToken = data.token;
      currentUser = data.user;
      localStorage.setItem("talentpulse_token", authToken);
      localStorage.setItem("talentpulse_user", JSON.stringify(currentUser));

      showAuthAlert("Account created successfully! Entering TalentPulse...", "success");
      setTimeout(updateAuthUI, 800);
    } catch (err) {
      showAuthAlert("Network connection error: " + err.message);
      fetchCaptcha("register");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Continue & Create Account →";
    }
  });

  // Handle Login Form Submission
  formLogin.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearAuthAlert();

    const email = document.getElementById("login-email").value.trim().toLowerCase();
    const password = document.getElementById("login-password").value;
    const captchaAnswer = document.getElementById("login-captcha-answer").value.trim();

    if (!email || !password) {
      showAuthAlert("Please enter your email and password.");
      return;
    }
    if (!captchaAnswer) {
      showAuthAlert("Please solve the security challenge.");
      return;
    }

    const submitBtn = document.getElementById("login-submit-btn");
    submitBtn.disabled = true;
    submitBtn.textContent = "Authenticating...";

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email,
          password: password,
          captcha_token: captchaTokens.login || "",
          captcha_answer: captchaAnswer
        })
      });

      const data = await res.json();
      if (!res.ok) {
        showAuthAlert(data.detail || "Invalid credentials.");
        fetchCaptcha("login");
        return;
      }

      authToken = data.token;
      currentUser = data.user;
      localStorage.setItem("talentpulse_token", authToken);
      localStorage.setItem("talentpulse_user", JSON.stringify(currentUser));

      showAuthAlert("Signed in successfully!", "success");
      setTimeout(updateAuthUI, 500);
    } catch (err) {
      showAuthAlert("Network connection error: " + err.message);
      fetchCaptcha("login");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Continue to TalentPulse →";
    }
  });

  // Handle Google OAuth Sign-In Modal
  googleLoginBtn.addEventListener("click", () => {
    clearAuthAlert();
    if (googleOAuthAlert) googleOAuthAlert.style.display = "none";
    if (googleOAuthModal) {
      googleOAuthModal.style.display = "flex";
      googleEmailInput.value = "";
      googlePwdInput.value = "";
      googleEmailInput.focus();
    }
  });

  if (googleOAuthCancelBtn) {
    googleOAuthCancelBtn.addEventListener("click", () => {
      if (googleOAuthModal) googleOAuthModal.style.display = "none";
    });
  }

  if (googleOAuthForm) {
    googleOAuthForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = googleEmailInput.value.trim().toLowerCase();
      const password = googlePwdInput.value.trim();

      if (!email || !password) {
        if (googleOAuthAlert) {
          googleOAuthAlert.textContent = "Please provide your Gmail address and account password / verification code.";
          googleOAuthAlert.className = "auth-alert error";
          googleOAuthAlert.style.display = "block";
        }
        return;
      }

      const submitBtn = document.getElementById("google-oauth-submit-btn");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Verifying...";
      }

      try {
        const res = await fetch("/api/auth/google", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email,
            password: password,
            full_name: email.split("@")[0].replace(/[._]/g, " ").replace(/\b\w/g, c => c.toUpperCase())
          })
        });

        const data = await res.json();
        if (!res.ok) {
          if (googleOAuthAlert) {
            googleOAuthAlert.textContent = data.detail || "Google verification failed. Check your password.";
            googleOAuthAlert.className = "auth-alert error";
            googleOAuthAlert.style.display = "block";
          }
          return;
        }

        authToken = data.token;
        currentUser = data.user;
        localStorage.setItem("talentpulse_token", authToken);
        localStorage.setItem("talentpulse_user", JSON.stringify(currentUser));
        if (googleOAuthModal) googleOAuthModal.style.display = "none";
        updateAuthUI();
      } catch (err) {
        if (googleOAuthAlert) {
          googleOAuthAlert.textContent = "Google OAuth network error: " + err.message;
          googleOAuthAlert.className = "auth-alert error";
          googleOAuthAlert.style.display = "block";
        }
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Verify & Sign In";
        }
      }
    });
  }

  // Handle GitHub OAuth Sign-In Modal
  githubLoginBtn.addEventListener("click", () => {
    clearAuthAlert();
    if (githubOAuthAlert) githubOAuthAlert.style.display = "none";
    if (githubOAuthModal) {
      githubOAuthModal.style.display = "flex";
      githubEmailInput.value = "";
      githubPwdInput.value = "";
      githubEmailInput.focus();
    }
  });

  if (githubOAuthCancelBtn) {
    githubOAuthCancelBtn.addEventListener("click", () => {
      if (githubOAuthModal) githubOAuthModal.style.display = "none";
    });
  }

  if (githubOAuthForm) {
    githubOAuthForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const emailOrUser = githubEmailInput.value.trim();
      const password = githubPwdInput.value.trim();

      if (!emailOrUser || !password) {
        if (githubOAuthAlert) {
          githubOAuthAlert.textContent = "Please provide your GitHub username/email and password/token.";
          githubOAuthAlert.className = "auth-alert error";
          githubOAuthAlert.style.display = "block";
        }
        return;
      }

      const email = emailOrUser.includes("@") ? emailOrUser.toLowerCase() : `${emailOrUser.toLowerCase()}@users.noreply.github.com`;
      const submitBtn = document.getElementById("github-oauth-submit-btn");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Authorizing...";
      }

      try {
        const res = await fetch("/api/auth/github", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: email,
            password: password,
            full_name: emailOrUser.replace(/[-_]/g, " ").replace(/\b\w/g, c => c.toUpperCase())
          })
        });

        const data = await res.json();
        if (!res.ok) {
          if (githubOAuthAlert) {
            githubOAuthAlert.textContent = data.detail || "GitHub authorization failed. Check your password or token.";
            githubOAuthAlert.className = "auth-alert error";
            githubOAuthAlert.style.display = "block";
          }
          return;
        }

        authToken = data.token;
        currentUser = data.user;
        localStorage.setItem("talentpulse_token", authToken);
        localStorage.setItem("talentpulse_user", JSON.stringify(currentUser));
        if (githubOAuthModal) githubOAuthModal.style.display = "none";
        updateAuthUI();
      } catch (err) {
        if (githubOAuthAlert) {
          githubOAuthAlert.textContent = "GitHub OAuth network error: " + err.message;
          githubOAuthAlert.className = "auth-alert error";
          githubOAuthAlert.style.display = "block";
        }
      } finally {
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Authorize";
        }
      }
    });
  }

  // Handle Logout
  async function handleLogout() {
    if (authToken) {
      try {
        await fetch("/api/auth/logout", {
          method: "POST",
          headers: { "Authorization": `Bearer ${authToken}` }
        });
      } catch (e) {
        // Ignore network errors on logout
      }
    }
    localStorage.removeItem("talentpulse_token");
    localStorage.removeItem("talentpulse_user");
    authToken = null;
    currentUser = null;
    updateAuthUI();
  }

  logoutBtn.addEventListener("click", handleLogout);
  headerAuthBtn.addEventListener("click", handleLogout);

  // ==============================================================================
  // 2. NAVIGATION & PLATFORM CONTROLS
  // ==============================================================================
  const viewTitles = {
    "match-view": "Match & Diagnose",
    "jobs-view": "Market Openings",
    "graph-view": "Knowledge Graph",
    "architecture-view": "Platform Insights"
  };

  navItems.forEach(item => {
    item.addEventListener("click", () => {
      navItems.forEach(n => n.classList.remove("active"));
      viewSections.forEach(v => v.classList.remove("active"));

      item.classList.add("active");
      const targetView = item.getAttribute("data-view");
      const targetElem = document.getElementById(targetView);
      if (targetElem) {
        targetElem.classList.add("active");
        if (activeViewTitle && viewTitles[targetView]) {
          activeViewTitle.textContent = viewTitles[targetView];
        }
        if (targetView === "graph-view") {
          loadKnowledgeGraph();
        }
      }
    });
  });

  // Experience Slider
  expSlider.addEventListener("input", (e) => {
    const val = parseFloat(e.target.value);
    expDisplay.textContent = `${val.toFixed(1)} ${val === 1 ? 'Year' : 'Years'}`;
  });

  // Quick Profile Loader
  document.getElementById("load-fresh-btn").addEventListener("click", () => loadDemoProfile("junior"));
  document.getElementById("load-rag-btn").addEventListener("click", () => loadDemoProfile("rag"));
  document.getElementById("load-senior-btn").addEventListener("click", () => loadDemoProfile("senior"));

  function loadDemoProfile(key) {
    const p = demoProfiles[key];
    if (!p) return;
    candNameInput.value = p.name;
    expSlider.value = p.exp;
    expDisplay.textContent = `${p.exp.toFixed(1)} ${p.exp === 1 ? 'Year' : 'Years'}`;
    resumeTextInput.value = p.text;

    selectedSkills.clear();
    p.skills.forEach(s => selectedSkills.add(s));

    document.querySelectorAll(".skill-chip").forEach(chip => {
      if (selectedSkills.has(chip.textContent)) {
        chip.classList.add("selected");
      } else {
        chip.classList.remove("selected");
      }
    });
  }

  // ==============================================================================
  // 2.1 PDF RESUME / CV UPLOADER (Strictly PDF format)
  // ==============================================================================

  if (browsePdfBtn && cvPdfInput) {
    browsePdfBtn.addEventListener("click", (e) => {
      e.preventDefault();
      cvPdfInput.click();
    });

    cvPdfInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (file) handlePDFFile(file);
    });
  }

  if (pdfDropzone) {
    pdfDropzone.addEventListener("click", (e) => {
      if (e.target !== browsePdfBtn && cvPdfInput) {
        cvPdfInput.click();
      }
    });

    ["dragenter", "dragover"].forEach(eventName => {
      pdfDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        pdfDropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach(eventName => {
      pdfDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        pdfDropzone.classList.remove("dragover");
      });
    });

    pdfDropzone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      const file = dt.files && dt.files[0];
      if (file) handlePDFFile(file);
    });
  }

  async function handlePDFFile(file) {
    if (!authToken) {
      alert("Please sign in before uploading your CV.");
      updateAuthUI();
      return;
    }
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Unsupported file format. Please upload your resume in PDF format only (.pdf).");
      return;
    }

    if (pdfStatusBanner) {
      pdfStatusBanner.style.display = "flex";
      pdfFileInfo.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      pdfSkillsSummary.textContent = "Extracting technical keywords...";
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/cv/upload-pdf", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${authToken}`
        },
        body: formData
      });

      const data = await res.json();
      if (!res.ok) {
        alert(data.detail || "PDF upload and parsing failed.");
        if (pdfSkillsSummary) pdfSkillsSummary.textContent = "Parsing failed";
        return;
      }

      // Auto-populate candidate profile
      if (data.extracted_skills && data.extracted_skills.length > 0) {
        selectedSkills.clear();
        data.extracted_skills.forEach(skill => selectedSkills.add(skill));

        document.querySelectorAll(".skill-chip").forEach(chip => {
          if (selectedSkills.has(chip.textContent)) {
            chip.classList.add("selected");
          } else {
            chip.classList.remove("selected");
          }
        });
      }

      if (data.years_experience !== undefined && data.years_experience !== null) {
        expSlider.value = data.years_experience;
        expDisplay.textContent = `${data.years_experience.toFixed(1)} ${data.years_experience === 1 ? 'Year' : 'Years'}`;
      }

      if (data.summary_excerpt) {
        resumeTextInput.value = data.summary_excerpt;
      }

      if (pdfSkillsSummary) {
        pdfSkillsSummary.textContent = `${data.total_skills_found} technical skills extracted`;
      }

      // Immediately render matches if returned
      if (data.top_matches && data.top_matches.length > 0) {
        renderMatchResults({
          candidate_name: currentUser ? currentUser.full_name : "Candidate",
          extracted_skills: data.extracted_skills,
          years_experience: data.years_experience,
          top_matches: data.top_matches,
          model_inference_ms: 12.0
        });
      }

      // Reload knowledge graph with candidate's newly extracted skills
      loadKnowledgeGraph();

    } catch (err) {
      alert("Network error while uploading CV: " + err.message);
      if (pdfSkillsSummary) pdfSkillsSummary.textContent = "Upload failed";
    }
  }

  // ==============================================================================
  // 3. SKILLS TAXONOMY & JOBS CATALOG
  // ==============================================================================

  async function loadSkills() {
    try {
      const res = await fetch("/api/skills");
      allSkillsTaxonomy = await res.json();
      
      chipContainer.innerHTML = "";
      const primarySkills = [
        "PyTorch", "Python", "Deep Learning", "Transformers", "LLMs", "RAG", 
        "LangChain", "Vector Databases", "Docker", "FastAPI", "SQL", 
        "OpenCV", "Scikit-Learn", "BERT", "MLflow", "Kubernetes", "Pandas"
      ];

      primarySkills.forEach(skill => {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "skill-chip";
        chip.textContent = skill;
        chip.addEventListener("click", () => {
          if (selectedSkills.has(skill)) {
            selectedSkills.delete(skill);
            chip.classList.remove("selected");
          } else {
            selectedSkills.add(skill);
            chip.classList.add("selected");
          }
        });
        chipContainer.appendChild(chip);
      });
    } catch (err) {
      console.error("Failed to load skills taxonomy:", err);
    }
  }

  async function loadJobs() {
    if (!authToken) return;
    try {
      const res = await fetch("/api/jobs", {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      if (!res.ok) return;
      jobsCache = await res.json();

      jobSelect.innerHTML = '<option value="">Compare across all active market jobs</option>';
      jobsTableBody.innerHTML = "";

      jobsCache.forEach(job => {
        const opt = document.createElement("option");
        opt.value = job.id;
        opt.textContent = `${job.title} — ${job.company} (${job.location})`;
        jobSelect.appendChild(opt);

        const applyHref = job.apply_url || `https://www.google.com/search?q=${encodeURIComponent(job.company + ' careers')}`;
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>
            <strong>${job.title}</strong>
            <div style="font-size: 12px; color: var(--text-secondary);">${job.company}</div>
          </td>
          <td>
            ${job.location}
            <div style="font-size: 11px; color: var(--text-muted);">${job.tier || 'Tech Employer'}</div>
          </td>
          <td>${job.experience_years} Years</td>
          <td style="color: var(--accent-green); font-weight: 500;">${job.salary_range || 'Market Competitive'}</td>
          <td>
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              ${job.required_skills.slice(0, 4).map(s => `<span class="tag-matched" style="font-size: 11px;">${s}</span>`).join('')}
              ${job.required_skills.length > 4 ? `<span style="font-size: 11px; color: var(--text-muted);">+${job.required_skills.length - 4}</span>` : ''}
            </div>
          </td>
          <td>
            <div class="table-actions-cell">
              <a href="${applyHref}" target="_blank" rel="noopener noreferrer" class="btn-apply btn-apply-sm" title="Open ${job.company} career portal">
                <span>Apply</span>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"></path>
                  <polyline points="15 3 21 3 21 9"></polyline>
                  <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
              </a>
              <button type="button" class="btn-secondary select-job-btn" data-job-id="${job.id}" style="padding: 4px 9px; font-size: 11.5px;" title="Select for match analysis">
                Match
              </button>
            </div>
          </td>
        `;
        jobsTableBody.appendChild(tr);
      });

      document.querySelectorAll(".btn-apply").forEach(link => {
        link.addEventListener("click", () => {
          const row = link.closest("tr");
          const mBtn = row && row.querySelector(".select-job-btn");
          const jId = mBtn && mBtn.getAttribute("data-job-id");
          if (jId) {
            trackJobView(jId);
            setTimeout(loadKnowledgeGraph, 400);
          }
        });
      });

      document.querySelectorAll(".select-job-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          const jId = btn.getAttribute("data-job-id");
          if (jId) {
            trackJobView(jId);
            setTimeout(loadKnowledgeGraph, 400);
          }
          jobSelect.value = jId;
          navItems.forEach(n => n.classList.remove("active"));
          viewSections.forEach(v => v.classList.remove("active"));
          document.querySelector('[data-view="match-view"]').classList.add("active");
          document.getElementById("match-view").classList.add("active");
          if (activeViewTitle) activeViewTitle.textContent = "Match & Diagnose";
          window.scrollTo({ top: 0, behavior: 'smooth' });
        });
      });

    } catch (err) {
      console.error("Failed to load jobs:", err);
    }
  }

  // ==============================================================================
  // 4. CANDIDATE MATCHING & SKILL GAP INFERENCE
  // ==============================================================================

  async function triggerMatchAnalysis() {
    if (!authToken) {
      alert("Please sign in to run candidate matching.");
      updateAuthUI();
      return;
    }

    const name = candNameInput.value.trim() || (currentUser ? currentUser.full_name : "Candidate");
    const yearsExp = parseFloat(expSlider.value) || 0.0;
    const resumeText = resumeTextInput.value.trim();
    const targetJobId = jobSelect.value || null;

    runMatchBtn.disabled = true;
    runMatchBtn.innerHTML = `
      <span style="display: inline-block; animation: spin 1s infinite linear;">⟳</span>
      <span>Evaluating Suitability...</span>
    `;

    try {
      const payload = {
        full_name: name,
        years_experience: yearsExp,
        skills: Array.from(selectedSkills),
        resume_text: resumeText,
        target_job_id: targetJobId
      };

      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${authToken}`
        },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Suitability evaluation failed");
      }

      const data = await res.json();
      renderMatchResults(data);
      loadKnowledgeGraph();
    } catch (err) {
      alert("Evaluation error: " + err.message);
    } finally {
      runMatchBtn.disabled = false;
      runMatchBtn.innerHTML = `
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
        </svg>
        <span>Analyze Match & Skill Gaps</span>
      `;
    }
  }

  runMatchBtn.addEventListener("click", triggerMatchAnalysis);

  function renderMatchResults(data) {
    resultsWrapper.style.display = "block";
    inferenceTimeTag.textContent = `Inference completed in ${data.model_inference_ms}ms • Semantic Suitability Engine`;
    matchResultsList.innerHTML = "";

    if (!data.top_matches || data.top_matches.length === 0) {
      matchResultsList.innerHTML = '<p style="color: var(--text-secondary);">No match results found.</p>';
      return;
    }

    data.top_matches.forEach(item => {
      const score = item.overall_match_score;
      const scoreClass = score >= 75 ? "high" : (score >= 50 ? "medium" : "low");
      const readinessClass = score >= 75 ? "high" : (score >= 50 ? "medium" : "low");
      const applyHref = item.apply_url || `https://www.google.com/search?q=${encodeURIComponent(item.company + ' careers')}`;

      const card = document.createElement("div");
      card.className = "result-card";
      card.innerHTML = `
        <div class="result-top-bar">
          <div class="job-title-group">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
              <h2>${item.job_title}</h2>
              <a href="${applyHref}" target="_blank" rel="noopener noreferrer" class="btn-apply btn-apply-sm" title="Open ${item.company} careers portal">
                <span>Apply</span>
                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"></path>
                  <polyline points="15 3 21 3 21 9"></polyline>
                  <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
              </a>
            </div>
            <div class="company-meta">
              <span><strong>${item.company}</strong></span>
              <span>•</span>
              <span>${item.location}</span>
              <span>•</span>
              <span style="color: var(--accent-green); font-weight: 500;">${item.salary_range || 'Market Competitive'}</span>
            </div>
          </div>
          <div class="match-score-pill">
            <span class="score-num ${scoreClass}">${score.toFixed(1)}%</span>
            <span class="score-label">Suitability Index</span>
            <span class="readiness-tag ${readinessClass}">${item.readiness_level}</span>
          </div>
        </div>

        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
          Latent Cosine Alignment: <code style="font-size: 12px; font-weight: 600; color: var(--accent-green-dark);">${item.cosine_similarity.toFixed(3)}</code> (Hyperspherical Distance: ${(1.0 - item.cosine_similarity).toFixed(3)})
        </div>

        <div class="skill-grid">
          <div>
            <div class="skill-col-title">Matched Core Competencies (${item.skill_gap.matched_skills.length})</div>
            <div class="tag-list">
              ${item.skill_gap.matched_skills.length > 0 
                ? item.skill_gap.matched_skills.map(s => `<span class="tag-matched">✓ ${s}</span>`).join('') 
                : '<span style="font-size: 12px; color: var(--text-muted);">None identified yet</span>'}
            </div>
          </div>
          <div>
            <div class="skill-col-title">Missing Target Requirements (${item.skill_gap.missing_required.length})</div>
            <div class="tag-list">
              ${item.skill_gap.missing_required.length > 0 
                ? item.skill_gap.missing_required.map(s => `<span class="tag-missing">✗ ${s}</span>`).join('') 
                : '<span class="tag-matched" style="font-size: 12px;">✓ All Core Requirements Satisfied</span>'}
            </div>
          </div>
        </div>

        <div class="roadmap-box">
          <div class="roadmap-title">Actionable Preparation & Career Milestone Roadmap</div>
          <ul class="roadmap-list">
            ${item.suggested_roadmap.map(step => `<li>${step}</li>`).join('')}
          </ul>
        </div>

        <div class="result-actions-bar">
          <a href="${applyHref}" target="_blank" rel="noopener noreferrer" class="btn-apply btn-apply-lg">
            <span>Apply on ${item.company} Career Portal</span>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"></path>
              <polyline points="15 3 21 3 21 9"></polyline>
              <line x1="10" y1="14" x2="21" y2="3"></line>
            </svg>
          </a>
          <span class="apply-direct-hint">Opens verified corporate career portal in a new tab</span>
        </div>
      `;
      matchResultsList.appendChild(card);
    });

    resultsWrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
    loadKnowledgeGraph();
  }

  // ==============================================================================
  // 5. USER KNOWLEDGE GRAPH (Interactive Canvas with Particle Simulation)
  // ==============================================================================

  let graphNodes = [];
  let graphLinks = [];
  let graphFilter = "all";
  let graphSearchQuery = "";
  let hoveredNode = null;
  let draggedNode = null;
  let animFrameId = null;

  const nodeColorMap = {
    user: "#0D734B",
    skill: "#06B6D4",
    job: "#6366F1",
    company: "#8B5CF6",
    gap: "#F59E0B"
  };

  let graphScope = "seen";

  async function loadKnowledgeGraph() {
    if (!authToken || !graphCanvas) return;

    try {
      const skillsQuery = Array.from(selectedSkills).join(",");
      const yearsExpQuery = parseFloat(expSlider.value) || 2.0;
      const url = `/api/knowledge-graph?skills=${encodeURIComponent(skillsQuery)}&years_exp=${yearsExpQuery}&scope=${graphScope}`;

      const res = await fetch(url, {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      if (!res.ok) return;

      const data = await res.json();

      // If user profile has saved skills and selectedSkills was empty, populate them
      if (selectedSkills.size === 0 && data.nodes) {
        data.nodes.filter(n => n.type === "skill").forEach(sNode => {
          selectedSkills.add(sNode.label);
        });
        document.querySelectorAll(".skill-chip").forEach(chip => {
          if (selectedSkills.has(chip.textContent)) {
            chip.classList.add("selected");
          } else {
            chip.classList.remove("selected");
          }
        });
      }

      // Update KPI Bar with user-specific metrics
      if (graphNodeCount) graphNodeCount.textContent = data.summary.total_entities || data.nodes.length;
      if (graphLinkCount) graphLinkCount.textContent = data.summary.total_connections || data.links.length;
      if (graphSkillsCount) graphSkillsCount.textContent = data.summary.acquired_skills || data.nodes.filter(n => n.type === "skill").length;
      if (graphJobsSeenCount) graphJobsSeenCount.textContent = data.summary.jobs_seen || data.nodes.filter(n => n.type === "job").length;
      if (graphHighMatchCount) graphHighMatchCount.textContent = data.summary.high_fit_hubs || 0;

      // Initialize Simulation Nodes & Links
      initGraphSimulation(data.nodes, data.links);
    } catch (err) {
      console.warn("Knowledge graph load error:", err);
    }
  }

  function initGraphSimulation(rawNodes, rawLinks) {
    if (!graphCanvas) return;
    const rect = graphCanvas.getBoundingClientRect();
    const width = rect.width || 800;
    const height = rect.height || 560;

    // Set canvas internal resolution for crisp retina rendering
    const dpr = window.devicePixelRatio || 1;
    graphCanvas.width = width * dpr;
    graphCanvas.height = height * dpr;
    const ctx = graphCanvas.getContext("2d");
    ctx.scale(dpr, dpr);

    const centerX = width / 2;
    const centerY = height / 2;

    const nodeMap = new Map();
    const total = rawNodes.length;

    graphNodes = rawNodes.map((n, i) => {
      let r = 7;
      if (n.type === "user") r = 16;
      else if (n.type === "job") r = 11;
      else if (n.type === "skill") r = 8.5;
      else if (n.type === "company") r = 8;
      else if (n.type === "gap") r = 8;

      let initX, initY;
      if (n.type === "user") {
        initX = centerX;
        initY = centerY;
      } else {
        let orbitRadius = 130;
        if (n.type === "skill") orbitRadius = 90 + Math.random() * 50;
        else if (n.type === "job") orbitRadius = 170 + Math.random() * 60;
        else if (n.type === "company") orbitRadius = 230 + Math.random() * 40;
        else if (n.type === "gap") orbitRadius = 150 + Math.random() * 70;

        const angle = (i / total) * Math.PI * 2 + (Math.random() - 0.5) * 0.4;
        initX = centerX + Math.cos(angle) * orbitRadius;
        initY = centerY + Math.sin(angle) * orbitRadius;
      }

      const nodeObj = {
        id: n.id,
        label: n.label,
        type: n.type,
        group: n.group,
        val: n.val,
        meta: n.meta || {},
        radius: r,
        color: nodeColorMap[n.type] || "#10B981",
        x: initX,
        y: initY,
        vx: 0,
        vy: 0,
        pinned: n.type === "user"
      };
      nodeMap.set(n.id, nodeObj);
      return nodeObj;
    });

    graphLinks = rawLinks
      .map(l => ({
        sourceNode: nodeMap.get(l.source),
        targetNode: nodeMap.get(l.target),
        type: l.type,
        weight: l.weight || 1.0,
        label: l.label
      }))
      .filter(l => l.sourceNode && l.targetNode);

    startGraphAnimation(width, height);
  }

  function startGraphAnimation(width, height) {
    if (animFrameId) cancelAnimationFrame(animFrameId);

    function step() {
      const kRepel = 700;
      const kSpring = 0.04;
      const centerX = width / 2;
      const centerY = height / 2;

      // Repulsion between all nodes
      for (let i = 0; i < graphNodes.length; i++) {
        const n1 = graphNodes[i];
        for (let j = i + 1; j < graphNodes.length; j++) {
          const n2 = graphNodes[j];
          const dx = n2.x - n1.x;
          const dy = n2.y - n1.y;
          const distSq = dx * dx + dy * dy + 100;
          const dist = Math.sqrt(distSq);
          const force = kRepel / distSq;
          const fx = (dx / dist) * force;
          const fy = (dy / dist) * force;

          if (!n1.pinned && n1 !== draggedNode) {
            n1.vx -= fx;
            n1.vy -= fy;
          }
          if (!n2.pinned && n2 !== draggedNode) {
            n2.vx += fx;
            n2.vy += fy;
          }
        }

        // Center gravity
        if (!n1.pinned && n1 !== draggedNode) {
          n1.vx += (centerX - n1.x) * 0.002;
          n1.vy += (centerY - n1.y) * 0.002;
        }
      }

      // Spring attraction along links
      for (let l of graphLinks) {
        const n1 = l.sourceNode;
        const n2 = l.targetNode;
        const dx = n2.x - n1.x;
        const dy = n2.y - n1.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;
        const targetDist = l.type === "possesses" ? 95 : (l.type === "evaluated" ? 140 : 110);
        const force = (dist - targetDist) * kSpring;
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;

        if (!n1.pinned && n1 !== draggedNode) {
          n1.vx += fx;
          n1.vy += fy;
        }
        if (!n2.pinned && n2 !== draggedNode) {
          n2.vx -= fx;
          n2.vy += fy;
        }
      }

      // Position update & damping
      for (let n of graphNodes) {
        if (!n.pinned && n !== draggedNode) {
          n.vx *= 0.82;
          n.vy *= 0.82;
          n.x += n.vx;
          n.y += n.vy;

          n.x = Math.max(n.radius + 12, Math.min(width - n.radius - 12, n.x));
          n.y = Math.max(n.radius + 12, Math.min(height - n.radius - 12, n.y));
        }
      }

      renderGraphCanvas(width, height);
      animFrameId = requestAnimationFrame(step);
    }

    step();
  }

  function renderGraphCanvas(width, height) {
    if (!graphCanvas) return;
    const ctx = graphCanvas.getContext("2d");
    ctx.clearRect(0, 0, width, height);

    // Draw grid pattern dots
    ctx.fillStyle = "rgba(16, 185, 129, 0.07)";
    const dotSpacing = 28;
    for (let x = 14; x < width; x += dotSpacing) {
      for (let y = 14; y < height; y += dotSpacing) {
        ctx.fillRect(x, y, 1.5, 1.5);
      }
    }

    function isNodeFiltered(n) {
      if (graphFilter === "skills") return n.type === "skill" || n.type === "user";
      if (graphFilter === "jobs") return n.type === "job" || n.type === "company" || n.type === "user";
      if (graphFilter === "gaps") return n.type === "gap" || n.type === "job";
      return true;
    }

    function isNodeSearchMatch(n) {
      if (!graphSearchQuery) return false;
      return n.label.toLowerCase().includes(graphSearchQuery.toLowerCase());
    }

    // Draw Links
    for (let l of graphLinks) {
      const activeLink = isNodeFiltered(l.sourceNode) && isNodeFiltered(l.targetNode);
      ctx.save();
      ctx.beginPath();
      ctx.moveTo(l.sourceNode.x, l.sourceNode.y);
      ctx.lineTo(l.targetNode.x, l.targetNode.y);

      if (l.type === "gap") {
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = activeLink ? "rgba(245, 158, 11, 0.55)" : "rgba(245, 158, 11, 0.12)";
        ctx.lineWidth = 1.2;
      } else if (l.type === "evaluated") {
        ctx.setLineDash([]);
        ctx.strokeStyle = activeLink ? "rgba(99, 102, 241, 0.45)" : "rgba(99, 102, 241, 0.1)";
        ctx.lineWidth = 1.6;
      } else {
        ctx.setLineDash([]);
        ctx.strokeStyle = activeLink ? "rgba(16, 185, 129, 0.35)" : "rgba(16, 185, 129, 0.08)";
        ctx.lineWidth = 1.2;
      }
      ctx.stroke();
      ctx.restore();
    }

    // Draw Nodes
    for (let n of graphNodes) {
      const isFiltered = isNodeFiltered(n);
      const isSearchHit = isNodeSearchMatch(n);
      const isHovered = hoveredNode === n;

      ctx.save();
      ctx.globalAlpha = isFiltered ? 1.0 : 0.18;

      if (n.type === "user" || isHovered || isSearchHit) {
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius + 6, 0, Math.PI * 2);
        ctx.fillStyle = isSearchHit ? "rgba(245, 158, 11, 0.35)" : `${n.color}33`;
        ctx.fill();
      }

      ctx.beginPath();
      ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
      ctx.fillStyle = n.color;
      ctx.fill();
      ctx.lineWidth = isHovered || isSearchHit ? 2.5 : 1.5;
      ctx.strokeStyle = isSearchHit ? "#F59E0B" : "#FFFFFF";
      ctx.stroke();

      ctx.font = n.type === "user" ? "600 12px var(--font-sans)" : (n.type === "job" ? "500 11px var(--font-sans)" : "400 10.5px var(--font-sans)");
      ctx.fillStyle = isHovered ? "#000000" : (isFiltered ? "#14221A" : "#8A9F94");
      ctx.textAlign = "center";
      ctx.fillText(n.label, n.x, n.y + n.radius + 12);

      ctx.restore();
    }
  }

  // Knowledge Graph Mouse / Touch Interactions
  if (graphCanvas) {
    function getNodeAt(x, y) {
      for (let i = graphNodes.length - 1; i >= 0; i--) {
        const n = graphNodes[i];
        const dx = x - n.x;
        const dy = y - n.y;
        if (Math.hypot(dx, dy) <= n.radius + 5) {
          return n;
        }
      }
      return null;
    }

    graphCanvas.addEventListener("mousemove", (e) => {
      const rect = graphCanvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      if (draggedNode) {
        draggedNode.x = mx;
        draggedNode.y = my;
        draggedNode.vx = 0;
        draggedNode.vy = 0;
      } else {
        const hit = getNodeAt(mx, my);
        if (hit !== hoveredNode) {
          hoveredNode = hit;
          graphCanvas.style.cursor = hit ? "pointer" : "grab";
        }
      }
    });

    graphCanvas.addEventListener("mousedown", (e) => {
      const rect = graphCanvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      const hit = getNodeAt(mx, my);
      if (hit) {
        draggedNode = hit;
        graphCanvas.style.cursor = "grabbing";
        showNodeInspector(hit);
      }
    });

    window.addEventListener("mouseup", () => {
      if (draggedNode) {
        draggedNode = null;
        graphCanvas.style.cursor = hoveredNode ? "pointer" : "grab";
      }
    });
  }

  function showNodeInspector(node) {
    if (!graphInspectorCard) return;
    graphInspectorCard.style.display = "block";
    if (inspectorBadge) {
      inspectorBadge.textContent = node.group.toUpperCase();
      inspectorBadge.className = `inspector-badge ${node.type}`;
    }
    if (inspectorTitle) inspectorTitle.textContent = node.label;

    if (inspectorMeta) {
      if (node.type === "job") {
        inspectorMeta.textContent = `${node.meta.company || ''} • ${node.meta.location || ''} • Match: ${node.meta.match_score ? node.meta.match_score.toFixed(1) + '%' : 'Calculated'}`;
      } else if (node.type === "skill") {
        inspectorMeta.textContent = `Acquired Candidate Competency • Verified in Profile`;
      } else if (node.type === "gap") {
        inspectorMeta.textContent = `Identified Skill Deficit • Recommended for high-fit roles`;
      } else if (node.type === "company") {
        inspectorMeta.textContent = `Employer Partner • Tier: ${node.meta.tier || 'Tech Enterprise'}`;
      } else {
        inspectorMeta.textContent = `Candidate Identity Root Node`;
      }
    }

    if (inspectorDetails) {
      if (node.type === "job" && node.meta.missing_skills) {
        inspectorDetails.innerHTML = `<strong>Required Missing:</strong> ${node.meta.missing_skills.join(", ") || "None (Fully Matched)"}<br><strong>Salary:</strong> ${node.meta.salary || 'Market Competitive'}`;
      } else if (node.type === "gap" && node.meta.required_by) {
        inspectorDetails.innerHTML = `<strong>Required By:</strong> ${node.meta.required_by.join(", ")}`;
      } else if (node.type === "skill") {
        inspectorDetails.innerHTML = `Active in candidate embedding space. Enables semantic similarity alignment.`;
      } else {
        inspectorDetails.innerHTML = `Connected to platform semantic hubs and market opportunities.`;
      }
    }

    if (inspectorActions) {
      inspectorActions.innerHTML = "";
      if (node.type === "job") {
        const applyHref = node.meta.apply_url || `https://www.google.com/search?q=${encodeURIComponent((node.meta.company || '') + ' careers')}`;
        const applyLink = document.createElement("a");
        applyLink.href = applyHref;
        applyLink.target = "_blank";
        applyLink.rel = "noopener noreferrer";
        applyLink.className = "btn-apply btn-apply-sm";
        applyLink.innerHTML = `<span>Apply</span><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>`;
        inspectorActions.appendChild(applyLink);
      } else if (node.type === "gap") {
        const addBtn = document.createElement("button");
        addBtn.type = "button";
        addBtn.className = "btn-secondary";
        addBtn.style.padding = "4px 8px";
        addBtn.style.fontSize = "11.5px";
        addBtn.textContent = "+ Add to My Skills";
        addBtn.addEventListener("click", () => {
          selectedSkills.add(node.label);
          document.querySelectorAll(".skill-chip").forEach(chip => {
            if (chip.textContent === node.label) chip.classList.add("selected");
          });
          loadKnowledgeGraph();
          showNodeInspector(node);
        });
        inspectorActions.appendChild(addBtn);
      }
    }
  }

  if (closeInspectorBtn) {
    closeInspectorBtn.addEventListener("click", () => {
      if (graphInspectorCard) graphInspectorCard.style.display = "none";
    });
  }

  // Knowledge Graph Filter Buttons
  graphFilterBtns.forEach(btn => {
    if (btn.id === "graph-scope-toggle-btn") return;
    btn.addEventListener("click", () => {
      graphFilterBtns.forEach(b => {
        if (b.id !== "graph-scope-toggle-btn") b.classList.remove("active");
      });
      btn.classList.add("active");
      graphFilter = btn.getAttribute("data-filter") || "all";
    });
  });

  // Scope Toggle: Seen Jobs vs All Market Jobs
  if (graphScopeToggleBtn) {
    graphScopeToggleBtn.addEventListener("click", () => {
      if (graphScope === "seen") {
        graphScope = "all";
        graphScopeToggleBtn.textContent = "🌐 All Market Jobs";
        graphScopeToggleBtn.classList.add("all-active");
      } else {
        graphScope = "seen";
        graphScopeToggleBtn.textContent = "⚡ Seen Only";
        graphScopeToggleBtn.classList.remove("all-active");
      }
      loadKnowledgeGraph();
    });
  }

  // Search input in graph
  if (graphSearchInput) {
    graphSearchInput.addEventListener("input", (e) => {
      graphSearchQuery = e.target.value.trim();
    });
  }

  // Reset graph button
  if (graphResetBtn) {
    graphResetBtn.addEventListener("click", () => {
      if (graphSearchInput) graphSearchInput.value = "";
      graphSearchQuery = "";
      graphFilter = "all";
      graphScope = "seen";
      if (graphScopeToggleBtn) {
        graphScopeToggleBtn.textContent = "⚡ Seen Only";
        graphScopeToggleBtn.classList.remove("all-active");
      }
      graphFilterBtns.forEach(b => {
        if (b.id !== "graph-scope-toggle-btn") {
          b.classList.toggle("active", b.getAttribute("data-filter") === "all");
        }
      });
      if (graphInspectorCard) graphInspectorCard.style.display = "none";
      loadKnowledgeGraph();
    });
  }

  // ==============================================================================
  // 6. PULSEAI CAREER ASSISTANT (Drawer & Domain Guardrail Interceptor)
  // ==============================================================================

  if (assistantToggleBtn && assistantDrawer) {
    assistantToggleBtn.addEventListener("click", () => {
      const isVisible = assistantDrawer.style.display !== "none";
      assistantDrawer.style.display = isVisible ? "none" : "flex";
      if (!isVisible && assistantInput) assistantInput.focus();
    });
  }

  if (closeAssistantBtn && assistantDrawer) {
    closeAssistantBtn.addEventListener("click", () => {
      assistantDrawer.style.display = "none";
    });
  }

  // Quick Chips
  assistantQuickChips.forEach(chip => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      if (prompt && assistantInput) {
        assistantInput.value = prompt;
        if (assistantChatForm) {
          assistantChatForm.dispatchEvent(new Event("submit", { cancelable: true, bubbles: true }));
        }
      }
    });
  });

  // Chat Form Submission
  if (assistantChatForm) {
    assistantChatForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const query = assistantInput.value.trim();
      if (!query) return;

      if (!authToken) {
        alert("Please sign in to chat with the PulseAI Career Assistant.");
        updateAuthUI();
        return;
      }

      // Append user bubble
      appendChatMessage(query, "user");
      assistantInput.value = "";

      // Append loading indicator
      const loadingBubble = appendChatMessage("Analyzing market signals and career graph...", "assistant", false, true);

      try {
        const res = await fetch("/api/assistant/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${authToken}`
          },
          body: JSON.stringify({
            message: query,
            current_skills: Array.from(selectedSkills),
            years_experience: parseFloat(expSlider.value) || 2.0
          })
        });

        const data = await res.json();
        if (loadingBubble && loadingBubble.parentNode) {
          loadingBubble.remove();
        }

        if (!res.ok) {
          appendChatMessage(data.detail || "Assistant service unavailable.", "assistant", true);
          return;
        }

        if (data.is_error) {
          // Off-topic or guardrail violation (e.g. "make biryani")
          appendChatMessage(data.reply, "assistant", true);
        } else {
          // Success response
          appendChatMessage(data.reply, "assistant", false, false, data.suggested_jobs);
        }
      } catch (err) {
        if (loadingBubble && loadingBubble.parentNode) {
          loadingBubble.remove();
        }
        appendChatMessage("Network connection error: " + err.message, "assistant", true);
      }
    });
  }

  function appendChatMessage(text, sender = "assistant", isError = false, isLoading = false, jobs = null) {
    if (!assistantChatMessages) return null;

    const row = document.createElement("div");
    row.className = `chat-msg ${sender}`;

    const bubble = document.createElement("div");
    bubble.className = `msg-bubble ${isError ? 'error' : ''}`;

    if (isLoading) {
      bubble.innerHTML = `<span style="display: inline-block; animation: spin 1s infinite linear;">⟳</span> ${escapeHtml(text)}`;
    } else if (isError) {
      bubble.innerHTML = `<strong>🛡️ Guardrail Alert:</strong><br>${escapeHtml(text).replace(/\n/g, '<br>')}`;
    } else {
      let formatted = escapeHtml(text)
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');

      bubble.innerHTML = formatted;

      if (jobs && jobs.length > 0) {
        jobs.slice(0, 3).forEach(j => {
          const jobCard = document.createElement("div");
          jobCard.className = "chat-job-card";
          const applyHref = j.apply_url || `https://www.google.com/search?q=${encodeURIComponent(j.company + ' careers')}`;
          jobCard.innerHTML = `
            <div class="chat-job-card-title">${escapeHtml(j.title)}</div>
            <div class="chat-job-card-sub">${escapeHtml(j.company)} • ${escapeHtml(j.location)} • <span style="color: var(--accent-green); font-weight: 600;">${j.match_score ? j.match_score.toFixed(1) + '%' : 'Match'}</span></div>
            <div class="chat-job-card-actions">
              <span style="font-size: 11px; color: var(--text-muted);">${escapeHtml(j.salary_range || 'Competitive')}</span>
              <a href="${applyHref}" target="_blank" rel="noopener noreferrer" class="btn-apply btn-apply-sm">
                <span>Apply</span>
                <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.3"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
              </a>
            </div>
          bubble.appendChild(jobCard);

          const chatApply = jobCard.querySelector(".btn-apply");
          if (chatApply) {
            chatApply.addEventListener("click", () => {
              trackJobView(j.id);
              setTimeout(loadKnowledgeGraph, 300);
            });
          }
      }
    }

    row.appendChild(bubble);
    assistantChatMessages.appendChild(row);
    assistantChatMessages.scrollTop = assistantChatMessages.scrollHeight;
    return row;
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  // Safe Recalibration Hook (if element present)
  if (retrainBtn) {
    retrainBtn.addEventListener("click", async () => {
      retrainBtn.disabled = true;
      retrainBtn.textContent = "Initiating Calibration...";
      try {
        const res = await fetch("/api/model/retrain", { method: "POST" });
        const data = await res.json();
        alert(data.message || "Model calibration cycle triggered!");
      } catch (err) {
        alert("Error: " + err.message);
      } finally {
        retrainBtn.disabled = false;
        retrainBtn.textContent = "Trigger Model Calibration";
      }
    });
  }

  // Start with session check
  verifyCurrentSession();
});
