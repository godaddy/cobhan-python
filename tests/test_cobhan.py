"""Tests for the main Cobhan module"""

from pathlib import Path
from unittest import mock, TestCase

from cobhan import Cobhan


class LoadLibraryTests(TestCase):
    """Tests for Cobhan.load_library"""

    def setUp(self) -> None:
        self.ffi_patcher = mock.patch("cobhan.cobhan.FFI")
        self.platform_patcher = mock.patch("cobhan.cobhan.platform")

        self.mock_ffi = self.ffi_patcher.start()
        self.mock_dlopen = self.mock_ffi.return_value.dlopen
        self.mock_platform = self.platform_patcher.start()

        self.addCleanup(self.ffi_patcher.stop)
        self.addCleanup(self.platform_patcher.stop)

        self.cobhan = Cobhan()
        return super().setUp()

    def test_load_linux_x64(self):
        self.mock_platform.system.return_value = "Linux"
        self.mock_platform.machine.return_value = "x86_64"

        self.cobhan.load_library("libfoo", "libbar", "")
        self.mock_dlopen.assert_called_once_with(
            str(Path("libfoo/libbar-x64.so").resolve())
        )

    def test_load_linux_arm64(self):
        self.mock_platform.system.return_value = "Linux"
        self.mock_platform.machine.return_value = "arm64"

        self.cobhan.load_library("libfoo", "libbar", "")
        self.mock_dlopen.assert_called_once_with(
            str(Path("libfoo/libbar-arm64.so").resolve())
        )

    def test_load_macos_x64(self):
        self.mock_platform.system.return_value = "Darwin"
        self.mock_platform.machine.return_value = "x86_64"

        self.cobhan.load_library("libfoo", "libbar", "")
        self.mock_dlopen.assert_called_once_with(
            str(Path("libfoo/libbar-x64.dylib").resolve())
        )

    def test_load_macos_arm64(self):
        self.mock_platform.system.return_value = "Darwin"
        self.mock_platform.machine.return_value = "arm64"

        self.cobhan.load_library("libfoo", "libbar", "")
        self.mock_dlopen.assert_called_once_with(
            str(Path("libfoo/libbar-arm64.dylib").resolve())
        )

    def test_load_windows_x64(self):
        self.mock_platform.system.return_value = "Windows"
        self.mock_platform.machine.return_value = "x86_64"

        self.cobhan.load_library("libfoo", "libbar", "")
        self.mock_dlopen.assert_called_once_with(
            str(Path("libfoo/libbar-x64.dll").resolve())
        )

    def test_load_windows_arm64(self):
        self.mock_platform.system.return_value = "Windows"
        self.mock_platform.machine.return_value = "arm64"

        self.cobhan.load_library("libfoo", "libbar", "")
        self.mock_dlopen.assert_called_once_with(
            str(Path("libfoo/libbar-arm64.dll").resolve())
        )


class StringTests(TestCase):
    def setUp(self) -> None:

        self.cobhan = Cobhan()
        return super().setUp()

    def test_minimum_allocation_is_enforced(self):
        buf = self.cobhan.str_to_buf("foo")
        self.assertEqual(
            len(buf), (self.cobhan.minimum_allocation + self.cobhan.header_size)
        )

    def test_can_allocate_beyond_minimum(self):
        long_str = "foobar" * 1000  # This will be 6k characters in length
        buf = self.cobhan.str_to_buf(long_str)
        self.assertEqual(len(buf), (len(long_str) + self.cobhan.header_size))

    def test_two_way_conversion_maintains_string(self):
        buf = self.cobhan.str_to_buf("foobar")
        result = self.cobhan.buf_to_str(buf)
        self.assertEqual(result, "foobar")

    def test_empty_string_returns_empty_buffer(self):
        buf = self.cobhan.str_to_buf("")
        self.assertEqual(len(buf), self.cobhan.header_size)

    def test_input_of_none_returns_empty_buffer(self):
        buf = self.cobhan.str_to_buf(None)
        self.assertEqual(len(buf), self.cobhan.header_size)
