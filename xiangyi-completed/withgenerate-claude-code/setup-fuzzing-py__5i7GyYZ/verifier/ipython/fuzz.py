"""Fuzz driver for IPython interactive shell library."""
import atheris
import sys
from io import StringIO

try:
    from IPython.terminal.interactiveshell import TerminalInteractiveShell
except ImportError:
    # Will be installed during virtual env setup
    pass


@atheris.instrument_func
def test_one(data: bytes) -> None:
    """Main fuzz target for IPython interactive shell."""
    if len(data) < 1:
        return

    try:
        fdp = atheris.FuzzedDataProvider(data)

        # Create a simple shell instance for testing
        shell = None
        try:
            # Create shell with minimal output redirection
            shell = TerminalInteractiveShell.instance()
        except Exception:
            return

        if shell is None:
            return

        # Parse input as Python code string
        python_code = fdp.ConsumeUnicodeString(2000)

        if len(python_code) == 0:
            return

        # Test 1: Run simple code snippets
        try:
            result = shell.run_cell(python_code, silent=True)
        except (SyntaxError, ValueError, AttributeError, NameError):
            pass
        except Exception:
            pass

        # Test 2: Test input transformation
        try:
            from IPython.core.inputtransformer2 import TransformerManager
            transformer = TransformerManager()
            # Try to transform the input
            transformer.transform_cell(python_code)
        except (SyntaxError, ValueError, AttributeError):
            pass
        except Exception:
            pass

        # Test 3: Test with magic-like commands
        if len(python_code) > 0:
            choice = fdp.ConsumeIntInRange(0, 2)
            test_code = python_code
            if choice == 0:
                test_code = "%" + python_code[:100]  # Line magic
            elif choice == 1:
                test_code = "%%" + python_code[:100]  # Cell magic
            elif choice == 2:
                test_code = "!" + python_code[:100]  # Shell command

            try:
                shell.run_cell(test_code, silent=True)
            except (SyntaxError, ValueError, AttributeError, NameError):
                pass
            except Exception:
                pass

    except (
        SyntaxError,
        ValueError,
        TypeError,
        AttributeError,
        NameError,
        RuntimeError,
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
