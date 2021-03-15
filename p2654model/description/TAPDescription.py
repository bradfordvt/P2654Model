#!/usr/bin/env python
"""
    Description information common to all instances of the TAP Assembly.
    Copyright (C) 2020  Bradford G. Van Treuren

    Description information common to all instances of the TAP Assembly.

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

from p2654model.description.AssemblyDescription import AssemblyDescription


# create logger
module_logger = logging.getLogger('P2654Model.description.TAPDescription')


@logged
@traced
class TAPDescription(AssemblyDescription):
    def __init__(self, entity_name, ir_length):
        self.logger = logging.getLogger('P2654Model.description.TAPDescription.TAPDescription')
        self.logger.info('Creating an instance of TAPDescription')
        self.__ir_length = ir_length
        self.__ir_str_intbv_map = {}
        self.__instruction_name_map = {}
        self.__instruction_register_map = {}
        AssemblyDescription.__init__(self, entity_name)

    def add_dr_register(self, ir_code, ir_name, dr_register):
        self.__instruction_register_map.update({bin(ir_code): dr_register})
        self.__instruction_name_map.update({bin(ir_code): ir_name})

    def get_ir_name(self, code):
        return self.__instruction_name_map[bin(code)]

    def get_ir_dr(self, code):
        return self.__instruction_register_map[bin(code)]

    def get_drs(self):
        return set(self.__instruction_register_map.values())
