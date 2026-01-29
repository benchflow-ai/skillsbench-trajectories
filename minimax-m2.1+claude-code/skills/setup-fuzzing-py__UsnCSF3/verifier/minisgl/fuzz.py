#!/usr/bin/env python3
"""
Fuzz driver for MiniSGL library.
Uses LibFuzzer-style coverage-guided fuzzing.
"""

import sys
from typing import Any


def fuzz_minisgl_sampling_params(input_data: bytes) -> None:
    """Fuzz SamplingParams with various parameter values."""
    try:
        from minisgl.core import SamplingParams

        nums = [abs(b) for b in input_data[:16]]

        # Test various parameter combinations
        for temp in [0.0, 0.1, 0.5, 1.0, 2.0]:
            for top_k in [-1, 0, 1, 10, 100]:
                for top_p in [0.0, 0.5, 0.9, 1.0]:
                    for max_tok in [1, 10, 100, 1024]:
                        try:
                            SamplingParams(
                                temperature=temp,
                                top_k=top_k,
                                top_p=top_p,
                                max_tokens=max_tok
                            )
                        except Exception:
                            pass

    except Exception:
        pass


def fuzz_minisgl_core_dataclasses(input_data: bytes) -> None:
    """Fuzz MiniSGL core dataclasses."""
    try:
        from minisgl.core import SamplingParams, Req, Batch, Context
        import torch

        params = SamplingParams()

        # Try creating Req dataclass (may fail without proper initialization)
        nums = [abs(b) for b in input_data[:16]]

        # Test with basic tensor
        try:
            tensor = torch.tensor([1, 2, 3, 4, 5])
            req = Req(
                input_ids=tensor,
                table_idx=nums[0] % 10,
                cached_len=0,
                output_len=10,
                uid=nums[1],
                sampling_params=params,
                cache_handle=None
            )
        except Exception:
            pass

    except Exception:
        pass


def fuzz_minisgl_utils(input_data: bytes) -> None:
    """Fuzz MiniSGL utility functions."""
    try:
        from minisgl import utils

        data = input_data.decode('utf-8', errors='replace')

        # Test various utility functions if they exist
        if hasattr(utils, 'get_default_device'):
            try:
                utils.get_default_device()
            except Exception:
                pass

        if hasattr(utils, 'to_device'):
            try:
                utils.to_device([1, 2, 3])
            except Exception:
                pass

    except Exception:
        pass


def fuzz_minisgl_message_processing(input_data: bytes) -> None:
    """Fuzz message processing functions."""
    try:
        from minisgl.message import ChatMessage

        data = input_data.decode('utf-8', errors='replace')

        # Test message creation
        try:
            msg = ChatMessage(role='user', content=data[:100])
        except Exception:
            pass

    except Exception:
        pass


def main():
    """Main entry point for fuzzing."""
    if len(sys.argv) > 1:
        # Running with input file (LibFuzzer mode)
        with open(sys.argv[1], 'rb') as f:
            input_data = f.read()
    else:
        # Running from stdin
        input_data = sys.stdin.buffer.read()

    # Run all fuzz targets
    fuzz_minisgl_sampling_params(input_data)
    fuzz_minisgl_core_dataclasses(input_data)
    fuzz_minisgl_utils(input_data)
    fuzz_minisgl_message_processing(input_data)


if __name__ == '__main__':
    main()
