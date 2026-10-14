/**
 * TalentPulse — Frontend Controller
 * Minimalist, responsive, Claude & Gemini interaction mechanics.
 * Robust Authentication, Captcha, Single-Account Isolation, & Semantic Diagnostics.
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

  // DOM Elements - Auth & Header
  const unauthView = document.getElementById("unauth-view");
  const authView = document.getElementById("auth-view");
  const authAvatar = document.getElementById("auth-avatar");
  const authUserName = document.getElementById("auth-user-name");
  const authUserEmail = document.getElementById("auth-user-email");
  const authUserProvider = document.getElementById("auth-user-provider");
  const logoutBtn = document.getElementById("logout-btn");
  const openAuthModalBtn = document.getElementById("open-auth-modal-btn");
  const headerAuthBtn = document.getElementById("header-auth-btn");
  const headerAccountLabel = document.getElementById("header-account-label");

  // DOM Elements - Auth Modal
  const authModal = document.getElementById("auth-modal");
  const closeAuthModalBtn = document.getElementById("close-auth-modal-btn");
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

  // Demo Profiles
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
  // 1. NAVIGATION CONTROLLER
  // ==============================================================================
  const viewTitles = {
    "match-view": "Match & Diagnose",
    "jobs-view": "Market Openings",
    "metrics-view": "Precision Analytics",
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
  // 2. AUTHENTICATION & SESSION MANAGEMENT
  // ==============================================================================

  function updateAuthUI() {
    if (currentUser && authToken) {
      unauthView.style.display = "none";
      authView.style.display = "flex";
      
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

      headerAccountLabel.textContent = (currentUser.full_name || "User").split(" ")[0];
      
      // Auto-fill candidate name if not modified
      if (candNameInput.value === "Hamza Tariq" && currentUser.full_name) {
        candNameInput.value = currentUser.full_name;
      }
    } else {
      unauthView.style.display = "flex";
      authView.style.display = "none";
      headerAccountLabel.textContent = "Sign In";
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
        // Token expired or invalid
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

  function openAuthModal(defaultTab = "login") {
    clearAuthAlert();
    authModal.style.display = "flex";
    if (defaultTab === "register") {
      switchTab("register");
    } else {
      switchTab("login");
    }
  }

  function closeAuthModal() {
    authModal.style.display = "none";
    clearAuthAlert();
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

  // Event Listeners for Auth Modal
  openAuthModalBtn.addEventListener("click", () => openAuthModal("login"));
  headerAuthBtn.addEventListener("click", () => {
    if (currentUser) {
      // Toggle sign out or show notification
      if (confirm(`You are currently signed in as ${currentUser.full_name} (${currentUser.email}). Sign out?`)) {
        handleLogout();
      }
    } else {
      openAuthModal("login");
    }
  });

  closeAuthModalBtn.addEventListener("click", closeAuthModal);
  authModal.addEventListener("click", (e) => {
    if (e.target === authModal) closeAuthModal();
  });

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

    // Client-side validations
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

      // Success
      authToken = data.token;
      currentUser = data.user;
      localStorage.setItem("talentpulse_token", authToken);
      localStorage.setItem("talentpulse_user", JSON.stringify(currentUser));

      showAuthAlert("Account created successfully! Welcome to TalentPulse.", "success");
      updateAuthUI();
      setTimeout(closeAuthModal, 1200);
    } catch (err) {
      showAuthAlert("Network connection error: " + err.message);
      fetchCaptcha("register");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Create Account";
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

      // Success
      authToken = data.token;
      currentUser = data.user;
      localStorage.setItem("talentpulse_token", authToken);
      localStorage.setItem("talentpulse_user", JSON.stringify(currentUser));

      showAuthAlert("Successfully signed in!", "success");
      updateAuthUI();
      setTimeout(closeAuthModal, 800);
    } catch (err) {
      showAuthAlert("Network connection error: " + err.message);
      fetchCaptcha("login");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Sign In";
    }
  });

  // Handle Google OAuth Sign-In
  googleLoginBtn.addEventListener("click", async () => {
    clearAuthAlert();
    const promptEmail = prompt("Continue with Google:\nEnter your Gmail or Workspace email:", currentUser ? currentUser.email : "hamza.ihsan@gmail.com");
    if (!promptEmail || !promptEmail.includes("@")) return;

    try {
      const res = await fetch("/api/auth/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: promptEmail.trim().toLowerCase(),
          full_name: promptEmail.split("@")[0].replace(".", " ").replace(/\b\w/g, c => c.toUpperCase())
        })
      });
      const data = await res.json();
      if (!res.ok) {
        showAuthAlert(data.detail || "Google authentication failed.");
        return;
      }
      authToken = data.token;
      currentUser = data.user;
      localStorage.setItem("talentpulse_token", authToken);
      localStorage.setItem("talentpulse_user", JSON.stringify(currentUser));
      updateAuthUI();
      closeAuthModal();
    } catch (err) {
      showAuthAlert("Google OAuth error: " + err.message);
    }
  });

  // Handle GitHub OAuth Sign-In
  githubLoginBtn.addEventListener("click", async () => {
    clearAuthAlert();
    const promptUsername = prompt("Continue with GitHub:\nEnter your GitHub username or developer email:", "hamzaihsan9");
    if (!promptUsername) return;

    const email = promptUsername.includes("@") ? promptUsername : `${promptUsername.toLowerCase()}@users.noreply.github.com`;

    try {
      const res = await fetch("/api/auth/github", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          full_name: promptUsername.replace(/[-_]/g, " ").replace(/\b\w/g, c => c.toUpperCase())
        })
      });
      const data = await res.json();
      if (!res.ok) {
        showAuthAlert(data.detail || "GitHub authentication failed.");
        return;
      }
      authToken = data.token;
      currentUser = data.user;
      localStorage.setItem("talentpulse_token", authToken);
      localStorage.setItem("talentpulse_user", JSON.stringify(currentUser));
      updateAuthUI();
      closeAuthModal();
    } catch (err) {
      showAuthAlert("GitHub OAuth error: " + err.message);
    }
  });

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

  // ==============================================================================
  // 3. SKILLS TAXONOMY & JOBS CATALOG
  // ==============================================================================

  async function loadSkills() {
    try {
      const res = await fetch("/api/skills");
      allSkillsTaxonomy = await res.json();
      
      chipContainer.innerHTML = "";
      // High-impact skills for quick-chips
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
    try {
      const res = await fetch("/api/jobs");
      jobsCache = await res.json();

      jobSelect.innerHTML = '<option value="">Compare across all active market jobs</option>';
      jobsTableBody.innerHTML = "";

      jobsCache.forEach(job => {
        const opt = document.createElement("option");
        opt.value = job.id;
        opt.textContent = `${job.title} — ${job.company} (${job.location})`;
        jobSelect.appendChild(opt);

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
            <button type="button" class="btn-secondary select-job-btn" data-job-id="${job.id}" style="padding: 4px 10px; font-size: 12px;">
              Target Opening
            </button>
          </td>
        `;
        jobsTableBody.appendChild(tr);
      });

      // Target Opening Buttons inside Table
      document.querySelectorAll(".select-job-btn").forEach(btn => {
        btn.addEventListener("click", () => {
          const jId = btn.getAttribute("data-job-id");
          jobSelect.value = jId;
          // Switch to match view
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

      const headers = { "Content-Type": "application/json" };
      if (authToken) {
        headers["Authorization"] = `Bearer ${authToken}`;
      }

      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: headers,
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Suitability evaluation failed");

      const data = await res.json();
      renderMatchResults(data);
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

      const card = document.createElement("div");
      card.className = "result-card";
      card.innerHTML = `
        <div class="result-top-bar">
          <div class="job-title-group">
            <h2>${item.job_title}</h2>
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
      `;
      matchResultsList.appendChild(card);
    });

    resultsWrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ==============================================================================
  // 5. METRICS & RECALIBRATION
  // ==============================================================================

  async function loadMetrics() {
    try {
      const res = await fetch("/api/model/metrics");
      const metrics = await res.json();
      if (metrics.val_mae) {
        document.getElementById("metric-mae").textContent = `${metrics.val_mae}%`;
      }
      if (metrics.val_r2 && metrics.val_r2.length) {
        const lastR2 = metrics.val_r2[metrics.val_r2.length - 1];
        document.getElementById("metric-corr").textContent = lastR2.toFixed(3);
      }
      if (metrics.vocab_size) {
        document.getElementById("metric-vocab").textContent = metrics.vocab_size;
      }
    } catch (err) {
      console.error("Failed to load metrics:", err);
    }
  }

  retrainBtn.addEventListener("click", async () => {
    retrainBtn.disabled = true;
    retrainBtn.textContent = "Initiating Calibration...";
    try {
      const res = await fetch("/api/model/retrain", { method: "POST" });
      const data = await res.json();
      alert(data.message || "Model calibration cycle triggered!");
      setTimeout(loadMetrics, 4000);
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      retrainBtn.disabled = false;
      retrainBtn.textContent = "Trigger Model Calibration";
    }
  });

  // Initial Boot
  verifyCurrentSession();
  loadSkills();
  loadJobs();
  loadMetrics();
});
