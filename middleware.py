from fastapi.middleware.cors import CORSMiddleware

def add_middleware(app):
    origins = [
    "http://127.0.0.1:5174/home",  # Example: Your React app's URL
    "http://127.0.0.1:5174",  # Example: Your React app's URL
    "http://127.0.0.1:5174/login",  # Example: Your React app's URL
    # ... other origins
]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins (INSECURE FOR PRODUCTION)
        allow_credentials=True, # Only if you need credentials
        allow_methods=["*"],    # Allow all methods
        allow_headers=["*"],    # Allow all headers
    )