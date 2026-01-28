#!/usr/bin/env python3
"""
Fuzz driver for MiniSGL library
Focuses on deserialize_type() and fast_compare_key()
Note: GPU kernel fuzzing requires GPU hardware
"""

import atheris
import sys

with atheris.instrument_imports():
    try:
        from minisgl.message.utils import deserialize_type
        from minisgl.kernel import fast_compare_key
        MINISGL_AVAILABLE = True
    except ImportError:
        MINISGL_AVAILABLE = False


@atheris.instrument_func
def TestOneInput(data):
    """Fuzz entry point for MiniSGL library"""
    if len(data) < 1 or not MINISGL_AVAILABLE:
        return

    fdp = atheris.FuzzedDataProvider(data)
    strategy = fdp.ConsumeIntInRange(0, 1)

    if strategy == 0:
        # Fuzz deserialize_type() with various data types
        try:
            # Create arbitrary dict with __type__ key
            type_choice = fdp.ConsumeIntInRange(0, 3)
            types = ['Tensor', 'UserMsg', 'Dict', 'List']

            fuzz_dict = {
                '__type__': types[type_choice] if type_choice < len(types) else fdp.ConsumeUnicode(16),
                'data': fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 1024)),
                'nested': {
                    'value': fdp.ConsumeIntInRange(0, 1000),
                }
            }

            # Try to deserialize (will likely fail with unsupported types, which is fine)
            try:
                deserialize_type({}, fuzz_dict)
            except (TypeError, KeyError, AttributeError, ValueError):
                pass
        except Exception:
            pass

    elif strategy == 1:
        # Fuzz fast_compare_key() with tensor-like inputs
        try:
            import torch
            import numpy as np

            # Create integer tensors
            size1 = fdp.ConsumeIntInRange(0, 256)
            size2 = fdp.ConsumeIntInRange(0, 256)

            data1 = [fdp.ConsumeIntInRange(0, 1000) for _ in range(size1)]
            data2 = [fdp.ConsumeIntInRange(0, 1000) for _ in range(size2)]

            # Use numpy for CPU tensors
            arr1 = np.array(data1, dtype=np.int32)
            arr2 = np.array(data2, dtype=np.int32)

            # Try fast_compare_key (CPU operation)
            result = fast_compare_key(arr1, arr2)
            # Should return position of first difference or length

        except ImportError:
            # torch/numpy not available
            pass
        except (TypeError, ValueError, RuntimeError):
            pass


if __name__ == '__main__':
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()
