"""
run_experiment.py
Standalone launcher for the PsychoPy experiment battery.
Records all data (peripheral inputs + experiment events) into a single unified CSV.
Run from terminal:  python run_experiment.py
"""
import numpy_compat  # noqa: F401 - must be first to patch NumPy for PsychoPy
import time

# --- Now safe to import PsychoPy-based modules ---
import flanker
import go_nogo
import twoback
import stroop
import sart
import bart

from unified_logger import logger

# --- Test sequence names for display ---
TEST_NAMES = {
    "flanker": "Flanker",
    "go_nogo": "Go/No-Go",
    "twoback": "2-Back",
    "stroop": "Stroop",
    "sart": "SART",
    "bart": "BART",
}


def show_break_screen(finished_test=None, next_test=None):
    """
    Show a waiting screen between tests using a simple PsychoPy window.
    Recording continues during this break.
    The participant presses SPACE to proceed.
    
    Uses input() as fallback if PsychoPy window fails.
    """
    logger.log_event("break_start",
                     f"finished={finished_test or ''} next={next_test or ''}")

    lines = []
    if finished_test:
        lines.append(f"Az előző feladat ({TEST_NAMES.get(finished_test, finished_test)}) befejeződött.")
        lines.append("")
    if next_test:
        lines.append(f"A következő feladat: {TEST_NAMES.get(next_test, next_test)}")
        lines.append("")
    lines.append("Tartson egy rövid szünetet.")
    lines.append("Ha készen áll, nyomja meg a SPACE billentyűt a folytatáshoz.")

    # Print to console as well (visible to experimenter)
    print("\n" + "=" * 50)
    for line in lines:
        if line:
            print(f"  {line}")
    print("=" * 50)

    # Give pyglet time to fully release previous context
    time.sleep(1.5)

    try:
        from psychopy import visual, core, event

        win = visual.Window(fullscr=True, color="black", units="pix")
        core.wait(0.2)

        msg_text = "\n".join(lines)
        msg = visual.TextStim(win, text=msg_text, color="white", font="Arial",
                              height=30, pos=(0, 0), wrapWidth=1000, alignText="center")
        msg.draw()
        win.flip()

        # Wait for SPACE key (more natural for participants)
        event.clearEvents()
        waiting = True
        while waiting:
            keys = event.getKeys(keyList=["space", "escape"])
            if keys:
                if "escape" in keys:
                    win.close()
                    time.sleep(0.5)
                    logger.log_event("break_end", f"next={next_test or ''} aborted=True")
                    return False
                waiting = False
            core.wait(0.01)

        win.close()
        time.sleep(1.5)

    except Exception as e:
        # Fallback: use console input if PsychoPy window fails
        print(f"  [Window error: {e}]")
        print("  >> Nyomjon ENTER-t a konzolban a folytatáshoz...")
        input()

    logger.log_event("break_end", f"next={next_test or ''}")
    return True


def run_all():
    print("=" * 50)
    print("  Kísérleti feladatok:")
    print("=" * 50)

    # Get participant ID
    participant_id = input("Adja meg a résztvevő azonosítóját: ").strip()
    if not participant_id:
        participant_id = "participant"

    print("=" * 50)
    print("  1) Flanker feladat")
    print("  2) Go/No-Go feladat")
    print("  3) 2-Back feladat")
    print("  4) Stroop feladat")
    print("  5) SART feladat")
    print("  6) BART feladat")
    print("  A) Minden feladat futtatása sorrendben")
    print("  Q) Kilépés")
    print("=" * 50)

    choice = input("Válasszon (1/2/3/4/5/6/A/Q): ").strip().lower()

    if choice == "q":
        print("Kilépés.")
        return

    # Start unified logger
    logger.start(participant_id)

    try:
        if choice == "1":
            print("\n>>> Flanker feladat indítása...")
            logger.set_active_test("flanker")
            flanker.main()
            logger.set_active_test("")
            print(">>> Flanker feladat befejezve.\n")
        elif choice == "2":
            print("\n>>> Go/No-Go feladat indítása...")
            logger.set_active_test("go_nogo")
            go_nogo.main()
            logger.set_active_test("")
            print(">>> Go/No-Go feladat befejezve.\n")
        elif choice == "3":
            print("\n>>> 2-Back feladat indítása...")
            logger.set_active_test("twoback")
            twoback.main()
            logger.set_active_test("")
            print(">>> 2-Back feladat befejezve.\n")
        elif choice == "4":
            print("\n>>> Stroop feladat indítása...")
            logger.set_active_test("stroop")
            stroop.main()
            logger.set_active_test("")
            print(">>> Stroop feladat befejezve.\n")
        elif choice == "5":
            print("\n>>> SART feladat indítása...")
            logger.set_active_test("sart")
            sart.main()
            logger.set_active_test("")
            print(">>> SART feladat befejezve.\n")
        elif choice == "6":
            print("\n>>> BART feladat indítása...")
            logger.set_active_test("bart")
            bart.main()
            logger.set_active_test("")
            print(">>> BART feladat befejezve.\n")
        elif choice == "a":
            print("\n>>> Flanker feladat indítása...")
            logger.set_active_test("flanker")
            flanker.main()
            logger.set_active_test("")
            print(">>> Flanker feladat befejezve.\n")

            if not show_break_screen("flanker", "go_nogo"):
                return

            print(">>> Go/No-Go feladat indítása...")
            logger.set_active_test("go_nogo")
            go_nogo.main()
            logger.set_active_test("")
            print(">>> Go/No-Go feladat befejezve.\n")

            if not show_break_screen("go_nogo", "twoback"):
                return

            print(">>> 2-Back feladat indítása...")
            logger.set_active_test("twoback")
            twoback.main()
            logger.set_active_test("")
            print(">>> 2-Back feladat befejezve.\n")

            if not show_break_screen("twoback", "stroop"):
                return

            print(">>> Stroop feladat indítása...")
            logger.set_active_test("stroop")
            stroop.main()
            logger.set_active_test("")
            print(">>> Stroop feladat befejezve.\n")

            if not show_break_screen("stroop", "sart"):
                return

            print(">>> SART feladat indítása...")
            logger.set_active_test("sart")
            sart.main()
            logger.set_active_test("")
            print(">>> SART feladat befejezve.\n")

            if not show_break_screen("sart", "bart"):
                return

            print(">>> BART feladat indítása...")
            logger.set_active_test("bart")
            bart.main()
            logger.set_active_test("")
            print(">>> BART feladat befejezve.\n")
        else:
            print(f"Ismeretlen választás: {choice}")
    finally:
        # Always stop the logger
        logger.stop()
        print(f"\n>>> Minden adat elmentve ide: {logger.log_path}")


if __name__ == "__main__":
    run_all()
