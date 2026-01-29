# Spring Boot 2.7 to 3.2 Migration Plan

## Overview
Migrate a legacy user management microservice from Java 8/Spring Boot 2.7 to Java 21/Spring Boot 3.2. The microservice includes REST API endpoints, JWT authentication, role-based access control, JPA/Hibernate persistence, and RestTemplate-based external API calls.

## Key Migrations Required

### 1. Maven Dependencies & Java Version
**Files:** `/workspace/pom.xml`

Changes:
- Update Spring Boot parent version from 2.7.18 to 3.2.x
- Update Java version from 1.8 to 21
- Update JJWT from 0.9.1 to 0.12.x (JWT support, fixes deprecated warnings)
- Remove javax.xml.bind:jaxb-api (no longer needed - jakarta.xml.bind included in Spring Boot 3)
- Ensure all Spring dependencies resolve to compatible versions via parent pom

### 2. Jakarta EE Namespace Migration
**Files affected:**
- `/workspace/src/main/java/com/example/userservice/model/User.java`
- `/workspace/src/main/java/com/example/userservice/controller/UserController.java`
- `/workspace/src/main/java/com/example/userservice/service/UserService.java`
- `/workspace/src/main/java/com/example/userservice/repository/UserRepository.java`
- `/workspace/src/main/java/com/example/userservice/config/SecurityConfig.java`

Changes:
- Replace `javax.persistence.*` with `jakarta.persistence.*`
- Replace `javax.validation.*` with `jakarta.validation.*`
- Replace `javax.servlet.*` with `jakarta.servlet.*`

### 3. Spring Security 6 Configuration
**File:** `/workspace/src/main/java/com/example/userservice/config/SecurityConfig.java`

Changes:
- Remove extends `WebSecurityConfigurerAdapter` (deprecated)
- Replace `@EnableGlobalMethodSecurity(prePostEnabled = true)` with `@EnableMethodSecurity`
- Implement SecurityFilterChain bean instead
- Replace `configure(HttpSecurity)` with SecurityFilterChain bean
- Replace `configure(AuthenticationManagerBuilder)` with UserDetailsService bean
- Replace `antMatchers()` with `requestMatchers()` in authorization rules
- Update lambda DSL syntax for modern Spring Security 6

### 4. RestTemplate to RestClient Migration
**File:** `/workspace/src/main/java/com/example/userservice/service/ExternalApiService.java`

Changes:
- Replace RestTemplate with new Spring Boot 3.2+ RestClient
- Update constructor to create RestClient bean via factory method
- Migrate all HTTP methods:
  - `restTemplate.getForEntity()` → `restClient.get().uri().retrieve().body()`
  - `restTemplate.postForEntity()` → `restClient.post().uri().body().retrieve().body()`
  - `restTemplate.exchange()` → `restClient.method().uri().retrieve().body()`
  - `restTemplate.delete()` → `restClient.delete().uri().retrieve().toBodilessEntity()`
- Keep error handling patterns (catch exceptions, return defaults)

### 5. Hibernate 6 Configuration
**File:** `/workspace/src/main/resources/application.properties`

Changes:
- Update `spring.jpa.database-platform` from `org.hibernate.dialect.H2Dialect` to use latest H2 dialect
- Spring Boot 3.2 auto-configures Hibernate 6 compatibility
- ID generation strategy (IDENTITY) already compatible with Hibernate 6
- No additional Hibernate-specific code changes needed

## Implementation Order

1. **Update pom.xml** - Dependencies and Java version
2. **Migrate SecurityConfig** - Remove WebSecurityConfigurerAdapter, implement SecurityFilterChain
3. **Migrate jakarta imports** - All model, controller, service files
4. **Migrate ExternalApiService** - RestTemplate to RestClient
5. **Verify and test** - Run `mvn clean compile` and `mvn test`

## Critical Files to Modify

1. `/workspace/pom.xml` - Dependencies
2. `/workspace/src/main/java/com/example/userservice/config/SecurityConfig.java` - Security config
3. `/workspace/src/main/java/com/example/userservice/service/ExternalApiService.java` - RestClient migration
4. `/workspace/src/main/java/com/example/userservice/model/User.java` - Jakarta imports
5. `/workspace/src/main/java/com/example/userservice/controller/UserController.java` - Jakarta imports
6. `/workspace/src/main/java/com/example/userservice/service/UserService.java` - Jakarta imports

## Verification

After migration:
1. Run `mvn clean compile` - Should complete with no errors
2. Run `mvn test` - All 6 integration tests should pass
3. Tests verify:
   - User creation with validation
   - User retrieval by ID
   - User updates
   - User deactivation
   - Duplicate username prevention
   - Context loading

## Notes

- The application uses H2 in-memory database for testing and development
- JWT support updated to JJWT 0.12.x (maintains compatibility)
- No changes needed to business logic - only framework/dependency updates
- All security annotations (@PreAuthorize) remain unchanged
- Custom UserDetailsService requires no changes for Spring Security 6
- ExternalApiService doesn't require SecurityConfig changes for RestClient usage
