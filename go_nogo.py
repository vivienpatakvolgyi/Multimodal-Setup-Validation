# go_nogo.py  (stable / no anchor / notebook-friendlier)
import numpy_compat  # noqa: F401
from psychopy import visual, core, event
import os, random, time
from unified_logger import logger

def main():
    HERE = os.path.dirname(os.path.abspath(__file__))
    STIMDIR = os.path.join(HERE, "go_nogo")

    def p(name): return os.path.join(STIMDIR, name)

    IMG_INSTRUCTIONS = p("instructions.png")
    IMG_GO          = p("gosignal.png")
    IMG_NOGO        = p("nogosignal.png")
    IMG_ERR_TYPE1   = p("errortype1.png")  # responded on NOGO
    IMG_ERR_TYPE2   = p("errortype2.png")  # timeout on GO

    # ---- Config (PsyToolkit)
    GO_N = 20
    NOGO_N = 5
    RESP_KEY = "space"
    RESP_LIMIT_S = 2.0
    ERROR_FEEDBACK_S = 2.0
    ITI_S = 0.5

    # ---- Window (stabil: windowed + no FBO)
    win = visual.Window(fullscr=True, color="black", units="pix")

    def quit_now():
        win.close()

    def make_img(path):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing image: {path}")
        return visual.ImageStim(win, image=path)

    stim_instructions = make_img(IMG_INSTRUCTIONS)
    stim_go = make_img(IMG_GO)
    stim_nogo = make_img(IMG_NOGO)
    stim_err1 = make_img(IMG_ERR_TYPE1)
    stim_err2 = make_img(IMG_ERR_TYPE2)

    clock = core.Clock()

    def pump():
        """Give time to OS/window event loop. Critical to prevent 'freezes'."""
        # event.getKeys already pumps, but a tiny sleep prevents 100% CPU spin.
        core.wait(0.005)

    def wait_for_space():
        event.clearEvents()
        while True:
            keys = event.getKeys(keyList=["space", "escape"])
            if keys:
                if "escape" in keys:
                    quit_now()
                return
            pump()

    def show(stim):
        stim.draw()
        win.flip()

    def show_for(stim, secs):
        stim.draw()
        win.flip()
        core.wait(secs)
        win.flip()

    def run_trial(taskname):
        """
        Returns (rt_ms or "", errorstatus)
        GO: must press SPACE within 2s; timeout => errortype2
        NOGO: must NOT press; any press within 2s => errortype1
        """
        errorstatus = 0
        event.clearEvents()

        logger.log_event("stimulus_shown", f"type={taskname}")

        # Stimulus on
        if taskname == "go":
            stim_go.draw()
        else:
            stim_nogo.draw()
        win.flip()
        clock.reset()

        resp = None
        rt_ms = ""

        # response window (2s)
        while clock.getTime() < RESP_LIMIT_S:
            keys = event.getKeys(keyList=[RESP_KEY, "escape"], timeStamped=clock)
            if keys:
                # keys: list of tuples (name, t)
                for k, t in keys:
                    if k == "escape":
                        quit_now()
                    if k == RESP_KEY:
                        resp = (k, t)
                        rt_ms = int(round(t * 1000))
                        break
            if resp is not None:
                break
            pump()

        # clear
        win.flip()

        if taskname == "go":
            if resp is None:
                errorstatus = 1
                show_for(stim_err2, ERROR_FEEDBACK_S)
        else:
            if resp is not None:
                errorstatus = 1
                show_for(stim_err1, ERROR_FEEDBACK_S)

        core.wait(ITI_S)
        logger.log_event("response", f"type={taskname} rt_ms={rt_ms} error={errorstatus}")
        return rt_ms, errorstatus

    # ---- Trial list (20 go, 5 nogo) shuffled
    trials = (["go"] * GO_N) + (["nogo"] * NOGO_N)
    random.shuffle(trials)

    rows = []

    try:
        show(stim_instructions)
        wait_for_space()

        for i, taskname in enumerate(trials, start=1):
            logger.log_event("trial_start", f"trial={i} type={taskname}")
            rt_ms, errorstatus = run_trial(taskname)
            rows.append({
                "trial": i,
                "taskname": taskname,
                "rt_ms": rt_ms,
                "errorstatus": errorstatus
            })

        logger.log_event("block_end", f"total_trials={len(trials)}")

        # done screen (optional)
        show(stim_instructions)
        core.wait(0.3)

    finally:
        win.close()
