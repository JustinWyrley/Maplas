"""
Pure-Python game logic. No Flask imports.
Mirrors the behaviour of countrydle.html exactly.
"""
import csv
import random
import re

BROAD_CLUES = [
    'gdp_nominal_total', 'population', 'area_total', 'languages',
    'currency', 'time_zone', 'observes_dst', 'calling_code',
    'continent', 'alphabetic_country_rank',
]
SPECIFIC_CLUES = ['capital', 'flag', 'anthem']
MAX_GUESSES = 7
NUM_CATEGORIES = frozenset([
    'area_total', 'population', 'gdp_nominal_total',
    'duck_pop_rank', 'gdp_nominal_per_capita',
])


def load_data(csv_path):
    with open(csv_path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def is_valid_fact(val):
    """Mirror JS isValidFact."""
    if val is None:
        return False
    s = str(val).strip()
    return s != '' and s.lower() != 'nan'


def parse_number(s):
    """Mirror JS parseNumber."""
    if not s:
        return 0
    s = str(s).lower().replace(',', '').replace('$', '').replace('£', '')
    multi = 1
    if 'trillion' in s:
        multi = 1_000_000_000_000
    elif 'billion' in s:
        multi = 1_000_000_000
    elif 'million' in s:
        multi = 1_000_000
    m = re.search(r'-?[\d.]+', s)
    return float(m.group()) * multi if m else 0


def is_match(cat, target_val, guess_val):
    """Mirror JS isMatch (substring + word-level fuzzy)."""
    if not target_val or not guess_val:
        return False
    t = str(target_val).lower()
    g = str(guess_val).lower()

    if t == g or t in g or g in t:
        return True

    stop_words = {
        'and', 'the', 'official', 'other', 'sq', 'km', 'mi', 'utc',
        'cet', 'million', 'billion', 'trillion', 'percent',
    }
    t_words = [w for w in re.findall(r'[a-z]+', t) if len(w) > 3 and w not in stop_words]
    g_words = [w for w in re.findall(r'[a-z]+', g) if len(w) > 3 and w not in stop_words]

    for w in t_words:
        if w in g_words:
            return True
    return False


def _clue_display(key, country):
    """Get the display value for a clue key, applying any formatting."""
    if key == 'flag':
        return country.get('flag_path', '')
    if key == 'anthem':
        return country.get('anthem_path', '')
    val = country.get(key, '')
    if key == 'observes_dst':
        val = 'Yes' if str(val) == '1' else 'No'
    return val


def _build_clue_entry(key, country):
    """Build a clue dict ready for storing in session."""
    return {
        'key': key,
        'title': key.replace('_', ' ').upper(),
        'display_val': _clue_display(key, country),
        'full_width': key in ('flag', 'anthem'),
        'guesses': [],
    }


def init_game(df):
    """
    Pick a random country, select up to MAX_GUESSES clues, reveal the first one.
    Returns the full initial game state dict.
    Mirrors JS initialiseGame().
    """
    target = random.choice(df)

    valid_specific = [
        c for c in SPECIFIC_CLUES if (
            is_valid_fact(target.get('flag_path')) if c == 'flag' else
            is_valid_fact(target.get('anthem_path')) if c == 'anthem' else
            is_valid_fact(target.get(c))
        )
    ]
    valid_broad = [c for c in BROAD_CLUES if is_valid_fact(target.get(c))]

    random.shuffle(valid_specific)
    random.shuffle(valid_broad)

    needed_broad = max(0, MAX_GUESSES - len(valid_specific))
    clues = valid_broad[:needed_broad] + valid_specific
    clues.reverse()  # reverse so pop() returns broad clues first

    state = {
        'target_name': target['name'],
        'available_facts': clues,   # stack: pop() = next clue to reveal
        'revealed_clues': [],
        'guess_count': 0,
        'streak': 0,
        'game_over': False,
        'won': False,
    }

    # Reveal the first clue immediately (mirrors showNextClue() at end of initialiseGame)
    _reveal_next_clue(state, target)
    return state


def _reveal_next_clue(state, target_row):
    """
    Pop the next clue key from available_facts and append to revealed_clues.
    Mutates state in place.
    """
    if not state['available_facts']:
        state['revealed_clues'].append({
            'key': '__no_more__',
            'title': 'NO MORE CLUES',
            'display_val': 'Further data unavailable',
            'full_width': True,
            'guesses': [],
        })
        return

    key = state['available_facts'].pop()
    state['revealed_clues'].append(_build_clue_entry(key, target_row))


def reveal_next_clue_for_state(state, df):
    """Public wrapper: look up target row and reveal next clue."""
    target = next(c for c in df if c['name'] == state['target_name'])
    _reveal_next_clue(state, target)


def process_guess(state, df, guess_name):
    """
    Validate and apply one guess. Mutates state in place.
    Returns a result dict:
      { 'error': str }                           — invalid country
      { 'correct': True,  'clue_feedback': {...}, 'guessed_name': str }
      { 'correct': False, 'clue_feedback': {...}, 'guessed_name': str,
        'new_clue': dict|None }
    Mirrors JS handleGuess() logic exactly.
    """
    target = next((c for c in df if c['name'] == state['target_name']), None)
    guessed = next((c for c in df if c['name'].lower() == guess_name.lower()), None)

    if guessed is None:
        return {'error': 'invalid_country'}

    # Build per-clue feedback for every currently visible data-clue
    clue_feedback = {}
    for clue in state['revealed_clues']:
        key = clue['key']
        if key in ('flag', 'anthem', '__no_more__'):
            continue

        t_val = target.get(key, '')
        g_val = guessed.get(key, '')

        # Display value for the guessed country on this clue
        g_display = g_val if is_valid_fact(g_val) else 'Unknown'
        if key == 'observes_dst' and is_valid_fact(g_val):
            g_display = 'Yes' if str(g_val) == '1' else 'No'

        if key in NUM_CATEGORIES:
            t_num = parse_number(t_val)
            g_num = parse_number(g_val)
            if t_num == g_num and t_num != 0:
                result = 'match'
            elif t_num != 0 and g_num != 0:
                result = 'higher' if t_num > g_num else 'lower'
            else:
                result = 'no-match'
        else:
            result = 'match' if is_match(key, t_val, g_val) else 'no-match'

        clue_feedback[key] = {'result': result, 'guessed_val': g_display}
        clue['guesses'].append({
            'name': guessed['name'],
            'result': result,
            'guessed_val': g_display,
        })

    # Correct guess — mirrors the win branch in handleGuess
    if guessed['name'].lower() == target['name'].lower():
        state['game_over'] = True
        state['won'] = True
        return {
            'correct': True,
            'clue_feedback': clue_feedback,
            'guessed_name': guessed['name'],
        }

    # Wrong guess
    state['guess_count'] += 1
    new_clue = None

    if state['guess_count'] < MAX_GUESSES:
        _reveal_next_clue(state, target)
        new_clue = state['revealed_clues'][-1]
    else:
        state['game_over'] = True
        state['won'] = False

    return {
        'correct': False,
        'clue_feedback': clue_feedback,
        'guessed_name': guessed['name'],
        'new_clue': new_clue,
    }
