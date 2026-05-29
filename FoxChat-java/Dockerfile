# ============================================
# Stage 1: Build fat JAR with Gradle (deps from base)
# ============================================
FROM foxchat-java-build-base:latest AS build
WORKDIR /app

# Copy ALL source code at once (single layer, faster context transfer)
COPY foxChat-common foxChat-pojo foxChat-service foxChat-netty foxChat-web ./

# Build fat JAR with Gradle build cache + dependency cache mount
RUN --mount=type=cache,target=/root/.gradle \
    ./gradlew :foxChat-web:bootJar --no-daemon --build-cache -x test

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
