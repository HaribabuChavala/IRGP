FROM maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /workspace
COPY pom.xml ./
COPY src ./src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:17-jre-jammy
WORKDIR /app
COPY --from=build /workspace/target/livy-service-1.0.0.jar /app/livy-service.jar
EXPOSE 8090
ENTRYPOINT ["java", "-jar", "/app/livy-service.jar"]
