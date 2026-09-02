import argparse

import uvicorn

from medquery.config import get_settings
from medquery.runtime import open_milvus


def main() -> None:
    parser = argparse.ArgumentParser(prog="medquery")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("serve", "init-db"),
        default="serve",
    )
    args = parser.parse_args()
    settings = get_settings()

    if args.command == "init-db":
        milvus = open_milvus(settings)
        milvus.close()
        print(f"Milvus Lite 已初始化：{settings.milvus_uri}")
        return

    uvicorn.run(
        "medquery.main:app",
        host=settings.app_host,
        port=settings.app_port,
        workers=1,
    )


if __name__ == "__main__":
    main()
