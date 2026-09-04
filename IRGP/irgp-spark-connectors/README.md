# IRGP Spark Connectors

Spark Data Connectors for the Instant Report Generation Platform.

## Modules

| Module | Description | Main Class |
|--------|-------------|------------|
| `oracle-connector` | JDBC read from Oracle with partitioning | `com.irgp.connectors.oracle.OracleConnector` |
| `hive-connector` | Spark SQL on HiveServer2 with optional Kerberos | `com.irgp.connectors.hive.HiveConnector` |

## Prerequisites

- Java 8+
- Maven 3.6+
- Apache Spark 3.5.0 (or compatible — connectors use `provided` scope for Spark dependencies)

## Build

```bash
# Build all modules
mvn clean package

# Build a single module
cd oracle-connector && mvn clean package
cd hive-connector && mvn clean package
```

Built JARs (with dependencies shaded) will be in each module's `target/` directory:
- `oracle-connector/target/oracle-connector-1.0.0.jar`
- `hive-connector/target/hive-connector-1.0.0.jar`

## Running

### Oracle Connector

```bash
spark-submit \
  --class com.irgp.connectors.oracle.OracleConnector \
  --jars /path/to/ojdbc8.jar \
  oracle-connector-1.0.0.jar \
  "SELECT * FROM sales WHERE region = 'US'" \
  "jdbc:oracle:thin:@//oracle-host:1521/ORCLCDB" \
  myuser mypassword \
  --partition-column sale_id \
  --num-partitions 8 \
  --output-path /tmp/oracle-results
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `sqlQuery` | Yes | SQL query to execute |
| `jdbcUrl` | Yes | Oracle JDBC URL |
| `user` | Yes | Oracle username |
| `password` | Yes | Oracle password |
| `--partition-column` | No | Column for parallel JDBC read partitioning |
| `--num-partitions` | No | Number of read partitions (default: 4) |
| `--output-path` | No | Write results as CSV to this HDFS/local path |

### Hive Connector

```bash
spark-submit \
  --class com.irgp.connectors.hive.HiveConnector \
  --principal user@YOUR.REALM.COM \
  --keytab /path/to/user.keytab \
  hive-connector-1.0.0.jar \
  "SELECT * FROM warehouse.sales WHERE year = 2024" \
  "jdbc:hive2://hive-host:10000/default" \
  --principal user@YOUR.REALM.COM \
  --output-path /tmp/hive-results
```

**Arguments:**

| Argument | Required | Description |
|----------|----------|-------------|
| `sqlQuery` | Yes | SQL query to execute |
| `hiveJdbcUrl` | Yes | HiveServer2 JDBC URL |
| `--principal` | No | Kerberos principal for authentication |
| `--output-path` | No | Write results as CSV to this HDFS/local path |

## Integration with Livy

These connector JARs are designed to be submitted to Apache Livy sessions. The Livy Service (see `../livy-service/`) sends connector JAR paths when creating sessions so that submitted SQL jobs can use the appropriate connector.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid arguments |
| 2 | SQL analysis error |
| 3 | JDBC/connection error |
| 4 | Kerberos error (Hive only) |
| 5 | Unexpected error (Hive only) |
