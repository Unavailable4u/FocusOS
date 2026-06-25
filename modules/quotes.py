"""
modules/quotes.py
-----------------
Motivational / focus-themed quotes for the dashboard header.

Quote tiers are keyed by focus-streak length so the messaging
escalates naturally as the user builds momentum:

  Tier 0  →  0 days streak      (spark / start)
  Tier 1  →  1–2 days streak    (building momentum)
  Tier 2  →  3–6 days streak    (finding rhythm)
  Tier 3  →  7–29 days streak   (strong habit)
  Tier 4  →  30+ days streak    (elite consistency)

Within each tier the quote is chosen deterministically by
day-of-year, so it stays the same all day and cycles smoothly.
"""

from datetime import datetime

# ---------------------------------------------------------------------------
# Quote bank — grouped by tier
# ---------------------------------------------------------------------------

_QUOTES: dict[str, list[str]] = {
    "tier0": [  # no streak yet — encourage starting
        "Every expert was once a beginner. Start today.",
        "The secret of getting ahead is getting started.",
        "One focused session today is all it takes.",
        "Small consistent actions create extraordinary results.",
        "You don't have to be great to start, but you have to start to be great.",
        "The best time to plant a tree was 20 years ago. The second best time is now.",
        "Progress, not perfection, is the goal.",
        "A single step forward breaks any streak of standing still.",
        "Your future self is rooting for you right now.",
        "Discipline is choosing between what you want now and what you want most.",
    ],
    "tier1": [  # 1–2 day streak — early momentum
        "Two days in. Momentum is quietly building.",
        "Consistency starts with a single repeated choice.",
        "You showed up again. That's already more than most.",
        "Every day you practice is a day you improve.",
        "The compound interest of good habits pays dividends you can't yet imagine.",
        "Brick by brick. Day by day.",
        "Small wins stack into big victories.",
        "Repetition is the mother of mastery.",
        "The difference between who you are and who you want to be is what you do daily.",
        "Keep going — the hardest streaks to build are the first few days.",
    ],
    "tier2": [  # 3–6 days — finding rhythm
        "A week of focus rewires a month of distraction.",
        "You're in the rhythm now. Protect it.",
        "Habits cement at the point where they stop feeling like effort.",
        "The person you're becoming is shaped by sessions like this one.",
        "Depth of focus beats hours of noise every time.",
        "Your streak is proof that intention can become identity.",
        "Excellence is not a destination — it's a direction.",
        "The mind, once focused, is a remarkable engine.",
        "What you do consistently eventually becomes effortless.",
        "Flow state isn't luck. It's earned through repetition.",
    ],
    "tier3": [  # 7–29 days — strong habit
        "Seven days of commitment beats seven months of intention.",
        "A one-week streak means you've built the habit. Now deepen it.",
        "You've proven the discipline. Now let it carry you.",
        "Great things are not done by impulse, but by a series of small things brought together.",
        "The mind is sharper when you train it like a muscle.",
        "Your consistency is compounding in ways you can't yet measure.",
        "Mastery is just sustained curiosity applied every day.",
        "You are the sum of what you repeatedly do. Choose wisely.",
        "Durability is the rarest competitive advantage.",
        "At this point, the streak defends itself. You just have to show up.",
    ],
    "tier4": [  # 30+ days — elite consistency
        "Thirty days of focus is a transformation, not a streak.",
        "You are no longer building a habit. You are the habit.",
        "Consistency at this level is its own form of genius.",
        "What looks like talent is usually disguised repetition.",
        "Legends aren't born in single moments — they're forged in daily discipline.",
        "You've outlasted the resistance. Keep going.",
        "At 30 days, what was willpower has become identity.",
        "The rarest skill in any field is simply not stopping.",
        "You've earned the right to call yourself consistent. Now protect it.",
        "Champions don't do extraordinary things. They do ordinary things extraordinarily consistently.",
    ],
}


def _get_tier_key(streak: int) -> str:
    if streak >= 30:
        return "tier4"
    if streak >= 7:
        return "tier3"
    if streak >= 3:
        return "tier2"
    if streak >= 1:
        return "tier1"
    return "tier0"


def get_quote_for_today(streak: int = 0) -> str:
    """Return a deterministic motivational quote for today.

    Parameters
    ----------
    streak:
        Current focus streak in days (from ``get_focus_streak()``).
        Defaults to 0 so callers that don't have streak data yet
        still get a sensible quote.

    The quote is stable throughout the day (keyed by day-of-year)
    and advances to the next quote in the tier pool the following
    day, cycling through the full list.
    """
    tier_key = _get_tier_key(streak)
    pool     = _QUOTES[tier_key]
    day_idx  = datetime.now().timetuple().tm_yday  # 1–366
    return pool[(day_idx - 1) % len(pool)]