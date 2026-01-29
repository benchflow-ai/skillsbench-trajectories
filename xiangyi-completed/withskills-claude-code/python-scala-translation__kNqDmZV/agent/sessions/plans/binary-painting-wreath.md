# Python to Scala Code Translation Plan

## Project Overview
Translate `/root/Tokenizer.py` (Python tokenizer module with advanced type system features) to idiomatic Scala (2.13) at `/root/Tokenizer.scala`.

The Python code demonstrates:
- Generic types with variance (covariant/contravariant)
- Protocol-based structural typing
- Mutable and immutable data structures
- Abstract base classes and inheritance
- Type unions and overloading
- Builder pattern with fluent interface
- Recursive type definitions (JSON)

## Key Translation Challenges & Approach

### 1. Type System Differences
**Python Capabilities:**
- Protocols (structural typing) without inheritance
- TypeVar with variance annotations
- Union types and Optional
- Runtime type checking with isinstance()

**Scala Solutions:**
- Use traits for structural typing (similar to Protocols)
- Use type bounds and variance annotations on type parameters
- Use sealed trait hierarchies for unions (more idiomatic than Option for discriminated types)
- Use pattern matching for type dispatch

### 2. Data Classes & Immutability
**Python:** `@dataclass(frozen=True)` for immutable Token
**Scala:** Use `case class` for immutability and structural equality

### 3. Generic Containers with Variance
**Python:** `TokenContainer(Generic[T_co])` with covariance
**Scala:** Use `+T` for covariance, `-T` for contravariance in trait definitions

### 4. Mutable vs Immutable Collections
**Python:** Mixes mutable and immutable collections
**Scala:**
- Prefer immutable by default (Vector, List, Map)
- Use mutable.Buffer for batch collections when needed
- Use sealed trait hierarchies for algebraic data types

### 5. Protocol-Based Dispatch (Python's duck typing)
**Python:** `isinstance()` checks with `Tokenizable` protocol
**Scala:**
- Use sealed trait hierarchies with pattern matching
- Leverage implicit type classes for stateless tokenizers
- Use method overloading for simple cases

### 6. Builder Pattern
**Python:** Generic `TokenizerBuilder[T]` with method chaining
**Scala:** Use `case class` with `.copy()` for immutable builder or mutable builder pattern with proper cleanup

## Detailed Implementation Plan

### Phase 1: Core Types & Enums
File: `/root/Tokenizer.scala`

1. **Sealed Trait for TokenType** (replaces Enum)
   - `sealed trait TokenType`
   - Case objects: STRING, NUMERIC, TEMPORAL, STRUCTURED, BINARY, NULL

2. **Case Classes for Data**
   - `case class Token(value: String, tokenType: TokenType, metadata: Map[String, Any] = Map.empty)`
   - `case class TokenBatch(tokens: Vector[Token] = Vector.empty, isProcessed: Boolean = false)`

3. **Traits for Protocols**
   - `trait Tokenizable { def toToken: String }`
   - `trait HasLength { def length: Int }`

### Phase 2: Generic Container Classes
Implement with proper variance:
- `trait TokenContainer[+T] { ... }` (covariant)
- `trait TokenSink[-T] { ... }` (contravariant)
- `case class BivariantHandler[T] { ... }` (invariant)

### Phase 3: Base Tokenizer Hierarchy
1. **Sealed Trait Hierarchy**
   ```scala
   sealed trait Tokenizer[T] {
     def tokenize(value: T): Token
     def tokenizeBatch(values: Iterable[T]): Iterator[Token]
   }
   ```

2. **Concrete Implementations**
   - `StringTokenizer` with encoding and normalization
   - `NumericTokenizer` with precision handling
   - `TemporalTokenizer` with format options
   - `WhitespaceTokenizer` with text processing
   - `JsonTokenizer` with recursive JSON handling
   - `UniversalTokenizer` with pattern matching dispatch

### Phase 4: Advanced Generic Patterns
- `TokenRegistry[T]` with Map[String, TokenContainer[T]]
- `TokenFunctor[T]` and `TokenMonad[T]` with map/flatMap
- Implicit conversions or extension methods where needed

### Phase 5: Builder Pattern
- `TokenizerBuilder[T]` using case class with immutable state accumulation
- Method chaining via `.copy()` or alternative builder class

## Scala Idioms & Best Practices to Apply

1. **Pattern Matching over instanceof**
   - Replace Python's `isinstance()` with Scala's pattern matching
   - Use sealed traits for exhaustiveness checking

2. **Case Classes over dataclass**
   - Automatic equals, hashCode, toString, copy
   - Better integration with pattern matching

3. **Sealed Trait Hierarchies**
   - Express unions (Python Union types) as sealed traits
   - Compiler ensures pattern matching exhaustiveness

4. **Implicit Conversions (sparingly)**
   - Use for type class patterns where appropriate
   - Avoid implicit conversions for core logic

5. **Option/Try for Error Handling**
   - Replace Python's None returns with Option[T]
   - Replace exceptions with Try[T] where appropriate

6. **Iterator/Seq for Lazy Evaluation**
   - Keep lazy evaluation for `tokenizeBatch` using Iterator
   - Use appropriate Seq types (Vector for immutability, List for cons-list ops)

7. **Naming Conventions**
   - camelCase for methods/values (not snake_case)
   - PascalCase for types/classes
   - Singleton objects for enums/constants

## File Structure

```
/root/Tokenizer.scala
├── Sealed traits for TokenType
├── Case classes (Token, TokenBatch)
├── Protocol/Structural Traits
├── Generic containers (covariant/contravariant)
├── Base Tokenizer trait
├── Concrete tokenizer implementations
├── Advanced patterns (Functor, Monad, Registry)
├── Builder implementation
└── Utility functions
```

## Critical Files to Modify
- `/root/Tokenizer.scala` (create new file)

## Verification Plan
1. **Compilation Test**: Scala 2.13 compiler should accept the code without errors
2. **Structural Comparison**: Verify all required classes/functions exist and have compatible signatures
3. **Functionality Test**: Create small test cases for:
   - Token creation with metadata
   - StringTokenizer with normalization
   - NumericTokenizer with precision
   - TemporalTokenizer with format strings
   - WhitespaceTokenizer with text processing
   - UniversalTokenizer with multiple input types
   - TokenizerBuilder with method chaining
   - Pattern matching dispatch

## Translation Guidelines
- Preserve functional behavior while leveraging Scala idioms
- Use Scala's standard library (scala.collection, scala.math, java.time)
- Handle errors with Option/Try rather than null/exceptions
- Leverage compiler's type checking (sealed traits, exhaustiveness)
- Maintain readability and clear intent
- No one-to-one word-for-word translation
