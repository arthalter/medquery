import argparse

import uvicorn

from medquery.config import get_settings
from medquery.retrieval import InstructionIngestor
from medquery.runtime import open_milvus


def main() -> None:
    parser = argparse.ArgumentParser(prog="medquery")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("serve", "init-db", "ingest"),
        default="serve",
    )
    args = parser.parse_args()
    settings = get_settings()

    if args.command == "init-db":
        milvus = open_milvus(settings)
        milvus.close()
        print(f"Milvus Lite 已初始化：{settings.milvus_uri}")
        return

    if args.command == "ingest":
        milvus = open_milvus(settings)
        try:
            report = InstructionIngestor(settings, milvus).ingest()
        finally:
            milvus.close()
        print(
            "说明书入库完成："
            f"{report.document_count} 份文档，"
            f"{report.chunk_count} 个切片，"
            f"集合 {report.collection_name}"
        )
        return

    uvicorn.run(
        "medquery.main:app",
        host=settings.app_host,
        port=settings.app_port,
        workers=1,
    )


if __name__ == "__main__":
    main()
