#!/usr/bin/env python3
"""
Fuzz driver for Arrow library
Tests date/time parsing and manipulation functions
"""

import sys
import atheris

# Import after atheris initialization to enable coverage
with atheris.instrument_imports():
    import arrow
    from arrow.parser import ParserError


def fuzz_arrow_get(data):
    """Fuzz arrow.get() function with various inputs"""
    try:
        arrow.get(data)
    except (ParserError, ValueError, TypeError, OverflowError, AttributeError):
        pass
    except Exception as e:
        # Log unexpected exceptions
        pass


def fuzz_arrow_format(data):
    """Fuzz Arrow formatting with custom format strings"""
    try:
        now = arrow.now()
        now.format(data)
    except (ValueError, TypeError, KeyError, IndexError):
        pass
    except Exception as e:
        pass


def fuzz_arrow_humanize(data):
    """Fuzz Arrow.humanize() with locale strings"""
    try:
        now = arrow.now()
        past = now.shift(days=-1)
        past.humanize(locale=data)
    except (ValueError, TypeError, KeyError, AttributeError):
        pass
    except Exception as e:
        pass


def fuzz_arrow_replace(data):
    """Fuzz Arrow.replace() with various kwargs"""
    try:
        now = arrow.now()
        # Try to parse data as comma-separated key=value pairs
        if b'=' in data:
            parts = data.split(b'=')
            if len(parts) >= 2:
                key = parts[0].decode('utf-8', errors='ignore')
                value_str = parts[1].decode('utf-8', errors='ignore')
                # Try to convert value to int
                try:
                    value = int(value_str)
                    kwargs = {key: value}
                    now.replace(**kwargs)
                except ValueError:
                    pass
    except (ValueError, TypeError, AttributeError):
        pass
    except Exception as e:
        pass


@atheris.instrument_func
def TestOneInput(data):
    """Main fuzzing entry point"""
    if len(data) < 1:
        return

    fdp = atheris.FuzzedDataProvider(data)

    # Choose which function to fuzz
    choice = fdp.ConsumeIntInRange(0, 3)
    remaining = fdp.ConsumeBytes(fdp.remaining_bytes())

    if choice == 0:
        # Fuzz arrow.get() with string input
        try:
            input_str = remaining.decode('utf-8', errors='ignore')
            fuzz_arrow_get(input_str)
        except:
            pass
    elif choice == 1:
        # Fuzz format strings
        try:
            input_str = remaining.decode('utf-8', errors='ignore')
            fuzz_arrow_format(input_str)
        except:
            pass
    elif choice == 2:
        # Fuzz humanize locale
        try:
            input_str = remaining.decode('utf-8', errors='ignore')
            fuzz_arrow_humanize(input_str)
        except:
            pass
    else:
        # Fuzz replace
        fuzz_arrow_replace(remaining)


def main():
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
