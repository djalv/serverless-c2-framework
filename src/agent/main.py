from . import core


if __name__ == "__main__":
    try:
        print("[INFO] Agent Running...")
        core.run_agent_loop()
    except (KeyboardInterrupt, EOFError):
        print("\n[INFO] Exiting...")
