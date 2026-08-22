document.addEventListener("DOMContentLoaded", () => {
  console.log("SmartLearn Homepage Loaded");
});

document.addEventListener("DOMContentLoaded", () => {
  const dataElement = document.getElementById("flashcards-topic-data");
  const modal = document.getElementById("flashcard-learn-modal");
  const addRowButton = document.querySelector("[data-add-flashcard-row]");
  const creatorList = document.querySelector("[data-flashcard-creator-list]");
  const createForm = document.getElementById("flashcard-create-form");
  const addMcqRowButton = document.querySelector("[data-add-mcq-row]");
  const mcqCreatorList = document.querySelector("[data-mcq-creator-list]");
  const mcqCreateForm = document.getElementById("mcq-create-form");

  if (addRowButton && creatorList) {
    addRowButton.addEventListener("click", () => {
      const existingRows = creatorList.querySelectorAll(
        ".flashcard-entry-card",
      ).length;
      const row = document.createElement("article");
      row.className = "flashcard-entry-card";
      row.innerHTML = `
                <div class="flashcard-entry-card__topline">
                    <span class="topic-card-count">Card ${existingRows + 1}</span>
                    <button type="button" class="reaction-button flashcard-remove-row">Remove</button>
                </div>
                <label class="label-bold">Front</label>
                <textarea name="front" class="form-control" rows="3" placeholder="Question or term" required></textarea>
                <label class="label-bold">Back</label>
                <textarea name="back" class="form-control" rows="4" placeholder="Answer or explanation" required></textarea>
            `;
      creatorList.appendChild(row);
    });

    creatorList.addEventListener("click", (event) => {
      const removeButton = event.target.closest(".flashcard-remove-row");
      if (!removeButton) {
        return;
      }

      const rows = creatorList.querySelectorAll(".flashcard-entry-card");
      if (rows.length === 1) {
        return;
      }

      removeButton.closest(".flashcard-entry-card").remove();
      creatorList
        .querySelectorAll(".flashcard-entry-card")
        .forEach((row, index) => {
          const count = row.querySelector(".topic-card-count");
          if (count) {
            count.textContent = `Card ${index + 1}`;
          }
        });
    });
  }

  if (createForm) {
    createForm.addEventListener("submit", () => {
      const submitButton = createForm.querySelector("button[type='submit']");
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Sharing...";
      }
    });
  }

  if (addMcqRowButton && mcqCreatorList) {
    addMcqRowButton.addEventListener("click", () => {
      const existingRows = mcqCreatorList.querySelectorAll(
        ".flashcard-entry-card",
      ).length;
      const row = document.createElement("article");
      row.className = "flashcard-entry-card";
      row.innerHTML = `
                <div class="flashcard-entry-card__topline">
                    <span class="topic-card-count">Question ${existingRows + 1}</span>
                    <button type="button" class="reaction-button flashcard-remove-row">Remove</button>
                </div>
                <label class="label-bold">Question</label>
                <textarea name="question" class="form-control" rows="3" required></textarea>
                <label class="label-bold">Options</label>
                <input type="text" name="option_a" class="form-control compact-input" placeholder="Option A" required>
                <input type="text" name="option_b" class="form-control compact-input" placeholder="Option B" required>
                <input type="text" name="option_c" class="form-control compact-input" placeholder="Option C" required>
                <input type="text" name="option_d" class="form-control compact-input" placeholder="Option D" required>
                <label class="label-bold">Correct Answer</label>
                <select name="correct_option" class="form-control" required>
                    <option value="A">A</option>
                    <option value="B">B</option>
                    <option value="C">C</option>
                    <option value="D">D</option>
                </select>
                <label class="label-bold">Explanation</label>
                <textarea name="explanation" class="form-control" rows="3" placeholder="Optional answer explanation"></textarea>
            `;
      mcqCreatorList.appendChild(row);
    });

    mcqCreatorList.addEventListener("click", (event) => {
      const removeButton = event.target.closest(".flashcard-remove-row");
      if (!removeButton) {
        return;
      }

      const rows = mcqCreatorList.querySelectorAll(".flashcard-entry-card");
      if (rows.length === 1) {
        return;
      }

      removeButton.closest(".flashcard-entry-card").remove();
      mcqCreatorList
        .querySelectorAll(".flashcard-entry-card")
        .forEach((row, index) => {
          const count = row.querySelector(".topic-card-count");
          if (count) {
            count.textContent = `Question ${index + 1}`;
          }
        });
    });
  }

  if (mcqCreateForm) {
    mcqCreateForm.addEventListener("submit", () => {
      const submitButton = mcqCreateForm.querySelector("button[type='submit']");
      if (submitButton) {
        submitButton.disabled = true;
        submitButton.textContent = "Sharing...";
      }
    });
  }

  if (!dataElement || !modal) return;

  let topicGroups = [];
  try {
    topicGroups = JSON.parse(dataElement.textContent || "[]");
  } catch (error) {
    console.error("Unable to parse flashcard topic data", error);
    return;
  }

  if (!topicGroups.length) return;

  // Create a topic lookup map that supports both modal_key and topic_slug
  const topicMap = new Map();
  topicGroups.forEach((group) => {
    if (group.modal_key) topicMap.set(group.modal_key, group);
    if (group.topic_slug) topicMap.set(group.topic_slug, group);
    if (group.topic) topicMap.set(group.topic, group);
  });

  const modalTopic = document.getElementById("flashcard-learn-topic");
  const modalTitle = document.getElementById("flashcard-learn-title");
  const modalCard = document.getElementById("flashcard-modal-card");
  const modalFrontTopic = document.getElementById(
    "flashcard-modal-front-topic",
  );
  const modalFrontText = document.getElementById("flashcard-modal-front-text");
  const modalBackTopic = document.getElementById("flashcard-modal-back-topic");
  const modalBackText = document.getElementById("flashcard-modal-back-text");
  const modalCounter = document.getElementById("flashcard-modal-counter");

  let activeGroup = null;
  let activeIndex = 0;

  const setModalCard = () => {
    if (!activeGroup || !activeGroup.cards || !activeGroup.cards.length) return;

    const card = activeGroup.cards[activeIndex];
    if (modalTopic) modalTopic.textContent = activeGroup.topic;
    if (modalTitle) modalTitle.textContent = activeGroup.topic;
    if (modalFrontTopic) modalFrontTopic.textContent = activeGroup.topic;
    if (modalFrontText) modalFrontText.textContent = card.front;
    if (modalBackTopic) modalBackTopic.textContent = activeGroup.topic;
    if (modalBackText) modalBackText.textContent = card.back;

    // Reset card to front side when navigating
    if (modalCard) modalCard.classList.remove("is-flipped");

    if (modalCounter) {
      modalCounter.textContent = `Card ${activeIndex + 1} of ${activeGroup.cards.length}`;
    }
  };

  const openModal = (key) => {
    const group = topicMap.get(key);
    if (!group) return;

    activeGroup = group;
    activeIndex = 0;
    setModalCard();

    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    modal.hidden = false;
    modal.style.display = "flex";
    document.body.style.overflow = "hidden";
  };

  const closeModal = () => {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    modal.hidden = true;
    modal.style.display = "none";
    document.body.style.overflow = "";
    if (modalCard) modalCard.classList.remove("is-flipped");
  };

  // --- EVENT DELEGATION (Prevents broken button click handlers) ---
  document.addEventListener("click", (event) => {
    // Open Learn Topic Modal
    const learnBtn = event.target.closest("[data-learn-topic]");
    if (learnBtn) {
      event.preventDefault();
      const topicKey = learnBtn.getAttribute("data-learn-topic");
      openModal(topicKey);
      return;
    }

    // Close Modal
    if (event.target.closest("[data-close-learn-modal]")) {
      closeModal();
      return;
    }

    // Previous Card Arrow
    if (event.target.closest("[data-learn-prev]")) {
      if (!activeGroup || !activeGroup.cards.length) return;
      activeIndex =
        (activeIndex - 1 + activeGroup.cards.length) % activeGroup.cards.length;
      setModalCard();
      return;
    }

    // Next Card Arrow
    if (event.target.closest("[data-learn-next]")) {
      if (!activeGroup || !activeGroup.cards.length) return;
      activeIndex = (activeIndex + 1) % activeGroup.cards.length;
      setModalCard();
      return;
    }

    // Tap/Click Card Body to Flip
    if (event.target.closest("#flashcard-modal-card")) {
      if (modalCard) modalCard.classList.toggle("is-flipped");
      return;
    }
  });

  // Keyboard controls (Left/Right arrows for nav, Space/Up/Down for flip, Esc for close)
  document.addEventListener("keydown", (event) => {
    if (!modal.classList.contains("is-open")) return;

    if (event.key === "Escape") {
      closeModal();
    } else if (event.key === "ArrowLeft") {
      if (!activeGroup || !activeGroup.cards.length) return;
      activeIndex =
        (activeIndex - 1 + activeGroup.cards.length) % activeGroup.cards.length;
      setModalCard();
    } else if (event.key === "ArrowRight") {
      if (!activeGroup || !activeGroup.cards.length) return;
      activeIndex = (activeIndex + 1) % activeGroup.cards.length;
      setModalCard();
    } else if (
      event.key === " " ||
      event.key === "ArrowUp" ||
      event.key === "ArrowDown"
    ) {
      event.preventDefault();
      if (modalCard) modalCard.classList.toggle("is-flipped");
    }
  });
});

// home.html ___________________

console.log("SmartLearn Home Page Loaded 🚀");

// simple interaction
// document.querySelector(".btn-primary").addEventListener("click", () => {
//     alert("Redirecting to Dashboard...");
// });

function goToSignup() {
  window.location.href = "register.html";
}

function goToLogin() {
  window.location.href = "login.html";
}

function goToDashboard() {
  window.location.href = "dashboard.html";
}

function goToHome() {
  window.location.href = "home.html";
}

// login.html
//function login(e) {
//            e.preventDefault();
//            alert("Login UI only");
//            window.location.href = "home.html";
//        }

// register.html
function register(e) {
  e.preventDefault();
  alert("Register UI only");
  window.location.href = "login.html";
}

document.addEventListener("DOMContentLoaded", () => {
  // Check if ScrollReveal is loaded
  if (typeof ScrollReveal !== "undefined") {
    const sr = ScrollReveal({
      origin: "bottom",
      distance: "30px",
      duration: 800,
      delay: 100,
      easing: "cubic-bezier(0.165, 0.84, 0.44, 1)",
      reset: false, // Set to true if you want animations to re-trigger on scroll up
    });

    // 1. Hero & Header Elements
    sr.reveal(".hero-greeting-card, .hero-section, .page-heading-large", {
      origin: "top",
      distance: "20px",
    });

    // 2. Filter & Metric Cards
    sr.reveal(".metrics-bar, .metric-card, .filter-panel, .styled-card.mb-4", {
      interval: 100,
    });

    // 3. Grid Cards (Classes, Topics, Modules)
    sr.reveal(
      ".cards-grid .styled-card, .module-card, .topic-collection-card, .smart-card",
      {
        interval: 120,
      },
    );

    // 4. Section Titles & Callout Rows
    sr.reveal(
      ".dashboard-section-header, .feature-callout-row, .note-section",
      {
        origin: "bottom",
        distance: "40px",
      },
    );

    // 5. Sidebars & Form Panels
    sr.reveal(".create-panel, .learning-panel", {
      origin: "right",
      distance: "30px",
    });

    // 6. Deck Cards
    sr.reveal(".deck-card", {
      container: ".carousel-scroll-container",
      reset: false,
    });
  }
});

document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('theme-toggle-btn');
    const toggleIcon = document.getElementById('theme-toggle-icon');
    
    const savedTheme = localStorage.getItem('theme') || 'light';

    function applyTheme(theme) {
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            if (toggleIcon) toggleIcon.className = 'fa-solid fa-sun';
        } else {
            document.documentElement.removeAttribute('data-theme');
            if (toggleIcon) toggleIcon.className = 'fa-regular fa-moon';
        }
    }

    applyTheme(savedTheme);

    if (toggleBtn) {
        toggleBtn.addEventListener('click', () => {
            const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
            const nextTheme = isDark ? 'light' : 'dark';
            localStorage.setItem('theme', nextTheme);
            applyTheme(nextTheme);
        });
    }
});
// ==========================================
// QUIZ TIMER FUNCTIONALITY
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a quiz page
    const timerDisplay = document.getElementById('timeRemaining');
    if (!timerDisplay) return; // Exit if not a quiz page
    
    const form = document.getElementById('quizForm');
    const submitBtn = document.getElementById('submitBtn');
    
    // Get time limit from the data attribute or hidden input
    let timeLimitMinutes = 0;
    const timeLimitInput = document.querySelector('input[name="time_limit"]');
    if (timeLimitInput) {
        timeLimitMinutes = parseInt(timeLimitInput.value) || 0;
    }
    
    if (timeLimitMinutes <= 0) return; // No timer needed
    
    let timeRemaining = timeLimitMinutes * 60;
    let timerStarted = false;
    let timerInterval = null;
    
    function updateTimer() {
        const minutes = Math.floor(timeRemaining / 60);
        const seconds = timeRemaining % 60;
        timerDisplay.textContent = minutes + ':' + seconds.toString().padStart(2, '0');
        
        if (timeRemaining <= 0) {
            clearInterval(timerInterval);
            alert('⏰ Time is up! Your quiz will be submitted automatically.');
            if (form) form.submit();
        }
        timeRemaining--;
    }
    
    function startTimer() {
        if (!timerStarted && timeRemaining > 0) {
            timerStarted = true;
            timerInterval = setInterval(updateTimer, 1000);
            
            // Warn at 1 minute remaining
            if (timeLimitMinutes > 1) {
                setTimeout(function() {
                    alert('⚠️ 1 minute remaining!');
                }, (timeLimitMinutes - 1) * 60 * 1000);
            }
        }
    }
    
    // Start timer on first user interaction
    document.addEventListener('click', startTimer);
    document.addEventListener('keydown', startTimer);
    document.addEventListener('scroll', startTimer);
    
    // Also start timer on page load if user is already active
    if (document.visibilityState === 'visible') {
        setTimeout(startTimer, 1000);
    }
    
    // Handle page visibility change (user switching tabs)
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible' && !timerStarted) {
            setTimeout(startTimer, 1000);
        }
    });
});

