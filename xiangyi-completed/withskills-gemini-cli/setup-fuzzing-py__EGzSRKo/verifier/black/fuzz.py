import sys
import atheris

with atheris.instrument_imports():
    import black
    from black import Mode

def TestOneInput(data):
    try:
        s = data.decode('utf-8')
        black.format_str(s, mode=Mode())
    except (UnicodeDecodeError, black.parsing.InvalidInput):
        pass
    except Exception as e:
        # Check if it's an internal black error that we might want to ignore?
        # For now, let other exceptions crash to find bugs.
        pass

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
