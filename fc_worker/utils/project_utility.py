# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2023 Werner Mayer
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

__title__="Document handling module"
__author__ = "Werner Mayer"
__url__ = "https://www.freecad.org"
__doc__ = "Tools for extracting or creating project files"


import os
import xml.sax
import xml.sax.handler
import xml.sax.xmlreader
import zipfile
import logging


logger = logging.getLogger(__name__)


# SAX handler to parse the Document.xml
class DocumentHandler(xml.sax.handler.ContentHandler):
    """ Parse content of Document.xml or GuiDocument.xml """
    def __init__(self, dirname):
        """ Init parser """
        super().__init__()
        self.files = []
        self.dirname = dirname

    def startElement(self, name, attrs):
        item = attrs.get("file")
        if item is not None:
            self.files.append(os.path.join(self.dirname, str(item)))

    def characters(self, content):
        return

    def endElement(self, name):
        return

def extractDocument(filename, outpath):
    """ Extract files from project archive """
    zfile = zipfile.ZipFile(filename)
    files = zfile.namelist()

    for i in files:
        data = zfile.read(i)
        dirs = i.split("/")
        if len(dirs) > 1:
            dirs.pop()
            curpath = outpath
            for j in dirs:
                curpath = curpath + "/" + j
                os.mkdir(curpath)
        output = open(outpath + "/"+i, 'wb')
        output.write(data)
        output.close()

def createDocument(filename, outpath):
    """ Create project archive """
    files = getFilesList(filename)
    dirname = os.path.dirname(filename)
    guixml = os.path.join(dirname, "GuiDocument.xml")
    if os.path.exists(guixml):
        files.extend(getFilesList(guixml))
    brep_folder = os.path.join(dirname, "breps")
    for i in os.listdir(brep_folder):
        files.append(os.path.join(brep_folder, i))

    compress = zipfile.ZipFile(outpath, 'w', zipfile.ZIP_DEFLATED)
    for i in files:
        dirs = os.path.split(i)
        try:
            compress.write(i, dirs[-1], zipfile.ZIP_DEFLATED)
        except Exception as ex:
            logger.warning(str(ex))
            continue
    compress.close()

def getFilesList(filename):
    """ Determine list of files referenced in a Document.xml or GuiDocument.xml """
    dirname = os.path.dirname(filename)
    handler = DocumentHandler(dirname)
    parser = xml.sax.make_parser()
    parser.setContentHandler(handler)
    parser.parse(filename)

    files = []
    files.append(filename)
    files.extend(iter(handler.files))
    return files
