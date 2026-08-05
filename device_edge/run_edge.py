import argparse
from pathlib import Path

from .config import copy_example_config, load_config
from .manual_input_server import run_manual_input_server


def run_manual_ui(config_path: str, host: str, port: int) -> None:
    config = load_config(config_path)
    run_manual_input_server(config, host=host, port=port)


def init_config(target: str) -> None:
    target_path = Path(target)
    if target_path.exists():
        raise FileExistsError(f"Config already exists: {target_path}")
    copy_example_config(target_path)
    print(f"created config: {target_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Industrial chamber device-edge agent.")
    parser.add_argument("command", choices=["init-config", "manual-ui"])
    parser.add_argument("--config", default="device-edge.config.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.command == "init-config":
        init_config(args.config)
    elif args.command == "manual-ui":
        run_manual_ui(args.config, args.host, args.port)


if __name__ == "__main__":
    main()
