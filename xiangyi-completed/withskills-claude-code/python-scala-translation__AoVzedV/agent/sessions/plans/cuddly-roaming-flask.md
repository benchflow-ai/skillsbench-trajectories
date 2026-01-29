# Python to Scala Tokenizer Translation Plan

## Overview
Translate `Tokenizer.py` to idiomatic Scala, maintaining all classes and functions while leveraging Scala's type system, pattern matching, and functional programming capabilities.

## Key Translation Decisions

### 1. **Type System & Variance**
- Python's flexible generics with variance will be translated to Scala's explicit variance annotations
- Use `+T` (covariant) for read-only containers (TokenContainer)
- Use `-T` (contravariant) for write-only containers (TokenSink)
- Use `T` (invariant) for handlers that both read and write (BivariantHandler)

### 2. **Enums**
- `TokenType` enum with sealed case objects matching Python's Enum structure
- Scala's sealed trait pattern provides better exhaustiveness checking than Python's Enum

### 3. **Core Data Structures**
- `Token`: Immutable case class with `metadata` as `Map[String, Any]`
- Remove `MutableTokenBatch` and replace with functional patterns (List[Token])
- `TokenContainer[+T]`, `TokenSink[-T]`, `BivariantHandler[T]`: Case classes with generic type parameters

### 4. **Abstract Base Tokenizer**
- `BaseTokenizer[T]` as abstract trait with `tokenize(value: T): Token` method
- `tokenizeBatch(values: Iterable[T]): Iterator[Token]` implementation using `map().toIterator`
- Create concrete implementations: `StringTokenizer`, `NumericTokenizer`, `TemporalTokenizer`

### 5. **String Handling**
- Replace `Callable[[str], str] | None` with `Option[String => String]`
- Use `Option` for optional normalizers
- Default to identity function using `identity` from scala.Predef

### 6. **Numeric Tokenizer**
- Remove mutable default argument anti-pattern
- Use sealed trait for numeric types: `sealed trait NumericValue`
- Leverage pattern matching for formatting logic

### 7. **Temporal Tokenizer**
- Use `java.time.LocalDateTime` and `java.time.LocalDate` (Java 8 time API)
- Format strings using `java.time.format.DateTimeFormatter`

### 8. **UniversalTokenizer**
- Use Scala's type classes pattern instead of method overloads
- Create sealed trait `Tokenizable` and implement for each type
- Use pattern matching in `tokenize` method with exhaustiveness checking

### 9. **Higher-Order Functions**
- Replace Python's `Callable` with Scala function types: `T => U`
- Use `=>` for pass-by-name and `T => U` for function values

### 10. **Generics & Collections**
- `TokenRegistry[T]`: Use `Map[String, TokenContainer[T]]` and `Vector[T => Option[Token]]`
- Prefer immutable collections: `Vector` over `List` for better performance on random access
- Use `scala.collection.immutable` explicitly where needed

### 11. **Option/Try Instead of Null**
- Replace `Token | None` with `Option[Token]`
- Use `Option` for optional values throughout
- Consider `Try` for error-prone operations if needed

### 12. **JSON Handling**
- Use `play-json` or `scala.util.parsing.json` for JSON operations
- Recursive types: Use `sealed trait JsonValue` with case objects/classes

### 13. **Builder Pattern**
- Maintain fluent builder using case class with copy method
- Return `this.type` for proper type safety in chaining

### 14. **WhitespaceTokenizer**
- Convert to case class with optional parameters
- Use `String.split()` and Scala collections API
- Leverage `flatMap`, `filter` for functional processing

### 15. **Special Cases**
- Remove `TokenMonad` and keep only practical `TokenFunctor`
- Simplify higher-kinded type simulation - not needed in Scala for this use case
- Remove `TokenProcessor` protocol - not necessary with Scala's type system

## File Structure

**Output: `/root/Tokenizer.scala`**

```
object Tokenizer {
  // Type aliases
  type Tokenizable = ... // trait with toToken(): String

  // Sealed traits for safe pattern matching
  sealed trait TokenType
  case object StringToken extends TokenType
  case object NumericToken extends TokenType
  // ...

  // Case classes for immutable data
  case class Token(...)
  case class TokenContainer[+T](...)
  case class TokenSink[-T](...)
  case class BivariantHandler[T](...)

  // Abstract trait for base tokenizer
  sealed trait BaseTokenizer[T] { ... }
  case class StringTokenizer(...) extends BaseTokenizer[String | Bytes]
  case class NumericTokenizer(...) extends BaseTokenizer[NumericValue]
  case class TemporalTokenizer(...) extends BaseTokenizer[LocalDateTime | LocalDate]

  // Utility tokenizers
  case class UniversalTokenizer(...)
  case class TokenRegistry[T](...)
  case class TokenFunctor[T](...)
  case class JsonTokenizer(...)
  case class WhitespaceTokenizer(...)

  // Builder
  case class TokenizerBuilder[T](...)

  // Top-level functions
  def tokenize[T](value: T): Token = ...
  def tokenizeBatch[T](values: Iterable[T]): Iterator[Token] = ...
  def toToken[T](value: T): String = ...
  def withMetadata(token: Token, metadata: (String, Any)*): Token = ...
}
```

## Naming Conventions
- Functions: `camelCase` (tokenize, tokenizeBatch, toToken, withMetadata)
- Types/Classes: `PascalCase` (Token, TokenType, BaseTokenizer)
- Type variables: `T`, `U`, `F` (single uppercase letters)
- Constants: `UPPER_CASE` (ISO_FORMAT, DATE_FORMAT)
- Private fields: `_fieldName` (Scala convention)

## Dependencies
- scala.collection.immutable (standard library)
- java.time (for temporal handling)
- Optional: play-json for JSON (if not in stdlib)

## Implementation Steps
1. Set up sealed traits for TokenType and numeric values
2. Implement Token case class with metadata
3. Implement generic containers (TokenContainer, TokenSink, BivariantHandler)
4. Implement BaseTokenizer trait and concrete implementations
5. Implement UniversalTokenizer with pattern matching
6. Implement TokenRegistry with functional approach
7. Implement JsonTokenizer (optional - if play-json available)
8. Implement WhitespaceTokenizer
9. Implement TokenizerBuilder with fluent interface
10. Add top-level helper functions
11. Verify compilation with Scala 2.13

## Testing & Verification
- Compile with `scalac` to ensure Scala 2.13 compatibility
- Verify all required functions exist and have correct signatures:
  - TokenType, Token, BaseTokenizer, StringTokenizer, NumericTokenizer
  - TemporalTokenizer, UniversalTokenizer, WhitespaceTokenizer
  - TokenizerBuilder, tokenize, tokenizeBatch, toToken, withMetadata
- Validate generic variance works correctly
- Check that pattern matching is exhaustive
