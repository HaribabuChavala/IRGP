package com.irgp.livy.controller;

import com.irgp.livy.model.LivyRequest;
import com.irgp.livy.model.LivySession;
import com.irgp.livy.model.LivyStatement;
import com.irgp.livy.service.LivyClientService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Mono;

import java.util.HashMap;
import java.util.Map;

/**
 * REST controller that proxies Livy session and statement operations.
 */
@Slf4j
@RestController
@RequestMapping("/api/livy")
@RequiredArgsConstructor
public class LivyController {

    private final LivyClientService livyClientService;

    /**
     * Create a new Livy session.
     * Can optionally submit a Spark job with SQL + connector JAR.
     */
    @PostMapping("/sessions")
    public Mono<ResponseEntity<LivySession>> createSession(@Valid @RequestBody LivyRequest request) {
        log.info("POST /api/livy/sessions - connectorType={}, kind={}", request.getConnectorType(), request.getKind());
        return livyClientService.createSession(request)
                .map(session -> ResponseEntity.status(201).body(session))
                .onErrorResume(e -> {
                    log.error("Error creating session: {}", e.getMessage());
                    return Mono.just(ResponseEntity.internalServerError().build());
                });
    }

    /**
     * Get the status of an existing Livy session.
     */
    @GetMapping("/sessions/{id}")
    public Mono<ResponseEntity<LivySession>> getSession(@PathVariable Integer id) {
        log.info("GET /api/livy/sessions/{}", id);
        return livyClientService.getSession(id)
                .map(ResponseEntity::ok)
                .defaultIfEmpty(ResponseEntity.notFound().build())
                .onErrorResume(e -> {
                    log.error("Error getting session {}: {}", id, e.getMessage());
                    return Mono.just(ResponseEntity.internalServerError().build());
                });
    }

    /**
     * Kill (delete) a Livy session.
     */
    @DeleteMapping("/sessions/{id}")
    public Mono<ResponseEntity<Map<String, Object>>> deleteSession(@PathVariable Integer id) {
        log.info("DELETE /api/livy/sessions/{}", id);
        Map<String, Object> payload = new HashMap<>();
        payload.put("message", "Session " + id + " deleted");

        return livyClientService.deleteSession(id)
                .thenReturn(ResponseEntity.ok(payload))
                .onErrorResume(e -> {
                    log.error("Error deleting session {}: {}", id, e.getMessage());
                    return Mono.just(ResponseEntity.internalServerError().build());
                });
    }

    /**
     * Submit a SQL statement to an existing Livy session.
     */
    @PostMapping("/sessions/{id}/statements")
    public Mono<ResponseEntity<LivyStatement>> submitStatement(
            @PathVariable Integer id,
            @RequestBody Map<String, String> body) {
        String code = body.get("code");
        if (code == null || code.isBlank()) {
            log.warn("Missing 'code' in request body for session {}", id);
            return Mono.just(ResponseEntity.badRequest().build());
        }
        log.info("POST /api/livy/sessions/{}/statements", id);
        return livyClientService.submitStatement(id, code)
                .map(stmt -> ResponseEntity.status(201).body(stmt))
                .onErrorResume(e -> {
                    log.error("Error submitting statement to session {}: {}", id, e.getMessage());
                    return Mono.just(ResponseEntity.internalServerError().build());
                });
    }

    /**
     * Get the result of a specific statement in a session.
     */
    @GetMapping("/sessions/{id}/statements/{stmtId}")
    public Mono<ResponseEntity<LivyStatement>> getStatement(
            @PathVariable Integer id,
            @PathVariable Integer stmtId) {
        log.info("GET /api/livy/sessions/{}/statements/{}", id, stmtId);
        return livyClientService.getStatement(id, stmtId)
                .map(ResponseEntity::ok)
                .defaultIfEmpty(ResponseEntity.notFound().build())
                .onErrorResume(e -> {
                    log.error("Error getting statement {}/{}: {}", id, stmtId, e.getMessage());
                    return Mono.just(ResponseEntity.internalServerError().build());
                });
    }
}