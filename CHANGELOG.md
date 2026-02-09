<!-- SPDX-License-Identifier: LGPL-2.1-or-later -->
<!-- SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com> -->

# Changelog

## [Unreleased](https://github.com/Ondsel-Development/FC-Worker/tree/main)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.17...main)

## [v1.17](https://github.com/Ondsel-Development/FC-Worker/tree/v1.17) (2024-08-21)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.16...v1.17)

**Logs:**
- [LENS-269](https://ondsel-brad.atlassian.net/browse/LENS-269): Handle exports from STEP file.

## [v1.16](https://github.com/Ondsel-Development/FC-Worker/tree/v1.16) (2024-07-22)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.15...v1.16)

**Logs:**
- [LENS-248](https://ondsel-brad.atlassian.net/browse/LENS-248): Fixed bug in loading multidoc assembly files.

## [v1.15](https://github.com/Ondsel-Development/FC-Worker/tree/v1.15) (2024-07-09)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.14...v1.15)

**Logs:**
- [LENS-221](https://ondsel-brad.atlassian.net/browse/LENS-221): Fixed color issue.
- [LENS-222](https://ondsel-brad.atlassian.net/browse/LENS-222): Avoid showing plane and origin object from object list view.

## [v1.14](https://github.com/Ondsel-Development/FC-Worker/tree/v1.14) (2024-07-03)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.13...v1.14)

**Logs:**
- [LENS-205](https://ondsel-brad.atlassian.net/browse/LENS-205): Implement sub directories, parent directories references
(in same workspace) in multi-doc features

## [v1.13](https://github.com/Ondsel-Development/FC-Worker/tree/v1.13) (2024-06-27)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.12...v1.13)

**Logs:**
- [LENS-202](https://ondsel-brad.atlassian.net/browse/LENS-202): Implemented Multi docs feature (minimal).
- [LENS-203](https://ondsel-brad.atlassian.net/browse/LENS-203): Implemented error codes mechanism; added MissingAssembliesError.
- [LENS-211](https://ondsel-brad.atlassian.net/browse/LENS-211): Only Peer or Enterprise tier user allow to render multi doc.

## [v1.12](https://github.com/Ondsel-Development/FC-Worker/tree/v1.12) (2024-05-02)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.11...v1.12)

**Logs:**
- [LENS-161](https://ondsel-brad.atlassian.net/browse/LENS-161): Update FC Worker to use VarSets instead of PropertyBag.
- [LENS-175](https://ondsel-brad.atlassian.net/browse/LENS-175): FC Worker not updating model with updated attributes.

## [v1.11](https://github.com/Ondsel-Development/FC-Worker/tree/v1.11) (2024-02-26)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.10...v1.11)

**Logs:**
- [#202-Trello](https://trello.com/c/ZqAm5LvF/202-import-fcstd-file-in-threejs-scene): Updated FC worker to support FCStd file on viewer side.

## [v1.10](https://github.com/Ondsel-Development/FC-Worker/tree/v1.10) (2024-01-24)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.9...v1.10)

**Logs:**
- [#192-Trello](https://trello.com/c/DIXA3Xbc/192-fc-worker-skipping-assembly-nested-shape-objects): FC worker skipping assembly nested shape objects.

## [v1.9](https://github.com/Ondsel-Development/FC-Worker/tree/v1.9) (2024-01-07)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.8...v1.9)

**Logs:**
- [#175-Trello](https://trello.com/c/i2ShRwva/175-update-viewer): Export BREP file instead of OBJ for viewer.

## [v1.8](https://github.com/Ondsel-Development/FC-Worker/tree/v1.8) (2023-09-02)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.7...v1.8)

**Logs:**
- [#38-Trello](https://trello.com/c/l9rsndSX/38-rebuild-runner-with-latest-freecad-source-code): Use FreeCAD 0.21 as base image.

## [v1.7](https://github.com/Ondsel-Development/FC-Worker/tree/v1.7) (2023-08-16)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.6...v1.7)

**Logs:**
- [#71](https://github.com/Ondsel-Development/Ondsel-Server/issues/71): Traced success and fails lambda logs

## [v1.6](https://github.com/Ondsel-Development/FC-Worker/tree/v1.6) (2023-08-09)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.5...v1.6)

**Logs:**
- [#49](https://github.com/Ondsel-Development/Ondsel-Server/issues/49): Support Path workbench object

## [v1.5](https://github.com/Ondsel-Development/FC-Worker/tree/v1.5) (2023-08-06)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.4...v1.5)

**Logs:**
- [#49](https://github.com/Ondsel-Development/Ondsel-Server/issues/49): Support 2D objects in OBJ

## [v1.4](https://github.com/Ondsel-Development/FC-Worker/tree/v1.4) (2023-05-15)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.3...v1.4)

**Logs:**
- Implemented export command (supported FCStd, STEP, STL, OBJ formats).
- Supported SharedModel objects for export command.

## [v1.3](https://github.com/Ondsel-Development/FC-Worker/tree/v1.3) (2023-04-18)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/v1.2...v1.3)

**Logs:**
- Used `context.id` as OBJ generated name instead of `filename.stem`.
- Allowed to patch model which is used in shared-models.

## [v1.2](https://github.com/Ondsel-Development/FC-Worker/tree/v1.2) (2023-04-04)
[Full Changelog](https://github.com/Ondsel-Development/FC-Worker/compare/4a5f23ed77d0267c6a950ff6b085cd8c032f8a5e...v1.2)

**Logs:**
- Implemented model configurer.
- Implemented logger.
