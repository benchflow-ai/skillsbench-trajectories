"""Fuzz driver for UltraJSON (ujson) library."""
import atheris
import sys

try:
    import ujson
except ImportError:
    # Will be installed during virtual env setup
    pass


@atheris.instrument_func
def test_one(data: bytes) -> None:
    """Main fuzz target for ujson JSON encoder/decoder."""
    if len(data) < 1:
        return

    try:
        # Test 1: Parse JSON from input data
        try:
            # Try to parse as UTF-8 JSON string
            json_str = data.decode('utf-8', errors='ignore')
            if json_str:
                obj = ujson.loads(json_str)
        except (ValueError, TypeError, ujson.JSONDecodeError):
            pass
        except UnicodeDecodeError:
            pass

        # Test 2: Test with raw bytes
        try:
            # Try direct bytes parsing
            obj = ujson.loads(data)
        except (ValueError, TypeError, UnicodeDecodeError):
            pass
        except AttributeError:
            # ujson might not support bytes directly
            pass

        fdp = atheris.FuzzedDataProvider(data)

        # Test 3: Test various encoding options with parsed data
        json_input = fdp.ConsumeUnicodeString(2000)

        if json_input:
            try:
                # Try parsing with different options
                obj = ujson.loads(json_input)

                # Test encoding back with various options
                choice = fdp.ConsumeIntInRange(0, 3)

                if choice == 0:
                    # Standard encode
                    ujson.dumps(obj)
                elif choice == 1:
                    # Encode with HTML escaping
                    ujson.dumps(obj, encode_html_chars=True)
                elif choice == 2:
                    # Encode with pretty printing
                    indent = fdp.ConsumeIntInRange(0, 8)
                    ujson.dumps(obj, indent=indent)
                else:
                    # Encode with escape forward slashes
                    ujson.dumps(obj, escape_forward_slashes=True)

            except (ValueError, TypeError, OverflowError):
                pass
            except UnicodeError:
                pass

        # Test 4: Test deeply nested structures
        try:
            nested_json = ""
            depth = fdp.ConsumeIntInRange(0, 50)
            for i in range(depth):
                nested_json += "["
            nested_json += "1"
            for i in range(depth):
                nested_json += "]"

            if nested_json:
                result = ujson.loads(nested_json)
                ujson.dumps(result)
        except (ValueError, RecursionError, OverflowError):
            pass

        # Test 5: Test with special JSON values
        try:
            special_inputs = [
                "",  # Empty string
                "null",  # Null value
                "true",  # Boolean
                "false",  # Boolean
                "0",  # Zero
                "-0",  # Negative zero
                "1e308",  # Very large number
                "1e-308",  # Very small number
                '""',  # Empty string JSON
                "[]",  # Empty array
                "{}",  # Empty object
            ]

            for special in special_inputs:
                try:
                    ujson.loads(special)
                except ValueError:
                    pass

        except (ValueError, TypeError):
            pass

    except (
        ValueError,
        TypeError,
        OverflowError,
        RecursionError,
        UnicodeDecodeError,
        UnicodeError,
        AttributeError,
    ):
        # Expected exceptions during fuzzing
        return
    except Exception as e:
        # Log unexpected exceptions
        raise


def main() -> None:
    atheris.Setup(sys.argv, test_one)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
