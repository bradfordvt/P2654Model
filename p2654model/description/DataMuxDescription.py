#!/usr/bin/env python
"""
    Description of information common to all instances of DataMux Assemblies.
    Copyright (C) 2020  Bradford G. Van Treuren

    Description of information common to all instances of DataMux Assemblies.

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


# create logger
module_logger = logging.getLogger('P2654Model.description.DataMuxDescription')


@logged
@traced
class DataMuxDescription(AssemblyDescription):
    def __init__(self, entity_name, addr_length):
        self.logger = logging.getLogger('P2654Model.description.DataMuxDescription.DataMuxDescription')
        self.logger.info('Creating an instance of DataMuxDescription')
        self.__addr_length = addr_length
        self.__addr_register_map = {}
        AssemblyDescription.__init__(self, entity_name)

    def add_dr_register(self, addr_code, dr_register):
        self.__addr_register_map.update({bin(addr_code): dr_register})

    def get_addr_dr(self, code):
        return self.__addr_register_map[bin(code)]

    def get_drs(self):
        return set(self.__addr_register_map.values())

    def get_default_code(self):
        code = list(self.__addr_register_map.keys())[0]
        self.logger.debug("DataMuxDescription.get_default_code(): code = {:s}, self.__ir_length = {:d}, intbv(code, _nrbits=self.__addr_length) = {:s}\n".format(
            str(code), self.__addr_length, str(intbv(str(code)[2:], _nrbits=self.__addr_length))))
        return intbv(str(code)[2:], _nrbits=self.__addr_length)

    def get_first_match(self, uid):
        for k, v in self.__addr_register_map.items():
            if v.uid == uid:
                return intbv(k, _nrbits=self.__addr_length)
        return None
