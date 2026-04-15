import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

app = FastAPI(title="Signal Craft Backend", version="0.2.0")
