package com.irgp.livy.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * Configuration properties for the Livy connection.
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "livy")
public class LivyConfig {

    /**
     * Base URL of the Apache Livy server (e.g., http://livy-host:8998).
     */
    private String baseUrl = "http://localhost:8998";

    /**
     * Connection timeout in milliseconds for Livy HTTP calls.
     */
    private int connectTimeoutMs = 5000;

    /**
     * Read timeout in milliseconds for Livy HTTP calls.
     */
    private int readTimeoutMs = 30000;

    /**
     * Path to the Oracle connector JAR on the Livy server's filesystem.
     */
    private String oracleConnectorJar = "/opt/irgp/jars/oracle-connector-1.0.0.jar";

    /**
     * Path to the Hive connector JAR on the Livy server's filesystem.
     */
    private String hiveConnectorJar = "/opt/irgp/jars/hive-connector-1.0.0.jar";
}
