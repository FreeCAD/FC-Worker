# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 Amritpal Singh <amrit3701@gmail.com>

import os
import re
import sys
import shutil
import struct
import zipfile
import logging
import xml.sax.saxutils
import FreeCAD
import Part
import DraftGeomUtils
import DraftVecUtils

logger = logging.getLogger(__name__)
logging.getLogger("fcad_parser.sexp_parser.sexp_parser").setLevel(logging.WARNING)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "third_party", "kicadStepUpMod"))
DraftGeomUtils.precision = DraftVecUtils.precision = lambda: 6

_DEFAULT_PART_COLOR = (0.5, 0.5, 0.5)
_BOARD_GREEN = (18 / 255, 76 / 255, 31 / 255)
_AMBIENT = 0x333333FF
_SPECULAR = 0x00000000
_EMISSIVE = 0x00000000
_SHININESS = 0.2


def _default_3d_model_dir():
    return os.environ.get("KICAD_3D_LIBRARIES") or os.environ.get(
        "KICAD_3DMODEL_DIR", "/usr/share/kicad/3dmodels"
    )


def _pack_rgba(rgb):
    # App::Color packed value: 0xRRGGBBAA
    r, g, b = (max(0, min(255, int(round(c * 255)))) for c in rgb[:3])
    return (r << 24) | (g << 16) | (b << 8) | 0xFF


def _material_list(face_colors):
    # App::PropertyMaterialList file: count, then per face four packed colors
    # + shininess + transparency, then three empty strings per face
    chunks = [struct.pack("<I", len(face_colors))]
    for rgb in face_colors:
        chunks.append(struct.pack("<IIIIff", _AMBIENT, _pack_rgba(rgb), _SPECULAR, _EMISSIVE, _SHININESS, 0.0))
    chunks.append(struct.pack("<I", 0) * (3 * len(face_colors)))
    return b"".join(chunks)


def _build_gui_document_xml(entries):
    lines = [
        '<?xml version="1.0" encoding="UTF-8" standalone="no" ?>',
        '<Document SchemaVersion="1">',
    ]
    for name, appearance_file in entries:
        safe = xml.sax.saxutils.escape(name, {'"': "&quot;"})
        lines.append(
            f'  <ViewProvider name="{safe}">\n'
            '    <Properties Count="2">\n'
            '      <Property name="ShapeAppearance" type="App::PropertyMaterialList" status="1">\n'
            f'        <MaterialList file="{appearance_file}" version="3"/>\n'
            '      </Property>\n'
            '      <Property name="Visibility" type="App::PropertyBool" status="1">\n'
            '        <Bool value="true"/>\n'
            '      </Property>\n'
            '    </Properties>\n'
            '  </ViewProvider>'
        )
    lines.append("</Document>\n")
    return "\n".join(lines)


def _inject_gui_document(fcstd_path, items):
    entries = []
    appearance_files = []
    for index, (name, face_colors) in enumerate(items):
        appearance_file = "ShapeAppearance" if index == 0 else f"ShapeAppearance{index}"
        entries.append((name, appearance_file))
        appearance_files.append((appearance_file, _material_list(face_colors)))
    temporary = fcstd_path + ".gui.zip"
    with zipfile.ZipFile(fcstd_path, "r") as source, zipfile.ZipFile(temporary, "w") as dest:
        for info in source.infolist():
            if info.filename == "GuiDocument.xml":
                continue
            dest.writestr(info, source.read(info.filename))
        dest.writestr("GuiDocument.xml", _build_gui_document_xml(entries))
        for appearance_file, data in appearance_files:
            dest.writestr(appearance_file, data)
    os.replace(temporary, fcstd_path)


def _safe_name(text):
    cleaned = re.sub(r"\W", "_", text).strip("_") or "obj"
    if cleaned[0].isdigit():
        cleaned = "n_" + cleaned
    return cleaned[:48]


def _as_shape(obj, part_module):
    if obj is None:
        return None
    if isinstance(obj, part_module.Shape):
        return obj if not obj.isNull() and obj.Faces else None
    shape = getattr(obj, "Shape", None)
    if shape is not None and not shape.isNull() and shape.Faces:
        return shape
    return None


def convert_kicad_pcb(board_path, output_path, part_path=None):
    import kicad_parser

    part_path = part_path or _default_3d_model_dir()
    fcad = kicad_parser.KicadFcad(board_path, add_feature=False, part_path=part_path)
    board_shape = _as_shape(fcad.makeBoard(shape_type="solid"), Part)
    if board_shape is None:
        raise RuntimeError(f"KiCad board has no Edge.Cuts outline: {board_path}")

    # one object per placed model; per-face colors only when they cover every face
    placed = []
    for group in fcad.loadAllParts(combo=False) or []:
        if not isinstance(group, dict):
            continue
        for label, data in group.items():
            pos = data["pos"]
            ref = label.split("#", 1)[-1] if "#" in label else "?"
            for model in data["models"]:
                shape = model["shape"].copy()
                shape.Placement = pos.multiply(shape.Placement)
                colors = model.get("color")
                if not colors or len(colors) != len(shape.Faces):
                    colors = [_DEFAULT_PART_COLOR]
                placed.append((f"{ref}_{model['name']}", shape, colors))

    named = [("board", board_shape, [_BOARD_GREEN])]
    label_counts = {}
    multi_color = 0
    for label, shape, colors in placed:
        label_counts[label] = label_counts.get(label, 0) + 1
        if label_counts[label] > 1:
            label = f"{label}_{label_counts[label]}"
        if len(colors) > 1:
            multi_color += 1
        named.append((label, shape, colors))

    doc = FreeCAD.ActiveDocument or FreeCAD.newDocument("kicad_import")
    for obj in list(doc.Objects):
        try:
            doc.removeObject(obj.Name)
        except Exception:
            pass

    gui_items = []
    for label, shape, colors in named:
        feature = doc.addObject("Part::Feature", _safe_name(label))
        feature.Label = label
        feature.Shape = shape
        gui_items.append((feature.Name, colors))
    doc.recompute()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    doc.saveAs(output_path)
    FreeCAD.closeDocument(doc.Name)
    _inject_gui_document(output_path, gui_items)

    missing = getattr(fcad, "missing_models", set())
    stats = {
        "objects": len(gui_items),
        "componentsPlaced": len(label_counts),
        "multiColorModels": multi_color,
        "missingModels": len(missing),
        "output": output_path,
    }
    logger.info("KiCad conversion stats: %s", stats)
    if missing:
        logger.warning("KiCad 3D models missing (%d), e.g. %s", len(missing), sorted(m.strip('"') for m in missing)[:3])
    embed_dir = getattr(fcad, "_embed_dir", None)
    if embed_dir:
        shutil.rmtree(embed_dir, ignore_errors=True)
    return stats
