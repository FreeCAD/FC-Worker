# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2024 Ondsel <development@ondsel.com>

"""FreeCAD Worker"""
import logging.config
import pathlib

_DIR = pathlib.Path(__file__).parent
LOGGER_CONFIG = _DIR / "logger.config"

logging.config.fileConfig(str(LOGGER_CONFIG))
logger = logging.getLogger(__name__)
logger.info("Imports successful!")


from fc_worker.model_configurer import model_configurer_command
from fc_worker.exporter import export_command

__all__ = [model_configurer, export_command]
