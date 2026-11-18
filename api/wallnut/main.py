import os

import psycopg
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import (
    ardi_help, ardy, ardy_nuts, campus, coin_payments, coin_shop, community, economy,
    events, evidence, feed, grades, identity, pairing, pilot_metrics, profiles, social, tournaments, workshop_agenda,
    workshops,
)
from .database import connect, migration_files, pending_migrations


def create_app(verify_identity=None):
    api = FastAPI(title="Wallnut", version="0.17.0")
    api.state.verify_identity = verify_identity if verify_identity is not None else identity.configured_verifier()
    allowed_origins = [
        origin.strip() for origin in os.environ.get("WEB_ORIGINS", "").split(",")
        if origin.strip()
    ]
    if allowed_origins:
        api.add_middleware(
            CORSMiddleware,
            allow_origins=allowed_origins,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type"],
        )
    api.include_router(identity.router, prefix="/v1")
    api.include_router(campus.router, prefix="/v1")
    api.include_router(community.router, prefix="/v1")
    api.include_router(feed.router, prefix="/v1")
    api.include_router(workshops.router, prefix="/v1")
    api.include_router(workshop_agenda.router, prefix="/v1")
    api.include_router(evidence.router, prefix="/v1")
    api.include_router(economy.router, prefix="/v1")
    api.include_router(grades.router, prefix="/v1")
    api.include_router(ardy.router, prefix="/v1")
    api.include_router(ardy_nuts.router, prefix="/v1")
    api.include_router(coin_payments.router, prefix="/v1")
    api.include_router(coin_shop.router, prefix="/v1")
    api.include_router(events.router, prefix="/v1")
    api.include_router(profiles.router, prefix="/v1")
    api.include_router(social.router, prefix="/v1")
    api.include_router(tournaments.router, prefix="/v1")
    api.include_router(pairing.router, prefix="/v1")
    api.include_router(ardi_help.router, prefix="/v1")
    api.include_router(pilot_metrics.router, prefix="/v1")

    @api.get("/health")
    def health():
        return {"status": "ok"}

    @api.get("/v1/ready")
    def readiness():
        try:
            with connect() as db:
                ready = bool(migration_files()) and not pending_migrations(db)
        except (KeyError, psycopg.Error):
            ready = False
        return JSONResponse(
            {"status": "ready" if ready else "not_ready"},
            status_code=200 if ready else 503,
            headers={"Cache-Control": "no-store"},
        )

    if web_dist := os.environ.get("WEB_DIST_DIR"):
        api.mount("/", StaticFiles(directory=web_dist, html=True), name="web")

    return api


app = create_app()
