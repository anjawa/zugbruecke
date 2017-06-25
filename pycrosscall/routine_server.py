# -*- coding: utf-8 -*-

"""

PYCROSSCALL
Calling routines in Windows DLLs from Python scripts running on unixlike systems
https://github.com/s-m-e/pycrosscall

	pycrosscall/dll_server.py: Classes relevant for managing routines in DLLs

	Required to run on platform / side: [WINE]

	Copyright (C) 2017 Sebastian M. Ernst <ernst@pleiszenburg.de>

<LICENSE_BLOCK>
The contents of this file are subject to the GNU Lesser General Public License
Version 2.1 ("LGPL" or "License"). You may not use this file except in
compliance with the License. You may obtain a copy of the License at
https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt
https://github.com/s-m-e/pycrosscall/blob/master/LICENSE

Software distributed under the License is distributed on an "AS IS" basis,
WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License for the
specific language governing rights and limitations under the License.
</LICENSE_BLOCK>

"""


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# IMPORT
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

import ctypes
from pprint import pformat as pf


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# DLL SERVER CLASS
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

class routine_server_class():


	def __init__(self, parent_dll, routine_name):

		# Store handle on parent dll
		self.dll = parent_dll

		# Store pointer to pycrosscall session
		self.session = self.dll.session

		# Get handle on log
		self.log = self.dll.log

		# Store my own name
		self.name = routine_name

		# Prepare dict for custom datatypes (structs)
		self.datatypes = {}

		# Log status
		self.log.out('[routine-server] Attaching to routine "%s" in DLL file "%s" ...' % (self.name, self.dll.name))

		try:

			# Get handler on routine in dll
			self.handler = getattr(
				self.dll.handler, routine_name
				)

			# Log status
			self.log.out('[routine-server] ... done.' %)

		except:

			# Log status
			self.log.out('[routine-server] ... failed!' %)

			# Push traceback to log
			self.log.err(traceback.format_exc())

			raise # TODO


	def register_argtype_and_restype(self, argtypes, restype):

		# Log status
		self.log.out('[routine-server] Set argument and return value types for "%s" ...' % self.name)

		# Parse & store argtype dicts into argtypes
		self.argtypes = argtypes
		self.handler.argtypes = [self.__unpack_type_dict__(arg_dict) for arg_dict in self.argtypes]

		# Parse & store return value type
		self.restype = restype
		self.handler.restype = self.__unpack_type_dict__(self.restype)

		# Log status
		self.log.out('[routine-server] ... argtypes: %s ...' % pf(self.handler.argtypes))
		self.log.out('[routine-server] ... restype: %s ...' % pf(self.handler.restype))

		# Log status
		self.log.out('[routine-server] ... done.')

		return True # Success


	def __unpack_type_dict__(self, datatype_dict):

		# Handle fundamental C datatypes (PyCSimpleType)
		if datatype_dict['f']:

			return self.__unpack_type_fundamental_dict__(datatype_dict)

		# Structures (PyCStructType)
		elif datatype_dict['s']:

			return self.__unpack_type_struct_dict__(datatype_dict)

		# Undhandled stuff (pointers of pointers etc.) TODO
		else:

			# Push traceback to log
			self.log.err('[routine-server] ERROR: Unhandled datatype: %s' % datatype_dict['t'])

			# HACK TODO
			return ctypes.c_int


	def __unpack_type_fundamental_dict__(self, datatype_dict):

		# Return type class or type pointer
		if datatype_dict['p']:
			return ctypes.POINTER(getattr(ctypes, datatype_dict['t']))
		else:
			return getattr(ctypes, datatype_dict['t'])


	def __unpack_type_struct_dict__(self, datatype_dict):

		# Generate struct class if it does not exist yet
		if datatype_dict['t'] not in self.datatypes.keys():
			self.__unpack_type_struct_dict_generator__(datatype_dict)

		# Return type class or type pointer
		if datatype_dict['p']:
			return ctypes.POINTER(self.datatypes[datatype_dict['t']])
		else:
			return self.datatypes[datatype_dict['t']]


	def __unpack_type_struct_dict_generator__(self, datatype_dict):

		# Prepare fields
		fields = []

		# Step through fields
		for field in datatype_dict['_fields_']:

			# Handle fundamental C datatypes (PyCSimpleType)
			if field['f']:

				# Add tuple with name and fundamental datatype
				fields.append((
					field['n'],
					self.__unpack_type_fundamental_dict__(field)
					))

			# Structures (PyCStructType)
			elif field['s']:

				# Add tuple with name and struct datatype
				fields.append((
					field['n'], self.__unpack_struct_dict__(field)
					))

			# Undhandled stuff (pointers of pointers etc.) TODO
			else:

				# Push traceback to log
				self.log.err('[dll-server] ERROR: Unhandled datatype in struct: %s' % datatype_dict['t'])

				# HACK TODO
				fields.append((
					field['n'], ctypes.c_int
					))

		# Generate actual class
		self.datatypes[datatype_dict['t']] = type(
			datatype_dict['t'], # Potenial BUG ends up in __main__ namespace, problematic
			(ctypes.Structure,),
			{'_fields_': fields}
			)

		# Log status
		self.log.out('[dll-server] Generated struct type "%s" with fields %s' % (
			datatype_dict['t'], pf(fields)
			))
