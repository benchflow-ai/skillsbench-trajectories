"""
Fuzz driver for UltraJSON library.
Focus: JSON parsing and encoding functionality
"""

import ujson
import time

def fuzz_ujson_decode(data):
    """Fuzz ujson.decode() with JSON-like strings"""
    try:
        json_str = data.decode('utf-8', errors='ignore')
        try:
            ujson.decode(json_str)
        except ValueError:
            pass
    except (TypeError, AttributeError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_ujson_decode: {type(e).__name__}")

def fuzz_ujson_encode(data):
    """Fuzz ujson.encode() with various Python objects"""
    try:
        if len(data) == 0:
            return

        test_objects = [
            data.decode('utf-8', errors='ignore'),
            list(data),
            {"key": data.decode('utf-8', errors='ignore')},
            [1, 2, 3, data[0] if data else 0],
        ]

        for obj in test_objects:
            try:
                ujson.encode(obj)
            except (ValueError, TypeError, OverflowError):
                pass
    except (AttributeError, IndexError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_ujson_encode: {type(e).__name__}")

def fuzz_ujson_with_options(data):
    """Fuzz ujson.encode() with various options"""
    try:
        if len(data) < 1:
            return

        json_str = data.decode('utf-8', errors='ignore')
        choice = data[0] % 4

        obj = {"test": json_str, "value": 123, "nested": {"key": "value"}}

        try:
            if choice == 0:
                ujson.encode(obj, encode_html_chars=True)
            elif choice == 1:
                ujson.encode(obj, escape_forward_slashes=True)
            elif choice == 2:
                ujson.encode(obj, ensure_ascii=True)
            else:
                ujson.encode(obj)
        except (ValueError, TypeError, OverflowError):
            pass
    except (AttributeError, IndexError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_ujson_with_options: {type(e).__name__}")

def main():
    """Main fuzzing function"""
    test_cases = [
        b'{"key": "value"}',
        b'[1, 2, 3]',
        b'"hello"',
        b'null',
        b'{"incomplete": ',
        b'' * 100,
        b'[' * 50,
        b'{' * 50,
    ]

    start_time = time.time()
    iterations = 0

    while time.time() - start_time < 10:
        for test_data in test_cases:
            choice = iterations % 3
            if choice == 0:
                fuzz_ujson_decode(test_data)
            elif choice == 1:
                fuzz_ujson_encode(test_data)
            else:
                fuzz_ujson_with_options(test_data)
            iterations += 1

    print(f"ujson fuzzer: Completed {iterations} iterations in 10 seconds")

if __name__ == "__main__":
    main()
