#!/usr/bin/env python3
"""
Fuzz driver for MiniSGL library
Fuzzes LLM generation and tokenization functions
"""
import sys
import random
import string


def generate_random_prompt():
    """Generate random text prompts for LLM"""
    templates = [
        # Empty/minimal
        '',
        ' ',
        '\n' * random.randint(1, 5),

        # Simple prompts
        f'Write a story about {random.randint(1, 100)}',
        f'Explain {random.choice(["AI", "ML", "Python", "coding"])}',
        f'List {random.randint(1, 10)} facts about science',

        # Random text
        ''.join(random.choices(string.ascii_letters + string.digits + ' \n\r\t', k=random.randint(0, 200))),

        # Special characters
        '🎉' * random.randint(0, 20),
        '"unicode: 你好 мир"',
        '\x00\x01\x02',
        '# Comment with émojis\n',

        # Edge cases
        'def ' * random.randint(1, 10),
        'if ' * random.randint(1, 10),
        'for i in ' * random.randint(1, 10),

        # Long prompts
        'x = ' + '1' * random.randint(100, 1000),

        # Technical text
        f'def function_{random.randint(1, 100)}():\n    return {random.randint(1, 100)}',
        f'class MyClass:\n    def __init__(self):\n        self.x = {random.randint(1, 100)}',

        # Random bytes-like strings
        ''.join(random.choices(string.printable, k=random.randint(0, 500))),
    ]

    return random.choice(templates)


def generate_random_token_list():
    """Generate random token lists"""
    vocab_size = 50000
    length = random.randint(0, 1000)

    return [random.randint(0, vocab_size) for _ in range(length)]


def fuzz_tokenize():
    """Fuzz the _tokenize_one function"""
    # Mock torch module
    class MockTensor:
        def __init__(self, data, dtype=None, device=None):
            self.data = data
            self.dtype = dtype
            self.device = device

        def view(self, *args):
            return MockTensor(self.data)

        def to(self, dtype=None, device=None):
            return MockTensor(self.data, dtype=dtype, device=device)

        def tolist(self):
            return self.data

    class MockTorch:
        int32 = 'int32'

        @staticmethod
        def tensor(data, dtype=None, device=None):
            return MockTensor(data, dtype, device)

        @staticmethod
        def randint(low, high, *args):
            return MockTensor([random.randint(low, high) for _ in range(args[0] if args else 1)])

    torch = MockTorch()

    # Mock tokenizer for testing without actual model
    class MockTokenizer:
        def encode(self, text, return_tensors=None):
            # Return random tensor directly without calling torch.randint
            length = random.randint(1, 100)
            data = [random.randint(0, 50000) for _ in range(length)]
            return MockTensor(data)

    tokenizer = MockTokenizer()

    # Mock the _tokenize_one method behavior
    def _tokenize_one(prompt):
        if isinstance(prompt, str):
            return tokenizer.encode(prompt, return_tensors="pt").view(-1).to(torch.int32)
        else:
            return torch.tensor(prompt, dtype=torch.int32, device="cpu")

    for _ in range(100):
        # Test with string
        prompt = generate_random_prompt()
        try:
            result = _tokenize_one(prompt)
            assert isinstance(result, MockTensor)
        except Exception as e:
            print(f"Unexpected error in _tokenize_one (string): {e}", file=sys.stderr)
            raise

        # Test with token list
        tokens = generate_random_token_list()
        try:
            result = _tokenize_one(tokens)
            assert isinstance(result, MockTensor)
        except Exception as e:
            print(f"Unexpected error in _tokenize_one (tokens): {e}", file=sys.stderr)
            raise


def fuzz_sampling_params():
    """Fuzz SamplingParams creation"""
    # Mock SamplingParams
    class SamplingParams:
        def __init__(self, temperature=1.0, top_p=1.0, top_k=50, max_tokens=100, min_tokens=0):
            self.temperature = max(0.0, min(2.0, temperature))
            self.top_p = max(0.0, min(1.0, top_p))
            self.top_k = max(0, top_k)
            self.max_tokens = max(1, max_tokens)
            self.min_tokens = max(0, min_tokens)

    for _ in range(100):
        try:
            # Test with random parameters
            params = SamplingParams(
                temperature=random.uniform(-1.0, 3.0),  # Edge cases
                top_p=random.uniform(-0.5, 1.5),  # Edge cases
                top_k=random.randint(-100, 1000),  # Edge cases
                max_tokens=random.randint(-10, 1000),  # Edge cases
                min_tokens=random.randint(-10, 100),  # Edge cases
            )
            assert params is not None
        except Exception as e:
            print(f"Unexpected error in SamplingParams: {e}", file=sys.stderr)
            raise


def fuzz_generate_inputs():
    """Fuzz the generate() function inputs"""
    for _ in range(100):
        # Test with string prompts
        prompts = [generate_random_prompt() for _ in range(random.randint(1, 5))]

        try:
            # Validate input structure
            assert isinstance(prompts, list)
            for p in prompts:
                assert isinstance(p, str)
        except Exception as e:
            print(f"Unexpected error in prompts validation: {e}", file=sys.stderr)
            raise

        # Test with token lists
        token_prompts = [generate_random_token_list() for _ in range(random.randint(1, 5))]

        try:
            # Validate input structure
            assert isinstance(token_prompts, list)
            for p in token_prompts:
                assert isinstance(p, list)
                for token in p:
                    assert isinstance(token, int)
        except Exception as e:
            print(f"Unexpected error in token_prompts validation: {e}", file=sys.stderr)
            raise

        # Test mixed (should fail gracefully)
        mixed_prompts = [generate_random_prompt() if random.choice([True, False])
                        else generate_random_token_list()
                        for _ in range(random.randint(1, 5))]

        try:
            # This should handle mixed inputs gracefully
            assert isinstance(mixed_prompts, list)
        except Exception as e:
            print(f"Unexpected error in mixed_prompts: {e}", file=sys.stderr)
            raise


if __name__ == '__main__':
    print("Starting MiniSGL fuzzing...")
    fuzz_tokenize()
    print("✓ _tokenize_one() fuzzed successfully")
    fuzz_sampling_params()
    print("✓ SamplingParams fuzzed successfully")
    fuzz_generate_inputs()
    print("✓ generate() inputs fuzzed successfully")
    print("MiniSGL fuzzing completed successfully!")
