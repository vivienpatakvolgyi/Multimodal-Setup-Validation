# stroop.py
# PsychoPy port of PsyToolkit Stroop task

import numpy_compat  # noqa: F401
from psychopy import visual, core, event
import os, random, time
from statistics import mean
from unified_logger import logger


# Config
N_TRIALS = 40
RESP_LIMIT_S = 2.0
FIXATION_DELAY_S = 0.5
FIXATION_SHOW_S = 0.2
POST_FIX_DELAY_S = 0.1
FEEDBACK_S = 0.5

# Keys: p=piros(1), z=zöld(2), k=kék(3), s=sárga(4)
KEY_MAP = {"p": 1, "z": 2, "k": 3, "s": 4}

# Table: condition_label, bitmap_name, correct_key_code
# condition format: "inkcolor wordcolor congruent"
TABLE = [
    {"label": "yellow yellow 1", "bitmap": "yellowyellow", "correct_code": 4, "congruent": 1},
    {"label": "yellow green  0", "bitmap": "yellowgreen",  "correct_code": 2, "congruent": 0},
    {"label": "yellow blue   0", "bitmap": "yellowblue",   "correct_code": 3, "congruent": 0},
    {"label": "yellow red    0", "bitmap": "yellowred",    "correct_code": 1, "congruent": 0},
    {"label": "red yellow    0", "bitmap": "redyellow",    "correct_code": 4, "congruent": 0},
    {"label": "red green     0", "bitmap": "redgreen",     "correct_code": 2, "congruent": 0},
    {"label": "red blue      0", "bitmap": "redblue",      "correct_code": 3, "congruent": 0},
    {"label": "red red       1", "bitmap": "redred",       "correct_code": 1, "congruent": 1},
    {"label": "green yellow  0", "bitmap": "greenyellow",  "correct_code": 4, "congruent": 0},
    {"label": "green green   1", "bitmap": "greengreen",   "correct_code": 2, "congruent": 1},
    {"label": "green blue    0", "bitmap": "greenblue",    "correct_code": 3, "congruent": 0},
    {"label": "green red     0", "bitmap": "greenred",     "correct_code": 1, "congruent": 0},
    {"label": "blue yellow   0", "bitmap": "blueyellow",   "correct_code": 4, "congruent": 0},
    {"label": "blue green    0", "bitmap": "bluegreen",    "correct_code": 2, "congruent": 0},
    {"label": "blue blue     1", "bitmap": "blueblue",     "correct_code": 3, "congruent": 1},
    {"label": "blue red      0", "bitmap": "bluered",      "correct_code": 1, "congruent": 0},
]

CODE_TO_KEY = {1: "p", 2: "z", 3: "k", 4: "s"}

# Paths
HERE = os.path.dirname(os.path.abspath(__file__))
STIMDIR = os.path.join(HERE, "stroop")

def ps(name: str) -> str:
    return os.path.join(STIMDIR, name + ".png")

def ensure_file(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")

# Validate assets exist
BITMAPS_NEEDED = [
    "instruction1", "instruction2", "correct", "mistake", "fixpoint",
    "yellowyellow", "yellowgreen", "yellowblue", "yellowred",
    "redyellow", "redgreen", "redblue", "redred",
    "greenyellow", "greengreen", "greenblue", "greenred",
    "blueyellow", "bluegreen", "blueblue", "bluered",
]
for bmp in BITMAPS_NEEDED:
    ensure_file(ps(bmp))


def main():
    # Window
    win = visual.Window(fullscr=True, color="black", units="pix")

    def quit_now():
        win.close()

    def pump(dt=0.01):
        core.wait(dt)

    # Load stimuli
    stim_instr1 = visual.ImageStim(win, image=ps("instruction1"))
    stim_instr2 = visual.ImageStim(win, image=ps("instruction2"))
    stim_correct = visual.ImageStim(win, image=ps("correct"))
    stim_mistake = visual.ImageStim(win, image=ps("mistake"))
    stim_fixpoint = visual.ImageStim(win, image=ps("fixpoint"))

    # Preload all stroop bitmaps
    stroop_stims = {}
    for entry in TABLE:
        bmp = entry["bitmap"]
        if bmp not in stroop_stims:
            stroop_stims[bmp] = visual.ImageStim(win, image=ps(bmp))

    txt = visual.TextStim(win, text="", color="yellow", height=20, pos=(0, 0), wrapWidth=1100)

    trial_clock = core.Clock()

    # Helpers
    def show_image(stim):
        stim.draw()
        win.flip()

    def wait_for_key(keylist):
        event.clearEvents()
        while True:
            keys = event.getKeys(keyList=keylist + ["escape"])
            if keys:
                if "escape" in keys:
                    quit_now()
                    return None
                return keys[0]
            pump(0.01)

    # Trial
    def run_trial(trial_entry):
        """
        PsyToolkit sequence:
          delay 500
          show fixpoint
          delay 200
          clear fixpoint
          delay 100
          show stimulus
          readkey correct_code 2000
          clear stimulus
          show feedback (correct/mistake)
          delay 500
          clear feedback
        Returns dict with trial data.
        """
        correct_code = trial_entry["correct_code"]
        correct_key = CODE_TO_KEY[correct_code]

        logger.log_event("trial_start", f"condition={trial_entry['label']} congruent={trial_entry['congruent']}")

        # Pre-trial delay 500ms
        win.flip()
        core.wait(FIXATION_DELAY_S)

        # Show fixpoint 200ms
        stim_fixpoint.draw()
        win.flip()
        core.wait(FIXATION_SHOW_S)

        # Clear fixpoint, wait 100ms
        win.flip()
        core.wait(POST_FIX_DELAY_S)

        # Show stimulus
        stroop_stims[trial_entry["bitmap"]].draw()
        event.clearEvents()
        win.flip()
        logger.log_event("stimulus_shown", f"bitmap={trial_entry['bitmap']} correct_key={correct_key}")
        trial_clock.reset()

        # Readkey (2000ms)
        status = "TIMEOUT"
        rt_ms = ""
        key_pressed = ""

        while trial_clock.getTime() < RESP_LIMIT_S:
            keys = event.getKeys(keyList=["p", "z", "k", "s", "escape"], timeStamped=trial_clock)
            if keys:
                k, kt = keys[0]
                if k == "escape":
                    quit_now()
                    return None
                key_pressed = k
                rt_ms = int(round(kt * 1000))
                if k == correct_key:
                    status = "CORRECT"
                else:
                    status = "WRONG"
                break
            pump(0.005)

        # Clear stimulus
        win.flip()

        # Feedback
        if status == "CORRECT":
            stim_correct.draw()
        else:
            stim_mistake.draw()
        win.flip()
        core.wait(FEEDBACK_S)

        # Clear feedback
        win.flip()

        return {
            "label": trial_entry["label"],
            "congruent": trial_entry["congruent"],
            "tablerow": TABLE.index(trial_entry) + 1,
            "key": key_pressed,
            "status": status,
            "rt_ms": rt_ms,
        }

    # Run experiment
    rows = []

    try:
        # Messages
        show_image(stim_instr1)
        wait_for_key(["space"])
        show_image(stim_instr2)
        wait_for_key(["space"])

        # Generate trial list: 40 trials, balanced sampling from 16 entries
        trial_list = (TABLE * ((N_TRIALS // len(TABLE)) + 1))[:N_TRIALS]
        random.shuffle(trial_list)

        # Run trials
        for ti, trial_entry in enumerate(trial_list, start=1):
            result = run_trial(trial_entry)
            if result is None:
                return  # escape pressed
            logger.log_event("response", f"trial={ti} key={result['key']} status={result['status']} rt_ms={result['rt_ms']} congruent={result['congruent']}")
            rows.append({
                "trial": ti,
                "blockname": "training",
                "condition": result["label"],
                "tablerow": result["tablerow"],
                "key": result["key"],
                "status": result["status"],
                "rt_ms": result["rt_ms"],
                "congruent": result["congruent"],
            })

        logger.log_event("block_end", f"total_trials={N_TRIALS}")

        # Feedback screen
        rt_con = [r["rt_ms"] for r in rows if r["status"] == "CORRECT" and r["congruent"] == 1 and r["rt_ms"] != ""]
        rt_inc = [r["rt_ms"] for r in rows if r["status"] == "CORRECT" and r["congruent"] == 0 and r["rt_ms"] != ""]

        rt_con_mean = mean(rt_con) if rt_con else float("nan")
        rt_inc_mean = mean(rt_inc) if rt_inc else float("nan")
        stroop_effect = rt_inc_mean - rt_con_mean if (rt_con and rt_inc) else float("nan")

        win.flip()
        x = -100

        lines = [
            ("Your speed in correct trials", (x, 0)),
            (f"congruent:   {rt_con_mean:.1f} ms" if rt_con else "congruent:   n/a", (x, 50)),
            (f"incongruent: {rt_inc_mean:.1f} ms" if rt_inc else "incongruent: n/a", (x, 100)),
            (f"Your Stroop effect is incongruent minus congruent: {stroop_effect:.1f} ms" if (rt_con and rt_inc) else "Stroop effect: n/a", (x, 150)),
            ("Press space key to end", (x, 200)),
        ]

        for text, pos in lines:
            txt.text = text
            txt.pos = pos
            txt.draw()

        win.flip()
        wait_for_key(["space"])

    finally:
        win.close()


if __name__ == "__main__":
    main()
