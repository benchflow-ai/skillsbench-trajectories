"""
Coverage-guided fuzzing driver for IPython library.
Fuzzes input transformation, parsing, and execution functions.
"""

import atheris
import sys

# Import IPython library
try:
    from IPython.core import interactiveshell
    from IPython.core import inputtransformer2
    from IPython.utils import text
    from IPython.core import magic_arguments
except ImportError:
    # Try alternative import path
    sys.path.insert(0, '/app/ipython')
    from IPython.core import interactiveshell
    from IPython.core import inputtransformer2
    from IPython.utils import text
    from IPython.core import magic_arguments

def fuzz_transform_cell(data):
    """Fuzz input transformation pipeline"""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Test TransformerManager
        manager = inputtransformer2.TransformerManager()

        try:
            result = manager.transform_cell(input_str)
        except Exception:
            pass

        try:
            is_complete = manager.check_complete(input_str)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_tokenize_input(data):
    """Fuzz tokenization functions"""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Test make_tokens_by_line
        try:
            lines = input_str.split('\n')
            result = inputtransformer2.make_tokens_by_line(lines)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_magic_parse_args(data):
    """Fuzz magic command argument parsing"""
    try:
        arg_str = data.decode('utf-8', errors='ignore')

        # Create a dummy magic function for testing
        @magic_arguments.magic_arguments()
        @magic_arguments.argument('--option', type=str)
        def dummy_magic(arg_str):
            pass

        try:
            result = magic_arguments.parse_argstring(dummy_magic, arg_str)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_string_utils(data):
    """Fuzz string utility functions"""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Test indent
        try:
            result = text.indent(input_str)
        except Exception:
            pass

        # Test dedent
        try:
            result = text.dedent(input_str)
        except Exception:
            pass

        # Test strip_email_quotes
        try:
            result = text.strip_email_quotes(input_str)
        except Exception:
            pass

        # Test format_screen
        try:
            result = text.format_screen(input_str)
        except Exception:
            pass

        # Test list_strings
        try:
            result = text.list_strings(input_str)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_arg_split(data):
    """Fuzz shell argument splitting"""
    try:
        cmd_str = data.decode('utf-8', errors='ignore')

        from IPython.utils._process_common import arg_split

        try:
            result = arg_split(cmd_str)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_check_complete(data):
    """Fuzz code completeness checking"""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Create an InteractiveShell instance
        shell = interactiveshell.InteractiveShell.instance()

        try:
            result = shell.check_complete(input_str)
        except Exception:
            pass

    except Exception:
        pass

def fuzz_escaped_commands(data):
    """Fuzz escaped command transformations"""
    try:
        input_str = data.decode('utf-8', errors='ignore')

        # Test EscapedCommand transformer
        try:
            transformer = inputtransformer2.EscapedCommand()
            lines = input_str.split('\n')
            result = transformer.transform(lines)
        except Exception:
            pass

        # Test HelpEnd transformer
        try:
            transformer = inputtransformer2.HelpEnd()
            lines = input_str.split('\n')
            result = transformer.transform(lines)
        except Exception:
            pass

    except Exception:
        pass

def TestOneInput(data):
    """Main fuzzing entry point"""
    # Limit input size to avoid timeouts
    if len(data) > 10000:
        data = data[:10000]

    # Run all fuzzing targets
    fuzz_transform_cell(data)
    fuzz_tokenize_input(data)
    fuzz_magic_parse_args(data)
    fuzz_string_utils(data)
    fuzz_arg_split(data)
    fuzz_check_complete(data)
    fuzz_escaped_commands(data)

if __name__ == '__main__':
    # Setup atheris
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
