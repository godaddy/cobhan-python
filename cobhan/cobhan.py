"""Cobhan FFI primary functionality"""

import json
import os
import pathlib
import platform
from io import UnsupportedOperation
from typing import Any, ByteString, Optional

from cffi import FFI

# Pending https://github.com/python/typing/issues/593
CBuf = bytearray  # Cobhan buffer -- returned from ffi.new()


class Cobhan:
    """Class representing the Cobhan translation layer"""

    def __init__(self):
        self._lib: Optional[Any] = None
        self.__ffi: FFI = FFI()
        self.__sizeof_int32: int = self.__ffi.sizeof("int32_t")
        self.__sizeof_int64: int = self.__ffi.sizeof("int64_t")
        self.__sizeof_header: int = self.__sizeof_int32 * 2
        self.__minimum_allocation: int = 1024
        self.__int32_zero_bytes: bytes = int(0).to_bytes(
            self.__sizeof_int32, byteorder="little", signed=True
        )

    def load_library(self, library_path: str, library_name: str, cdefines: str) -> None:
        """Locate and load a library based on the current platform.

        :param library_path: The filesystem path where the library is located
        :param library_name: The name of the library to be loaded
        :param cdefines: A declaration of the C types, functions, and globals
          globals needed to use the shared object. This must be valid C syntax,
          with one definition per line.
        :raises UnsupportedOperation: If the operating system or CPU arch are
          not supported
        """
        self.__ffi.cdef(cdefines)

        system = platform.system()
        need_chdir = False
        if system == "Linux":
            if pathlib.Path("/lib").match("libc.musl*"):
                os_ext = "-musl.so"
                need_chdir = True
            else:
                os_ext = ".so"
        elif system == "Darwin":
            os_ext = ".dylib"
        elif system == "Windows":
            os_ext = ".dll"
        else:
            raise UnsupportedOperation("Unsupported operating system")

        machine = platform.machine()
        if machine in ("x86_64", "AMD64"):
            arch_part = "-x64"
        elif machine == "arm64":
            arch_part = "-arm64"
        else:
            raise UnsupportedOperation("Unsupported CPU")

        # Get absolute library path
        resolved_library_path = pathlib.Path(library_path).resolve()

        # Build library path with file name
        library_file_path = os.path.join(
            str(resolved_library_path), f"{library_name}{arch_part}{os_ext}"
        )

        if need_chdir:
            old_dir = os.getcwd()
            os.chdir(library_path)

        self._lib = self.__ffi.dlopen(library_file_path)

        if need_chdir:
            os.chdir(old_dir)

    def load_library_direct(self, library_file_path: str, cdefines: str) -> None:
        """Directly load a specific library file.

        Generally speaking, you probably don't want this. Instead, you probably
        want the `load_library` method which will load a platform-specific
        library for you.

        :param library_file_path: The full file path to the library
        :param cdefines: A declaration of the C types, functions, and globals
          globals needed to use the shared object. This must be valid C syntax,
          with one definition per line.
        """
        self.__ffi.cdef(cdefines)
        self._lib = self.__ffi.dlopen(library_file_path)

    def to_json_buf(self, obj: Any) -> CBuf:
        """Serialize an object into JSON in a Cobhan buffer.

        :param obj: The object to be serialized
        :returns: A new Cobhan buffer containing the JSON serialized object
        """
        return self.str_to_buf(json.dumps(obj))

    def from_json_buf(self, buf: CBuf) -> Any:
        """Deserialize a JSON serialized Cobhan buffer into an object.

        :param buf: The Cobhan buffer to be deserialized
        :returns: The deserialized object
        """
        return json.loads(self.buf_to_str(buf))

    def __set_header(self, buf: CBuf, length: int) -> None:
        """Create a header in a Cobhan buffer.

        :param buf: The Cobhan buffer in which to create a header
        :param length: The length of the header to be created
        """
        self.__ffi.memmove(
            buf[0 : self.__sizeof_int32],
            length.to_bytes(self.__sizeof_int32, byteorder="little", signed=True),
            self.__sizeof_int32,
        )
        self.__ffi.memmove(
            buf[self.__sizeof_int32 : self.__sizeof_int32 * 2],
            self.__int32_zero_bytes,
            self.__sizeof_int32,
        )

    def __set_payload(self, buf: CBuf, payload: ByteString, length: int) -> None:
        """Copy a payload into a Cobhan buffer.

        :param buf: The Cobhan buffer to copy the payload into
        :param payload: The payload to be copied
        :param length: The length of the payload
        """
        self.__set_header(buf, length)
        self.__ffi.memmove(
            buf[self.__sizeof_header : self.__sizeof_header + length - 1],
            payload,
            length,
        )

    def bytearray_to_buf(self, payload: ByteString) -> CBuf:
        """Copy a bytearray to a Cobhan buffer.

        :param payload: The bytearray to be copied
        """
        length = len(payload)
        buf = self.allocate_buf(length)
        self.__set_payload(buf, payload, length)
        return buf

    def str_to_buf(self, string: str) -> CBuf:
        """Encode a string in utf8 and copy into a Cobhan buffer.

        :param string: The string to be copied
        :returns: A new Cobhan buffer containing the utf8 encoded string
        """
        encoded_bytes = string.encode("utf8")
        length = len(encoded_bytes)
        buf = self.allocate_buf(length)
        self.__set_payload(buf, encoded_bytes, length)
        return buf

    def allocate_buf(self, buffer_len: int) -> CBuf:
        """Allocate a new Cobhan buffer.

        :param buffer_len: The length of the buffer to be allocated
        :returns: A new Cobhan buffer of the specified length
        """
        length = int(buffer_len)
        length = max(length, self.__minimum_allocation)
        buf = self.__ffi.new(f"char[{self.__sizeof_header + length}]")
        self.__set_header(buf, length)
        return buf

    def buf_to_str(self, buf: CBuf) -> str:
        """Read a Cobhan buffer into a string.

        :param buf: The Cobhan buffer to be read
        :returns: The string contents of the buffer
        """
        length_buf = self.__ffi.unpack(buf, self.__sizeof_int32)
        length = int.from_bytes(length_buf, byteorder="little", signed=True)
        if length < 0:
            return self.__temp_to_str(buf, length)
        encoded_bytes = self.__ffi.unpack(
            buf[self.__sizeof_header : self.__sizeof_header + length], length
        )
        return encoded_bytes.decode("utf8")

    def buf_to_bytearray(self, buf: CBuf) -> bytearray:
        """Copy a Cobhan buffer into a bytearray.

        :param buf: The Cobhan buffer to be copied
        :returns: The bytearray contents of the buffer
        """
        length_buf = self.__ffi.unpack(buf, self.__sizeof_int32)
        length = int.from_bytes(length_buf, byteorder="little", signed=True)
        if length < 0:
            return self.__temp_to_bytearray(buf, length)
        payload = bytearray(length)
        self.__ffi.memmove(
            payload, buf[self.__sizeof_header : self.__sizeof_header + length], length
        )
        return payload

    def __temp_to_str(self, buf: CBuf, length: int) -> str:
        """Copy a temporary file backed Cobhan buffer into a string.

        :param buf: The Cobhan buffer to be read from
        :param length: The length of the file name of the temporary file
        :returns: The string contents copied from the buffer
        """
        encoded_bytes = self.__temp_to_bytearray(buf, length)
        return encoded_bytes.decode("utf8")

    def __temp_to_bytearray(self, buf: CBuf, length: int) -> bytearray:
        """Copy a temporary file backed Cobhan buffer into a bytearray.

        :param buf: The Cobhan buffer to be copied
        :param length: The length of the file name of the temporary file
        :returns: The bytearray contents copied from the buffer
        """
        length = 0 - length
        encoded_bytes = self.__ffi.unpack(
            buf[self.__sizeof_header : self.__sizeof_header + length], length
        )
        file_name = encoded_bytes.decode("utf8")
        with open(file_name, "rb") as binaryfile:
            payload = bytearray(binaryfile.read())
        os.remove(file_name)
        return payload

    def int_to_buf(self, num: int) -> CBuf:
        """Copy an integer into a Cobhan buffer.

        :param num: The integer to be copied
        :returns: A new Cobhan buffer containing the integer
        """
        buf = self.__ffi.new(f"char[{self.__sizeof_int64}]")
        self.__ffi.memmove(
            buf[0 : self.__sizeof_int64],
            num.to_bytes(self.__sizeof_int64, byteorder="little", signed=True),
            self.__sizeof_int64,
        )
        return buf

    def buf_to_int(self, buf: CBuf) -> int:
        """Read a Cobhan buffer into an integer.

        :param buf: The Cobhan buffer to be read
        :returns: The integer contents of the buffer
        """
        value_buf = self.__ffi.unpack(buf, self.__sizeof_int64)
        return int.from_bytes(value_buf, byteorder="little", signed=True)
