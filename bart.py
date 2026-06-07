# bart.py
# PsychoPy port of PsyToolkit BART (Balloon Analogue Risk Task)
# Mouse-based task. Everything inside main().

import numpy_compat  # noqa: F401
from psychopy import visual, core, event
import os, random, time, math
from unified_logger import logger


# Config (matching PsyToolkit script)
POINTS_PER_PUMP = 5  # 5 cents per pump in original paper
BALLOON_X = -350     # balloon position (in PsyToolkit coords, we'll map)
BALLOON_Y = -65

# Predetermined explosion points (from PsyToolkit script)
BLUE_EXPLOSION_POINTS = [49, 101, 65, 25, 74, 100, 18, 31, 49, 128, 71, 100, 89, 37, 110, 20, 26, 114, 70, 3, 89, 27, 36, 101, 95, 109, 5, 52, 34, 92]
YELLOW_EXPLOSION_POINTS = [3, 26, 1, 10, 24, 30, 11, 7, 22, 26, 18, 1, 24, 23, 17, 21, 26, 18, 6, 6, 20, 3, 22, 21, 21, 23, 6, 26, 10, 8]
ORANGE_EXPLOSION_POINTS = [5, 4, 1, 4, 7, 4, 2, 3, 5, 5, 1, 7, 8, 2, 3, 2, 2, 8, 4, 3, 4, 6, 5, 2, 1, 1, 5, 3, 6, 7]

# Mixed block: 10 of each type (2=blue, 3=yellow, 4=orange)
MIXED_BLOCK_TYPES = [2]*10 + [3]*10 + [4]*10

# Balloon colors (RGB normalized 0-1 for PsychoPy)
COLORS = {
    "green":  (0/255, 128/255, 0/255),
    "blue":   (100/255, 100/255, 255/255),
    "yellow": (255/255, 255/255, 0/255),
    "orange": (255/255, 128/255, 0/255),
}

# Paths
HERE = os.path.dirname(os.path.abspath(__file__))
BARTDIR = os.path.join(HERE, "bart")

def bp(name: str) -> str:
    """Get bitmap path for BART stimuli (webp format)."""
    return os.path.join(BARTDIR, name + ".webp")

def ensure_file(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")

# Validate assets
BITMAPS_NEEDED = [
    "instructions1", "instructions2", "instructions3",
    "pumpButton", "collectButton", "collectButtonGrey",
    "screenoutline", "explode1", "explode2", "arrows",
    "startButton", "nextPage", "previousPage",
    "reportLayout", "greenContinueButton",
]
for bmp in BITMAPS_NEEDED:
    ensure_file(bp(bmp))


def main():
    # Window (1920x1080 scaled)
    win = visual.Window(fullscr=True, color="white", units="pix")
    win_w, win_h = win.size
    # PsyToolkit uses resolution 1920x1080 with origin at center
    # Scale factor to map PsyToolkit coords to actual screen
    sx = win_w / 1920.0
    sy = win_h / 1080.0

    def px(x): return x * sx
    def py(y): return -y * sy  # PsyToolkit Y is inverted vs PsychoPy

    mouse = event.Mouse(win=win)

    def quit_now():
        win.close()

    def pump_wait(dt=0.01):
        core.wait(dt)

    # Load bitmaps
    stim_outline = visual.ImageStim(win, image=bp("screenoutline"))
    stim_pump = visual.ImageStim(win, image=bp("pumpButton"), pos=(px(-595), py(450)))
    stim_collect = visual.ImageStim(win, image=bp("collectButton"), pos=(px(-80), py(450)))
    stim_collect_grey = visual.ImageStim(win, image=bp("collectButtonGrey"), pos=(px(-80), py(450)))
    stim_explode1 = visual.ImageStim(win, image=bp("explode1"))
    stim_explode2 = visual.ImageStim(win, image=bp("explode2"))
    stim_arrows = visual.ImageStim(win, image=bp("arrows"))
    stim_instr1 = visual.ImageStim(win, image=bp("instructions1"))
    stim_instr2 = visual.ImageStim(win, image=bp("instructions2"))
    stim_instr3 = visual.ImageStim(win, image=bp("instructions3"))
    stim_report = visual.ImageStim(win, image=bp("reportLayout"), pos=(px(-140), py(0)))
    stim_green_continue = visual.ImageStim(win, image=bp("greenContinueButton"))

    # Text stimuli
    txt_earnings = visual.TextStim(win, text="0", color="black", height=50*sy, pos=(px(550), py(-50)))
    txt_this_balloon = visual.TextStim(win, text="0", color="black", height=50*sy, pos=(px(550), py(-350)))
    txt_balloon_count = visual.TextStim(win, text="0", color="black", height=50*sy, pos=(px(550), py(250)))
    txt_training = visual.TextStim(win, text="TRAINING BLOCK", color="black", height=50*sy, pos=(px(570), py(450)))
    txt_generic = visual.TextStim(win, text="", color="black", height=50*sy, pos=(0, 0))

    # Helpers
    def show_image_wait(stim):
        stim.draw()
        win.flip()
        # Wait for mouse click or space
        event.clearEvents()
        mouse.clickReset()
        while True:
            keys = event.getKeys(keyList=["space", "escape"])
            if keys:
                if "escape" in keys:
                    quit_now()
                    return False
                return True
            buttons = mouse.getPressed()
            if buttons[0]:
                # wait for release
                while mouse.getPressed()[0]:
                    pump_wait(0.01)
                return True
            pump_wait(0.01)

    def is_mouse_on(stim):
        """Check if mouse is currently over a stimulus."""
        if hasattr(stim, 'contains'):
            return stim.contains(mouse)
        # Fallback: check bounding box
        mx, my = mouse.getPos()
        sx2, sy2 = stim.size[0]/2, stim.size[1]/2
        cx, cy = stim.pos
        return (cx - sx2 <= mx <= cx + sx2) and (cy - sy2 <= my <= cy + sy2)

    def wait_click_on(stim_list):
        """Wait for left click on one of the stimuli in list. Returns index."""
        mouse.clickReset()
        while True:
            keys = event.getKeys(keyList=["escape"])
            if keys:
                quit_now()
                return -1
            buttons, times = mouse.getPressed(getTime=True)
            if buttons[0]:
                for i, stim in enumerate(stim_list):
                    if is_mouse_on(stim):
                        # Wait for release
                        while mouse.getPressed()[0]:
                            pump_wait(0.005)
                        return i
                # Clicked but not on any valid target, wait for release
                while mouse.getPressed()[0]:
                    pump_wait(0.005)
            pump_wait(0.005)

    # Instructions (pager-style)
    def show_instructions():
        pages = [stim_instr1, stim_instr2]
        page_idx = 0
        while True:
            pages[page_idx].draw()
            win.flip()
            event.clearEvents()
            mouse.clickReset()
            # Wait for click or key
            while True:
                keys = event.getKeys(keyList=["escape", "space", "right", "left"])
                if keys:
                    if "escape" in keys:
                        quit_now()
                        return False
                    if "right" in keys or "space" in keys:
                        if page_idx < len(pages) - 1:
                            page_idx += 1
                        else:
                            return True
                        break
                    if "left" in keys:
                        if page_idx > 0:
                            page_idx -= 1
                        break
                buttons = mouse.getPressed()
                if buttons[0]:
                    while mouse.getPressed()[0]:
                        pump_wait(0.005)
                    # Simple: click advances
                    if page_idx < len(pages) - 1:
                        page_idx += 1
                    else:
                        return True
                    break
                pump_wait(0.01)

    # BART Trial
    def run_bart_trial(explosion_point, balloon_color_name, block_type, balloon_count_display):
        """
        One BART trial.
        Returns dict with trial data, or None if escaped.
        """
        color_rgb = COLORS[balloon_color_name]
        # Convert to PsychoPy color space (-1 to 1)
        color_pp = (color_rgb[0]*2-1, color_rgb[1]*2-1, color_rgb[2]*2-1)

        balloon_size = 10 * min(sx, sy)  # starting radius in pixels
        size_increment = 3 * min(sx, sy)

        times_pumped = 0
        earnings_this_balloon = 0
        explosion = False
        collected = False
        rt_list = []

        pump_clock = core.Clock()

        # Is collect button active?
        collect_active = False

        while not explosion and not collected:
            # Draw screen
            stim_outline.draw()
            stim_pump.draw()
            if collect_active:
                stim_collect.draw()
            else:
                stim_collect_grey.draw()

            # Draw balloon
            balloon = visual.Circle(
                win,
                radius=balloon_size,
                fillColor=color_pp,
                lineColor=color_pp,
                pos=(px(BALLOON_X), py(BALLOON_Y))
            )
            balloon.draw()

            # Draw texts
            txt_earnings.draw()
            txt_this_balloon.text = str(earnings_this_balloon)
            txt_this_balloon.draw()
            txt_balloon_count.text = str(balloon_count_display)
            txt_balloon_count.draw()

            if block_type == 0:
                txt_training.draw()

            win.flip()

            # Wait for click
            pump_clock.reset()
            mouse.clickReset()
            clicked_idx = -1

            while clicked_idx == -1:
                keys = event.getKeys(keyList=["escape"])
                if keys:
                    quit_now()
                    return None

                buttons = mouse.getPressed()
                if buttons[0]:
                    if is_mouse_on(stim_pump):
                        clicked_idx = 0  # pump
                    elif collect_active and is_mouse_on(stim_collect):
                        clicked_idx = 1  # collect
                    # Wait for release
                    while mouse.getPressed()[0]:
                        pump_wait(0.005)
                pump_wait(0.005)

            rt_list.append(pump_clock.getTime() * 1000)  # ms

            if clicked_idx == 0:  # PUMP
                if times_pumped == 0:
                    collect_active = True
                times_pumped += 1
                logger.log_event("action", f"pump times_pumped={times_pumped} color={balloon_color_name}")

                if times_pumped >= explosion_point:
                    explosion = True
                else:
                    earnings_this_balloon += POINTS_PER_PUMP
                    balloon_size += size_increment

                # Pump animation (scale button briefly)
                # Just a brief visual flash
                core.wait(0.05)

            elif clicked_idx == 1:  # COLLECT
                collected = True

        # Post-trial
        if explosion:
            # Explosion animation
            stim_outline.draw()
            stim_pump.draw()
            stim_collect_grey.draw()
            txt_earnings.draw()
            txt_balloon_count.text = str(balloon_count_display)
            txt_balloon_count.draw()
            # Show explode frames
            stim_explode1.pos = (px(BALLOON_X), py(BALLOON_Y))
            stim_explode2.pos = (px(BALLOON_X), py(BALLOON_Y))
            stim_explode1.draw()
            win.flip()
            core.wait(0.1)

            stim_outline.draw()
            stim_pump.draw()
            stim_collect_grey.draw()
            txt_earnings.draw()
            stim_explode2.draw()
            win.flip()
            core.wait(0.1)

            # Show "balloon exploded..."
            stim_outline.draw()
            txt_generic.text = "balloon exploded..."
            txt_generic.pos = (px(BALLOON_X), py(BALLOON_Y))
            txt_generic.color = "black"
            txt_generic.draw()
            txt_earnings.draw()
            txt_balloon_count.text = "earnings lost"
            txt_balloon_count.draw()
            win.flip()
            core.wait(0.5)

            earnings_this_balloon = 0

        elif collected:
            # Arrow animation (simplified)
            for y_off in range(-270, -220, 10):
                stim_outline.draw()
                stim_pump.draw()
                stim_collect.draw()
                txt_earnings.draw()
                txt_this_balloon.text = str(earnings_this_balloon)
                txt_this_balloon.draw()
                txt_balloon_count.text = str(balloon_count_display)
                txt_balloon_count.draw()
                stim_arrows.pos = (px(550), py(y_off))
                stim_arrows.draw()
                win.flip()
                core.wait(0.05)

        avg_rt = round(sum(rt_list) / len(rt_list)) if rt_list else 0
        potential_earnings_this = (explosion_point - 1) * POINTS_PER_PUMP

        outcome = "explosion" if explosion else "collected"
        logger.log_event("trial_end", f"color={balloon_color_name} outcome={outcome} pumps={times_pumped} earnings={earnings_this_balloon if collected else 0} avg_rt={avg_rt}")

        return {
            "balloon_color": balloon_color_name,
            "times_pumped": times_pumped,
            "explosion": 1 if explosion else 0,
            "earnings_this_balloon": earnings_this_balloon if collected else 0,
            "avg_rt": avg_rt,
            "potential_earnings_this": potential_earnings_this,
        }

    # Report screen
    def show_report(potential_earnings, earnings, balloon_count, unexploded, exploded, bart_score):
        missed_potential = potential_earnings - earnings

        stim_report.draw()

        report_x = px(360)
        values = [
            (str(potential_earnings), (report_x, py(-390))),
            (str(earnings), (report_x, py(-260))),
            (str(missed_potential), (report_x, py(-130))),
            (str(balloon_count), (report_x, py(0))),
            (str(unexploded), (report_x, py(130))),
            (str(exploded), (report_x, py(260))),
            (str(bart_score), (report_x, py(385))),
        ]
        for text, pos in values:
            txt_generic.text = text
            txt_generic.pos = pos
            txt_generic.color = "black"
            txt_generic.draw()

        win.flip()
        core.wait(2.0)

        # Show continue button
        stim_report.draw()
        for text, pos in values:
            txt_generic.text = text
            txt_generic.pos = pos
            txt_generic.draw()
        stim_green_continue.pos = (px(780), py(392))
        stim_green_continue.draw()
        win.flip()

        # Wait for click on continue
        mouse.clickReset()
        while True:
            keys = event.getKeys(keyList=["escape", "space"])
            if keys:
                if "escape" in keys:
                    quit_now()
                    return
                return
            buttons = mouse.getPressed()
            if buttons[0]:
                while mouse.getPressed()[0]:
                    pump_wait(0.005)
                return
            pump_wait(0.01)

    # Run experiment
    rows = []
    earnings = 0
    potential_earnings = 0
    balloon_count = 0
    balloon_count_exploded = 0
    balloon_count_unexploded = 0
    bart_score_array = []

    # Make copies of explosion point lists
    blue_points = BLUE_EXPLOSION_POINTS.copy()
    yellow_points = YELLOW_EXPLOSION_POINTS.copy()
    orange_points = ORANGE_EXPLOSION_POINTS.copy()
    mixed_types = MIXED_BLOCK_TYPES.copy()
    random.shuffle(mixed_types)

    try:
        # === TRAINING BLOCK ===
        logger.log_event("block_start", "block=training")
        show_instructions()

        # 3 green training balloons (fixed explosion at 10)
        for _ in range(3):
            balloon_count += 1
            txt_earnings.text = str(earnings)

            result = run_bart_trial(10, "green", 0, balloon_count)
            if result is None:
                return

            potential_this = result["potential_earnings_this"]
            potential_earnings += potential_this

            if result["explosion"] == 0:
                earnings += result["earnings_this_balloon"]
                balloon_count_unexploded += 1
                bart_score_array.append(result["times_pumped"])
            else:
                balloon_count_exploded += 1

            txt_earnings.text = str(earnings)
            bart_score = round(sum(bart_score_array) / len(bart_score_array)) if bart_score_array else 0

            rows.append({
                "blockname": "training",
                "balloon_color": result["balloon_color"],
                "balloon_count": balloon_count,
                "times_pumped": result["times_pumped"],
                "explosion": result["explosion"],
                "earnings_this_balloon": result["earnings_this_balloon"],
                "total_earnings": earnings,
                "bart_score_so_far": bart_score,
                "avg_rt": result["avg_rt"],
                "potential_earnings_this": potential_this,
                "potential_earnings_total": potential_earnings,
            })

        # === FEEDBACK 1 ===
        bart_score = round(sum(bart_score_array) / len(bart_score_array)) if bart_score_array else 0
        show_report(potential_earnings, earnings, balloon_count, balloon_count_unexploded, balloon_count_exploded, bart_score)

        # === RESET FOR REAL DATA ===
        potential_earnings = 0
        earnings = 0
        balloon_count = 0
        balloon_count_unexploded = 0
        balloon_count_exploded = 0
        bart_score_array = []
        txt_earnings.text = "0"

        # === MIXED BLOCK (30 trials) ===
        logger.log_event("block_start", "block=realdataMixed")
        show_image_wait(stim_instr3)
        core.wait(1.0)
        show_image_wait(stim_green_continue)

        for _ in range(30):
            # Pick type from mixed list
            btype = mixed_types.pop(0)
            if btype == 2:
                color_name = "blue"
                exp_point = blue_points.pop(0)
            elif btype == 3:
                color_name = "yellow"
                exp_point = yellow_points.pop(0)
            else:
                color_name = "orange"
                exp_point = orange_points.pop(0)

            balloon_count += 1
            txt_earnings.text = str(earnings)

            result = run_bart_trial(exp_point, color_name, 1, balloon_count)
            if result is None:
                return

            potential_this = result["potential_earnings_this"]
            potential_earnings += potential_this

            if result["explosion"] == 0:
                earnings += result["earnings_this_balloon"]
                balloon_count_unexploded += 1
                bart_score_array.append(result["times_pumped"])
            else:
                balloon_count_exploded += 1

            txt_earnings.text = str(earnings)
            bart_score = round(sum(bart_score_array) / len(bart_score_array)) if bart_score_array else 0

            rows.append({
                "blockname": "realdataMixed",
                "balloon_color": result["balloon_color"],
                "balloon_count": balloon_count,
                "times_pumped": result["times_pumped"],
                "explosion": result["explosion"],
                "earnings_this_balloon": result["earnings_this_balloon"],
                "total_earnings": earnings,
                "bart_score_so_far": bart_score,
                "avg_rt": result["avg_rt"],
                "potential_earnings_this": potential_this,
                "potential_earnings_total": potential_earnings,
            })

        # === BLOCKED BLUE (20 trials) ===
        for _ in range(20):
            exp_point = blue_points.pop(0)
            balloon_count += 1
            txt_earnings.text = str(earnings)

            result = run_bart_trial(exp_point, "blue", 2, balloon_count)
            if result is None:
                return

            potential_this = result["potential_earnings_this"]
            potential_earnings += potential_this

            if result["explosion"] == 0:
                earnings += result["earnings_this_balloon"]
                balloon_count_unexploded += 1
                bart_score_array.append(result["times_pumped"])
            else:
                balloon_count_exploded += 1

            txt_earnings.text = str(earnings)
            bart_score = round(sum(bart_score_array) / len(bart_score_array)) if bart_score_array else 0

            rows.append({
                "blockname": "realdataBlockedBlue",
                "balloon_color": result["balloon_color"],
                "balloon_count": balloon_count,
                "times_pumped": result["times_pumped"],
                "explosion": result["explosion"],
                "earnings_this_balloon": result["earnings_this_balloon"],
                "total_earnings": earnings,
                "bart_score_so_far": bart_score,
                "avg_rt": result["avg_rt"],
                "potential_earnings_this": potential_this,
                "potential_earnings_total": potential_earnings,
            })

        # === BLOCKED YELLOW (20 trials) ===
        for _ in range(20):
            exp_point = yellow_points.pop(0)
            balloon_count += 1
            txt_earnings.text = str(earnings)

            result = run_bart_trial(exp_point, "yellow", 3, balloon_count)
            if result is None:
                return

            potential_this = result["potential_earnings_this"]
            potential_earnings += potential_this

            if result["explosion"] == 0:
                earnings += result["earnings_this_balloon"]
                balloon_count_unexploded += 1
                bart_score_array.append(result["times_pumped"])
            else:
                balloon_count_exploded += 1

            txt_earnings.text = str(earnings)
            bart_score = round(sum(bart_score_array) / len(bart_score_array)) if bart_score_array else 0

            rows.append({
                "blockname": "realdataBlockedYellow",
                "balloon_color": result["balloon_color"],
                "balloon_count": balloon_count,
                "times_pumped": result["times_pumped"],
                "explosion": result["explosion"],
                "earnings_this_balloon": result["earnings_this_balloon"],
                "total_earnings": earnings,
                "bart_score_so_far": bart_score,
                "avg_rt": result["avg_rt"],
                "potential_earnings_this": potential_this,
                "potential_earnings_total": potential_earnings,
            })

        # === BLOCKED ORANGE (20 trials) ===
        for _ in range(20):
            exp_point = orange_points.pop(0)
            balloon_count += 1
            txt_earnings.text = str(earnings)

            result = run_bart_trial(exp_point, "orange", 4, balloon_count)
            if result is None:
                return

            potential_this = result["potential_earnings_this"]
            potential_earnings += potential_this

            if result["explosion"] == 0:
                earnings += result["earnings_this_balloon"]
                balloon_count_unexploded += 1
                bart_score_array.append(result["times_pumped"])
            else:
                balloon_count_exploded += 1

            txt_earnings.text = str(earnings)
            bart_score = round(sum(bart_score_array) / len(bart_score_array)) if bart_score_array else 0

            rows.append({
                "blockname": "realdataBlockedOrange",
                "balloon_color": result["balloon_color"],
                "balloon_count": balloon_count,
                "times_pumped": result["times_pumped"],
                "explosion": result["explosion"],
                "earnings_this_balloon": result["earnings_this_balloon"],
                "total_earnings": earnings,
                "bart_score_so_far": bart_score,
                "avg_rt": result["avg_rt"],
                "potential_earnings_this": potential_this,
                "potential_earnings_total": potential_earnings,
            })

        # === FEEDBACK 2 ===
        bart_score = round(sum(bart_score_array) / len(bart_score_array)) if bart_score_array else 0
        show_report(potential_earnings, earnings, balloon_count, balloon_count_unexploded, balloon_count_exploded, bart_score)

        logger.log_event("experiment_summary", f"total_earnings={earnings} potential={potential_earnings} exploded={balloon_count_exploded} unexploded={balloon_count_unexploded} bart_score={bart_score}")

    finally:
        win.close()


if __name__ == "__main__":
    main()
