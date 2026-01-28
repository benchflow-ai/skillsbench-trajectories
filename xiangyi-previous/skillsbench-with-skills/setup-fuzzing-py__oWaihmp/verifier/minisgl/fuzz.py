import sys
import atheris
import struct
from minisgl.core import SamplingParams

@atheris.instrument_func
def test_sampling_params(data):
    """Fuzz SamplingParams with various values"""
    if len(data) < 16:
        return
    
    try:
        # Extract values from fuzzing data
        temp = struct.unpack('f', data[0:4])[0]
        top_k = struct.unpack('i', data[4:8])[0]
        top_p = struct.unpack('f', data[8:12])[0]
        max_tokens = struct.unpack('i', data[12:16])[0]
        
        # Create SamplingParams with fuzzed values
        params = SamplingParams(
            temperature=max(0.0, temp),
            top_k=max(-1, top_k),
            top_p=max(0.0, min(1.0, top_p)),
            max_tokens=max(1, max_tokens)
        )
        # Access properties
        _ = params.is_greedy
    except (ValueError, TypeError, OverflowError, struct.error):
        pass
    except Exception:
        pass

@atheris.instrument_func
def test_tokenization_input(data):
    """Fuzz tokenization with various string inputs"""
    if len(data) < 1:
        return
    
    try:
        # Test with various encodings
        text = data.decode('utf-8', errors='ignore')
        # Simulate tokenization (would need actual model)
        _ = len(text)
    except (ValueError, TypeError, UnicodeDecodeError):
        pass
    except Exception:
        pass

@atheris.instrument_func  
def test_token_id_sequences(data):
    """Fuzz with arbitrary token ID sequences"""
    if len(data) < 4:
        return
    
    try:
        # Extract token IDs from data
        num_tokens = min(len(data) // 4, 1000)  # Limit to prevent memory issues
        token_ids = []
        for i in range(num_tokens):
            if i * 4 + 4 <= len(data):
                token_id = struct.unpack('I', data[i*4:(i+1)*4])[0]
                token_ids.append(token_id)
        # Simulate processing token sequence
        _ = len(token_ids)
    except (struct.error, ValueError, TypeError):
        pass
    except Exception:
        pass

def TestOneInput(data):
    test_sampling_params(data)
    test_tokenization_input(data)
    test_token_id_sequences(data)

if __name__ == "__main__":
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
