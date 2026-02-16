from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import registry, runs, backtests

app = FastAPI(
    title="ptrl-v02-batch Dashboard API",
    description="Read-only API for viewing models, runs, and backtests",
    version="1.0.0"
)

# CORS configuration
# Allowing all origins for local development convenience
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(registry.router, prefix="/api")
app.include_router(runs.router, prefix="/api")
app.include_router(backtests.router, prefix="/api")

@app.get("/")
def root():
    return {"message": "Welcome to ptrl-v02-batch Dashboard API. Visit /docs for Swagger UI."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
