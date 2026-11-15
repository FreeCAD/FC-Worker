<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com> -->
<!-- SPDX-FileCopyrightText: 2026 Amritpal Singh <amrit3701@gmail.com> -->

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

## KiCad 3D model library

Converting KiCad boards needs the KiCad 3D model library (about 5 GB). `scripts/fetch-kicad-3dmodels.sh` downloads it into the `kicad_3dmodels` volume. The `kicad-3dmodels` init service runs the script on `docker-compose up`, and the worker waits for it.

| Variable | Description | Default |
|----------|-------------|---------|
| `KICAD_ENABLED` | Enable KiCad support. `false` skips the download | `true` |
| `KICAD_3D_REF` | `kicad-packages3D` release to download | `10.0.7` |
| `KICAD_3D_REPO` | Repository to download from | Official `kicad-packages3D` repository |
| `KICAD_3DMODELS_VOLUME` | Volume or host directory mounted into the worker. Point it at an existing library directory to skip the download | `kicad_3dmodels` |
| `KICAD_3D_LIBRARIES` | Mount path inside the worker | `/usr/share/kicad/3dmodels` |

The FreeCAD CLI image must include the CAM module.

## Testing

```bash
curl -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" -H "Content-Type: application/json" -d '{"command": "health_check"}'
```
