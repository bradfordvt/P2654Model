#!/usr/bin/env python
"""
    Description information common to all instances of a DataRegister Assembly.
    Copyright (C) 2020  Bradford G. Van Treuren

    Description information common to all instances of a DataRegister Assembly.

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
from myhdl import intbv

from p2654model.description.AssemblyDescription import AssemblyDescription
from p2654model.error.SchedulerError import SchedulerError


# create logger
module_logger = logging.getLogger('P2654Model.description.DataRegisterDescription')


@logged
@traced
class DataRegisterDescription(AssemblyDescription):
    def __init__(self, entity_name, reg_length, safe_value):
        self.logger = logging.getLogger('P2654Model.description.DataRegisterDescription.DataRegisterDescription')
        self.logger.info('Creating an instance of DataRegisterDescription')
        if not isinstance(safe_value, intbv):
            raise SchedulerError("safe_value is not of type intbv.")
        if reg_length != len(safe_value):
            raise SchedulerError("reg_length does not match the number of bits in the safe_value.")
        self.__reg_length = reg_length  # the length of the Test Data Register of the given leaf segment.
        self.__safe_value = safe_value  # reference to the safe value or default value to use
        AssemblyDescription.__init__(self, entity_name)

    @property
    def reg_length(self):
        return self.__reg_length

    @property
    def safe_value(self):
        return self.__safe_value
