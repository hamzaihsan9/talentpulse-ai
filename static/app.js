/**
 * TalentPulse AI — Frontend Controller
 * Minimalist, responsive, Claude & Gemini interaction mechanics.
 */

document.addEventListener("DOMContentLoaded", () => {
  // State
  let selectedSkills = new Set();
  let allSkillsTaxonomy = {};
  let jobsCache = [];

  // DOM Elements
  const navItems = document.querySelectorAll(".nav-item");
  const viewSections = document.querySelectorAll(".view-section");
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
      text: "Senior Deep Learning Specialist with 5 years leading ML solutions. Specialized in custom PyTorch architectures, transformer fine-tuning, metric learning, and low-latency ONNX/Triton inference deployments. Proven track record scaling ML systems across cloud infrastructures."
    }
  };

  // 1. Navigation Controller
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      navItems.forEach(n => n.classList.remove("active"));
      viewSections.forEach(v => v.classList.remove("active"));

      item.classList.add("active");
      const targetView = item.getAttribute("data-view");
      const targetElem = document.getElementById(targetView);
      if (targetElem) {
        targetElem.classList.add("active");
      }
    });
  });

  // 2. Experience Slider
  expSlider.addEventListener("input", (e) => {
    const val = parseFloat(e.target.value);
    expDisplay.textContent = `${val.toFixed(1)} ${val === 1 ? 'Year' : 'Years'}`;
  });

  // 3. Load Skills Taxonomy
  async function loadSkills() {
    try {
      const res = await fetch("/api/skills");
      allSkillsTaxonomy = await res.json();
      
      chipContainer.innerHTML = "";
      // Gather top high-impact skills for quick-chips
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

  // 4. Load Active Jobs
  async function loadJobs() {
    try {
      const res = await fetch("/api/jobs");
      jobsCache = await res.json();

      // Populate select dropdown
      jobSelect.innerHTML = '<option value="">Compare across all active market jobs</option>';
      jobsTableBody.innerHTML = "";

      jobsCache.forEach(job => {
        // Select option
        const opt = document.createElement("option");
        opt.value = job.id;
        opt.textContent = `${job.title} — ${job.company} (${job.location})`;
        jobSelect.appendChild(opt);

        // Table row
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>
            <strong>${job.title}</strong>
            <div style="font-size: 12.5px; color: var(--text-secondary);">${job.company}</div>
          </td>
          <td>
            <div>${job.location}</div>
            <span style="font-size: 11.5px; color: var(--accent-warm);">${job.tier || 'Enterprise'}</span>
          </td>
          <td>${job.experience_years}+ years</td>
          <td><code style="font-size: 12px; background: var(--bg-tertiary); padding: 2px 6px; border-radius: 4px;">${job.salary_range || 'Competitive'}</code></td>
          <td>
            <div class="tag-list">
              ${job.required_skills.slice(0, 3).map(s => `<span class="skill-chip" style="padding: 2px 8px; font-size: 11px;">${s}</span>`).join('')}
              ${job.required_skills.length > 3 ? `<span style="font-size: 11px; color: var(--text-muted);">+${job.required_skills.length - 3}</span>` : ''}
            </div>
          </td>
          <td>
            <button class="btn-secondary" style="padding: 5px 12px; font-size: 12px;" onclick="window.quickMatchJob('${job.id}')">Match</button>
          </td>
        `;
        jobsTableBody.appendChild(tr);
      });
    } catch (err) {
      console.error("Failed to load jobs list:", err);
    }
  }

  // Quick match from table
  window.quickMatchJob = function(jobId) {
    jobSelect.value = jobId;
    const matchNav = document.querySelector('[data-view="match-view"]');
    if (matchNav) matchNav.click();
    triggerMatchAnalysis();
  };

  // 5. Populate Demo Profiles
  function applyDemoProfile(profileKey) {
    const p = demoProfiles[profileKey];
    if (!p) return;

    candNameInput.value = p.name;
    expSlider.value = p.exp;
    expDisplay.textContent = `${p.exp.toFixed(1)} ${p.exp === 1 ? 'Year' : 'Years'}`;
    resumeTextInput.value = p.text;

    // Reset chips
    selectedSkills.clear();
    p.skills.forEach(s => selectedSkills.add(s));

    document.querySelectorAll(".skill-chip").forEach(chip => {
      if (selectedSkills.has(chip.textContent.trim())) {
        chip.classList.add("selected");
      } else {
        chip.classList.remove("selected");
      }
    });

    // Automatically run match
    triggerMatchAnalysis();
  }

  document.getElementById("load-fresh-btn").addEventListener("click", () => applyDemoProfile("junior"));
  document.getElementById("load-rag-btn").addEventListener("click", () => applyDemoProfile("rag"));
  document.getElementById("load-senior-btn").addEventListener("click", () => applyDemoProfile("senior"));

  // 6. Execute Neural Semantic Match
  async function triggerMatchAnalysis() {
    const name = candNameInput.value.trim() || "Candidate";
    const yearsExp = parseFloat(expSlider.value) || 0.0;
    const resumeText = resumeTextInput.value.trim();
    const targetJobId = jobSelect.value || null;

    runMatchBtn.disabled = true;
    runMatchBtn.innerHTML = `
      <span style="display: inline-block; animation: spin 1s infinite linear;">⟳</span>
      <span>Computing Embeddings...</span>
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) throw new Error("Inference failed");

      const data = await res.json();
      renderMatchResults(data);
    } catch (err) {
      alert("Inference error: " + err.message);
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

  // 7. Render Match Results
  function renderMatchResults(data) {
    resultsWrapper.style.display = "block";
    inferenceTimeTag.textContent = `Inference completed in ${data.model_inference_ms}ms • PyTorch Dual-Encoder`;
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
              <span style="color: var(--accent-warm);">${item.salary_range || 'Competitive'}</span>
            </div>
          </div>
          <div class="match-score-pill">
            <span class="score-num ${scoreClass}">${score.toFixed(1)}%</span>
            <span class="score-label">Neural Match</span>
            <span class="readiness-tag ${readinessClass}">${item.readiness_level}</span>
          </div>
        </div>

        <div style="font-size: 13px; color: var(--text-secondary); margin-bottom: 12px;">
          Latent Cosine Alignment: <code style="font-size: 12px; font-weight: 600; color: var(--text-main);">${item.cosine_similarity.toFixed(3)}</code> (Hyperspherical Distance: ${(1.0 - item.cosine_similarity).toFixed(3)})
        </div>

        <div class="skill-grid">
          <div>
            <div class="skill-col-title">Matched Core Competencies (${item.skill_gap.matched_skills.length})</div>
            <div class="tag-list">
              ${item.skill_gap.matched_skills.length > 0 
                ? item.skill_gap.matched_skills.map(s => `<span class="tag-matched">✓ ${s}</span>`).join('') 
                : '<span style="font-size: 12px; color: var(--text-muted);">None matched yet</span>'}
            </div>
          </div>
          <div>
            <div class="skill-col-title">Missing Critical Requirements (${item.skill_gap.missing_required.length})</div>
            <div class="tag-list">
              ${item.skill_gap.missing_required.length > 0 
                ? item.skill_gap.missing_required.map(s => `<span class="tag-missing">✗ ${s}</span>`).join('') 
                : '<span class="tag-matched" style="font-size: 12px;">✓ 100% Core Requirements Met</span>'}
            </div>
          </div>
        </div>

        <div class="roadmap-box">
          <div class="roadmap-title">Actionable Career Roadmap & Interview Preparation</div>
          <ul class="roadmap-list">
            ${item.suggested_roadmap.map(step => `<li>${step}</li>`).join('')}
          </ul>
        </div>
      `;
      matchResultsList.appendChild(card);
    });

    // Smooth scroll down to results
    resultsWrapper.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // 8. Load Metrics
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

  // 9. Retrain trigger
  retrainBtn.addEventListener("click", async () => {
    retrainBtn.disabled = true;
    retrainBtn.textContent = "Initiating Retraining...";
    try {
      const res = await fetch("/api/model/retrain", { method: "POST" });
      const data = await res.json();
      alert(data.message || "Model retraining started!");
      setTimeout(loadMetrics, 4000);
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      retrainBtn.disabled = false;
      retrainBtn.textContent = "Trigger Retraining";
    }
  });

  // Initial Boot
  loadSkills();
  loadJobs();
  loadMetrics();
});
