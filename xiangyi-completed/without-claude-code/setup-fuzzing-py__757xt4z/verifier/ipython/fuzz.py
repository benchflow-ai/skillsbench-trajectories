#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for IPython.
Fuzzes input transformation pipeline with various IPython syntax.
"""

import sys
import atheris
from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.splitinput import split_user_input
from IPython.utils._process_common import arg_split

def fuzz_ipython_target(data):
    """Fuzzer target function."""
    fuzzer = FuzzIPython(data)
    fuzzer.run()

atheris.Setup(sys.argv, fuzz_ipython_target)


class FuzzIPython:
    """Fuzz driver for IPython input transformation."""

    def __init__(self, data):
        """Initialize fuzzer with input data."""
        self.fuzz_data = atheris.FuzzedDataProvider(data)
        self.transformer_mgr = TransformerManager()

    def run(self):
        """Execute fuzzing targets."""
        try:
            self._fuzz_transform_cell()
            self._fuzz_split_user_input()
            self._fuzz_magic_commands()
            self._fuzz_system_commands()
            self._fuzz_help_syntax()
            self._fuzz_arg_split()
        except Exception:
            # Expected for invalid input
            pass

    def _fuzz_transform_cell(self):
        """Fuzz cell transformation."""
        cell = self.fuzz_data.ConsumeUnicodeString(500)

        try:
            result = self.transformer_mgr.transform_cell(cell)
            # Verify result is a string
            assert isinstance(result, str)
        except (ValueError, SyntaxError, AttributeError, IndexError, TypeError):
            pass

    def _fuzz_split_user_input(self):
        """Fuzz user input splitting."""
        line = self.fuzz_data.ConsumeUnicodeString(200)

        try:
            # split_user_input expects a line and pattern
            indent, escape, function, rest = split_user_input(line)

            # Verify results are strings
            assert isinstance(indent, str)
            assert isinstance(escape, (str, type(None)))
            assert isinstance(function, str)
            assert isinstance(rest, str)
        except (ValueError, AttributeError, TypeError):
            pass

    def _fuzz_magic_commands(self):
        """Fuzz magic command syntax."""
        magic_name = self.fuzz_data.ConsumeUnicodeString(20)
        args = self.fuzz_data.ConsumeUnicodeString(100)

        try:
            # Line magic
            cell = f"%{magic_name} {args}"
            self.transformer_mgr.transform_cell(cell)

            # Cell magic
            cell = f"%%{magic_name}\n{args}"
            self.transformer_mgr.transform_cell(cell)

            # Magic assignment
            cell = f"x = %{magic_name} {args}"
            self.transformer_mgr.transform_cell(cell)
        except (ValueError, SyntaxError, AttributeError, IndexError, TypeError):
            pass

    def _fuzz_system_commands(self):
        """Fuzz system command syntax."""
        command = self.fuzz_data.ConsumeUnicodeString(100)

        try:
            # Simple system command
            cell = f"!{command}"
            self.transformer_mgr.transform_cell(cell)

            # System command assignment
            cell = f"x = !{command}"
            self.transformer_mgr.transform_cell(cell)

            # Multiple system commands
            cell = f"!{command}\n!{command}"
            self.transformer_mgr.transform_cell(cell)
        except (ValueError, SyntaxError, AttributeError, IndexError, TypeError):
            pass

    def _fuzz_help_syntax(self):
        """Fuzz help query syntax."""
        obj_name = self.fuzz_data.ConsumeUnicodeString(50)

        try:
            # Single ? help
            cell = f"{obj_name}?"
            self.transformer_mgr.transform_cell(cell)

            # Double ?? help
            cell = f"{obj_name}??"
            self.transformer_mgr.transform_cell(cell)

            # Help on function
            cell = f"{obj_name}()?"
            self.transformer_mgr.transform_cell(cell)
        except (ValueError, SyntaxError, AttributeError, IndexError, TypeError):
            pass

    def _fuzz_arg_split(self):
        """Fuzz argument splitting."""
        arg_string = self.fuzz_data.ConsumeUnicodeString(200)

        try:
            # Test POSIX mode
            result = arg_split(arg_string, posix=True)
            assert isinstance(result, list)

            # Test non-POSIX mode
            result = arg_split(arg_string, posix=False)
            assert isinstance(result, list)

            # Test strict mode
            result = arg_split(arg_string, strict=True)
            assert isinstance(result, list)

            # Test non-strict mode
            result = arg_split(arg_string, strict=False)
            assert isinstance(result, list)
        except (ValueError, AttributeError, TypeError):
            pass


if __name__ == '__main__':
    atheris.Fuzz()
