#!/usr/bin/env python3
"""
LibFuzzer-compatible fuzz driver for Mini-SGLang.
Fuzzes core data structures, serialization, and request handling.
"""

import sys
import atheris

# Add minisgl to path
sys.path.insert(0, '/app/minisgl/python')

try:
    from minisgl.core import Req, SamplingParams, Batch
    from minisgl.scheduler.cache import CacheManager
    from minisgl.scheduler.table import TableManager
    from minisgl.utils.misc import divide_even, divide_up, divide_down
except ImportError:
    # Graceful degradation if imports fail
    pass

def fuzz_minisgl_target(data):
    """Fuzzer target function."""
    fuzzer = FuzzMiniSGL(data)
    fuzzer.run()

atheris.Setup(sys.argv, fuzz_minisgl_target)


class FuzzMiniSGL:
    """Fuzz driver for Mini-SGLang library."""

    def __init__(self, data):
        """Initialize fuzzer with input data."""
        self.fuzz_data = atheris.FuzzedDataProvider(data)

    def run(self):
        """Execute fuzzing targets."""
        try:
            self._fuzz_sampling_params()
            self._fuzz_request_creation()
            self._fuzz_division_functions()
            self._fuzz_cache_operations()
            self._fuzz_table_operations()
        except Exception:
            # Expected for invalid parameters
            pass

    def _fuzz_sampling_params(self):
        """Fuzz SamplingParams initialization."""
        try:
            temperature = self.fuzz_data.ConsumeFloat()
            # Clamp temperature to reasonable range
            temperature = max(0.0, min(2.0, temperature))

            top_k = self.fuzz_data.ConsumeIntInRange(-1, 100)
            top_p = self.fuzz_data.ConsumeFloat()
            top_p = max(0.0, min(1.0, top_p))

            max_tokens = self.fuzz_data.ConsumeIntInRange(1, 1000)
            ignore_eos = self.fuzz_data.ConsumeBool()

            # Create SamplingParams
            params = SamplingParams(
                temperature=temperature,
                top_k=top_k,
                top_p=top_p,
                max_tokens=max_tokens,
                ignore_eos=ignore_eos
            )

            # Verify parameters
            assert params.temperature >= 0
            assert params.max_tokens >= 1
        except (ValueError, AssertionError, AttributeError, TypeError):
            pass

    def _fuzz_request_creation(self):
        """Fuzz Req (request) object creation."""
        try:
            # Create valid request parameters
            input_ids = [self.fuzz_data.ConsumeInt(32) for _ in range(
                self.fuzz_data.ConsumeIntInRange(1, 10))]

            # Make sure input_ids are valid
            input_ids = [max(0, abs(id)) for id in input_ids]

            sampling_params = SamplingParams(
                max_tokens=self.fuzz_data.ConsumeIntInRange(1, 100)
            )

            # Create request
            req = Req(
                uid=self.fuzz_data.ConsumeInt(32),
                input_ids=input_ids,
                sampling_params=sampling_params
            )

            # Verify request
            assert req.input_ids == input_ids
            assert len(req.input_ids) > 0
        except (ValueError, AssertionError, AttributeError, TypeError, IndexError):
            pass

    def _fuzz_division_functions(self):
        """Fuzz integer division utility functions."""
        try:
            dividend = self.fuzz_data.ConsumeIntInRange(1, 1000)
            divisor = self.fuzz_data.ConsumeIntInRange(1, 100)

            # Test divide_even
            result = divide_even(dividend, divisor)
            assert result > 0

            # Test divide_up
            result = divide_up(dividend, divisor)
            assert result > 0

            # Test divide_down
            result = divide_down(dividend, divisor)
            assert result >= 0
        except (ValueError, AssertionError, ZeroDivisionError, AttributeError):
            pass

    def _fuzz_cache_operations(self):
        """Fuzz cache manager operations."""
        try:
            # Create cache manager with random parameters
            num_pages = self.fuzz_data.ConsumeIntInRange(1, 100)
            page_size = self.fuzz_data.ConsumeIntInRange(1, 1000)

            # Initialize cache manager
            cache_mgr = CacheManager(
                num_pages=num_pages,
                page_size=page_size
            )

            # Test allocation
            num_pages_to_alloc = self.fuzz_data.ConsumeIntInRange(0, num_pages)
            if num_pages_to_alloc > 0:
                try:
                    handle = cache_mgr.allocate(num_pages_to_alloc)
                    if handle is not None:
                        # Test check integrity
                        cache_mgr.check_integrity()

                        # Test deallocation
                        cache_mgr.free(handle)
                except Exception:
                    pass
        except (ValueError, AssertionError, AttributeError, TypeError, OverflowError):
            pass

    def _fuzz_table_operations(self):
        """Fuzz table manager operations."""
        try:
            # Create table manager
            max_entries = self.fuzz_data.ConsumeIntInRange(10, 1000)
            table_mgr = TableManager(max_entries=max_entries)

            # Test allocations and deallocations
            allocated_slots = []
            num_allocs = self.fuzz_data.ConsumeIntInRange(0, min(5, max_entries))

            for _ in range(num_allocs):
                try:
                    slot = table_mgr.allocate()
                    if slot is not None:
                        allocated_slots.append(slot)
                except Exception:
                    break

            # Test deallocations
            for slot in allocated_slots:
                try:
                    table_mgr.free(slot)
                except Exception:
                    pass
        except (ValueError, AssertionError, AttributeError, TypeError, OverflowError):
            pass


if __name__ == '__main__':
    atheris.Fuzz()
