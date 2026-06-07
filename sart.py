# sart.py
# PsychoPy port of PsyToolkit SART (Sustained Attention to Response Task)

import numpy_compat  # noqa: F401
from psychopy import visual, core, event
import os, random, time
from unified_logger import logger


# Config
DIGIT_DISPLAY_S = 0.250       # 250ms digit shown
MASK_DISPLAY_S = 0.900        # 900ms mask shown (remaining response window)
TOTAL_TRIAL_S = 1.150         # 250 + 900 = 1150ms total
ERROR_FEEDBACK_S = 3.0        # error feedback shown 3s
POST_ERROR_DELAY_S = 0.5      # 500ms after error feedback

NOGO_DIGIT = 3                # don't press on "3"
RESP_KEY = "space"

# Font sizes matching PsyToolkit (font2-font5 = 48,72,94,100,120 -> indices 1-5)
FONT_SIZES = [48, 72, 94, 100, 120]

# Training: digits 1-9 x2 = 18 trials (shuffled, no repeat)
TRAINING_REPEATS = 2
TRAINING_N = 18

# Real test: digits 1-9 x25 = 225 trials (shuffled, no repeat)
REAL_REPEATS = 25
REAL_N = 225

# Paths
HERE = os.path.dirname(os.path.abspath(__file__))
STIMDIR = os.path.join(HERE, "sart")

def ps(name: str) -> str:
    return os.path.join(STIMDIR, name + ".png")

def ensure_file(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")

# Validate assets exist
BITMAPS_NEEDED = [
    "mask", "instruction1", "instruction2",
    "instruction_real", "mistake_wrong_press", "mistake_missed",
    "welldone_training", "welldone_experiment",
    "ready1", "ready2", "ready3",
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
    stim_mask = visual.ImageStim(win, image=ps("mask"))
    stim_instr1 = visual.ImageStim(win, image=ps("instruction1"))
    stim_instr2 = visual.ImageStim(win, image=ps("instruction2"))
    stim_instr_real = visual.ImageStim(win, image=ps("instruction_real"))
    stim_mistake_wrong = visual.ImageStim(win, image=ps("mistake_wrong_press"))
    stim_mistake_missed = visual.ImageStim(win, image=ps("mistake_missed"))
    stim_welldone_training = visual.ImageStim(win, image=ps("welldone_training"))
    stim_welldone_experiment = visual.ImageStim(win, image=ps("welldone_experiment"))
    stim_ready1 = visual.ImageStim(win, image=ps("ready1"))
    stim_ready2 = visual.ImageStim(win, image=ps("ready2"))
    stim_ready3 = visual.ImageStim(win, image=ps("ready3"))

    # Text for digits (will change font size per trial)
    digit_text = visual.TextStim(win, text="", color="white", height=72, pos=(0, 0))

    # Text for feedback screen
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

    def generate_digit_sequence(repeats):
        """
        Generate digits 1-9 repeated 'repeats' times, shuffled with no immediate repeats.
        PsyToolkit: set &&digitrange range 1 9; set &&mydigits &&digitrange times N; shuffle no_repeat
        """
        digits = list(range(1, 10)) * repeats
        # Shuffle with no consecutive repeats
        for _ in range(1000):  # try up to 1000 times
            random.shuffle(digits)
            ok = True
            for i in range(1, len(digits)):
                if digits[i] == digits[i - 1]:
                    ok = False
                    break
            if ok:
                return digits
        # Fallback: just shuffle (might have repeats, but unlikely to matter)
        random.shuffle(digits)
        return digits

    def countdown():
        """Show ready3, ready2, ready1 each for 1s, then clear 1s"""
        show_image(stim_ready3)
        core.wait(1.0)
        show_image(stim_ready2)
        core.wait(1.0)
        show_image(stim_ready1)
        core.wait(1.0)
        win.flip()
        core.wait(1.0)

    # Trial
    def run_trial(current_digit):
        """
        PsyToolkit SART trial:
          - Show digit (random font size) for 250ms, collect response
          - Show mask for 900ms, continue collecting response
          - Total window = 1150ms
          - If digit==3 and pressed -> error (wrong press)
          - If digit!=3 and not pressed -> error (missed)
        Returns dict with trial data.
        """
        # Random font size (indices 0-4, corresponding to font2-font6 in PsyToolkit)
        random_font_idx = random.randint(0, 4)
        digit_size = random_font_idx + 1  # 1-5 for reporting
        font_height = FONT_SIZES[random_font_idx]

        digit_text.height = font_height
        digit_text.text = str(current_digit)

        # Determine trial type
        trial_type = 0 if current_digit == NOGO_DIGIT else 1

        logger.log_event("stimulus_shown", f"digit={current_digit} type={'nogo' if trial_type==0 else 'go'} font_size={digit_size}")

        # Show digit
        digit_text.draw()
        event.clearEvents()
        win.flip()
        trial_clock.reset()

        responded = False
        my_rt_ms = ""

        # Phase 1: digit visible (250ms)
        while trial_clock.getTime() < DIGIT_DISPLAY_S:
            keys = event.getKeys(keyList=[RESP_KEY, "escape"], timeStamped=trial_clock)
            if keys:
                for k, kt in keys:
                    if k == "escape":
                        quit_now()
                        return None
                    if k == RESP_KEY and not responded:
                        responded = True
                        my_rt_ms = int(round(kt * 1000))
            pump(0.005)

        # Show mask
        stim_mask.draw()
        win.flip()

        # Phase 2: mask visible (900ms), continue collecting if not responded
        if not responded:
            phase2_start = trial_clock.getTime()
            while trial_clock.getTime() < TOTAL_TRIAL_S:
                keys = event.getKeys(keyList=[RESP_KEY, "escape"], timeStamped=trial_clock)
                if keys:
                    for k, kt in keys:
                        if k == "escape":
                            quit_now()
                            return None
                        if k == RESP_KEY and not responded:
                            responded = True
                            my_rt_ms = int(round(kt * 1000))
                pump(0.005)

        # Determine status
        mystatus = 1  # assume correct

        if current_digit == NOGO_DIGIT and responded:
            # Pressed when there was a 3 -> error
            mystatus = 0
            stim_mistake_wrong.draw()
            win.flip()
            core.wait(ERROR_FEEDBACK_S)
            win.flip()
            core.wait(POST_ERROR_DELAY_S)
        elif current_digit != NOGO_DIGIT and not responded:
            # Not pressed when there was no 3 -> error
            mystatus = 0
            stim_mistake_missed.draw()
            win.flip()
            core.wait(ERROR_FEEDBACK_S)
            win.flip()
            core.wait(POST_ERROR_DELAY_S)
        else:
            # Correct - wait remaining time
            remaining = TOTAL_TRIAL_S - trial_clock.getTime()
            if remaining > 0:
                core.wait(remaining)

        logger.log_event("response", f"digit={current_digit} type={'nogo' if trial_type==0 else 'go'} status={'correct' if mystatus==1 else 'error'} rt_ms={my_rt_ms if my_rt_ms != '' else 0} responded={responded}")

        return {
            "trial_type": trial_type,
            "current_digit": current_digit,
            "digit_size": digit_size,
            "mystatus": mystatus,
            "rt_ms": my_rt_ms if my_rt_ms != "" else 0,
        }

    # Block feedback
    def show_block_feedback(rows, blocknumber):
        block_rows = [r for r in rows if r["blocknumber"] == blocknumber]

        total_go = sum(1 for r in block_rows if r["trial_type"] == 1)
        go_mistakes = sum(1 for r in block_rows if r["trial_type"] == 1 and r["mystatus"] == 0)
        total_nogo = sum(1 for r in block_rows if r["trial_type"] == 0)
        nogo_mistakes = sum(1 for r in block_rows if r["trial_type"] == 0 and r["mystatus"] == 0)

        go_mistakes_p = (go_mistakes / total_go * 100.0) if total_go else 0.0
        nogo_mistakes_p = (nogo_mistakes / total_nogo * 100.0) if total_nogo else 0.0

        block_label = "training" if blocknumber == 1 else "second"

        x = -200
        y0 = -200
        dy = 50

        win.flip()
        lines = [
            f"Results in {block_label} block:",
            f"Number Go trials: {total_go}",
            f"Number Go mistakes: {go_mistakes}",
            f"Go mistakes: {go_mistakes_p:.0f}%",
            f"Number No Go trials: {total_nogo}",
            f"Number No Go mistakes: {nogo_mistakes}",
            f"No Go mistakes: {nogo_mistakes_p:.0f}%",
            "Press space bar to continue",
        ]

        for i, s in enumerate(lines):
            txt.text = s
            txt.pos = (x, y0 + i * dy)  # PsyToolkit: y increases downward visually
            txt.draw()

        win.flip()
        wait_for_key(["space"])

    # Run experiment
    rows = []

    try:
        # === TRAINING BLOCK ===
        logger.log_event("block_start", "block=training")
        # Messages
        show_image(stim_instr1)
        wait_for_key(["space"])
        show_image(stim_instr2)
        wait_for_key(["space"])

        # Generate digit sequence
        digits = generate_digit_sequence(TRAINING_REPEATS)

        # Countdown
        countdown()

        # Run trials
        for digit in digits:
            result = run_trial(digit)
            if result is None:
                return
            rows.append({
                "blockname": "training",
                "blocknumber": 1,
                "trial_type": result["trial_type"],
                "current_digit": result["current_digit"],
                "digit_size": result["digit_size"],
                "mystatus": result["mystatus"],
                "rt_ms": result["rt_ms"],
            })

        # Training feedback
        show_block_feedback(rows, 1)

        # Well done training
        show_image(stim_welldone_training)
        wait_for_key(["space"])

        # === REAL TEST BLOCK ===
        logger.log_event("block_start", "block=realtest")
        show_image(stim_instr_real)
        wait_for_key(["space"])

        # Generate digit sequence
        digits = generate_digit_sequence(REAL_REPEATS)

        # Countdown
        countdown()

        # Run trials
        for digit in digits:
            result = run_trial(digit)
            if result is None:
                return
            rows.append({
                "blockname": "realtest",
                "blocknumber": 2,
                "trial_type": result["trial_type"],
                "current_digit": result["current_digit"],
                "digit_size": result["digit_size"],
                "mystatus": result["mystatus"],
                "rt_ms": result["rt_ms"],
            })

        # Real test feedback
        show_block_feedback(rows, 2)

        # Well done experiment
        show_image(stim_welldone_experiment)
        wait_for_key(["space"])

    finally:
        win.close()


if __name__ == "__main__":
    main()
