# nback2_psychopy.py
# PsychoPy port of PsyToolkit nback2.psy
# Everything inside main() to avoid kernel crashes when imported.

import numpy_compat  # noqa: F401
from psychopy import visual, core, event
import os, random, time
from unified_logger import logger

# Config (matching the PsyToolkit script)
STIM_DISPLAY_S = 0.5      # 500 ms
ITI_S = 2.5               # 2500 ms
TRIAL_WINDOW_S = STIM_DISPLAY_S + ITI_S  # 3000 ms
CHOOSECHANCE = 3          # 1 in 3 trials are 2-back matches (after trial 2)
N_TRIALS_PER_BLOCK = 25

RESP_KEY = "m"
CONTINUE_KEY = "q"

# Paths
HERE = os.path.dirname(os.path.abspath(__file__))
STIMDIR = os.path.join(HERE, "twoback", "stimuli")

def ps(name: str) -> str:
    return os.path.join(STIMDIR, name)

def ensure_file(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")

# Letters listed in the PsyToolkit script (15 items)
LETTER_NAMES = [
    "letterA.png", "letterB.png", "letterC.png", "letterD.png", "letterE.png",
    "letterH.png", "letterI.png", "letterK.png", "letterL.png", "letterM.png",
    "letterO.png", "letterP.png", "letterR.png", "letterS.png", "letterT.png"
]

# Feedback overlays
GREY_FB = ps("grey_feedback.png")
ERR_FB  = ps("error_feedback.png")
OK_FB   = ps("correct_feedback.png")

# Instruction / block messages
INSTR2 = ps("instruction2.png")
REAL1  = ps("realblock1.png")
REAL2  = ps("realblock2.png")

# Validate assets exist
for fn in LETTER_NAMES:
    ensure_file(ps(fn))
for fn in [GREY_FB, ERR_FB, OK_FB, INSTR2, REAL1, REAL2]:
    ensure_file(fn)


def main():
    # Window
    win = visual.Window(fullscr=True, color="black", units="pix")

    def quit_now():
        win.close()

    def pump(dt=0.01):
        core.wait(dt)

    # Preload stimuli
    letter_stims = [visual.ImageStim(win, image=ps(fn)) for fn in LETTER_NAMES]
    stim_grey = visual.ImageStim(win, image=GREY_FB)
    stim_err  = visual.ImageStim(win, image=ERR_FB)
    stim_ok   = visual.ImageStim(win, image=OK_FB)

    msg_instr2 = visual.ImageStim(win, image=INSTR2)
    msg_real1  = visual.ImageStim(win, image=REAL1)
    msg_real2  = visual.ImageStim(win, image=REAL2)

    txt = visual.TextStim(win, text="", color="yellow", height=22, pos=(0, 0), wrapWidth=1100)

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

    def choose_letter_index_not(equal_index: int) -> int:
        idx = random.randint(0, 14)
        while idx == equal_index:
            idx = random.randint(0, 14)
        return idx

    # Trial (2-back)
    def run_twoback_trial(trialcount, nback1_idx, nback2_idx):
        memory_draw = random.randint(1, CHOOSECHANCE)
        typeoftrial = 0
        requiredresponse = 0

        if memory_draw == 1 and trialcount > 2:
            current_idx = nback2_idx
            requiredresponse = 1
            typeoftrial = 1
        else:
            current_idx = choose_letter_index_not(nback2_idx)
            requiredresponse = 0
            typeoftrial = 0

        logger.log_event("stimulus_shown", f"trial={trialcount} letter_idx={current_idx} type={'match' if typeoftrial==1 else 'nomatch'}")

        score = 0
        match = 0
        miss = 0
        false_alarm = 0
        my_rt_ms = ""

        responded = False
        fb = None

        event.clearEvents()
        trial_clock = core.Clock()

        letter_stims[current_idx].draw()
        stim_grey.draw()
        win.flip()
        trial_clock.reset()

        letter_phase_done = False
        feedback_flipped = False

        while trial_clock.getTime() < TRIAL_WINDOW_S:
            t = trial_clock.getTime()

            if (not letter_phase_done) and (t >= STIM_DISPLAY_S):
                stim_grey.draw()
                if fb is not None:
                    fb.draw()
                win.flip()
                letter_phase_done = True

            keys = event.getKeys(keyList=[RESP_KEY, "escape"], timeStamped=trial_clock)
            if keys:
                for k, kt in keys:
                    if k == "escape":
                        quit_now()
                        return None, nback1_idx, nback2_idx

                    if k == RESP_KEY and not responded:
                        responded = True
                        my_rt_ms = int(round(kt * 1000))

                        if requiredresponse == 0:
                            score = 0
                            false_alarm = 1
                            fb = stim_err
                        else:
                            score = 1
                            match = 1
                            fb = stim_ok

                        if not feedback_flipped:
                            if t < STIM_DISPLAY_S:
                                letter_stims[current_idx].draw()
                                fb.draw()
                                win.flip()
                            else:
                                stim_grey.draw()
                                fb.draw()
                                win.flip()
                            feedback_flipped = True

            pump(0.01)

        if requiredresponse == 1 and score == 0 and not responded:
            miss = 1
        if requiredresponse == 0 and not responded:
            score = 1

        new_nback2 = nback1_idx
        new_nback1 = current_idx

        logger.log_event("response", f"trial={trialcount} type={'match' if typeoftrial==1 else 'nomatch'} score={score} match={match} miss={miss} false_alarm={false_alarm} rt_ms={my_rt_ms}")

        return {
            "trialcount": trialcount,
            "typeoftrial": typeoftrial,
            "score": score,
            "requiredresponse": requiredresponse,
            "match": match,
            "miss": miss,
            "false_alarm": false_alarm,
            "my_rt_ms": my_rt_ms,
            "memory_draw": memory_draw,
            "currentletter_idx": current_idx,
            "nback1_idx": new_nback1,
            "nback2_idx": new_nback2,
        }, new_nback1, new_nback2

    # Feedback screen per block
    def block_feedback(rows, blocknumber):
        block_rows = [r for r in rows if r["blocknumber"] == blocknumber]

        total_match_trials = sum(1 for r in block_rows if r["typeoftrial"] == 1)
        total_nomatch_trials = sum(1 for r in block_rows if r["typeoftrial"] == 0)

        matches = sum(1 for r in block_rows if r["match"] == 1)
        misses = sum(1 for r in block_rows if r["miss"] == 1)
        false_alarms = sum(1 for r in block_rows if r["false_alarm"] == 1)

        matches_perc = (matches / total_match_trials * 100.0) if total_match_trials else float("nan")
        misses_perc = (misses / total_match_trials * 100.0) if total_match_trials else float("nan")
        false_alarms_perc = (false_alarms / total_nomatch_trials * 100.0) if total_nomatch_trials else float("nan")

        x = -520
        y0 = 260
        dy = 42

        win.flip()
        lines = [
            "25 próba volt ebnl a blokkban.",
            f"Az összes próba, ami egyezett: {total_match_trials}",
            f"Az összes próba, ami nem egyezett: {total_nomatch_trials}",
            f"Helyesen egyező tételek száma: {matches}",
            f"Elmaradt tételek száma: {misses}",
            f"Hamis riasztások száma: {false_alarms}",
            f"Helyesen egyező tételek aránya: {matches_perc:.1f} %",
            f"Elmaradt tételek aránya: {misses_perc:.1f} %",
            f"Hamis riasztások aránya: {false_alarms_perc:.1f} %",
            "Nyomd meg a Q gombot a folytatáshoz",
        ]

        for i, s in enumerate(lines):
            txt.text = s
            txt.pos = (x, y0 - i * dy)
            txt.draw()

        win.flip()
        wait_for_key([CONTINUE_KEY])

    # Block runner
    def run_block(blocknumber, message_stims, rows):
        for stim in message_stims:
            show_image(stim)
            wait_for_key(["space"])

        trialcount = 0
        nback1 = random.randint(0, 14)
        nback2 = random.randint(0, 14)

        for _ in range(N_TRIALS_PER_BLOCK):
            trialcount += 1
            out, nback1, nback2 = run_twoback_trial(trialcount, nback1, nback2)
            if out is None:
                return
            rows.append({
                "blocknumber": blocknumber,
                "trialcount": out["trialcount"],
                "typeoftrial": out["typeoftrial"],
                "score": out["score"],
                "requiredresponse": out["requiredresponse"],
                "match": out["match"],
                "miss": out["miss"],
                "false_alarm": out["false_alarm"],
                "my_rt_ms": out["my_rt_ms"],
                "memory_draw": out["memory_draw"],
                "currentletter_idx": out["currentletter_idx"],
                "nback1_idx": out["nback1_idx"],
                "nback2_idx": out["nback2_idx"],
            })

        block_feedback(rows, blocknumber)

    # Run experiment
    rows = []

    try:
        logger.log_event("block_start", "block=1 type=training")
        run_block(1, [msg_instr2], rows)
        logger.log_event("block_start", "block=2 type=real")
        run_block(2, [msg_real1], rows)
        logger.log_event("block_start", "block=3 type=real")
        run_block(3, [msg_real2], rows)

        win.flip()
        pump(0.2)

    finally:
        win.close()


if __name__ == "__main__":
    main()
