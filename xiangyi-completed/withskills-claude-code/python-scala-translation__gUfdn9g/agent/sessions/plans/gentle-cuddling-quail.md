# Python to Scala Tokenizer Translation Plan

## Overview
Translate `/root/Tokenizer.py` to idiomatic Scala 2.13 code, producing `/root/Tokenizer.scala`. The translation must preserve all classes and functions while following Scala best practices and conventions.

## Key Translation Considerations

### 1. Type System & Generics
- **Python**: Flexible runtime typing with overloads; TypeVars with variance (covariant, contravariant)
- **Scala**: Static typing; use type parameters with variance annotations (+T, -T)
- Scala's sealed trait hierarchy for Token types instead of Python enums
- Use `Option[T]` instead of nullable types for safe handling of absence

### 2. Enums and ADTs
- `TokenType` enum → Scala sealed trait hierarchy with case objects
- Immutable case classes for `Token`, `MutableTokenBatch`
- Use pattern matching instead of isinstance checks

### 3. Protocols & Structural Typing
- `Tokenizable`, `HasLength`, `TokenProcessor` → Scala traits
- Focus on composition and trait mixing rather than protocol checking

### 4. Collections & Mutability
- Python lists → Scala immutable collections (List, Vector) by default
- `MutableTokenBatch` → Use Scala `ArrayBuffer` or explicit `var` fields
- Covariant container (`TokenContainer[+T]`) → Use immutable Seq[T]
- Contravariant sink (`TokenSink[-T]`) → Custom implementation with type bounds

### 5. Error Handling
- Python's `None` returns → `Option[T]`
- Python's `RuntimeError`, `ValueError` → Scala exception hierarchy
- Use `Try[T]` for operations that may fail

### 6. Higher-Order Functions
- Python's `Callable` types → Scala function types (e.g., `T => String`)
- Use function values and partial application

### 7. JSON Processing
- Python's `json` module → Scala's `spray-json` or `play-json` (optional; can use string-based approach)
- Recursive types → Scala sealed trait for JSON structure

### 8. Builder Pattern
- Method chaining with generic return types → Scala's fluent builder with self types or explicit builder class
- Return type `TokenizerBuilder[T]` → Use self type or abstract type members

## Implementation Structure

### File: `/root/Tokenizer.scala`

1. **TokenType Sealed Hierarchy** (replaces enum)
   - `sealed trait TokenType`
   - Case objects: `STRING`, `NUMERIC`, `TEMPORAL`, `STRUCTURED`, `BINARY`, `NULL`

2. **Core Data Classes**
   - `Token(value: String, tokenType: TokenType, metadata: Map[String, Any])`
   - `withMetadata(kwargs: (String, Any)*): Token` method
   - `MutableTokenBatch` with add() and mark_processed()

3. **Generic Containers**
   - `TokenContainer[+T]` (covariant) for immutable collections
   - `TokenSink[-T]` (contravariant) for consuming items
   - `BivariantHandler[T]` (invariant) for getting/setting

4. **Tokenizer Trait & Implementations**
   - `trait BaseTokenizer[T]` with abstract `tokenize(value: T): Token`
   - `tokenizeBatch(values: Iterable[T]): Iterator[Token]` as concrete method
   - `StringTokenizer(encoding: String, normalizer: String => String)`
   - `NumericTokenizer(precision: Int, formatOptions: Map[String, Any])`
   - `TemporalTokenizer(formatStr: Option[String])`
   - `UniversalTokenizer` with pattern matching dispatch
   - `WhitespaceTokenizer` with all processing options
   - `JsonTokenizer` (recursive type handling)

5. **Registry and Handlers**
   - `TokenRegistry[T]` with nested generics
   - Pattern matching over handlers

6. **Functional Abstractions**
   - `TokenFunctor[T]` with map/flatMap/getOrElse
   - `TokenMonad[T]` extending TokenFunctor with pure/ap

7. **Builder Pattern**
   - `TokenizerBuilder[T]` with method chaining
   - Returns a function `T => Token`

## Scala Conventions Applied

1. **Naming**: CamelCase for classes/traits, camelCase for methods/variables (matching Python)
2. **Immutability**: Prefer `val`, immutable collections by default
3. **Type Safety**: Use sealed hierarchies and pattern matching
4. **Error Handling**: `Option[T]`, `Either[Throwable, T]`, or exceptions as appropriate
5. **Functional Style**: Higher-order functions, composition, type classes where applicable

## File Organization

```scala
// Top-level structure
package tokenizer

// 1. Sealed trait for TokenType
sealed trait TokenType { def value: String }

// 2. Token and related classes
case class Token(...)
case class MutableTokenBatch(...)

// 3. Traits for protocols
trait Tokenizable { def toToken: String }
trait HasLength { def length: Int }

// 4. Generic containers
class TokenContainer[+T](items: Seq[T])
class TokenSink[-T]
class BivariantHandler[T]

// 5. Base tokenizer trait
trait BaseTokenizer[T] { ... }

// 6. Concrete tokenizers
class StringTokenizer(...)
class NumericTokenizer(...)
class TemporalTokenizer(...)
class UniversalTokenizer(...)
class WhitespaceTokenizer(...)
class JsonTokenizer(...)

// 7. Registry
class TokenRegistry[T] { ... }

// 8. Functor/Monad abstractions
class TokenFunctor[T](value: T)
class TokenMonad[T]

// 9. Builder
class TokenizerBuilder[T] { ... }

// 10. Top-level helper functions
def toToken[T](value: T, tokenizer: BaseTokenizer[T]): Token
def tokenize[T](value: T, tokenizer: BaseTokenizer[T]): Token
def tokenizeBatch[T](values: Seq[T], tokenizer: BaseTokenizer[T]): Seq[Token]
def withMetadata(token: Token, metadata: (String, Any)*): Token
```

## Status: ✅ COMPLETED

The Scala translation has been successfully implemented and compiled.

### Compilation Results
- **Scala Version**: Scala 2.13.12
- **File**: `/root/Tokenizer.scala` (767 lines, 20KB)
- **Compilation Status**: ✅ Success (only minor deprecation warnings)
- **Generated Classes**: 50+ compiled classes in tokenizer package

## Verification & Testing

1. **Compilation**: Ensure code compiles with Scala 2.13
   ```bash
   scalac -version  # Verify Scala 2.13+
   scalac Tokenizer.scala  # Compile
   ```
   ✅ Verified with Scala 2.13.12

2. **Functional Testing**:
   - Create token from string → verify StringTokenizer
   - Create token from numeric → verify NumericTokenizer
   - Create token from datetime → verify TemporalTokenizer
   - WhitespaceTokenizer text splitting → verify token extraction
   - Builder pattern method chaining → verify fluent interface
   - Metadata operations → verify immutability
   - UniversalTokenizer dispatch → verify type-based routing

3. **Type Safety**:
   - Verify generic constraints are enforced
   - Check variance annotations work as expected
   - Ensure pattern matching covers all cases

## Critical Files
- Source: `/root/Tokenizer.py` (582 lines)
- Target: `/root/Tokenizer.scala` (to be created)

## Implementation Notes

1. **Numeric Type Constraints**: Use type bounds `T <: Number` or pattern matching on actual types
2. **JSON Handling**: Use recursive sealed trait for JSON values instead of Union types
3. **Mutable Defaults**: Scala naturally avoids mutable default arguments (immutable by default)
4. **Lambda Conversions**: Python's `lambda x: x` → Scala's `identity` or `(x: T) => x`
5. **String Formatting**: Use Scala string interpolation `f"${value}%.6f"` for formatting
6. **DateTime Handling**: Use `java.time` API (Scala/Java standard)
