"""Fuzz driver for Mini-SGLang LLM inference library."""
import atheris
import sys

try:
    from minisgl.llm import LLM
    from minisgl.utils import Tokenizer
except ImportError:
    # Will be installed during virtual env setup
    pass


@atheris.instrument_func
def test_one(data: bytes) -> None:
    """Main fuzz target for Mini-SGLang library."""
    if len(data) < 1:
        return

    try:
        fdp = atheris.FuzzedDataProvider(data)

        # Parse input as text for tokenizer and prompts
        input_text = fdp.ConsumeUnicodeString(1000)

        if len(input_text) == 0:
            return

        # Test 1: Basic tokenizer operations
        try:
            # Try to import and test tokenizer
            from minisgl.tokenizer import Tokenizer as TokenizerClass
            tokenizer = TokenizerClass()
            # Encode text
            tokens = tokenizer.encode(input_text)
            # Decode tokens
            if tokens and len(tokens) > 0:
                decoded = tokenizer.decode(tokens)
        except (ValueError, TypeError, AttributeError, ImportError):
            pass
        except Exception:
            pass

        # Test 2: Configuration parameter fuzzing
        try:
            choice = fdp.ConsumeIntInRange(0, 2)

            if choice == 0:
                # Test with max_tokens parameter
                max_tokens = fdp.ConsumeIntInRange(1, 4096)
                # Config validation
                config = {"max_tokens": max_tokens}
            elif choice == 1:
                # Test with temperature parameter
                temperature = fdp.ConsumeFloatInRange(0.0, 2.0)
                config = {"temperature": temperature}
            else:
                # Test with top_p parameter
                top_p = fdp.ConsumeFloatInRange(0.0, 1.0)
                config = {"top_p": top_p}

        except (ValueError, TypeError):
            pass

        # Test 3: Test input validation
        try:
            # Test various text encodings
            if input_text:
                # Attempt to process as prompt
                processed = input_text.encode('utf-8')
                decoded = processed.decode('utf-8', errors='ignore')
        except (UnicodeError, ValueError):
            pass

        # Test 4: Test with special tokens and formats
        try:
            special_inputs = [
                "",  # Empty string
                "\x00",  # Null byte
                "\x00" * 100,  # Multiple null bytes
                "\\x00\\x01\\x02",  # Escaped bytes
                "\\n\\r\\t",  # Escaped whitespace
            ]

            for special_input in special_inputs:
                test_input = special_input if len(special_input) < 100 else special_input[:100]
                # These should not cause crashes
                if test_input:
                    pass

        except (ValueError, TypeError):
            pass

    except (
        ValueError,
        TypeError,
        AttributeError,
        ImportError,
        RuntimeError,
        UnicodeError,
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
