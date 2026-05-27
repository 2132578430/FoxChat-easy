# ============================================
# Stage 1: Build fat JAR with Gradle
# ============================================
FROM gradle:9.4.0-jdk17 AS build
WORKDIR /app

# Copy build scripts first (layer caching)
COPY gradle gradle
COPY gradlew gradlew
COPY build.gradle settings.gradle ./
COPY gradle/libs.versions.toml gradle/libs.versions.toml

# Pre-download dependencies (cacheable layer)
RUN ./gradlew dependencies --no-daemon || true

# Copy source code
COPY foxChat-common foxChat-common
COPY foxChat-pojo foxChat-pojo
COPY foxChat-service foxChat-service
COPY foxChat-netty foxChat-netty
COPY foxChat-web foxChat-web

# Build fat JAR (skip tests for CI speed)
RUN ./gradlew :foxChat-web:bootJar --no-daemon -x test

# ============================================
# Stage 2: Minimal JRE runtime
# ============================================
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

# Copy built JAR
COPY --from=build /app/foxChat-web/build/libs/foxChat-web-1.0.0-SNAPSHOT.jar app.jar

EXPOSE 12000 13000

# JVM options: 512MB heap max, use G1GC for container
ENTRYPOINT ["java", \
    "-Xmx512m", \
    "-XX:+UseG1GC", \
    "-XX:MaxGCPauseMillis=200", \
    "-XX:+UseContainerSupport", \
    "-jar", "app.jar" \
]
