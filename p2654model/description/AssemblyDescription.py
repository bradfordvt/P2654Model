#!/usr/bin/env python
"""
    Common class for all AssemblyDescriptions.
    Copyright (C) 2020  Bradford G. Van Treuren

    Common class for all AssemblyDescriptions.  A Description class contains information that is common and useful
    unchanged for all instances of the same Assembly type.  For example, contents from a BSDL file.

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
__date__ = "2020/09/15"
__deprecated__ = False
__email__ = "bradvt59@gmail.com"
__license__ = "GPLv3"
__maintainer__ = "Bradford G. Van Treuren"
__status__ = "Alpha/Experimental"
__version__ = "0.0.1"


import logging
from autologging import traced, logged

from p2654model.error.SchedulerError import SchedulerError

# create logger
module_logger = logging.getLogger('P2654Model.description.AssemblyDescription')


@logged
@traced
class AssemblyDescription:
    def __init__(self, entity_name):
        self.logger = logging.getLogger('P2654Model.description.AssemblyDescription.AssemblyDescription')
        self.logger.info('Creating an instance of AssemblyDescription')
        if entity_name is None:
            raise SchedulerError("entity_name has not bee defined.")
        self.__entity_name = entity_name

    @property
    def entity_name(self):
        return self.__entity_name
