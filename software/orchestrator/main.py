"""HERE Experience Orchestrator — CLI entry point.

All service construction/wiring lives in bootstrap.py; config schema
migrations in migrations.py. This file only parses args, sets up
logging, and runs the uvicorn server around the service lifecycle.
"""
import argparse
import logging

import uvicorn

from admin.routes import LogHandler
from bootstrap import build_services
from config import ConfigManager


def main():
    parser = argparse.ArgumentParser(description="HERE Experience Orchestrator")
    parser.add_argument("--host", default="0.0.0.0", help="Admin panel bind address")
    parser.add_argument("--port", type=int, default=8000, help="Admin panel port")
    parser.add_argument("--config", default="config.json", help="Config file path")
    args = parser.parse_args()

    # Logging — stdout + the in-memory ring buffer behind /api/logs.
    log_handler = LogHandler()
    log_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S"))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(), log_handler],
    )
    logger = logging.getLogger("here")

    config = ConfigManager(path=args.config)
    services = build_services(config)
    app = services.create_admin_app()

    services.start()
    logger.info(f"HERE Experience running — admin at http://{args.host}:{args.port}")
    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    finally:
        services.stop()


if __name__ == "__main__":
    main()
