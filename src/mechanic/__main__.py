"""Entry point and composition root: `python -m mechanic`."""

import logging
import sys

from mechanic.config import Settings


logger = logging.getLogger("mechanic")


def main() -> int:
    # Built once here and passed down; nothing reads settings through a global.
    # An invalid value raises pydantic's ValidationError, no fallback.
    settings = Settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    logger.info("mechanic started")
    return 0


if __name__ == "__main__":
    sys.exit(main())
