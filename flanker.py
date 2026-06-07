# flanker_arrows_psychopy.py
# Uses event.getKeys (pyglet) instead of hardware.keyboard to avoid freezes.
import numpy_compat  # noqa: F401
from psychopy import visual, core, event
import random
from statistics import mean
from unified_logger import logger


def main():
    # Config
    N_TRIALS = 50
    RESP_LIMIT_S = 2.0
    ITI_S = 0.5

    TABLE = [
        {"stim": "←←←←←", "congruent": 1, "correct_code": 1},  # A
        {"stim": "→→→→→", "congruent": 1, "correct_code": 2},  # L
        {"stim": "→→←→→", "congruent": 0, "correct_code": 1},  # A (middle is left)
        {"stim": "←←→←←", "congruent": 0, "correct_code": 2},  # L (middle is right)
    ]
    CODE_TO_KEY = {1: "a", 2: "l"}

    # Window & stimuli
    win = visual.Window(fullscr=True, color="black", units="pix")

    fix_v = visual.Rect(win, width=10, height=50, fillColor="red", lineColor="red", pos=(0, 25))
    fix_h = visual.Rect(win, width=50, height=10, fillColor="red", lineColor="red", pos=(0, 25))

    stim_text = visual.TextStim(win, text="", color="white", height=80, pos=(0, 0))
    small_text = visual.TextStim(win, text="", color="white", height=18, pos=(0, 0))

    trial_clock = core.Clock()

    def pump(dt=0.01):
        core.wait(dt)

    def wait_for_space():
        event.clearEvents()
        while True:
            keys = event.getKeys(keyList=["space", "escape"])
            if keys:
                if "escape" in keys:
                    win.close()
                    return False
                return True
            pump()

    def warning_signal():
        # PsyToolkit: rectangle 0 25
        wfix_v = visual.Rect(win, width=10, height=50, fillColor="red", lineColor="red", pos=(0, 25))
        wfix_h = visual.Rect(win, width=50, height=10, fillColor="red", lineColor="red", pos=(0, 25))
        for _ in range(15):
            wfix_v.draw()
            wfix_h.draw()
            win.flip()
            core.wait(0.1)
            win.flip()
            core.wait(0.1)

    def show_instructions_block():
        small_text.height = 18
        lines = [
            "Ha a középső nyíl ←, akkor nyomd meg az A gombot",
            "Ha a középső nyíl →, akkor nyomd meg az L gombot",
        ]
        for idx, line in enumerate(lines):
            small_text.text = line
            small_text.pos = (0, -100 + idx * 50)
            small_text.draw()
        win.flip()

    def draw_text_center(text, color="white", height=18, y=0):
        small_text.text = text
        small_text.color = color
        small_text.height = height
        small_text.pos = (0, y)
        small_text.draw()

    # Trial generation
    base = (TABLE * ((N_TRIALS // len(TABLE)) + 1))[:N_TRIALS]
    random.shuffle(base)
    trials = base

    # Data logging
    rows = []

    # Start screen
    win.flip()
    draw_text_center('Látsz 5 nyilat, például így → → → → →', y=-50)
    draw_text_center('Csak a középső nyílra figyelj, ebben a példában az →', y=-100)
    draw_text_center('Ha a középső nyíl ←, nyomd meg az A gombot', y=-150)
    draw_text_center('Ha a középső nyíl →, nyomd meg az L gombot', y=-200)
    draw_text_center('Ezt többször fogod csinálni', y=-250)
    draw_text_center('Nyomd meg a szóköz gombot a feladat indításához', y=-300)
    win.flip()
    if not wait_for_space():
        return

    # Main loop
    for ti, tr in enumerate(trials, start=1):
        correct_key = CODE_TO_KEY[tr["correct_code"]]

        logger.log_event("trial_start", f"trial={ti} stimulus={tr['stim']} congruent={tr['congruent']}")

        fix_v.draw()
        fix_h.draw()
        stim_text.text = tr["stim"]
        stim_text.pos = (0, -50)
        stim_text.draw()

        event.clearEvents()
        win.flip()
        logger.log_event("stimulus_shown", f"trial={ti} arrows={tr['stim']}")
        trial_clock.reset()

        # Collect response up to 2 seconds
        status = "TIMEOUT"
        rt_ms = ""
        resp = None

        while trial_clock.getTime() < RESP_LIMIT_S:
            keys = event.getKeys(keyList=["a", "l", "escape"], timeStamped=trial_clock)
            if keys:
                k, kt = keys[0]
                if k == "escape":
                    win.close()
                    return
                resp = k
                rt_ms = int(round(kt * 1000))
                status = "CORRECT" if resp == correct_key else "WRONG"
                break
            pump(0.005)

        # Clear screen
        win.flip()

        # Feedback
        if status == "CORRECT":
            fb = visual.TextStim(win, text="Helyes", color="green", height=18, pos=(0, 25))
            fb.draw()
            win.flip()
            core.wait(0.2)
            win.flip()
        else:
            if status == "WRONG":
                draw_text_center("Rossz gombot nyomtál.", y=-150)
            else:
                draw_text_center("Túl lassan válaszoltál. Válaszolj 2 másodpercen belül.", y=-150)

            show_instructions_block()
            warning_signal()
            win.flip()

        # ITI 500 ms
        core.wait(ITI_S)

        logger.log_event("response", f"trial={ti} key={resp or ''} status={status} rt_ms={rt_ms} congruent={tr['congruent']}")

        rows.append({
            "trial": ti,
            "stimulus": tr["stim"],
            "congruent": tr["congruent"],
            "correct_key": correct_key,
            "status": status,
            "rt_ms": rt_ms,
        })

    # Feedback screen
    rt_con = [r["rt_ms"] for r in rows if r["status"] == "CORRECT" and r["congruent"] == 1 and r["rt_ms"] != ""]
    rt_inc = [r["rt_ms"] for r in rows if r["status"] == "CORRECT" and r["congruent"] == 0 and r["rt_ms"] != ""]

    rt_con_mean = mean(rt_con) if rt_con else float("nan")
    rt_inc_mean = mean(rt_inc) if rt_inc else float("nan")
    flanker_effect = rt_inc_mean - rt_con_mean if (rt_con and rt_inc) else float("nan")

    fb_lines = ["Átlagos reakcióidő a feltételekben:", ""]
    fb_lines.append(f"Kompatibilis: {rt_con_mean:.1f} ms" if rt_con else "Kompatibilis: n/a")
    fb_lines.append(f"Inkompatibilis: {rt_inc_mean:.1f} ms" if rt_inc else "Inkompatibilis: n/a")
    fb_lines.append(f"Flanker hatás: {flanker_effect:.1f} ms" if (rt_con and rt_inc) else "Flanker hatás: n/a")
    fb_lines.append("")
    fb_lines.append("Nyomd meg a szóköz gombot a folytatáshoz")

    logger.log_event("feedback", f"rt_con={rt_con_mean:.1f} rt_inc={rt_inc_mean:.1f} effect={flanker_effect:.1f}")

    try:
        win.flip()
        core.wait(0.1)  # let pyglet settle
        event.clearEvents()
        fb_stim = visual.TextStim(win, text="\n".join(fb_lines), color="yellow",
                                  font='Arial', height=32, pos=(0, 0), wrapWidth=900)
        fb_stim.draw()
        win.flip()
        # Wait for space with explicit pump loop (don't rely on wait_for_space)
        while True:
            keys = event.getKeys(keyList=["space", "escape"])
            if keys:
                break
            core.wait(0.01)
    except Exception as e:
        # Fallback: print to console if pyglet text rendering fails
        print("\n--- Flanker Eredmények ---")
        for line in fb_lines:
            if line:
                print(f"  {line}")
        print("(Nyomd meg az Enter gombot a folytatáshoz)")
        input()

    win.close()


if __name__ == "__main__":
    main()
