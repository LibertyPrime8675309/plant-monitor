"""Waiting in a browser check (1.58.0; November 12 review, item 6).

The checks held 1,101 fixed pauses, 29 minutes of waiting in all. A fixed pause is too long on a quick machine and, now and then,
too short on GitHub's: on November 12 `pots` failed there because a save took longer than its 1.5 seconds, though nothing was
wrong. These wait for the thing itself, and give up after 15 seconds. Use them in a check you are changing anyway, in place of a
`pg.wait_for_timeout(n)` that is followed by a `check(...)`:

    from waits import until, redrawn
    again = redrawn(pg, '#ct-7')                       # before something that makes the app draw that part again
    q.fill('6'); q.press('Enter')
    check(again() and until(pg, lambda: '3 / 6 in use' in pg.locator('#ct-7').inner_text()), 'typing a new quantity saves it')

`until` alone is enough when what you wait for can only be true afterwards (a value the server has, words on the page).
`redrawn` is for the step after: the app draws a card or a page again once a save is back, and a box filled in just before that
is thrown away with the old page. A pause that has nothing to wait for (a debounce that must pass before the next key) can stay."""
import time

def until(pg, fn, ms=15000, step=100):
    """Asks fn() until it is true, for at most ms milliseconds, and returns whether it became true.
    An error inside fn (the element is not on the page yet) counts as "not yet"."""
    end = time.monotonic() + ms / 1000
    while True:
        try:
            if fn(): return True
        except Exception: pass
        if time.monotonic() >= end: return False
        pg.wait_for_timeout(step)

def redrawn(pg, selector):
    """Call before an action that makes the app draw `selector` again; call what it returns afterwards. That waits until the element
    which was there has been replaced by a new one, and returns whether it was."""
    old = pg.locator(selector).first.element_handle()
    return lambda ms=15000: until(pg, lambda: not old.evaluate('el => el.isConnected') and pg.locator(selector).count() > 0, ms)
