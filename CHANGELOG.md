## [0.2.1] - 2022-03-04

- Added `minimum_allocation` and `header_size` properties to the `Cobhan` class
- Fixed `load_library` and added tests
- Fixed allocation of empty buffers in `str_to_buf` and added tests

## [0.2.0] - 2022-03-03

- Renamed the `_load_*` methods to `load_*` to make them part of the public API,
  rather than protected.
- Added the `int_to_buf` and `buf_to_int` methods.

## [0.1.0] - 2022-02-28

- Initial Release
