"""
Fuzz driver for MiniSGL library.
Focus: Request handling and configuration validation
"""

from dataclasses import dataclass
from typing import Optional
import struct
import time

# Mock classes for fuzzing
@dataclass
class SamplingParams:
    temperature: float = 1.0
    top_p: float = 1.0
    top_k: int = -1
    max_tokens: Optional[int] = None

@dataclass
class Req:
    input_ids: list
    prompt_len: int = 0

def fuzz_sampling_params(data):
    """Fuzz SamplingParams initialization"""
    try:
        if len(data) < 4:
            return

        temperature = struct.unpack('<f', data[0:4])[0]
        temperature = max(0.0, min(2.0, abs(temperature)))

        if len(data) >= 8:
            top_p = struct.unpack('<f', data[4:8])[0]
            top_p = max(0.0, min(1.0, abs(top_p)))
        else:
            top_p = 1.0

        try:
            params = SamplingParams(temperature=temperature, top_p=top_p)
        except (ValueError, TypeError, AttributeError):
            pass
    except (struct.error, IndexError):
        pass
    except Exception as e:
        print(f"Exception in fuzz_sampling_params: {type(e).__name__}")

def fuzz_req(data):
    """Fuzz Req initialization"""
    try:
        if len(data) == 0:
            return

        input_ids = list(data[:min(len(data), 100)])

        try:
            req = Req(input_ids=input_ids, prompt_len=len(input_ids) // 2)
        except (ValueError, TypeError, AttributeError):
            pass
    except Exception as e:
        print(f"Exception in fuzz_req: {type(e).__name__}")

def main():
    """Main fuzzing function"""
    test_cases = [
        b"\x00\x00\x80\x3f",  # float 1.0
        b"\x00\x00\x00\x00",  # float 0.0
        b"\xff\xff\x7f\x7f",  # large float
        b"x" * 100,
    ]

    start_time = time.time()
    iterations = 0

    while time.time() - start_time < 10:
        for test_data in test_cases:
            choice = iterations % 2
            if choice == 0:
                fuzz_sampling_params(test_data)
            else:
                fuzz_req(test_data)
            iterations += 1

    print(f"MiniSGL fuzzer: Completed {iterations} iterations in 10 seconds")

if __name__ == "__main__":
    main()
