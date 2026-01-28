#!/usr/bin/env python3
"""Coverage-guided fuzzer for ujson library using atheris."""

import sys
import atheris


def TestOneInput(data: bytes) -> None:
    """Fuzz target for ujson.loads() and ujson.dumps()."""
    try:
        import ujson
        
        # Convert bytes to string for JSON parsing
        try:
            json_str = data.decode('utf-8')
        except UnicodeDecodeError:
            json_str = data.decode('latin-1')
        
        # Test ujson.loads() - main attack surface
        try:
            result = ujson.loads(json_str)
            
            # If parsing succeeded, test dumps with various options
            try:
                ujson.dumps(result)
            except (ValueError, TypeError, OverflowError):
                pass
            
            try:
                ujson.dumps(result, indent=2)
            except (ValueError, TypeError, OverflowError):
                pass
                
            try:
                ujson.dumps(result, ensure_ascii=False)
            except (ValueError, TypeError, OverflowError):
                pass
                
            try:
                ujson.dumps(result, encode_html_chars=True)
            except (ValueError, TypeError, OverflowError):
                pass
                
        except (ValueError, TypeError, OverflowError, ujson.JSONDecodeError):
            pass
        
        # Test with bytes input directly
        try:
            ujson.loads(data)
        except (ValueError, TypeError, OverflowError, ujson.JSONDecodeError,
                UnicodeDecodeError):
            pass
            
    except Exception:
        pass


def main():
    """Main entry point for the fuzzer."""
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()


if __name__ == "__main__":
    main()
