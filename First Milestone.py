from flask import Flask, render_template_string, request, redirect, url_for, session, flash
from collections import defaultdict, Counter
from datetime import datetime
import os, uuid

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

USERS = {}
DECKS = defaultdict(list)
STATS = defaultdict(lambda: {"today": Counter(), "by_deck": Counter(), "streak": 0, "last_day": None})

def nav():
    return """
    <nav class="nav">
      <div class="left">FlipDeck</div>
      <div class="right">
        <a href="{{ url_for('home') }}">Home</a>
        <a href="{{ url_for('help_page') }}">Help</a>
        {% if session.get('user') %}
          <a href="{{ url_for('decks_home') }}">Profile</a>
          <a class="btn" href="{{ url_for('new_deck') }}">New Deck</a>
          <a href="{{ url_for('logout') }}">Logout</a>
        {% else %}
          <a href="{{ url_for('login') }}">Login</a>
          <a href="{{ url_for('signup') }}">Create Account</a>
        {% endif %}
      </div>
    </nav>
    """

LAYOUT_TOP = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>FlipDeck</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  .form-narrow input[type=text],
  .form-narrow input[type=password],
  .form-narrow textarea {
    max-width: 420px;
  }
  :root { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; }
  body{ margin:0; background:#0b0b0c; color:#f4f4f5;}
  .wrap{max-width:900px;margin:0 auto;padding:16px;}
  .card{background:#151518;border:1px solid #23232a;border-radius:16px;padding:16px;margin:12px 0;}
  .grid{display:grid;gap:12px;}
  .grid-2{grid-template-columns:repeat(2,1fr)}
  input[type=text], input[type=password], textarea{
    width:100%; padding:10px; border-radius:10px; border:1px solid #2b2b33; background:#101014; color:#f4f4f5;
  }
  .btn, button{background:#3a76ff;border:none;padding:10px 14px;border-radius:10px;color:white;cursor:pointer;text-decoration:none;display:inline-block}
  .btn.secondary{background:#2b2b33}
  .nav{display:flex;justify-content:space-between;align-items:center;padding:12px 16px;border-bottom:1px solid #23232a;position:sticky;top:0;background:#0b0b0c}
  .nav a{color:#e9e9ee;margin-left:12px;text-decoration:none}
  .left{font-weight:700}
  .hint{color:#b5b5c0;font-size:0.95rem}
  .ok{color:#7efcb3} .warn{color:#ffc36a} .err{color:#ff8f8f}
  .row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
  .kbd{border:1px solid #2b2b33;background:#101014;border-radius:6px;padding:2px 6px}
  .meta{font-size:.9rem;color:#b5b5c0}
</style>
</head>
<body>
""" + nav() + """
<div class="wrap">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      {% for cat,msg in messages %}
        <div class="card"><span class="{{cat}}">{{msg}}</span></div>
      {% endfor %}
    {% endif %}
  {% endwith %}
"""

LAYOUT_BOTTOM = """
</div>
<script>
document.addEventListener('keydown', (e)=>{
  const elShow = document.getElementById('btn-show');
  const elC = document.getElementById('btn-correct');
  const elI = document.getElementById('btn-incorrect');
  if(!elShow && !elC && !elI) {
    // no review hotkeys visible; keep going to check for Ctrl+Enter on forms
  } else {
    if (e.code === 'Space' && elShow) { e.preventDefault(); elShow.click(); }
    if (e.key.toLowerCase() === 'c' && elC) { elC.click(); }
    if (e.key.toLowerCase() === 'i' && elI) { elI.click(); }
  }

  // Ctrl/Cmd + Enter submits the first form that opts in
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    const form = document.querySelector('form[data-ctrl-enter="true"]');
    if (form) { e.preventDefault(); form.requestSubmit(); }
  }
});
</script>

</body></html>
"""

def page(content, **ctx):
    return render_template_string(LAYOUT_TOP + content + LAYOUT_BOTTOM, **ctx)

def authed(): return "user" in session
def require_auth():
    if not authed():
        flash("Please log in first.", "warn")
        return redirect(url_for("login"))

@app.context_processor
def inject_session():
    return dict(session=session)

@app.route("/")
def home():
    return page("""
      <div class="card">
        <h2>Flashcards & Study</h2>
        <p class="hint">Turn your notes into spaced-repetition flashcards—fast. (IH1)</p>
        {% if not session.get('user') %}
          <div class="row">
            <a class="btn" href="{{ url_for('signup') }}">Create Account</a>
            <a class="btn secondary" href="{{ url_for('login') }}">Login</a>
          </div>
        {% else %}
          <a class="btn" href="{{ url_for('decks_home') }}">Go to Decks</a>
        {% endif %}
      </div>
    """)

@app.route("/help")
def help_page():
    return page("""
      <div class="card">
        <h3>Help</h3>
        <p class="hint">Use <span class="kbd">/</span> to focus search, <span class="kbd">Space</span> to show answer, <span class="kbd">C</span>/<span class="kbd">I</span> to grade. (IH7)</p>
        <p>Cancel buttons won’t save changes. (IH2) Back links are present. (IH5)</p>
      </div>
    """)

@app.route("/signup", methods=["GET","POST"])
def signup():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        pw = request.form.get("password") or ""
        if not email or not pw:
            flash("Email and password are required.", "err")
        elif email in USERS:
            flash("Account already exists. Please log in.", "warn")
            return redirect(url_for("login"))
        else:
            USERS[email] = {"password": pw}
            session["user"] = email
            flash("Welcome! Account created.", "ok")
            return redirect(url_for("decks_home"))
    return page("""
      <div class="card grid">
        <h2>Create Account</h2>
        <form method="post" class="grid form-narrow">
          <label>Email <input name="email" type="text" placeholder="you@school.edu"></label>
          <label>Password <input name="password" type="password" placeholder="••••••••"></label>
          <div class="row">
            <button class="btn">Create Account</button>
            <a class="btn secondary" href="{{ url_for('home') }}">Cancel</a>
          </div>
          <p class="hint">Demo data only. (IH2)</p>
        </form>
      </div>
    """)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        pw = (request.form.get("password") or "")
        if email in USERS and USERS[email]["password"] == pw:
            session["user"] = email
            flash("Logged in.", "ok")
            return redirect(url_for("decks_home"))
        flash("Invalid credentials.", "err")
    return page("""
      <div class="card grid">
        <h2>Login</h2>
        <form method="post" class="grid form-narrow">
          <label>Email <input name="email" type="text" autofocus></label>
          <label>Password <input name="password" type="password"></label>
          <div class="row">
            <button class="btn">Login</button>
            <a class="btn secondary" href="{{ url_for('home') }}">Cancel</a>
          </div>
        </form>
      </div>
    """)

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("Logged out.", "ok")
    return redirect(url_for("home"))

@app.route("/decks")
def decks_home():
    if not authed(): return require_auth()
    email = session["user"]
    query = (request.args.get("q") or "").strip().lower()
    decks = DECKS[email]
    if query:
        decks = [d for d in decks if query in d["title"].lower()]
    return page("""
      <div class="card">
        <div class="row" style="justify-content:space-between">
          <h2>Decks Home</h2>
          <a class="btn" href="{{ url_for('new_deck') }}">New Deck</a>
        </div>
        <form method="get" class="row" style="margin:8px 0">
          <input name="q" type="text" placeholder="Search title or #tag (press / to focus)" onkeydown="if(event.key=='/'){this.focus();event.preventDefault();}" value="{{ request.args.get('q','') }}">
          <button class="btn secondary">Search</button>
        </form>
        {% if decks %}
          <div class="grid">
            {% for d in decks %}
              <div class="card">
                <div class="row" style="justify-content:space-between">
                  <div>
                     <strong>{{ d.title }}</strong> <span class="meta">({{ d.cards|length }} cards)</span>
                  </div>
                  <div class="row">
                    <a class="btn secondary" href="{{ url_for('deck_detail', deck_id=d.id) }}">Open</a>
                    <a class="btn" href="{{ url_for('review_session', deck_id=d.id) }}">Start Review</a>
                  </div>
                </div>
              </div>
            {% endfor %}
          </div>
        {% else %}
          <p class="hint">No decks yet. Click <em>New Deck</em> to create your first study set. (IH3)</p>
        {% endif %}
      </div>
    """, decks=decks)

@app.route("/decks/new", methods=["GET","POST"])
def new_deck():
    if not authed(): return require_auth()
    email = session["user"]
    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        desc = (request.form.get("desc") or "").strip()
        if not title:
            flash("Deck name is required.", "err")
        else:
            d = {"id": str(uuid.uuid4())[:8], "title": title, "desc": desc, "cards": []}
            DECKS[email].append(d)
            flash("Deck created.", "ok")
            return redirect(url_for("decks_home"))
    return page("""
      <div class="card grid">
        <h2>Create Deck</h2>
        <form method="post" class="grid">
          <label>Deck Name <input name="title" type="text" placeholder="Biology 101"></label>
          <label>Deck Description <textarea name="desc" rows="3" placeholder="Short description (optional)"></textarea></label>
          <div class="row">
            <button class="btn">Create Deck</button>
            <a class="btn secondary" href="{{ url_for('decks_home') }}">Cancel</a>
          </div>
          <p class="hint">Cancel won’t save. (IH2) Nav stays consistent. (IH4)</p>
        </form>
      </div>
    """)

@app.route("/deck/<deck_id>")
def deck_detail(deck_id):
    if not authed(): return require_auth()
    email = session["user"]
    deck = next((d for d in DECKS[email] if d["id"] == deck_id), None)
    if not deck:
        flash("Deck not found.", "err")
        return redirect(url_for("decks_home"))
    return page("""
      <div class="card">
        <div class="row" style="justify-content:space-between">
          <div><a class="btn secondary" href="{{ url_for('decks_home') }}">&lt; Back</a></div>
          <h2>{{ deck.title }}</h2>
          <div class="row">
            <a class="btn" href="{{ url_for('add_card', deck_id=deck.id) }}">New Card</a>
            <a class="btn" href="{{ url_for('review_session', deck_id=deck.id) }}">Start Review</a>
          </div>
        </div>

        {% if deck.cards %}
          <div class="grid">
            {% for c in deck.cards %}
              <div class="card">
                <!-- Row with content on the left and Edit aligned to the right -->
                <div class="row">
                  <div>
                    <div><strong>Front:</strong> {{ c.front }}</div>
                    <div><strong>Back:</strong> {{ c.back }}</div>
                    {% if c.hint %}<div class="hint">Hint: {{ c.hint }}</div>{% endif %}
                  </div>
                  <!-- Actions aligned right -->
                  <div class="row" style="margin-left:auto">
                    <a class="btn secondary" href="{{ url_for('edit_card', deck_id=deck.id, i=loop.index0) }}">Edit</a>
                  </div>
                </div>
              </div>
            {% endfor %}
          </div>
        {% else %}
          <p class="hint">This deck is empty. Click <em>New Card</em> to create your first flashcard. (IH3)</p>
        {% endif %}
      </div>
    """, deck=deck)


@app.route("/deck/<deck_id>/add", methods=["GET","POST"])
def add_card(deck_id):
    if not authed(): return require_auth()
    email = session["user"]
    deck = next((d for d in DECKS[email] if d["id"] == deck_id), None)
    if not deck:
        flash("Deck not found.", "err")
        return redirect(url_for("decks_home"))
    if request.method == "POST":
        front = (request.form.get("front") or "").strip()
        back = (request.form.get("back") or "").strip()
        hint = (request.form.get("hint") or "").strip()
        if not front or not back:
            flash("Front and Back are required.", "err")
        else:
            deck["cards"].append({"front": front, "back": back, "hint": hint})
            flash("Card saved to deck.", "ok")
            return redirect(url_for("add_card", deck_id=deck_id))
    return page("""
      <div class="card grid">
        <h2>Add Card to {{ deck.title }}</h2>
        <form method="post" class="grid" data-ctrl-enter="true">
          <label>Front (Prompt):
            <textarea name="front" rows="2" placeholder="e.g., Define homeostasis" autofocus></textarea>
          </label>
          <label>Back (Answer):
            <textarea name="back" rows="2" placeholder="e.g., Homeostasis is..."></textarea>
          </label>
          <label>Hint (Optional):
            <input name="hint" type="text" placeholder="Short cue" />
          </label>
          <div class="row">
            <button class="btn">Save Card</button>
            <a class="btn secondary" href="{{ url_for('deck_detail', deck_id=deck.id) }}">Cancel</a>
          </div>
          <p class="hint">Press <span class="kbd">Ctrl</span>+<span class="kbd">Enter</span> to save. (IH7)</p>
        </form>
      </div>
    """, deck=deck)

@app.route("/deck/<deck_id>/edit/<int:i>", methods=["GET", "POST"])
def edit_card(deck_id, i):
    if not authed(): return require_auth()
    email = session["user"]
    deck = next((d for d in DECKS[email] if d["id"] == deck_id), None)
    if not deck:
        flash("Deck not found.", "err")
        return redirect(url_for("decks_home"))

    if i < 0 or i >= len(deck["cards"]):
        flash("Card not found.", "err")
        return redirect(url_for("deck_detail", deck_id=deck_id))

    card = deck["cards"][i]

    if request.method == "POST":
        front = (request.form.get("front") or "").strip()
        back  = (request.form.get("back") or "").strip()
        hint  = (request.form.get("hint") or "").strip()
        if not front or not back:
            flash("Front and Back are required.", "err")
        else:
            card["front"], card["back"], card["hint"] = front, back, hint
            flash("Card updated.", "ok")
            return redirect(url_for("deck_detail", deck_id=deck_id))

    return page("""
      <div class="card grid">
        <div class="row" style="justify-content:space-between">
          <h2>Edit Card — {{ deck.title }}</h2>
          <a class="btn secondary" href="{{ url_for('deck_detail', deck_id=deck.id) }}">Cancel</a>
        </div>
        <form method="post" class="grid form-narrow" data-ctrl-enter="true">
          <label>Front (Prompt):
            <textarea name="front" rows="2" autofocus>{{ card.front }}</textarea>
          </label>
          <label>Back (Answer):
            <textarea name="back" rows="2">{{ card.back }}</textarea>
          </label>
          <label>Hint (Optional):
            <input name="hint" type="text" value="{{ card.hint or '' }}" />
          </label>
          <div class="row">
            <button class="btn">Save Changes</button>
            <a class="btn secondary" href="{{ url_for('deck_detail', deck_id=deck.id) }}">Cancel</a>
          </div>
          <p class="hint">Tip: Press <span class="kbd">Ctrl</span>+<span class="kbd">Enter</span> to save.</p>
        </form>
      </div>
    """, deck=deck, card=card)

@app.route("/review/<deck_id>", methods=["GET","POST"])
def review_session(deck_id):
    if not authed(): return require_auth()
    email = session["user"]
    deck = next((d for d in DECKS[email] if d["id"] == deck_id), None)
    if not deck or not deck["cards"]:
        flash("Need at least one card to review.", "warn")
        return redirect(url_for("deck_detail", deck_id=deck_id if deck else ""))

    key = f"idx:{email}:{deck_id}"
    idx = session.get(key, 0)
    reveal = session.get(f"reveal:{email}:{deck_id}", False)

    if request.method == "POST":
        action = request.form.get("action")
        if action == "show":
            session[f"reveal:{email}:{deck_id}"] = True
            return redirect(url_for("review_session", deck_id=deck_id))
        elif action in ("correct", "incorrect"):
            today = datetime.now().date().isoformat()
            s = STATS[email]
            if s["last_day"] != today:
                s["streak"] = s["streak"] + 1 if s["last_day"] is not None else 1
                s["last_day"] = today
            s["today"][action] += 1
            s["by_deck"][deck["title"]] += 1

            idx = (idx + 1) % len(deck["cards"])
            session[key] = idx
            session[f"reveal:{email}:{deck_id}"] = False
            return redirect(url_for("review_session", deck_id=deck_id))

    card = deck["cards"][idx]
    progress = f"{idx+1}/{len(deck['cards'])}"
    return page("""
      <div class="card">
        <div class="row" style="justify-content:space-between">
          <div><a class="btn secondary" href="{{ url_for('deck_detail', deck_id=deck.id) }}">&lt; Back</a></div>
          <h2>{{ deck.title }} <span class="meta">Card {{ progress }}</span></h2>
          <div class="row">
            <a class="btn" href="{{ url_for('grade_stats') }}">Stats</a>
          </div>
        </div>

        {% if not reveal %}
          <h3>{{ card.front }}</h3>
          <form method="post" class="row" style="margin-top:10px">
            <button id="btn-show" name="action" value="show" class="btn">Show Answer</button>
            <span class="hint">Press <span class="kbd">Space</span></span>
          </form>
        {% else %}
          <div class="card">
            <div class="hint">Prompt</div>
            <div>{{ card.front }}</div>
            <div class="hint" style="margin-top:8px">Answer</div>
            <div>{{ card.back }}</div>
            {% if card.hint %}
              <div class="hint" style="margin-top:8px">Hint: {{ card.hint }}</div>
            {% endif %}
          </div>
          <form method="post" class="row" style="margin-top:10px">
            <button id="btn-correct" class="btn" name="action" value="correct">Correct (C)</button>
            <button id="btn-incorrect" class="btn secondary" name="action" value="incorrect">Incorrect (I)</button>
          </form>
          <p class="hint">Progress/time cues set expectations. (IH6)</p>
        {% endif %}
      </div>
    """, deck=deck, card=card, reveal=reveal, progress=progress)

@app.route("/stats")
def grade_stats():
    if not authed(): return require_auth()
    email = session["user"]
    s = STATS[email]
    today = s["today"]
    total = today["correct"] + today["incorrect"]
    acc = (today["correct"]/total*100) if total else 0
    return page("""
      <div class="card">
        <h2>Today</h2>
        <p><strong>{{ total }}</strong> Reviews,
           <strong>{{ today.correct }}</strong> Correct
           (<strong>{{ "%.0f"|format(acc) }}%</strong> Accuracy)</p>
        <div class="row meta">
          <div>Day Streak: {{ s.streak }}</div>
          <div>Last Session: {{ s.last_day or "—" }}</div>
        </div>
        <h3 style="margin-top:16px">Total Reviews by Deck</h3>
        {% if s.by_deck %}
          <div class="grid">
            {% for name, cnt in s.by_deck.items() %}
              <div class="card">{{ name }} — {{ cnt }}</div>
            {% endfor %}
          </div>
        {% else %}
          <p class="hint">No reviews yet. Start a session from any deck.</p>
        {% endif %}
        <p class="hint" style="margin-top:12px">Inline confirmations appear after actions. (IH8)</p>
      </div>
    """, today=today, total=total, acc=acc, s=s)

if __name__ == "__main__":
    app.run(debug=True)
