<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com> -->

# FreeCAD Worker

## Running in non-aws mode

```bash
# Build the docker image
docker-compose build

# Run the docker container
BACKEND_URL=<backend_url> docker-compose up -d

# For development
docker-compose -f docker-compose.dev.yml build
BACKEND_URL=<backend_url> docker-compose -f docker-compose.dev.yml up -d
```

## Running in aws mode

### Building

```bash
# Build the docker image
docker build -t fc-worker .

# Run the docker container
docker run -p 9000:8080 -v <path_of_fc_worker>:/fc_worker --name fc_worker fc-worker:latest
```

## Testing

```bash
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -H "Content-Type: application/json" -d '{"command": "health_check"}'
```