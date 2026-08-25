package com.irgp.livy.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.Map;

/**
 * Represents a Livy statement (code execution within a session).
 */
@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class LivyStatement {

    private Integer id;

    /** Livy statement state: waiting, running, available, error, cancelling, cancelled */
    private String state;

    /** The code that was submitted. */
    private String code;

    /** The output of the statement, if available. */
    private Map<String, Object> output;

    /** Timestamp of statement submission (epoch ms). */
    @JsonProperty("started")
    private Long startedAt;

    /** Timestamp of statement completion (epoch ms). */
    @JsonProperty("completed")
    private Long completedAt;

    /** Progress of statement execution (0-1). */
    private Double progress;
}
