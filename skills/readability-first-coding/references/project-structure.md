# Project Structure

Directory structure separates responsibilities. It does **not** require common parent classes, interfaces, converters, or utility modules.

## Java Backend

```
com.example.project
├── controller
├── dto
│   ├── request
│   └── response
├── service
├── mapper
├── entity
├── config
└── exception
```

### controller

Receives parameters, calls Service, returns results.

### dto/request

Request body data for incoming API calls.

### dto/response

Response body data returned to clients.

### service

Business logic goes here directly. Do **not** create `Service` interface + `ServiceImpl` by default. Only split when:

- Multiple implementations actually exist
- The existing project convention requires it
- The user explicitly requests it

### mapper

Database access layer.

### entity

Database table mappings.

## Python Backend

```
src/app
├── controller
├── dto
│   ├── request
│   └── response
├── service
├── repository
├── entity
├── config
└── main.py
```

### main.py

Application entry point. Creates and wires the application, starts the server.

### repository

Data access layer (equivalent to Java's `mapper`). Database queries and persistence logic.

Same principles as Java — the directory structure organizes code by its role in the application (controller, service, repository, entity), not by abstract design-layer patterns (interface/impl, domain/infrastructure, strategy/factory).
