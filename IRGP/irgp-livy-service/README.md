# IRGP Livy Service

Spring Boot microservice that proxies REST requests to Apache Livy for managing Spark sessions and executing SQL.

## Prerequisites

- Java 17+
- Maven 3.6+
- Running Apache Livy instance (default: `http://localhost:8998`)

## Build

```bash
mvn clean package
```

JAR: `target/livy-service-1.0.0.jar`

## Run

```bash
java -jar target/livy-service-1.0.0.jar
```

Or with custom Livy URL:

```bash
LIVY_BASE_URL=http://livy-host:8998 \
LIVY_ORACLE_JAR=/path/to/oracle-connector-1.0.0.jar \
LIVY_HIVE_JAR=/path/to/hive-connector-1.0.0.jar \
java -jar target/livy-service-1.0.0.jar
```

## API Endpoints

| Method | Endpoint | Description | Request Body |
|--------|----------|-------------|--------------|
| POST | `/api/livy/sessions` | Create a Livy session | `LivyRequest` JSON |
| GET | `/api/livy/sessions/{id}` | Get session status | — |
| DELETE | `/api/livy/sessions/{id}` | Kill a session | — |
| POST | `/api/livy/sessions/{id}/statements` | Submit a statement | `{"code": "..."}` |
| GET | `/api/livy/sessions/{id}/statements/{stmtId}` | Get statement result | — |

### Create Session Example

```json
POST /api/livy/sessions
{
  "kind": "spark",
  "connectorType": "oracle",
  "sql": "SELECT * FROM sales WHERE year = 2024",
  "jdbcUrl": "jdbc:oracle:thin:@//host:1521/ORCLCDB",
  "user": "myuser",
  "password": "mypass",
  "partitionColumn": "sale_id",
  "numPartitions": 8
}
```

### Create Hive Session Example

```json
POST /api/livy/sessions
{
  "kind": "spark",
  "connectorType": "hive",
  "sql": "SELECT * FROM warehouse.sales WHERE year = 2024",
  "principal": "user@REALM.COM"
}
```

### Submit Statement Example

```json
POST /api/livy/sessions/0/statements
{
  "code": "spark.sql(\"SELECT COUNT(*) FROM sales\").show()"
}
```

## Configuration

| Property | Environment Variable | Default | Description |
|----------|---------------------|---------|-------------|
| `server.port` | `SERVER_PORT` | 8090 | Service HTTP port |
| `livy.base-url` | `LIVY_BASE_URL` | `http://localhost:8998` | Livy REST endpoint |
| `livy.connect-timeout-ms` | — | 5000 | HTTP connect timeout (ms) |
| `livy.read-timeout-ms` | — | 30000 | HTTP read timeout (ms) |
| `livy.oracle-connector-jar` | `LIVY_ORACLE_JAR` | `/opt/irgp/jars/oracle-connector-1.0.0.jar` | Oracle connector JAR path |
| `livy.hive-connector-jar` | `LIVY_HIVE_JAR` | `/opt/irgp/jars/hive-connector-1.0.0.jar` | Hive connector JAR path |

## Architecture

```
Report Gen Service ──> Livy Service (:8090) ──> Apache Livy (:8998)
                                                   │
                                                   ├── Spark Session (Oracle connector JAR)
                                                   └── Spark Session (Hive connector JAR)
```
