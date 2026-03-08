---
description: Backend follows best practices like dependency injection, thin routers with service layer, feature-based architecture, isolated external integrations, centralized config, separate DB layer, async APIs, reusable utilities, validation, caching, rate li
---

Backend Good Practices
Core Practices

1. Dependency Injection
Inject services and dependencies instead of creating them inside functions to improve testability and loose coupling.

@router.post("/projects")
async def create_project(
    project: ProjectCreate,
    service: Annotated[ProjectService, Depends()]
):
    return service.create_project(project)

1. Thin Routers / Controllers
Routers should only handle HTTP requests and responses, not business logic.

2. Service Layer Pattern
Business logic should live inside service classes instead of routers.

3. Feature-Based Architecture
Organize code by features instead of file types.

features/
   authentication/
   dashboard/
   projects/

1. External Integration Isolation
Keep third-party APIs isolated inside a dedicated layer.

externals/
   gemini/
   ollama/

1. Centralized Configuration
All environment variables and settings should live in a single configuration module.

config/settings.py

1. Database Abstraction Layer
Separate database connection and models from business logic.

database/
   models/
   db.py

1. Type Hints Everywhere
Use type annotations to improve readability and tooling support.

2. Reusable Utilities
Shared helpers should be placed inside a global utils directory.

3. Async-First Design
Use asynchronous APIs and database calls to improve performance.

Advanced Backend Practices

1. Repository Pattern
Create repository classes to handle database queries separately from services.

2. Unit of Work Pattern
Manage transactions and database operations within a controlled lifecycle.

3. Caching Layer
Use caching (Redis, memory cache) for frequently accessed data.

4. Rate Limiting
Prevent API abuse by limiting requests per user or IP.

5. Background Workers
Move heavy operations (emails, AI jobs, reports) into background tasks.

6. Structured Logging
Implement centralized and structured logs for monitoring and debugging.

7. Observability
Track system health with metrics, tracing, and monitoring tools.

8. Input Validation & Schema Enforcement
Always validate incoming data using schemas.

9. Error Handling Strategy
Use consistent error responses and centralized exception handlers.

10. Scalability-Friendly Architecture
Design the system so it can evolve into microservices or distributed systems if needed.
