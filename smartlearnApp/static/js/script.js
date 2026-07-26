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
            const existingRows = creatorList.querySelectorAll(".flashcard-entry-card").length;
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
            creatorList.querySelectorAll(".flashcard-entry-card").forEach((row, index) => {
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
            const existingRows = mcqCreatorList.querySelectorAll(".flashcard-entry-card").length;
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
            mcqCreatorList.querySelectorAll(".flashcard-entry-card").forEach((row, index) => {
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

    if (dataElement && modal) {
        let topicGroups = [];
        try {
            topicGroups = JSON.parse(dataElement.textContent || "[]");
        } catch (error) {
            console.error("Unable to parse flashcard topic data", error);
            return;
        }

        if (!topicGroups.length) {
            return;
        }

        const topicMap = new Map(topicGroups.map((group) => [group.modal_key || group.topic_slug, group]));
        const modalTopic = document.getElementById("flashcard-learn-topic");
        const modalTitle = document.getElementById("flashcard-learn-title");
        const modalCard = document.getElementById("flashcard-modal-card");
        const modalFrontTopic = document.getElementById("flashcard-modal-front-topic");
        const modalFrontText = document.getElementById("flashcard-modal-front-text");
        const modalBackTopic = document.getElementById("flashcard-modal-back-topic");
        const modalBackText = document.getElementById("flashcard-modal-back-text");
        const prevButton = modal.querySelector("[data-learn-prev]");
        const nextButton = modal.querySelector("[data-learn-next]");
        const flipButton = modal.querySelector("[data-learn-flip]");
        const closeButtons = modal.querySelectorAll("[data-close-learn-modal]");
        const openButtons = document.querySelectorAll("[data-learn-topic]");

        let activeGroup = null;
        let activeIndex = 0;

        const setModalCard = () => {
            if (!activeGroup || !activeGroup.cards.length) {
                return;
            }

            const card = activeGroup.cards[activeIndex];
            modalTopic.textContent = activeGroup.topic;
            modalTitle.textContent = activeGroup.topic;
            modalFrontTopic.textContent = activeGroup.topic;
            modalFrontText.textContent = card.front;
            modalBackTopic.textContent = activeGroup.topic;
            modalBackText.textContent = card.back;
            modalCard.classList.remove("is-flipped");
        };

        const openModal = (topicSlug) => {
            const group = topicMap.get(topicSlug);
            if (!group) {
                return;
            }

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
            modalCard.classList.remove("is-flipped");
        };

        openButtons.forEach((button) => {
            button.addEventListener("click", () => {
                openModal(button.dataset.learnTopic);
            });
        });

        prevButton.addEventListener("click", () => {
            if (!activeGroup || !activeGroup.cards.length) {
                return;
            }

            activeIndex = (activeIndex - 1 + activeGroup.cards.length) % activeGroup.cards.length;
            setModalCard();
        });

        nextButton.addEventListener("click", () => {
            if (!activeGroup || !activeGroup.cards.length) {
                return;
            }

            activeIndex = (activeIndex + 1) % activeGroup.cards.length;
            setModalCard();
        });

        flipButton.addEventListener("click", () => {
            modalCard.classList.toggle("is-flipped");
        });

        closeButtons.forEach((button) => {
            button.addEventListener("click", closeModal);
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && modal.classList.contains("is-open")) {
                closeModal();
            }
        });
    }
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


