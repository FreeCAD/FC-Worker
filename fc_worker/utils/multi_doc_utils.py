# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

import os
import xml.etree.ElementTree as ET


class UnsupportedException(Exception):
    """An exception that indicates that an action is unsupported"""

    pass


def find_path_link(link):
    """Find the path of a (missing) link

    Normally you can find the path of a link by doing
    link.LinkedObject.FileName but in case of a missing link, the property
    LinkedObject will be empty.  Therefore, we parse the contents of document
    object to find the path.  Since link.Content is a list of XML elements, we
    need to wrap these tags inside some root XML element.
    """

    root = ET.fromstring("<root>" + link.Content + "</root>")
    props = root.findall(".//Property[@name='LinkedObject']/XLink")
    if len(props) == 1:
        file_path = props[0].get("file")
        if file_path:
            return file_path
        else:
            return None
    else:
        return None


def find_missing_links(doc):
    """Return a list of filenames that are not available for links.

    CopyOnChange links are not supported."""

    missing_links = set()

    for link in doc.findObjects("App::Link"):
        if link.LinkCopyOnChange != "Disabled":
            raise UnsupportedException("CopyOnChange links are not supported")

        linked_path = find_path_link(link)
        if linked_path and not os.path.exists(linked_path):
            missing_links.add(linked_path)

    return list(missing_links)
