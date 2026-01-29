"""Fuzz driver for Black code formatter library."""
import atheris
import sys

try:
    import black
except ImportError:
    # Will be installed during virtual env setup
    pass


@atheris.instrument_func
def test_one(data: bytes) -> None:
    """Main fuzz target for Black code formatter."""
    if len(data) < 1:
        return

    try:
        fdp = atheris.FuzzedDataProvider(data)

        # Parse input as Python code string
        python_code = fdp.ConsumeUnicodeString(5000)

        if len(python_code) == 0:
            return

        # Test 1: Format arbitrary Python code
        try:
            result = black.format_str(python_code, mode=black.Mode())
        except (black.NothingChanged, SyntaxError, ValueError, AttributeError):
            pass
        except black.InvalidInput:
            pass

        # Test 2: Try with different line length settings
        line_length = fdp.ConsumeIntInRange(10, 200)
        try:
            mode = black.Mode(line_length=line_length)
            black.format_str(python_code, mode=mode)
        except (black.NothingChanged, SyntaxError, ValueError, AttributeError):
            pass
        except black.InvalidInput:
            pass

        # Test 3: Test with target versions
        choice = fdp.ConsumeIntInRange(0, 1)
        if choice == 0:
            try:
                mode = black.Mode(target_versions={black.TargetVersion.PY38})
                black.format_str(python_code, mode=mode)
            except (black.NothingChanged, SyntaxError, ValueError, AttributeError):
                pass
            except (black.InvalidInput, ValueError):
                pass

    except (
        black.NothingChanged,
        SyntaxError,
        ValueError,
        TypeError,
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
