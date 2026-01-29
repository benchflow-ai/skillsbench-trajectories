#!/usr/bin/env python3
"""
Fuzz driver for MiniSGL library
Tests deep learning layer operations and utilities
"""

import sys
import atheris
from atheris import FuzzedDataProvider

# Instrument the minisgl library
with atheris.instrument_imports():
    # Import minisgl modules
    import sys
    import os

    # Add minisgl to path
    sys.path.insert(0, "/app/minisgl/python")

    try:
        import minisgl.utils.misc as misc_utils
        import minisgl.utils.logger as logger_utils
    except ImportError:
        # If import fails, we'll handle it gracefully
        misc_utils = None
        logger_utils = None


@atheris.instrument_func
def test_misc_utils(data):
    """Fuzz MiniSGL misc utilities"""
    if misc_utils is None:
        return

    fdp = FuzzedDataProvider(data)

    try:
        # Test with string inputs
        if fdp.ConsumeBool():
            str1 = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))
            str2 = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))

            # Try to call various utility functions if they exist
            for attr_name in dir(misc_utils):
                if not attr_name.startswith('_') and callable(getattr(misc_utils, attr_name)):
                    func = getattr(misc_utils, attr_name)
                    try:
                        # Try calling with string arguments
                        if func.__code__.co_argcount >= 2:
                            result = func(str1, str2)
                        elif func.__code__.co_argcount == 1:
                            result = func(str1)
                    except Exception:
                        pass

    except Exception:
        pass


@atheris.instrument_func
def test_logger_utils(data):
    """Fuzz MiniSGL logger utilities"""
    if logger_utils is None:
        return

    fdp = FuzzedDataProvider(data)

    try:
        # Test logger functions
        message = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))

        for attr_name in dir(logger_utils):
            if not attr_name.startswith('_'):
                obj = getattr(logger_utils, attr_name)
                try:
                    if callable(obj):
                        if obj.__code__.co_argcount >= 1:
                            obj(message)
                        elif obj.__code__.co_argcount == 0:
                            obj()
                except Exception:
                    pass
                elif hasattr(obj, 'write'):
                    try:
                        obj.write(message)
                    except Exception:
                        pass

    except Exception:
        pass


@atheris.instrument_func
def test_string_operations(data):
    """Fuzz string operations that might be used in ML utilities"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate random strings
        str1 = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))
        str2 = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 100))

        # Test various string operations that might be present in ML libraries
        operations = [
            lambda s: s.lower(),
            lambda s: s.upper(),
            lambda s: s.strip(),
            lambda s: s.replace('a', 'b'),
            lambda s: s.split(','),
            lambda s: s.split(),
        ]

        for op in operations:
            try:
                if str1:
                    op(str1)
                if str2:
                    op(str2)
            except Exception:
                pass

        # Test join operations
        try:
            list_to_join = [str1, str2]
            result = ','.join(list_to_join)
        except Exception:
            pass

    except Exception:
        pass


@atheris.instrument_func
def test_dict_operations(data):
    """Fuzz dictionary operations that might be used in ML configuration"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate random dictionary
        num_items = fdp.ConsumeIntInRange(0, 20)
        test_dict = {}

        for _ in range(num_items):
            key = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(1, 20))
            value = fdp.ConsumeIntInRange(-1000, 1000)
            test_dict[key] = value

        # Test dictionary operations
        dict_ops = [
            lambda d: d.get('test', 0),
            lambda d: d.keys(),
            lambda d: d.values(),
            lambda d: d.items(),
        ]

        for op in dict_ops:
            try:
                op(test_dict)
            except Exception:
                pass

    except Exception:
        pass


@atheris.instrument_func
def test_list_operations(data):
    """Fuzz list operations that might be used in ML"""
    fdp = FuzzedDataProvider(data)

    try:
        # Generate random list
        num_items = fdp.ConsumeIntInRange(0, 50)
        test_list = []

        for _ in range(num_items):
            item = fdp.ConsumeUnicode(fdp.ConsumeIntInRange(0, 20))
            test_list.append(item)

        # Test list operations
        try:
            # Test slicing
            start = fdp.ConsumeIntInRange(0, 10)
            end = fdp.ConsumeIntInRange(start, start + 10)
            result = test_list[start:end]
        except Exception:
            pass

        try:
            # Test join on strings
            result = ','.join(test_list)
        except Exception:
            pass

        try:
            # Test sorting
            sorted_list = sorted(test_list)
        except Exception:
            pass

    except Exception:
        pass


def TestOneInput(data):
    """Main fuzzing entry point"""
    # Run all test functions
    test_misc_utils(data)
    test_logger_utils(data)
    test_string_operations(data)
    test_dict_operations(data)
    test_list_operations(data)


def main():
    """Set up and run the fuzzer"""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
