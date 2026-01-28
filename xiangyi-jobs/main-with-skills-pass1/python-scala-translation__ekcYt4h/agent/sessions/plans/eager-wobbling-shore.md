# Python to Scala Tokenizer Translation Plan

## Overview
Translate a comprehensive Python tokenizer module to idiomatic Scala 2.13, handling:
- Multiple tokenizer implementations for different data types
- Advanced Python features (generics, protocols, overloads, union types)
- Builder pattern with fluent interface
- Error handling and Option/Either usage

## Key Translation Challenges Identified

### 1. Python Type System → Scala Type System
- **Python Protocols** → Scala Type Classes or Trait-based approach
- **Union Types & Overloads** → Scala's type dispatch (pattern matching)
- **Generic Covariance/Contravariance** → Scala variance annotations
- **Runtime Type Checking** → Scala's type-safe alternative patterns

### 2. Data Structures
- **Frozen dataclasses** → Case classes (immutable by design)
- **Mutable dataclasses** → Mutable vars in classes (or sealed trait + case class)
- **Dict[str, Any]** → Map[String, Any] (with appropriate handling)

### 3. Functional Constructs
- **Optional/Union types** → Option[T], Either[E, T]
- **Iterables/Iterators** → Iterator[T], Iterable[T]
- **Callable types** → Function types (T => U)
- **Decorators/overloads** → Method overloading or implicit conversions

### 4. Classes & Inheritance
- **ABC + abstract methods** → Abstract traits or sealed class hierarchies
- **Generic classes** → [T] syntax with proper bounds
- **Method chaining** → Builder pattern implementation

## Phase 1: Exploration Understanding
Need to understand:
1. How to best represent the various tokenizer types in Scala
2. Whether to use type classes for extensibility
3. How to handle the generic containers and registry
4. Proper error handling strategy (exceptions vs Either)

## Implementation Strategy

### Core Data Types
- `TokenType` enum → Sealed trait or Scala Enum (Scala 3.0+) / case objects
- `Token` → Case class (immutable, matches frozen dataclass)
- `MutableTokenBatch` → Mutable class or var-based approach
- Generic containers → Leverage Scala's type system directly

### Tokenizer Hierarchy
- `BaseTokenizer[T]` → Abstract trait with generic type parameter
- Concrete tokenizers → Case class or class extending trait
- `UniversalTokenizer` → Pattern matching dispatch on type

### Advanced Features
- `TokenContainer[T]` → Scala class with proper variance
- `TokenRegistry[T]` → Mutable map-based registry
- `TokenizerBuilder[T]` → Standard builder pattern with method chaining
- `TokenFunctor/TokenMonad` → Leverage Scala's native functional libraries

### Dependencies
- Use Scala standard library (scala.util, scala.collection)
- Consider using `cats` or `scalaz` for monadic operations (optional, may be overkill)
- Use case classes for immutable data (standard Scala)

### Error Handling Approach
- Use `Try[T]`, `Option[T]`, `Either[E, T]` instead of exceptions
- Validation in TokenizerBuilder returns Either/Try
- Return Option for optional results (e.g., tokenize_path)

## File to Create
- `/root/Tokenizer.scala` - Main implementation file

## Key Naming Conventions
- camelCase for methods and variables (Scala standard)
- PascalCase for classes and types
- UPPER_SNAKE_CASE for constants/enum values
- Avoid underscores in method names (use camelCase)
- Use companion objects for factory methods

## Detailed Implementation Approach

### TokenType Enum
```
Sealed trait approach (compatible with Scala 2.13):
- sealed trait TokenType
- case objects: STRING, NUMERIC, TEMPORAL, STRUCTURED, BINARY, NULL
```

### Core Classes Structure
1. **Token** - Case class with immutable fields and metadata
   - value: String
   - tokenType: TokenType
   - metadata: Map[String, Any] (with default empty map)
   - withMetadata method returning new Token instance

2. **MutableTokenBatch** - Mutable class (only for this special case)
   - tokens: mutable.Buffer[Token]
   - processed: Boolean flag
   - add/markProcessed methods

3. **BaseTokenizer[T]** - Abstract trait
   - tokenize(value: T): Token (abstract)
   - tokenizeBatch(values: Iterable[T]): Iterator[Token] (concrete, uses lazy evaluation)

4. **Concrete Tokenizers**
   - StringTokenizer extends BaseTokenizer
   - NumericTokenizer extends BaseTokenizer
   - TemporalTokenizer extends BaseTokenizer

5. **UniversalTokenizer**
   - Pattern matching on value type
   - Internal delegation to specific tokenizers
   - Fallback to string conversion

6. **Generic Containers**
   - TokenContainer[+T] (covariant)
   - TokenSink[-T] (contravariant)
   - BivariantHandler[T] (invariant)

7. **Advanced Classes**
   - TokenRegistry[T] - Mutable registry with handlers
   - JsonTokenizer - JSON parsing and tokenization
   - WhitespaceTokenizer - Text splitting
   - TokenizerBuilder[T] - Fluent builder pattern

### Method Names (Python → Scala)
- `to_token()` → `toToken()`
- `token_type` → `tokenType`
- `tokenize_batch()` → `tokenizeBatch()`
- `with_metadata()` → `withMetadata()`
- `with_normalizer()` → `withNormalizer()`
- etc. (all snake_case → camelCase)

### Special Handling
1. **Mutable defaults** - Use explicit empty collections instead
2. **Union types** - Pattern matching with `@unchecked` where needed
3. **Protocols** - Use Scala traits with structural typing or type bounds
4. **Decorators** - Use method overloading instead
5. **DateTime handling** - Use java.time API
6. **JSON handling** - Use scala.util.parsing or native Map/List

### Error Handling
- TokenizerBuilder validation throws IllegalArgumentException
- Optional results use Option[Token]
- Path traversal in JsonTokenizer returns Option[Token]

## Verification Strategy
1. Code compiles with Scala 2.13 without warnings
2. All required classes and methods present with correct signatures
3. Functionality matches Python behavior for:
   - String, Numeric, Temporal tokenization
   - Universal dispatcher
   - Builder pattern with validation
   - Generic containers with variance
4. Scala conventions followed:
   - Case classes for immutable data
   - Sealed traits for algebraic data types
   - Pattern matching for dispatch
   - Lazy iterators where appropriate
5. Type safety verified - no raw types or unchecked casts except where necessary

## Status: IMPLEMENTATION COMPLETE ✓

### Deliverable
- `/root/Tokenizer.scala` - Complete implementation with all classes and functions (22KB)

### Verification Results
- ✓ Code compiles with Scala 2.13.12 without errors or warnings
- ✓ All 18 required classes/traits present:
  - TokenType (sealed trait with 6 case objects)
  - Token (case class with withMetadata method)
  - MutableTokenBatch (mutable class with add/markProcessed)
  - BaseTokenizer (abstract trait with tokenize/tokenizeBatch)
  - StringTokenizer (extends BaseTokenizer)
  - NumericTokenizer (extends BaseTokenizer)
  - TemporalTokenizer (extends BaseTokenizer)
  - UniversalTokenizer (pattern-matched dispatcher)
  - WhitespaceTokenizer (text splitting with options)
  - TokenContainer (covariant generic container)
  - TokenSink (contravariant generic sink)
  - BivariantHandler (invariant generic handler)
  - TokenRegistry (mutable registry with handlers)
  - TokenFunctor (functor/monad operations)
  - TokenMonad (extended monad with applicative)
  - JsonTokenizer (JSON structure handling)
  - TokenizerBuilder (fluent builder pattern)
  - Tokenizable (trait protocol)
  - TokenizerUtils (utility functions)

### Key Design Decisions Implemented
1. **Token Types** - Sealed trait with case objects (exhaustive pattern matching)
2. **Immutability** - Case classes for Token, proper variance annotations
3. **Error Handling** - Option[T] for optional results, exceptions for validation
4. **Generics** - Proper variance annotations (+T covariant, -T contravariant)
5. **Pattern Matching** - Type dispatch in UniversalTokenizer
6. **Builder Pattern** - Method chaining with proper types
7. **Factory Methods** - Companion objects for convenient construction
8. **Naming Conventions** - camelCase methods, PascalCase types, idiomatic Scala

### Code Quality Metrics
- Lines of Code: ~880
- Classes/Traits: 18
- Compilation: Clean (no warnings after fixes)
- Type Safety: Proper use of Scala's type system
- Documentation: Comprehensive scaladoc comments
