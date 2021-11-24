:github_url:

.. _memsync:

.. index::
	single: pointer

Handling Pointers
=================

The memory synchronization protocol
-----------------------------------

Because *zugbruecke* runs code in a separate *Python* interpreter on *Wine*,
pointers pose a special kind of problem. They can, unfortunately, not be passed
from the code running on the *Unix* side to the code running on the *Wine* side
or vice versa. This is why the memory (to where pointers are pointing) must be kept in
sync on both sides. The memory synchronization can be controlled by the user
through the ``memsync`` protocol. ``memsync`` implements special directives,
which do not interfere with *ctypes* should the code be required to run on
*Windows* as well.

*zugbruecke* can handle some types of pointers on its own, without additional ``memsync`` directives.
Pointers to variables containing a single element (e.g. a floating pointer number or a structure) and
pointers to fixed-length arrays are handled transparently without additional directives.
If, on the other hand, the size of the memory a pointer is pointing to is dynamically determined at runtime,
*zugbruecke* must be provided with a hint on where it can find information on the size of the memory section
within the arguments or return value of a routine call. Those hints can be provided through ``memsync``.

A simple example: An array of floating point numbers of variable length
-----------------------------------------------------------------------

Consider the following example DLL routine in C:

.. code:: C

	void __stdcall __declspec(dllimport) bubblesort(
		float *a,
		int n
		)
	{
		int i, j;
		for (i = 0; i < n - 1; ++i)
		{
			for (j = 0; j < n - i - 1; ++j)
			{
				if (a[j] > a[j + 1])
				{
					float tmp = a[j];
					a[j] = a[j + 1];
					a[j + 1] = tmp;
				}
			}
		}
	}

It is a simple implementation of the "bubblesort" algorithm, which accepts
a pointer to an array of floats of arbitrary length and an integer with length information.
The array is being sorted within its own memory, so the caller expects a sorted
array at the passed pointer after the call.

With *ctypes* on *Windows*, you could call it like this:

.. code:: python

	from ctypes import windll, cast, pointer, POINTER, c_float, c_int

	__dll__ = windll.LoadLibrary('demo_dll.dll')
	__bubblesort__ = __dll__.bubblesort
	__bubblesort__.argtypes = (POINTER(c_float), c_int)

	def bubblesort(values):

		ctypes_float_values = ((c_float)*len(values))(*values)
		ctypes_float_pointer_firstelement = cast(
			pointer(ctypes_float_values), POINTER(c_float)
			)
		__bubblesort__(ctypes_float_pointer_firstelement, len(values))
		values[:] = ctypes_float_values[:]

	test_vector = [5.74, 3.72, 6.28, 8.6, 9.34, 6.47, 2.05, 9.09, 4.39, 4.75]
	bubblesort(test_vector)

For running the same code with *zugbruecke* on *Unix*, you need to add
information on the memory segment representing the array. This is done by
adding another attribute, ``memsync``, to the ``__bubblesort__`` function handle
(just like you usually specify ``argtypes`` and/or ``restype``). The following
example demonstrates how you must modify the above example so it works with
*zugbruecke*:

.. code:: python

	from zugbruecke.ctypes import windll, cast, pointer, POINTER, c_float, c_int

	__dll__ = windll.LoadLibrary('demo_dll.dll')
	__bubblesort__ = __dll__.bubblesort
	__bubblesort__.argtypes = (POINTER(c_float), c_int)
	__bubblesort__.memsync = [
		{
			'p': [0],
			'l': [1],
			't': 'c_float'
			}
		]

	def bubblesort(values):

		ctypes_float_values = ((c_float)*len(values))(*values)
		ctypes_float_pointer_firstelement = cast(
			pointer(ctypes_float_values), POINTER(c_float)
			)
		__bubblesort__(ctypes_float_pointer_firstelement, len(values))
		values[:] = ctypes_float_values[:]

	test_vector = [5.74, 3.72, 6.28, 8.6, 9.34, 6.47, 2.05, 9.09, 4.39, 4.75]
	bubblesort(test_vector)

Two things have changed. First, the import statement turned from *ctypes* to
*zugbruecke*, although the exact same types, routines and objects were imported.
Second, ``__bubblesort__`` received an additional ``memsync`` attribute.

Because the ``memsync`` attribute will be ignored by *ctypes*, you can make the
above piece of code platform-independent by adjusting the import statement only.
The complete example, which will run on *Unix* and on *Windows* looks just like this:

.. code:: python

	from sys import platform
	if any([platform.startswith(os_name) for os_name in ['linux', 'darwin', 'freebsd']]):
		from zugbruecke.ctypes import windll, cast, pointer, POINTER, c_float, c_int
	elif platform.startswith('win'):
		from ctypes import windll, cast, pointer, POINTER, c_float, c_int
	else:
		raise # handle other platforms here

	__dll__ = windll.LoadLibrary('demo_dll.dll')
	__bubblesort__ = __dll__.bubblesort
	__bubblesort__.argtypes = (POINTER(c_float), c_int)
	__bubblesort__.memsync = [
		{
			'p': [0],
			'l': [1],
			't': 'c_float'
			}
		]

	def bubblesort(values):

		ctypes_float_values = ((c_float)*len(values))(*values)
		ctypes_float_pointer_firstelement = cast(
			pointer(ctypes_float_values), POINTER(c_float)
			)
		__bubblesort__(ctypes_float_pointer_firstelement, len(values))
		values[:] = ctypes_float_values[:]

	test_vector = [5.74, 3.72, 6.28, 8.6, 9.34, 6.47, 2.05, 9.09, 4.39, 4.75]
	bubblesort(test_vector)


A more complex example: Computing the size of the memory from multiple arguments
--------------------------------------------------------------------------------

There are plenty of cases where you will encounter function (or structure)
definitions like the following:

.. code:: C

	void __stdcall __declspec(dllimport) process_image(
		float *image_data,
		int image_width,
		int image_height
		);

The ``image_data`` parameter is a flattened 1D array representing a 2D image.
Its length is defined by its width and its height. So the length of the array equals
``image_width * image_height``. For cases like this, ``memsync`` has the ability
to dynamically compute the length of the memory through custom functions.
Let's have a look at how the above function would be configured in *Python*:

.. code:: python

	process_image.argtypes = (ctypes.POINTER(ctypes.c_float), ctypes.c_int, ctypes.c_int)
	process_image.memsync = [
		{
			'p': [0],
			'l': ([1], [2]),
			'f': 'lambda x, y: x * y',
			't': 'c_float'
			}
		]

The above definition will extract the values of the ``image_width`` and
``image_height`` parameters for every function call and feed them into the
specified lambda function.

Using string buffers, null-terminated strings and Unicode
---------------------------------------------------------

Let's assume you are confronted with a regular *Python* (3) string. With the help of a
DLL function, you want to replace all occurrences of a letter with another letter.

.. code:: python

	some_string = 'zategahuba'

The DLL function's definition looks like this:

.. code:: C

	void __stdcall __declspec(dllimport) replace_letter(
		char *in_string,
		char old_letter,
		char new_letter
		);

In *Python*, it can be configured as follows:

.. code:: python

	replace_letter.argtypes = (
		ctypes.POINTER(ctypes.c_char),
		ctypes.c_char,
		ctypes.c_char
		)
	replace_letter.memsync = [
		{
			'p': [0],
			'n': True
			}
		]

The above configuration indicates that the first argument of the function is a
pointer to a NULL-terminated string.

While *Python* (3) strings are actually Unicode strings, the function accepts an
array of type ``char`` - a bytes array in *Python* terms. I.e. you have to encode the
string before it is copied into a string buffer. The following example illustrates
how the function ``replace_letter`` can be called on the string ``some_string``,
exchanging all letters ``a`` with ``e``. Subsequently, the result is printed.

.. code:: python

	string_buffer = ctypes.create_string_buffer(some_string.encode('utf-8'))
	replace_letter(string_buffer, 'a'.encode('utf-8'), 'e'.encode('utf-8'))
	print(string_buffer.value.decode('utf-8'))

The process differs if the DLL function accepts Unicode strings. Let's assume
the DLL function is defined as follows:

.. code:: C

	void __stdcall __declspec(dllimport) replace_letter_w(
		wchar_t *in_string,
		wchar_t old_letter,
		wchar_t new_letter
		);

In Python, it can be configured like this:

.. code:: python

	replace_letter_w.argtypes = (
		ctypes.POINTER(ctypes.c_wchar),
		ctypes.c_wchar,
		ctypes.c_wchar
		)
	replace_letter_w.memsync = [
		{
			'p': [0],
			'n': True,
			'w': True
			}
		]

One key aspect has changed: ``memsync`` contains another field, ``w``.
It must be set to ``True``, indicating that the argument is a Unicode string.
Now you can call the function as follows:

.. code:: python

	unicode_buffer = ctypes.create_unicode_buffer(some_string)
	replace_letter_w(unicode_buffer, 'a', 'e')
	print(unicode_buffer.value)


Applying memory synchronization to callback functions (function pointers)
-------------------------------------------------------------------------

Let's assume that you're dealing with structures of the following kind:

.. code:: python

	class image_data(ctypes.Structure):
		_fields_ = [
			('data', ctypes.POINTER(ctypes.c_int16)),
			('width', ctypes.c_int16),
			('height', ctypes.c_int16)
			]

2D monochrome image data is represented as a flattened 1D array, field ``data``,
with size information attached to it in the fields ``width`` and ``height``.
You furthermore have a function prototype which accepts an ``image_data`` structure
as an argument:

.. code:: python

	filter_func_type = ctypes.WINFUNCTYPE(ctypes.c_int16, ctypes.POINTER(image_data))

Before you actually decorate a *Python* function with it, all you have to do is
to change the contents of the ``memsync`` attribute of the function prototype,
``filter_func_type``:

.. code:: python

	filter_func_type.memsync = [
		{
			'p': [0, 'data'],
			'l': ([0, 'width'], [0, 'height']),
			'f': 'lambda x, y: x * y',
			't': 'c_int16'
			}
		]

The above syntax also does not interfere with ``ctypes`` on *Windows*, i.e.
the code remains perfectly platform-independent. Once the function prototype
has been configured through ``memsync``, it can be applied to a *Python* function:

.. code:: python

	@filter_func_type
	def filter_edge_detection(in_buffer):
		# do something ...

Attribute: ``memsync`` (list of dict)
-------------------------------------

``memsync`` is a list of dictionaries. Every dictionary represents one memory
section, which must be kept in sync. It has the following keys:

* ``p`` (:ref:`path to pointer <pathpointer>`)
* ``l`` (:ref:`path to length <pathlength>`, optional)
* ``n`` (:ref:`NULL-terminated string flag <nullstring>`, optional)
* ``w`` (:ref:`Unicode character flag <unicodechar>`, optional)
* ``t`` (:ref:`data type of pointer <pointertype>`, optional)
* ``f`` (:ref:`custom length function <length function>`, optional)
* ``_c`` (:ref:`custom data type <customtype>`, optional)

.. _pathpointer:

Key: ``p``, path to pointer (list of int and/or str)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This parameter describes where in the arguments or return value
(along the lines of ``argtypes`` and ``restype``)
*zugbruecke*'s parser can find the pointer, which it is expected to handle.
Consider the following example:

.. code:: python

	# arg nr:    0        1        2
	some_routine(param_a, param_b, param_c)

If ``param_b`` was the pointer, ``p`` would be ``[1]`` (a list with a single int),
referring to the second argument of ``some_routine`` (counted from zero).

The following more complex example illustrates why ``p`` is a list actually
representing something like a "path":

.. code:: python

	class some_struct(Structure):
		_fields_ = [
			('field_a', POINTER(c_float)),
			('field_b', c_int)
			]

	# arg nr:          0        1        2        3
	some_other_routine(param_a, param_b, param_c, param_d)

Let's assume that ``param_a`` is of type ``some_struct`` and ``field_a`` contains
the pointer. ``p`` would look like this: ``[0, 'field_a']``. The pointer is found
in ``field_a`` of the first parameter of ``some_other_routine``, ``param_a``.

Return values or elements within can be targeted by setting the first element
of a path to ``'r'`` (instead of an integer targeting an argument).

.. _pathlength:

Key: ``l``, path to length (list of int and/or str OR tuple of lists of int and/or str) (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This parameter works just like the :ref:`path to pointer <pathpointer>` parameter.
It is expected to tell the parser, where it can find a number (int) which represents
the length of the memory block or, alternatively, arguments for a custom length function.

It is expected to be either a single path list like ``[0, 'field_a']`` or a tuple
of multiple (or even zero) path lists, if the optional ``f`` key (custom length function) is defined.

.. _nullstring:

Key: ``n``, NULL-terminated string flag (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Can be set to ``True`` if a NULL-terminated string is passed as an argument.
``memsync`` will automatically determine the length of the string, so no
extra information on its length (through ``l`` is required).

.. _unicodechar:

Key: ``w``, Unicode character flag (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a Unicode string (buffer) is passed into a function, this parameter must be
set to ``True``. If not specified, it will default to ``False``.

.. _pointertype:

Key: ``t``, data type of pointer (PyCSimpleType or PyCStructType) (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This field expects a string representing the name of a ctypes datatype.
If you want to specify a custom structure type, you simply specify its class name as a string instead.

This parameter will be used by ``ctypes.sizeof`` for determining the datatype's size in bytes.
The result is then multiplied with the ``length`` to get an actual size of the
memory block in bytes. If it is not explicitly defined, it defaults to ``'c_ubyte'``.

For details on ``sizeof``, consult the `Python documentation on sizeof`_.
It will accept `fundamental types`_ as well as `structure types`_.

.. _Python documentation on sizeof: https://docs.python.org/3/library/ctypes.html?highlight=ctypes#ctypes.sizeof
.. _fundamental types: https://docs.python.org/3/library/ctypes.html?highlight=ctypes#fundamental-data-types
.. _structure types: https://docs.python.org/3/library/ctypes.html?highlight=ctypes#ctypes.Structure

.. _length function:

Key: ``f``, custom function for computing the length of the memory segment (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This field can be used to plug in a string, which can be parsed into a function or
lambda expression for computing the ``length`` of the memory section from multiple parameters.
The function is expected to accept a number of arguments equal to the number of elements
of the tuple of length paths defined in ``l``.

.. _customtype:

Key: ``_c``, custom data type (optional)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are using a custom non-*ctypes* datatype, which offers a ``from_param`` method,
you must specify it here. This applies when you construct your own array types
or use *numpy* types for instance.
