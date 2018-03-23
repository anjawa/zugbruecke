# -*- coding: utf-8 -*-

"""

ZUGBRUECKE
Calling routines in Windows DLLs from Python scripts running on unixlike systems
https://github.com/pleiszenburg/zugbruecke

	tests/test_null_terminated_string.py: Demonstrates null terminated strings

	Required to run on platform / side: [UNIX, WINE]

	Copyright (C) 2017-2018 Sebastian M. Ernst <ernst@pleiszenburg.de>

<LICENSE_BLOCK>
The contents of this file are subject to the GNU Lesser General Public License
Version 2.1 ("LGPL" or "License"). You may not use this file except in
compliance with the License. You may obtain a copy of the License at
https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt
https://github.com/pleiszenburg/zugbruecke/blob/master/LICENSE

Software distributed under the License is distributed on an "AS IS" basis,
WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License for the
specific language governing rights and limitations under the License.
</LICENSE_BLOCK>

"""


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# IMPORT
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# import pytest

from sys import platform
if any([platform.startswith(os_name) for os_name in ['linux', 'darwin', 'freebsd']]):
	import zugbruecke as ctypes
elif platform.startswith('win'):
	import ctypes


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# CLASSES AND ROUTINES
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

class sample_class:


	def __init__(self):

		self.__dll__ = ctypes.windll.LoadLibrary('tests/demo_dll.dll')

		self.__replace_letter_in_null_terminated_string__ = self.__dll__.replace_letter_in_null_terminated_string
		self.__replace_letter_in_null_terminated_string__.argtypes = (
			ctypes.POINTER(ctypes.c_char),
			ctypes.c_char,
			ctypes.c_char
			)


	def replace_letter_in_null_terminated_string(self, in_string, old_letter, new_letter):

		BUFFER_LENGTH = 128

		string_buffer = ctypes.create_string_buffer(BUFFER_LENGTH)
		string_buffer.value = in_string.encode('utf-8')

		self.__replace_letter_in_null_terminated_string__(
			string_buffer,
			old_letter.encode('utf-8'),
			new_letter.encode('utf-8')
			)

		return string_buffer.value.decode('utf-8')


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# TEST(s)
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

def test_callback_simple():

	sample = sample_class()

	assert 'zetegehube' == sample.replace_letter_in_null_terminated_string('zategahuba', 'a', 'e')
