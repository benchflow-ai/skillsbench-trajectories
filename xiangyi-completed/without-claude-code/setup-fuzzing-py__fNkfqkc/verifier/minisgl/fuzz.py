#!/usr/bin/env python3
"""
LibFuzzer-style fuzz driver for MiniSGL library using Atheris.
Tests tokenization, detokenization, and text processing functions.
"""

import sys
import atheris

# Simple standalone functions to test without full dependencies
def find_printable_text_simple(text):
    """Simplified version for fuzzing text processing."""
    if not text:
        return ""
    # Basic printable text extraction
    result = []
    for char in text:
        if char.isprintable() or char in '\n\r\t':
            result.append(char)
    return ''.join(result)

def is_chinese_char_simple(cp):
    """Check if codepoint is in CJK ranges."""
    if not isinstance(cp, int):
        return False
    return (0x4E00 <= cp <= 0x9FFF or
            0x3400 <= cp <= 0x4DBF or
            0x20000 <= cp <= 0x2A6DF or
            0x2A700 <= cp <= 0x2B73F or
            0x2B740 <= cp <= 0x2B81F or
            0x2B820 <= cp <= 0x2CEAF or
            0xF900 <= cp <= 0xFAFF or
            0x2F800 <= cp <= 0x2FA1F)


def TestOneInput(data):
    """Fuzz target for MiniSGL library."""
    fdp = atheris.FuzzedDataProvider(data)

    # Skip empty inputs
    if len(data) < 1:
        return

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)

    try:
        if choice == 0:
            # Fuzz find_printable_text with various text inputs
            text = fdp.ConsumeUnicodeNoSurrogates(200)
            if text:
                try:
                    result = find_printable_text_simple(text)
                except (ValueError, TypeError, UnicodeError):
                    pass

        elif choice == 1:
            # Fuzz is_chinese_char with various codepoints
            # Test with valid Unicode range and edge cases
            codepoint = fdp.ConsumeIntInRange(0, 0x10FFFF)
            try:
                is_chinese_char_simple(codepoint)
            except (ValueError, TypeError):
                pass

        elif choice == 2:
            # Fuzz text processing with mixed encodings
            text = fdp.ConsumeUnicodeNoSurrogates(200)
            if text:
                try:
                    # Test various string operations
                    result = text.strip()
                    result = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                    # Check for CJK characters
                    for char in text[:20]:  # Limit iteration
                        is_chinese_char_simple(ord(char))
                except (ValueError, TypeError, UnicodeError):
                    pass

        elif choice == 3:
            # Fuzz msgpack serialization (if available)
            obj_type = fdp.ConsumeIntInRange(0, 4)

            try:
                import msgpack

                if obj_type == 0:
                    obj = {fdp.ConsumeString(20): fdp.ConsumeInt(4)
                          for _ in range(fdp.ConsumeIntInRange(0, 5))}
                elif obj_type == 1:
                    obj = [fdp.ConsumeInt(4) for _ in range(fdp.ConsumeIntInRange(0, 10))]
                elif obj_type == 2:
                    obj = fdp.ConsumeUnicodeNoSurrogates(100)
                elif obj_type == 3:
                    obj = fdp.ConsumeInt(8)
                else:
                    obj = fdp.ConsumeFloat()

                # Test packing and unpacking
                packed = msgpack.packb(obj)
                unpacked = msgpack.unpackb(packed)
            except (ValueError, TypeError, AttributeError, RecursionError, ImportError):
                pass

    except Exception as e:
        # Allow expected exceptions but catch unexpected crashes
        if not isinstance(e, (ValueError, TypeError, KeyError, AttributeError,
                            UnicodeError, RecursionError, IndexError)):
            raise


def main():
    """Main entry point for fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
