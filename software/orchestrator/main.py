"""HERE Experience Orchestrator — entry point."""
import argparse
import logging
import uvicorn

from config import ConfigManager
from transport import UDPTransport
from animation_engine import AnimationEngine
from admin.routes import create_app, LogHandler


def main():
    parser = argparse.ArgumentParser(description="HERE Experience Orchestrator")
    parser.add_argument("--host", default="0.0.0.0", help="Admin panel bind address")
    parser.add_argument("--port", type=int, default=8000, help="Admin panel port")
    parser.add_argument("--config", default="config.json", help="Config file path")
    args = parser.parse_args()

    # Logging
    log_handler = LogHandler()
    log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(), log_handler],
    )
    logger = logging.getLogger("here")

    # Init
    config = ConfigManager(path=args.config)
    transport = UDPTransport(config.get("targets") or [], config)
    engine = AnimationEngine(config, transport)
    app = create_app(config, engine, transport)

    # Start animation
    engine.start()
    logger.info(f"HERE Experience running — admin at http://{args.host}:{args.port}")

    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    finally:
        engine.stop()
        transport.stop()


if __name__ == "__main__":
    main()
