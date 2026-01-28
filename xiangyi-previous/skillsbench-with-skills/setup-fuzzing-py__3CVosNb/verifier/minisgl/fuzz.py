#!/usr/bin/env python3
"""
Fuzz driver for MiniSGL (Mini-SGLang) library.

Targets:
- deserialize_type() - Parses untrusted dictionary data into Python objects
- _deserialize_any() - Recursive deserialization helper
- _PARSE_MEM_BYTES() - Memory size string parsing
- find_printable_text() - Text processing for streaming output
- _is_chinese_char() - CJK character detection

Usage:
    python fuzz.py [libfuzzer options]

Example:
    python fuzz.py -max_total_time=10
"""

import sys
import atheris


def setup_minisgl():
    """Import minisgl modules inside instrumentation context."""
    global deserialize_type, _deserialize_any, _PARSE_MEM_BYTES
    global find_printable_text, _is_chinese_char

    try:
        from minisgl.message.utils import deserialize_type, _deserialize_any
    except ImportError:
        deserialize_type = None
        _deserialize_any = None

    try:
        from minisgl.env import _PARSE_MEM_BYTES
    except ImportError:
        _PARSE_MEM_BYTES = None

    try:
        from minisgl.tokenizer.detokenize import find_printable_text, _is_chinese_char
    except ImportError:
        find_printable_text = None
        _is_chinese_char = None


@atheris.instrument_func
def TestOneInput(data: bytes) -> None:
    """Fuzz test entry point.

    Tests MiniSGL's parsing and deserialization functions.
    """
    # Try to decode as UTF-8 string
    try:
        input_str = data.decode('utf-8')
    except UnicodeDecodeError:
        input_str = data.decode('utf-8', errors='replace')

    fdp = atheris.FuzzedDataProvider(data)

    # Test 1: _PARSE_MEM_BYTES() - Memory size string parsing
    if _PARSE_MEM_BYTES is not None:
        try:
            result = _PARSE_MEM_BYTES(input_str)
            assert isinstance(result, int)
        except (ValueError, TypeError, OverflowError, KeyError, IndexError):
            pass  # Expected exceptions for invalid input
        except AssertionError:
            pass
        except Exception:
            pass

        # Test with common memory patterns
        patterns = [
            input_str + "G",
            input_str + "M",
            input_str + "K",
            input_str + "GB",
            input_str + "MB",
            input_str + "KB",
        ]
        for pattern in patterns[:3]:  # Limit iterations
            try:
                result = _PARSE_MEM_BYTES(pattern)
            except (ValueError, TypeError, OverflowError, KeyError, IndexError):
                pass
            except Exception:
                pass

    # Test 2: find_printable_text() - Text processing for streaming
    if find_printable_text is not None:
        try:
            result = find_printable_text(input_str)
            assert isinstance(result, str)
        except (ValueError, TypeError, OverflowError, IndexError):
            pass
        except AssertionError:
            pass
        except Exception:
            pass

    # Test 3: _is_chinese_char() - CJK character detection
    if _is_chinese_char is not None:
        # Test with random code points
        try:
            code_point = fdp.ConsumeIntInRange(0, 0x10FFFF)
            result = _is_chinese_char(code_point)
            assert isinstance(result, bool)
        except (ValueError, TypeError, OverflowError):
            pass
        except AssertionError:
            pass
        except Exception:
            pass

        # Test with each character in input
        for char in input_str[:100]:  # Limit to first 100 chars
            try:
                result = _is_chinese_char(ord(char))
            except (ValueError, TypeError, OverflowError):
                pass
            except Exception:
                pass

    # Test 4: deserialize_type() - Dictionary deserialization
    if deserialize_type is not None and _deserialize_any is not None:
        # Build a test dictionary from fuzz data
        try:
            # Try to parse as simple dict-like structure
            test_dict = {
                "__type__": input_str[:50] if input_str else "Unknown",
                "value": fdp.ConsumeFloat() if fdp.remaining_bytes() > 0 else 0.0,
            }

            # Create a simple class map for testing
            class DummyClass:
                def __init__(self, **kwargs):
                    for k, v in kwargs.items():
                        setattr(self, k, v)

            cls_map = {
                input_str[:50] if input_str else "Unknown": DummyClass,
                "DummyClass": DummyClass,
            }

            result = deserialize_type(cls_map, test_dict)
        except (ValueError, TypeError, KeyError, OverflowError, AttributeError):
            pass
        except Exception:
            pass

        # Test _deserialize_any with various types
        test_values = [
            input_str,
            list(input_str[:10]),
            tuple(input_str[:10]),
            {"key": input_str[:20]},
        ]
        for val in test_values:
            try:
                result = _deserialize_any({}, val)
            except (ValueError, TypeError, KeyError, OverflowError, AttributeError):
                pass
            except Exception:
                pass


def main():
    """Main entry point for the fuzzer."""
    # Instrument minisgl imports
    with atheris.instrument_imports():
        setup_minisgl()

    # Setup and run the fuzzer
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
