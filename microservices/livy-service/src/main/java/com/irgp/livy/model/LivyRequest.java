package com.irgp.livy.model;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Map;

/**
 * Request body for creating a Livy session.
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonIgnoreProperties(ignoreUnknown = true)
public class LivyRequest {

    /** Kind of session: spark, pyspark, sparkr, or sql. */
    private String kind;

    /** JAR files to add to the session classpath. */
    @JsonProperty("jars")
    private List<String> jars;

    /** Files to place in the working directory. */
    @JsonProperty("files")
    private List<String> files;

    /** Spark configuration properties. */
    @JsonProperty("conf")
    private Map<String, String> conf;

    /** Proxy user to impersonate when running the session. */
    @JsonProperty("proxyUser")
    private String proxyUser;

    /** The SQL query to execute upon session start (for spark-submit style jobs). */
    private String sql;

    /** Connector type: "oracle" or "hive". Determines which JAR to attach. */
    private String connectorType;

    /** JDBC URL for the data source. */
    private String jdbcUrl;

    /** Username for the data source. */
    private String user;

    /** Password for the data source. */
    private String password;

    /** Kerberos principal (for Hive). */
    private String principal;

    /** Partition column for Oracle parallel reads. */
    @JsonProperty("partitionColumn")
    private String partitionColumn;

    /** Number of partitions for Oracle parallel reads. */
    @JsonProperty("numPartitions")
    private Integer numPartitions;
}
