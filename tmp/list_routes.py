from backend.gateway import app
for route in app.routes:
    if hasattr(route, "path"):
        methods = getattr(route, "methods", "GET")
        print(f"{methods} {route.path}")
