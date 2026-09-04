package com.irgp.livy.service;

import com.irgp.livy.config.LivyConfig;
import com.irgp.livy.model.LivyRequest;
import com.irgp.livy.model.LivySession;
import com.irgp.livy.model.LivyStatement;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * WebClient-based HTTP client for the Apache Livy REST API.
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class LivyClientService {

    private final LivyConfig livyConfig;

    private WebClient webClient() {
        return WebClient.builder()
                .baseUrl(livyConfig.getBaseUrl())
                .defaultHeader(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE)
                .defaultHeader(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
                .build();
    }

    // ─── Sessions ──────────────────────────────────────────────────────────

    /**
     * Create a new Livy session and optionally submit a Spark job.
     */
    public Mono<LivySession> createSession(LivyRequest request) {
        log.info("Creating Livy session: kind={}, connectorType={}", request.getKind(), request.getConnectorType());

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("kind", request.getKind() != null ? request.getKind() : "spark");

        // Attach the correct connector JAR
        List<String> jars = new ArrayList<>();
        if (request.getConnectorType() != null) {
            String jar = switch (request.getConnectorType().toLowerCase()) {
                case "oracle" -> livyConfig.getOracleConnectorJar();
                case "hive" -> livyConfig.getHiveConnectorJar();
                default -> null;
            };
            if (jar != null) {
                jars.add(jar);
            }
        }
        if (request.getJars() != null) {
            jars.addAll(request.getJars());
        }
        if (!jars.isEmpty()) {
            body.put("jars", jars);
        }

        Map<String, String> conf = new HashMap<>();
        if (request.getConf() != null) {
            conf.putAll(request.getConf());
        }
        if (!conf.containsKey("spark.master")) {
            conf.put("spark.master", "local[*]");
        }
        body.put("conf", conf);

        if (request.getProxyUser() != null) {
            body.put("proxyUser", request.getProxyUser());
        }

        // Apache Livy session creation accepts only session metadata fields such as kind/conf/jars.
        // SQL execution must be submitted in a separate statement request after the session is created.
        log.info("Forwarding sanitized Livy session body: {}", body);

        return webClient()
                .post()
                .uri("/sessions")
                .bodyValue(body)
                .retrieve()
                .bodyToMono(LivySession.class)
                .doOnSuccess(session -> log.info("Livy session created: id={}, state={}", session.getId(), session.getState()))
                .doOnError(e -> log.error("Failed to create Livy session: {}", e.getMessage()));
    }

    /**
     * Get the status of an existing Livy session.
     */
    public Mono<LivySession> getSession(Integer sessionId) {
        log.info("Getting Livy session: id={}", sessionId);
        return webClient()
                .get()
                .uri("/sessions/{id}", sessionId)
                .retrieve()
                .bodyToMono(LivySession.class)
                .timeout(Duration.ofMillis(livyConfig.getReadTimeoutMs()))
                .doOnError(e -> log.error("Failed to get session {}: {}", sessionId, e.getMessage()));
    }

    /**
     * Kill (delete) a Livy session.
     */
    public Mono<Void> deleteSession(Integer sessionId) {
        log.info("Deleting Livy session: id={}", sessionId);
        return webClient()
                .delete()
                .uri("/sessions/{id}", sessionId)
                .retrieve()
                .bodyToMono(Void.class)
                .doOnSuccess(v -> log.info("Livy session deleted: id={}", sessionId))
                .doOnError(e -> log.error("Failed to delete session {}: {}", sessionId, e.getMessage()));
    }

    // ─── Statements ────────────────────────────────────────────────────────

    /**
     * Submit a SQL statement to an existing Livy session.
     */
    public Mono<LivyStatement> submitStatement(Integer sessionId, String code) {
        log.info("Submitting statement to session {}: {}", sessionId, code);

        Map<String, String> body = Map.of("code", code);

        return webClient()
                .post()
                .uri("/sessions/{id}/statements", sessionId)
                .bodyValue(body)
                .retrieve()
                .bodyToMono(LivyStatement.class)
                .doOnSuccess(stmt -> log.info("Statement submitted: id={}, state={}", stmt.getId(), stmt.getState()))
                .doOnError(e -> log.error("Failed to submit statement to session {}: {}", sessionId, e.getMessage()));
    }

    /**
     * Get the result of a specific statement in a session.
     */
    public Mono<LivyStatement> getStatement(Integer sessionId, Integer statementId) {
        log.info("Getting statement {}/{}", sessionId, statementId);
        return webClient()
                .get()
                .uri("/sessions/{id}/statements/{stmtId}", sessionId, statementId)
                .retrieve()
                .bodyToMono(LivyStatement.class)
                .timeout(Duration.ofMillis(livyConfig.getReadTimeoutMs()))
                .doOnError(e -> log.error("Failed to get statement {}/{}: {}", sessionId, statementId, e.getMessage()));
    }

    // ─── Code Generation ───────────────────────────────────────────────────

    /**
     * Build a Scala code snippet that uses the appropriate connector
     * to execute the given SQL query.
     */
    private String buildSparkCode(LivyRequest request) {
        String sql = request.getSql() == null ? "SELECT 1" : request.getSql().replace("\"", "\\\"").replace("\n", " ");

        if ("oracle".equalsIgnoreCase(request.getConnectorType())) {
            String jdbcUrl = request.getJdbcUrl() != null ? request.getJdbcUrl() : "";
            String user = request.getUser() != null ? request.getUser() : "";
            String password = request.getPassword() != null ? request.getPassword() : "";
            String partitionCol = request.getPartitionColumn() != null ? request.getPartitionColumn() : "";
            int numPartitions = request.getNumPartitions() != null ? request.getNumPartitions() : 4;

            String querySql = sql.isBlank() ? "SELECT 1 FROM dual" : sql;
            String wrappedSql = String.format("(%s) tmp", querySql);

            if (!partitionCol.isEmpty()) {
                return String.format(
                    "val df = spark.read.format(\"jdbc\").option(\"url\", \"%s\").option(\"dbtable\", \"%s\").option(\"user\", \"%s\").option(\"password\", \"%s\").option(\"partitionColumn\", \"%s\").option(\"numPartitions\", %d).option(\"lowerBound\", \"0\").option(\"upperBound\", \"99999999\").option(\"fetchsize\", \"10000\").load()",
                    jdbcUrl, wrappedSql, user, password, partitionCol, numPartitions
                );
            }
            return String.format(
                "val spark = org.apache.spark.sql.SparkSession.builder().getOrCreate(); val df = spark.read.format(\"jdbc\").option(\"url\", \"%s\").option(\"dbtable\", \"%s\").option(\"user\", \"%s\").option(\"password\", \"%s\").option(\"fetchsize\", \"10000\").load(); val result = spark.sql(\"%s\"); result.show(50, false)",
                jdbcUrl, wrappedSql, user, password, sql
            );
        } else if ("hive".equalsIgnoreCase(request.getConnectorType())) {
            return String.format(
                "val spark = org.apache.spark.sql.SparkSession.builder().enableHiveSupport().getOrCreate(); val result = spark.sql(\"%s\"); result.show(50, false)",
                sql
            );
        }

        // Fallback: plain Spark SQL
        return String.format(
            "val spark = org.apache.spark.sql.SparkSession.builder().getOrCreate(); val result = spark.sql(\"%s\"); result.show(50, false)",
            sql
        );
    }
}
