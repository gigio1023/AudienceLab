import asyncio

from runner import run_smoke_test


if __name__ == "__main__":
    exit_code, message = asyncio.run(run_smoke_test())
    print(message)
    raise SystemExit(exit_code)
