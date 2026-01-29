#!/usr/bin/env python3
"""
Fuzzing driver for IPython library.
Targets: TransformerManager.transform_cell(), split_user_input(), tokenization
"""

import atheris
import sys

# Instrument the library before importing
atheris.instrument_imports(["IPython"])

from IPython.core.inputtransformer2 import TransformerManager
from IPython.core.splitinput import split_user_input


@atheris.instrument_func
def fuzz_split_user_input(data):
    """Fuzz split_user_input() - line parsing"""
    try:
        line = data.decode('utf-8', errors='ignore')

        # Try splitting the line
        result = split_user_input(line)

    except (ValueError, TypeError):
        # Expected - invalid input
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def fuzz_transform_cell(data):
    """Fuzz TransformerManager.transform_cell() - cell transformation"""
    try:
        cell = data.decode('utf-8', errors='ignore')

        # Create transformer manager
        tm = TransformerManager()

        # Try transforming the cell
        result = tm.transform_cell(cell)

    except (ValueError, TypeError, SyntaxError):
        # Expected - invalid input
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def fuzz_check_complete(data):
    """Fuzz TransformerManager.check_complete() - code completeness check"""
    try:
        code = data.decode('utf-8', errors='ignore')

        # Create transformer manager
        tm = TransformerManager()

        # Check if code is complete
        result = tm.check_complete(code)

    except (ValueError, TypeError, SyntaxError):
        return
    except Exception as e:
        raise


@atheris.instrument_func
def fuzz_ipython_magic_commands(data):
    """Fuzz IPython magic command parsing"""
    try:
        fdp = atheris.FuzzedDataProvider(data)

        # Generate different magic command patterns
        magic_type = fdp.ConsumeIntInRange(0, 3)

        if magic_type == 0:
            # Line magic: %magic_name
            magic_name = fdp.ConsumeString(size=30)
            args = fdp.ConsumeString(size=50)
            cell = f"%{magic_name} {args}"
        elif magic_type == 1:
            # System command: !cmd
            cmd = fdp.ConsumeString(size=50)
            cell = f"!{cmd}"
        elif magic_type == 2:
            # Help syntax: obj?
            obj_name = fdp.ConsumeString(size=30)
            cell = f"{obj_name}?"
        else:
            # Assignment with magic: a = %magic
            var_name = fdp.ConsumeString(size=20)
            magic_name = fdp.ConsumeString(size=20)
            cell = f"{var_name} = %{magic_name}"

        # Try transforming
        tm = TransformerManager()
        result = tm.transform_cell(cell)

    except (ValueError, TypeError, SyntaxError):
        return
    except Exception as e:
        raise


@atheris.instrument_func
def fuzz_ipython_multiline(data):
    """Fuzz IPython multiline input handling"""
    try:
        fdp = atheris.FuzzedDataProvider(data)

        # Generate multiline code
        lines = []
        num_lines = fdp.ConsumeIntInRange(1, 10)

        for i in range(num_lines):
            line = fdp.ConsumeString(size=50)
            lines.append(line)

        code = "\n".join(lines)

        # Try transforming
        tm = TransformerManager()
        result = tm.transform_cell(code)

        # Check completeness
        status, indent = tm.check_complete(code)

    except (ValueError, TypeError, SyntaxError):
        return
    except Exception as e:
        raise


@atheris.instrument_func
def test_ipython_fuzzer(data):
    """Main fuzz target dispatcher"""
    if len(data) < 2:
        return

    # Route to different fuzz targets based on first byte
    target = data[0] % 5
    remaining_data = data[1:]

    if target == 0:
        fuzz_split_user_input(remaining_data)
    elif target == 1:
        fuzz_transform_cell(remaining_data)
    elif target == 2:
        fuzz_check_complete(remaining_data)
    elif target == 3:
        fuzz_ipython_magic_commands(remaining_data)
    else:
        fuzz_ipython_multiline(remaining_data)


# Setup and run fuzzer
atheris.Setup(sys.argv, test_ipython_fuzzer)
atheris.Fuzz()
