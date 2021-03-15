#!/usr/bin/env python
"""
    Description information common to all instances of a PortalRegister Assembly.
    Copyright (C) 2020  Bradford G. Van Treuren

    Description information common to all instances of a PortalRegister Assembly.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

__authors__ = ["Bradford G. Van Treuren"]
__contact__ = "bradvt59@gmail.com"
__copyright__ = "Copyright 2020, VT Enterprises Consulting Services"
__credits__ = ["Bradford G. Van Treuren"]
__date__ = "2020/09/30"
__deprecated__ = False
__email__ = "bradvt59@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Bradford G. Van Treuren"
__status__ = "Alpha/Experimental"
__version__ = "0.0.1"


import logging
from autologging import traced, logged

from p2654model.description.DataRegisterDescription import DataRegisterDescription


# create logger
module_logger = logging.getLogger('P2654Model.description.PortalRegisterDescription')


@logged
@traced
class PortalRegisterDescription(DataRegisterDescription):
    def __init__(self, entity_name, reg_length, safe_value):
        self.logger = logging.getLogger('P2654Model.description.PortalRegisterDescription.PortalRegisterDescription')
        self.logger.info('Creating an instance of PortalRegisterDescription')
        DataRegisterDescription.__init__(self, entity_name, reg_length, safe_value)
