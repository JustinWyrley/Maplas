import copy
import json
import os
import subprocess
import sys
from pathlib import Path

from flask import (Flask, Response, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)

from game_logic import (MAX_GUESSES, NUM_CATEGORIES, init_game,
                        process_guess, reveal_next_clue_for_state)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'maplas-dev-secret-change-in-prod')

BASE_DIR = Path(__file__).parent
COLLECTING_DIR = BASE_DIR / 'collecting_info'
CSV_PATH = COLLECTING_DIR / 'country_info_updated.csv'
MEDIA_DIR = COLLECTING_DIR / 'countries'

# Scraping pipeline: (human label, script filename)
SCRAPER_STEPS = [
    ("Collecting country list from Wikipedia", "country_collection.py"),
    ("Scraping country info (capitals, flags, anthems…)", "scrape_country_info.py"),
    ("Scraping alcohol consumption data", "Alcohol_consumption_ranked_scraper.py"),
    ("Scraping border / neighbour data", "Bordering_Countries_Scraper.py"),
    ("Scraping flag colours", "Country_flag_colour_scraper.py"),
    ("Generating country outline images", "country_outline_scraper.py"),
    ("Cleaning and finalising dataset", "cleaning.py"),
]

_df = None  # loaded once per process


def get_df():
    global _df
    if _df is None and CSV_PATH.exists():
        from game_logic import load_data
        _df = load_data(str(CSV_PATH))
    return _df


def media_url(path):
    """Convert a CSV path like 'countries/X.png' to a Flask /media/X.png URL."""
    if not path:
        return ''
    return url_for('media', filename=Path(path).name)


app.jinja_env.globals['media_url'] = media_url


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if CSV_PATH.exists():
        return redirect(url_for('game'))
    return redirect(url_for('setup'))


@app.route('/game')
def game():
    df = get_df()
    if df is None:
        return redirect(url_for('setup'))

    # If session has no game state (or target no longer exists) start fresh
    if 'target_name' not in session or not any(
        c['name'] == session['target_name'] for c in df
    ):
        streak = session.get('streak', 0)
        state = init_game(df)
        state['streak'] = streak
        session.clear()
        session.update(state)

    return render_template(
        'game.html',
        revealed_clues=session.get('revealed_clues', []),
        guess_count=session.get('guess_count', 0),
        streak=session.get('streak', 0),
        game_over=session.get('game_over', False),
        won=session.get('won', False),
        target_name=session.get('target_name', ''),
        country_names=sorted(c['name'] for c in df),
        MAX_GUESSES=MAX_GUESSES,
        NUM_CATEGORIES=NUM_CATEGORIES,
    )


@app.route('/guess', methods=['POST'])
def guess():
    df = get_df()
    if df is None:
        return jsonify({'error': 'no_data'}), 500

    data = request.get_json(silent=True) or {}
    guess_name = data.get('guess', '').strip()
    if not guess_name:
        return jsonify({'error': 'empty_guess'}), 400

    state = copy.deepcopy(dict(session))
    result = process_guess(state, df, guess_name)

    if 'error' in result:
        return jsonify(result), 400

    # Update streak (mirrors JS currentStreak logic)
    if result['correct']:
        state['streak'] = state.get('streak', 0) + 1
    elif state['game_over']:
        state['streak'] = 0

    session.clear()
    session.update(state)

    # Transform media paths in new_clue before sending to client
    new_clue = None
    if result.get('new_clue'):
        nc = dict(result['new_clue'])
        if nc['key'] in ('flag', 'anthem'):
            nc['display_val'] = media_url(nc['display_val'])
        new_clue = nc

    return jsonify({
        'correct': result['correct'],
        'game_over': state['game_over'],
        'won': state.get('won', False),
        'streak': state.get('streak', 0),
        'guess_count': state['guess_count'],
        'guessed_name': result['guessed_name'],
        'target_name': state['target_name'] if state['game_over'] else None,
        'clue_feedback': result['clue_feedback'],
        'new_clue': new_clue,
    })


@app.route('/new-round', methods=['POST'])
def new_round():
    df = get_df()
    if df is None:
        return redirect(url_for('setup'))

    streak = session.get('streak', 0)
    state = init_game(df)
    state['streak'] = streak
    session.clear()
    session.update(state)
    return redirect(url_for('game'))


@app.route('/media/<path:filename>')
def media(filename):
    return send_from_directory(str(MEDIA_DIR), filename)


# ---------------------------------------------------------------------------
# Setup / scraping
# ---------------------------------------------------------------------------

@app.route('/setup')
def setup():
    return render_template('setup.html',
                           has_data=CSV_PATH.exists(),
                           steps=SCRAPER_STEPS)


@app.route('/setup/run')
def setup_run():
    """
    Server-Sent Events stream that runs each scraper step in order,
    emitting progress events the setup page can consume.
    """
    def generate():
        total = len(SCRAPER_STEPS)
        for i, (label, script) in enumerate(SCRAPER_STEPS):
            script_path = COLLECTING_DIR / script
            # Announce step starting
            yield (
                f"data: {json.dumps({'step': i, 'total': total, 'label': label, 'running': True})}\n\n"
            )
            try:
                proc = subprocess.run(
                    [sys.executable, str(script_path)],
                    cwd=str(COLLECTING_DIR),
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                success = proc.returncode == 0
                error_msg = proc.stderr.strip() if not success else None
            except subprocess.TimeoutExpired:
                success = False
                error_msg = 'Timed out after 10 minutes'
            except Exception as exc:
                success = False
                error_msg = str(exc)

            yield (
                f"data: {json.dumps({'step': i + 1, 'total': total, 'label': label, 'running': False, 'success': success, 'error': error_msg})}\n\n"
            )

            if not success:
                yield f"data: {json.dumps({'finished': True, 'success': False, 'failed_step': label})}\n\n"
                return

        # Reload data after scraping completes
        global _df
        _df = None
        get_df()

        yield f"data: {json.dumps({'finished': True, 'success': True})}\n\n"

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )


if __name__ == '__main__':
    app.run(debug=True)
