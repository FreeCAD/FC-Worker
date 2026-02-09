# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

import Part

from ..freecad_libs.PathGeom import wireForPath


def get_path_main_object(doc) -> list:
    objs = []
    for obj in doc.Objects:
        if (
            getattr(obj, "TypeId", None) == "Path::FeaturePython"
            and getattr(obj, "Operations", None)
            and hasattr(obj, "Model")
        ):
            objs.append(obj)
    return objs


def create_path_shape_objects(path_main_objs: list) -> None:

    for path_obj in path_main_objs:

        if getattr(path_obj.Model, "Group", None):
            for obj in path_obj.Model.Group:
                if getattr(obj, "Shape", None):
                    Part.show(obj.Shape)

        if getattr(path_obj.Operations, "Group", None):
            for obj in path_obj.Operations.OutList:
                if hasattr(obj, "Path"):
                    wire, _ = wireForPath(obj.Path)
                    Part.show(wire)
