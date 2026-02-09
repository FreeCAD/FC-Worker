# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

import logging
import xml.etree.ElementTree as ET
from enum import Enum
from typing import List

import FreeCAD


logger = logging.getLogger(__name__)


EXCLUDE_PROPERTIES = ("CustomPropertyGroups", "ExpressionEngine", "Label", "Label2", "Proxy", "Visibility")


class PropertyType(Enum):
    STRING = "string"
    NUMBER = "number"
    SELECT = "select"
    BOOL = "bool"
    FLOAT = "float"
    LENGTH = "length"
    PERCENT = "percent"
    ANGLE = "angle"


PROPERTY_TYPE_MAPPING = {
    "App::PropertyString": PropertyType.STRING.value,
    "App::PropertyEnumeration": PropertyType.SELECT.value,
    "App::PropertyAngle": PropertyType.ANGLE.value,
    "App::PropertyBool": PropertyType.BOOL.value,
    "App::PropertyDistance": PropertyType.NUMBER.value,
    "App::PropertyFloat": PropertyType.FLOAT.value,
    "App::PropertyInteger": PropertyType.NUMBER.value,
    "App::PropertyLength": PropertyType.LENGTH.value,
    "App::PropertyPercent": PropertyType.PERCENT.value,
}


def get_property_data(obj, exclude_prps=EXCLUDE_PROPERTIES):
    data = dict()
    for prp in obj.PropertiesList:
        if prp in exclude_prps:
            continue
        prp_id = obj.getTypeIdOfProperty(prp)
        if prp_id not in PROPERTY_TYPE_MAPPING:
            logger.warning(f"{prp_id} not implemented yet.")
            continue
        value = obj.getPropertyByName(prp)
        unit = ""
        if isinstance(value, FreeCAD.Units.Quantity):
            _, unit = str(value).split(" ")
            value = value.Value

        if PROPERTY_TYPE_MAPPING[prp_id] == PropertyType.SELECT.value:
            data[prp] = {
                "type": PROPERTY_TYPE_MAPPING[prp_id],
                "value": value,
                "unit": unit,
                "items": obj.getEnumerationsOfProperty(prp)
            }
        else:
            data[prp] = {
                "type": PROPERTY_TYPE_MAPPING[prp_id],
                "value": value,
                "unit": unit,
            }
    return data


def get_property_bag_obj(doc: FreeCAD.ActiveDocument):
    property_bag = "PropertyBag"
    return doc.getObject(property_bag)


def get_app_varset_obj(doc: FreeCAD.ActiveDocument):
    property_bag = "VarSet"
    return doc.getObject(property_bag)


def get_shape_objs(doc: FreeCAD.ActiveDocument, objects_to_skip=None) -> list:
    """Return all objects which create shape in the document."""

    def _get_shape(obj) -> list:
        objs = []
        if objects_to_skip and obj in objects_to_skip:
            return objs
        if (
            hasattr(obj, "Shape")
            and not obj.Shape.isNull()
            and not obj.isDerivedFrom("App::LinkGroup")
        ):
            objs.append(obj)
        elif obj.OutList:
            for child_obj in obj.OutList:
                objs += _get_shape(child_obj)
        return objs

    shape_objs = []
    for root_obj in doc.RootObjects:
        shape_objs += _get_shape(root_obj)
    return shape_objs


def update_model(prp_bag, initial_attributes, new_attributes):

    for key, items in new_attributes.items():
        if items["value"] != initial_attributes[key]["value"]:
            logger.info(f"{key} is changed!!")

            _value = getattr(prp_bag, key)
            if hasattr(_value, "Value"):
                _type = type(_value.Value)
            else:
                _type = type(_value)
            setattr(prp_bag, key, _type(items["value"]))
            FreeCAD.ActiveDocument.recompute()


def get_visible_objects(xml_gui_root: ET.ElementTree) -> List[str]:
    return [view_provider.get('name') for view_provider in xml_gui_root.iter('ViewProvider') if view_provider.find("Properties/Property[@name='Visibility']/Bool[@value='true']") is not None]


def is_obj_have_part_file(obj_name: str, xml_root: ET.ElementTree) -> bool:
    for obj in xml_root.findall(".//Object[@name='{}']".format(obj_name)):
        for prop in obj.findall(".//Property[@name='Shape']"):
            part_file = prop.find("Part")
            if part_file is not None and 'file' in part_file.attrib:
                return True
    return False
