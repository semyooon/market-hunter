import hmac
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException, status

from market_hunter.config import get_settings
from market_hunter.models import Listing, SearchRequest, SearchResponse, Watch, WatchCreate
from market_hunter.service import MarketService
from market_hunter.storage import Storage

settings = get_settings()
storage = Storage(settings.database_path)
service = MarketService(storage)


@asynccontextmanager
async def lifespan(_: FastAPI):
    storage.initialize()
    yield


app = FastAPI(title="Market Hunter", version="0.1.0", lifespan=lifespan)


async def require_token(authorization: Annotated[str | None, Header()] = None) -> None:
    if not settings.api_token:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API token")
    received_token = authorization.removeprefix("Bearer ")
    if not hmac.compare_digest(received_token, settings.api_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API token")


@app.get("/health", dependencies=[Depends(require_token)])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/search", response_model=SearchResponse, dependencies=[Depends(require_token)])
async def search(request: SearchRequest) -> SearchResponse:
    return await service.search(request)


@app.get("/v1/listings/{listing_id}", response_model=Listing, dependencies=[Depends(require_token)])
async def get_listing(listing_id: str) -> Listing:
    listing = storage.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@app.post("/v1/watches", response_model=Watch, status_code=201, dependencies=[Depends(require_token)])
async def create_watch(watch: WatchCreate) -> Watch:
    return storage.create_watch(watch)


@app.get("/v1/watches", response_model=list[Watch], dependencies=[Depends(require_token)])
async def list_watches() -> list[Watch]:
    return storage.list_watches()


def run() -> None:
    uvicorn.run("market_hunter.api:app", host="0.0.0.0", port=8000, reload=False)
