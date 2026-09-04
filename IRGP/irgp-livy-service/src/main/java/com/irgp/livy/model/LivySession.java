package com.irgp.livy.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

/**
 * Represents a Livy session response.
 */
@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class LivySession {

    private Integer id;

    private String appId;

    private String owner;

    /** Livy state: not_started, starting, idle, busy, dead, success, error, killing */
    private String state;

    private String kind;

    private List<String> log;

    @JsonProperty("proxyUser")
    private String proxyUser;
}
