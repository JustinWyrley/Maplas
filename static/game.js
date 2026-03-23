// Numeric clue categories — mirrors JS in countrydle.html
const NUM_CATEGORIES = [
    'area_total', 'population', 'gdp_nominal_total',
    'duck_pop_rank', 'gdp_nominal_per_capita',
];

// GAME_STATE and COUNTRY_NAMES are injected by game.html as inline <script> variables.

// ---------------------------------------------------------------------------
// Autocomplete — identical logic to countrydle.html
// ---------------------------------------------------------------------------

const guessInput = document.getElementById('guess-input');
const autocompleteList = document.getElementById('autocomplete-list');
let currentFocus = -1;

guessInput.addEventListener('input', function () {
    const val = this.value.trim().toLowerCase();
    autocompleteList.innerHTML = '';
    currentFocus = -1;

    if (!val) {
        autocompleteList.style.display = 'none';
        return;
    }

    const matches = COUNTRY_NAMES.filter(name => name.toLowerCase().includes(val));

    if (matches.length > 0) {
        autocompleteList.style.display = 'block';
        matches.forEach(name => {
            const item = document.createElement('div');
            item.className = 'autocomplete-item';

            const matchIndex = name.toLowerCase().indexOf(val);
            const before = name.substring(0, matchIndex);
            const match  = name.substring(matchIndex, matchIndex + val.length);
            const after  = name.substring(matchIndex + val.length);
            item.innerHTML = `${before}<strong>${match}</strong>${after}`;

            item.addEventListener('click', function () {
                guessInput.value = name;
                closeAllLists();
                guessInput.focus();
            });

            autocompleteList.appendChild(item);
        });
    } else {
        autocompleteList.style.display = 'none';
    }
});

guessInput.addEventListener('keydown', function (e) {
    const items = autocompleteList.getElementsByTagName('div');

    if (e.key === 'ArrowDown') {
        currentFocus++;
        addActive(items);
    } else if (e.key === 'ArrowUp') {
        currentFocus--;
        addActive(items);
    } else if (e.key === 'Enter') {
        e.preventDefault();
        if (currentFocus > -1 && items.length > 0) {
            guessInput.value = items[currentFocus].innerText;
            closeAllLists();
            handleGuess();
        } else if (items.length > 0) {
            guessInput.value = items[0].innerText;
            closeAllLists();
            handleGuess();
        } else {
            closeAllLists();
            handleGuess();
        }
    }
});

function addActive(items) {
    if (!items || items.length === 0) return;
    removeActive(items);
    if (currentFocus >= items.length) currentFocus = 0;
    if (currentFocus < 0) currentFocus = items.length - 1;
    items[currentFocus].classList.add('autocomplete-active');
    items[currentFocus].scrollIntoView({ block: 'nearest' });
}

function removeActive(items) {
    for (let i = 0; i < items.length; i++) {
        items[i].classList.remove('autocomplete-active');
    }
}

function closeAllLists() {
    autocompleteList.innerHTML = '';
    autocompleteList.style.display = 'none';
    currentFocus = -1;
}

document.addEventListener('click', function (e) {
    if (e.target !== guessInput) closeAllLists();
});

// ---------------------------------------------------------------------------
// Guess submission
// ---------------------------------------------------------------------------

async function handleGuess() {
    const guess = guessInput.value.trim();
    const msgArea = document.getElementById('message-area');

    if (!guess) return;

    let data;
    try {
        const resp = await fetch('/guess', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ guess }),
        });
        data = await resp.json();
    } catch (err) {
        msgArea.innerText = 'Network error. Please try again.';
        msgArea.style.color = '#e53935';
        return;
    }

    if (data.error === 'invalid_country') {
        msgArea.innerText = 'Please select a valid country from the list.';
        msgArea.style.color = '#e53935';
        setTimeout(() => {
            if (msgArea.innerText === 'Please select a valid country from the list.') {
                msgArea.innerText = '';
                msgArea.style.color = '#333';
            }
        }, 2500);
        return;
    }

    closeAllLists();
    msgArea.innerText = '';

    if (data.correct) {
        // Win: turn all data-clue boxes green, hide feedback (mirrors handleGuess win branch)
        document.querySelectorAll('.data-clue').forEach(box => {
            box.classList.remove('bg-red');
            box.classList.add('bg-green');
            box.querySelector('.guess-feedback').style.display = 'none';
        });
        endGame(`Brilliant! You guessed ${data.target_name} correctly.`, true);
    } else {
        // Apply per-clue colours and append feedback rows
        applyClueUpdates(data.clue_feedback, data.guessed_name);

        if (data.game_over) {
            // Ran out of guesses
            document.getElementById('guess-counter').innerText = 'Out of Guesses!';
            document.getElementById('streak-counter').innerText = `🔥 Streak: ${data.streak}`;
            endGame(`Game Over! The correct answer was ${data.target_name}.`, false);
        } else {
            // Wrong guess, game continues — update counter and reveal next clue
            document.getElementById('guess-counter').innerText =
                `Guess ${data.guess_count + 1} of ${GAME_STATE.maxGuesses}`;
            document.getElementById('streak-counter').innerText =
                `🔥 Streak: ${data.streak}`;
            guessInput.value = '';

            if (data.new_clue) addClueBox(data.new_clue);
        }
    }
}

function applyClueUpdates(clueFeedback, guessedName) {
    for (const [key, fb] of Object.entries(clueFeedback)) {
        const box = document.querySelector(`.data-clue[data-category="${key}"]`);
        if (!box) continue;

        box.classList.remove('bg-green', 'bg-red');
        box.classList.add(fb.result === 'match' ? 'bg-green' : 'bg-red');

        const feedbackDiv = box.querySelector('.guess-feedback');
        feedbackDiv.innerHTML += buildFeedbackEntry(key, guessedName, fb);
        feedbackDiv.style.display = 'block';
        feedbackDiv.scrollTop = feedbackDiv.scrollHeight;
    }
}

function buildFeedbackEntry(key, guessName, fb) {
    if (NUM_CATEGORIES.includes(key)) {
        if (fb.result === 'match') {
            return `<div class="guess-entry"><strong>${guessName}:</strong> Match!</div>`;
        }
        const arrow = fb.result === 'higher' ? '⬆️' : (fb.result === 'lower' ? '⬇️' : '');
        return `<div class="guess-entry"><strong>${guessName}:</strong> ${fb.guessed_val} <span class="arrow">${arrow}</span></div>`;
    }
    return `<div class="guess-entry"><strong>${guessName}:</strong> ${fb.guessed_val}</div>`;
}

function addClueBox(clue) {
    const container = document.getElementById('clues-container');
    const div = document.createElement('div');

    if (clue.key === 'flag') {
        div.className = 'clue-box full-width-container';
        div.innerHTML = `
            <div class="clue-title">FLAG</div>
            <img src="${clue.display_val}" alt="Flag clue">
        `;
    } else if (clue.key === 'anthem') {
        div.className = 'clue-box full-width-container';
        div.innerHTML = `
            <div class="clue-title">NATIONAL ANTHEM</div>
            <audio controls controlsList="nodownload noplaybackrate">
                <source src="${clue.display_val}">
            </audio>
        `;
    } else if (clue.key === '__no_more__') {
        div.className = 'clue-box full-width-container';
        div.innerHTML = `
            <div class="clue-title">NO MORE CLUES</div>
            <div class="clue-value">Further data unavailable</div>
        `;
    } else {
        div.className = 'clue-box data-clue';
        div.setAttribute('data-category', clue.key);
        div.innerHTML = `
            <div class="clue-title">${clue.title}</div>
            <div class="clue-value">${clue.display_val}</div>
            <div class="guess-feedback"></div>
        `;
    }

    container.appendChild(div);
}

function endGame(message, isWin) {
    document.getElementById('message-area').innerText = message;
    document.getElementById('message-area').style.color = isWin ? '#4caf50' : '#e53935';
    guessInput.disabled = true;
    document.getElementById('submit-btn').disabled = true;
    const btn = document.getElementById('play-again-btn');
    btn.style.display = 'block';
    btn.focus();
}
