import asyncio
from Channels.BondingChannel import worker

if __name__ == "__main__":
    asyncio.run(worker(interval=300))
