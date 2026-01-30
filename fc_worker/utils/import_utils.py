# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

import pathlib

import FreeCAD


def open_doc_in_freecad(input_file_path: str):
    input_file_path = pathlib.Path(input_file_path)
    suffix = input_file_path.suffix.upper()
    if suffix == ".FCSTD":
        doc = FreeCAD.openDocument(str(input_file_path))
        FreeCAD.setActiveDocument(doc.Name)
    elif suffix == ".OBJ":
        import Mesh
        Mesh.open(str(input_file_path))
    elif suffix == ".STEP" or suffix == ".STP":
        import Import
        Import.open(str(input_file_path))
    else:
        raise ValueError(f"Given input file format ({input_file_path}) importer not implemented yet.")

    return FreeCAD.activeDocument()
