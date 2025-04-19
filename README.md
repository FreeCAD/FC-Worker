<!--
SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

SPDX-License-Identifier: LGPL-2.0-or-later
-->

# FreeCAD Worker

## Running in non-aws mode

### Building
```bash
docker-compose build
```

### Running
```bash
BACKEND_URL=<backend_url> docker-compose up -d
```

## Running in aws mode

### Building

```bash
docker build -t fc-worker .
```

### Running

```bash
docker run -p 9000:8080 -v <path_of_fc_worker>:/fc_worker --name fc_worker fc-worker:latest
```

## Testing

```bash
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -H "Content-Type: application/json" -d '{"command": "health_check"}'
```