#!/usr/bin/env python3
"""
Fuzzing driver for minisgl library.
Targets: Message deserialization, API request parsing, tokenization
"""

import atheris
import sys

# Instrument the library before importing
atheris.instrument_imports(["minisgl"])

deserialize_type = None
SamplingParams = None

try:
    from minisgl.message.utils import deserialize_type, serialize_type
except (ImportError, ModuleNotFoundError):
    pass

try:
    from minisgl.core import SamplingParams
except (ImportError, ModuleNotFoundError):
    pass


@atheris.instrument_func
def fuzz_deserialize_type(data):
    """Fuzz message deserialization - critical for network data"""
    if deserialize_type is None:
        return

    try:
        fdp = atheris.FuzzedDataProvider(data)

        # Generate malformed dictionary structures
        test_dict = {
            "__type__": fdp.ConsumeString(size=50),
            "field1": fdp.ConsumeString(size=100),
            "field2": fdp.ConsumeInt(bytes=4),
            "field3": fdp.ConsumeBool(),
        }

        # Try deserializing with empty cls_map (safe for fuzzing)
        try:
            result = deserialize_type({}, test_dict)
        except (KeyError, ValueError, TypeError, AttributeError):
            # Expected - unknown type or malformed data
            return

    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def fuzz_sampling_params(data):
    """Fuzz SamplingParams validation"""
    if SamplingParams is None:
        return

    try:
        fdp = atheris.FuzzedDataProvider(data)

        # Generate parameter values
        temperature = fdp.ConsumeFloatInRange(-1.0, 10.0)
        top_k = fdp.ConsumeIntInRange(-1000, 1000000)
        top_p = fdp.ConsumeFloatInRange(-1.0, 2.0)
        max_tokens = fdp.ConsumeIntInRange(-1, 100000)

        # Try creating SamplingParams with extreme values
        params = SamplingParams(
            temperature=temperature,
            top_k=top_k,
            top_p=top_p,
            max_tokens=max_tokens,
        )

    except (ValueError, TypeError, OverflowError):
        # Expected - invalid parameter values
        return
    except Exception as e:
        # Unexpected exceptions - report them
        raise


@atheris.instrument_func
def fuzz_api_request_json(data):
    """Fuzz API request JSON parsing"""
    try:
        import json

        # Try to parse as JSON
        try:
            json_str = data.decode('utf-8', errors='ignore')
            parsed = json.loads(json_str)
        except (json.JSONDecodeError, ValueError, UnicodeDecodeError):
            # Expected - invalid JSON
            return

        # Try to use as OpenAI API request
        try:
            from minisgl.server.api_server import OpenAICompletionRequest

            if isinstance(parsed, dict):
                # Add required fields if missing
                parsed.setdefault('model', 'test')
                parsed.setdefault('prompt', 'test')

                # Try creating request object
                request = OpenAICompletionRequest(**parsed)

        except TypeError:
            # Expected - invalid field types
            return

    except (ImportError, AttributeError):
        # Library not fully available
        return
    except Exception as e:
        raise


@atheris.instrument_func
def fuzz_tokenization_input(data):
    """Fuzz tokenization input handling"""
    try:
        # Try as raw text
        text = data.decode('utf-8', errors='ignore')

        # Create tokenization message
        from minisgl.tokenizer.tokenize import TokenizeMsg

        msg = TokenizeMsg(text=text, request_id=0)

        # This should not crash but we can't fully execute without models
        # Just validate the message structure

    except (ImportError, AttributeError, ValueError, TypeError):
        # Expected - library constraints or invalid input
        return
    except Exception as e:
        raise


@atheris.instrument_func
def fuzz_detokenization_edge_cases(data):
    """Fuzz detokenization with invalid sequences"""
    try:
        # Try to create malformed token IDs
        fdp = atheris.FuzzedDataProvider(data)

        # Generate token IDs (typically 0-50000 for most tokenizers)
        num_tokens = fdp.ConsumeIntInRange(1, 100)
        token_ids = []

        for _ in range(num_tokens):
            # Include extreme values to test boundaries
            token_id = fdp.ConsumeInt(bytes=4)
            token_ids.append(abs(token_id))

        # Create detokenization message
        from minisgl.tokenizer.detokenize import DetokenizeMsg

        msg = DetokenizeMsg(ids=token_ids, request_id=0)

        # Just validate the message structure
        assert isinstance(msg.ids, list)

    except (ImportError, AssertionError, ValueError, TypeError):
        return
    except Exception as e:
        raise


@atheris.instrument_func
def test_minisgl_fuzzer(data):
    """Main fuzz target dispatcher"""
    if len(data) < 2:
        return

    # Route to different fuzz targets based on first byte
    target = data[0] % 5
    remaining_data = data[1:]

    if target == 0:
        fuzz_deserialize_type(remaining_data)
    elif target == 1:
        fuzz_sampling_params(remaining_data)
    elif target == 2:
        fuzz_api_request_json(remaining_data)
    elif target == 3:
        fuzz_tokenization_input(remaining_data)
    else:
        fuzz_detokenization_edge_cases(remaining_data)


# Setup and run fuzzer
atheris.Setup(sys.argv, test_minisgl_fuzzer)
atheris.Fuzz()
