FROM maven:3.9.9-eclipse-temurin-17 AS connector-build
WORKDIR /workspace

COPY spark-connectors/pom.xml ./pom.xml
COPY spark-connectors/oracle-connector ./oracle-connector
COPY spark-connectors/hive-connector ./hive-connector

RUN mvn -q -DskipTests package

FROM apache/spark:3.5.3

USER root

RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ca-certificates procps && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/irgp/jars /opt/livy /opt/livy/logs /opt/livy/state && \
    curl -L --fail https://downloads.apache.org/incubator/livy/0.8.0-incubating/apache-livy-0.8.0-incubating_2.12-bin.zip -o /tmp/livy.zip && \
    unzip -q /tmp/livy.zip -d /tmp && \
    mv /tmp/apache-livy-0.8.0-incubating_2.12-bin/* /opt/livy/ && \
    rm -rf /tmp/livy.zip /tmp/apache-livy-0.8.0-incubating_2.12-bin && \
    cp /opt/livy/conf/livy.conf.template /opt/livy/conf/livy.conf && \
    printf '\nlivy.file.local-dir-whitelist = /opt/irgp/jars,/opt/livy\nlivy.spark.master = local[*]\nlivy.log.dir = /opt/livy/logs\nlivy.server.recovery.state-store = /opt/livy/state\n' >> /opt/livy/conf/livy.conf

COPY --from=connector-build /workspace/oracle-connector/target/oracle-connector-1.0.0.jar /opt/irgp/jars/oracle-connector-1.0.0.jar
COPY --from=connector-build /workspace/hive-connector/target/hive-connector-1.0.0.jar /opt/irgp/jars/hive-connector-1.0.0.jar

ENV SPARK_HOME=/opt/spark \
    LIVY_HOME=/opt/livy \
    LIVY_CONF_DIR=/opt/livy/conf \
    LIVY_LOG_DIR=/opt/livy/logs \
    LIVY_STATE_DIR=/opt/livy/state \
    PATH=/opt/spark/bin:/opt/livy/bin:${PATH} \
    LIVY_ORACLE_JAR=/opt/irgp/jars/oracle-connector-1.0.0.jar \
    LIVY_HIVE_JAR=/opt/irgp/jars/hive-connector-1.0.0.jar

EXPOSE 8998

ENTRYPOINT ["/bin/bash", "-lc", "mkdir -p /tmp/livy /tmp/livy-state /opt/livy/logs /opt/livy/state && /opt/livy/bin/livy-server start && (touch /tmp/livy/livy--server.out || true) && tail -n +1 -F /tmp/livy/livy--server.out"]
