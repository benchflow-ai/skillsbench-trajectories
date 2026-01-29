# Spring Boot 2.7 to 3.2 & Java 8 to 21 Migration Plan

## Executive Summary
Migrate legacy user management microservice from Java 8/Spring Boot 2.7 to Java 21/Spring Boot 3.2. Key changes: namespace migration (javax → jakarta), Spring Security 6 configuration, Hibernate 6 compatibility, and RestTemplate → RestClient migration.

## Critical Files to Modify

1. **pom.xml** - Update versions and dependencies
2. **src/main/java/com/example/userservice/config/SecurityConfig.java** - Spring Security 6 migration
3. **src/main/java/com/example/userservice/service/ExternalApiService.java** - RestTemplate → RestClient
4. **src/main/java/com/example/userservice/config/CustomUserDetailsService.java** - Check for namespace issues
5. **src/main/java/com/example/userservice/model/User.java** - JPA namespace migration
6. **src/main/java/com/example/userservice/exception/GlobalExceptionHandler.java** - Namespace migration
7. **src/main/java/com/example/userservice/controller/UserController.java** - Namespace migration (validation)
8. **src/main/java/com/example/userservice/dto/CreateUserRequest.java** - Namespace migration (validation)

## Migration Steps

### Phase 1: POM.xml Updates
- Update Spring Boot parent from 2.7.18 to 3.2.x
- Update Java version from 1.8 to 21
- Remove/update deprecated dependencies:
  - Remove old jjwt (0.9.1) - use newer version (0.12.x)
  - Remove jaxb-api javax dependency (Jakarta provides this)
  - Update all other dependencies to compatible versions with Spring Boot 3.2

### Phase 2: Namespace Migration (javax → jakarta)
- `javax.persistence.*` → `jakarta.persistence.*`
- `javax.servlet.*` → `jakarta.servlet.*`
- `javax.validation.*` → `jakarta.validation.*`
- Files affected:
  - User.java (JPA annotations)
  - UserService.java (EntityNotFoundException)
  - GlobalExceptionHandler.java (servlet, persistence imports)
  - SecurityConfig.java (servlet imports)
  - UserController.java (validation annotations)
  - CreateUserRequest.java (validation annotations)

### Phase 3: Spring Security 6 Migration
**SecurityConfig.java** - Major refactoring required:
- Remove WebSecurityConfigurerAdapter extension
- Replace configure(AuthenticationManagerBuilder) with AuthenticationProvider bean or UserDetailsService injection
- Replace configure(HttpSecurity) with SecurityFilterChain bean
- Replace `@EnableGlobalMethodSecurity(prePostEnabled = true)` with `@EnableMethodSecurity`
- Replace deprecated HttpSecurity methods:
  - `csrf().disable()` → `csrf(csrf -> csrf.disable())`
  - `sessionManagement().sessionCreationPolicy()` → lambda DSL
  - `authorizeRequests()` → `authorizeHttpRequests()`
  - `antMatchers()` → `requestMatchers()`
  - `and()` → removed (use lambda chaining)
  - Custom authenticationEntryPoint setup in exceptionHandling
  - `headers().frameOptions().disable()` → `headers(headers -> headers.frameOptions().disable())`

### Phase 4: RestTemplate → RestClient Migration
**ExternalApiService.java** changes:
- Replace RestTemplate construction with RestClient.create()
- Update GET requests: `restTemplate.getForEntity()` → `restClient.get().uri().retrieve()`
- Update POST requests: `restTemplate.postForEntity()` → `restClient.post().uri().body().retrieve()`
- Update DELETE requests: `restTemplate.delete()` → `restClient.delete().uri().retrieve()`
- Update EXCHANGE requests: Use RestClient's fluent API
- Add RestClient bean if needed in SecurityConfig or separate config class

### Phase 5: Hibernate 6 Compatibility
- Validate JPA queries use JPQL (not HQL-specific syntax)
- Check UserRepository queries - should be compatible
- Ensure cascade configurations are correct
- Test database operations with new version

### Phase 6: Additional Updates
- **CustomUserDetailsService.java** - Validate no deprecated APIs used
- **UserDTO.java** - No changes needed (plain POJO)
- **Role.java** - No changes needed (enum)
- **UserRepository.java** - Verify JPQL queries compatible with Hibernate 6
- Update application.properties if needed (Hibernate dialect already set correctly)

## Execution Checklist

1. Update pom.xml with new versions
2. Update all namespace imports (javax → jakarta)
3. Refactor SecurityConfig.java
4. Migrate ExternalApiService.java to RestClient
5. Add RestClient bean configuration if needed
6. Update all other imports systematically
7. Run `mvn clean compile` - should have zero errors
8. Run `mvn test` - all tests should pass

## Verification

After migration:
1. Code compiles without errors: `mvn clean compile`
2. All unit tests pass: `mvn test`
3. Application starts successfully
4. Key functionality verified:
   - User CRUD operations work
   - JWT authentication functions
   - Role-based access control enforced
   - External API calls via RestClient function

## Known Breaking Changes to Handle
- WebSecurityConfigurerAdapter removed - must use SecurityFilterChain bean
- EnableGlobalMethodSecurity moved to EnableMethodSecurity
- RestTemplate deprecated - migrate to RestClient
- javax.* packages moved to jakarta.*
- JAXB support moved to separate dependency (but Spring Boot 3 includes it)
