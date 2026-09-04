package com.irgp.connectors.hive

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.slf4j.LoggerFactory

/**
  * HiveConnector — Spark-based connector for Apache Hive.
  *
  * Supports optional Kerberos authentication via principal.
  *
  * Usage:
  *   spark-submit --class com.irgp.connectors.hive.HiveConnector \
  *     hive-connector-1.0.0.jar \
  *     "SELECT * FROM warehouse.sales WHERE year = 2024" \
  *     "jdbc:hive2://hive-host:10000/default" \
  *     --principal user@REALM.COM --output-path /tmp/results
  */
object HiveConnector {

  private val logger = LoggerFactory.getLogger(HiveConnector.getClass)

  case class Config(
      sqlQuery: String,
      hiveJdbcUrl: String,
      principal: Option[String] = None,
      output_path: Option[String] = None
  )

  def main(args: Array[String]): Unit = {
    logger.info("HiveConnector starting...")

    try {
      val config = parseArgs(args)
      logger.info(s"Configuration parsed: query='${config.sqlQuery.take(80)}...'")
      config.principal.foreach(p => logger.info(s"Kerberos principal: $p"))

      val spark = createSparkSession(config)
      logger.info("SparkSession created with Hive support")

      // Execute the SQL query directly via Spark SQL
      val resultDF: DataFrame = spark.sql(config.sqlQuery)

      val rowCount = resultDF.count()
      logger.info(s"Query executed. Row count: $rowCount")

      // Show results in console
      resultDF.show(50, truncate = false)

      // Optionally write to output path
      config.output_path.foreach { path =>
        logger.info(s"Writing results to: $path")
        resultDF.write
          .mode("overwrite")
          .option("header", "true")
          .csv(path)
        logger.info(s"Results written to $path")
      }

      logger.info("HiveConnector completed successfully")

    } catch {
      case e: IllegalArgumentException =>
        logger.error(s"Invalid arguments: ${e.getMessage}")
        printUsage()
        System.exit(1)
      case e: org.apache.spark.sql.AnalysisException =>
        logger.error(s"SQL analysis error: ${e.getMessage}")
        System.exit(2)
      case e: java.sql.SQLException =>
        logger.error(s"JDBC/Hive connection error: ${e.getMessage}")
        System.exit(3)
      case e: Exception =>
        logger.error(s"Unexpected error: ${e.getMessage}", e)
        System.exit(5)
    }
  }

  /**
    * Parse command-line arguments into a Config object.
    * Positional: sqlQuery hiveJdbcUrl
    * Named (optional): --principal <principal> --output-path <path>
    */
  private def parseArgs(args: Array[String]): Config = {
    if (args.length < 2) {
      throw new IllegalArgumentException("At least 2 arguments required: sqlQuery hiveJdbcUrl")
    }

    val positionalArgs = args.take(2).map(_.trim)
    val namedArgs = args.drop(2).grouped(2).filter(_.length == 2).map {
      case Array(key, value) => key.stripPrefix("--") -> value
    }.toMap

    Config(
      sqlQuery = positionalArgs(0),
      hiveJdbcUrl = positionalArgs(1),
      principal = namedArgs.get("principal"),
      output_path = namedArgs.get("output-path")
    )
  }

  /** Create a SparkSession with Hive support enabled. */
  private def createSparkSession(config: Config): SparkSession = {
    val builder = SparkSession.builder()
      .appName("IRGP-Hive-Connector")
      .enableHiveSupport()

    // Configure Kerberos if principal is provided
    config.principal.foreach { principal =>
      logger.info(s"Configuring Kerberos authentication with principal: $principal")
      builder.config("hive.metastore.kerberos.principal", principal)
      builder.config("spark.yarn.principal", principal)

      // Attempt to login via UGI if in a Kerberos environment
      val userGroupInformation = {
        val ugi = org.apache.hadoop.security.UserGroupInformation.getCurrentUser
        logger.info(s"Current UGI: ${ugi.getUserName}, hasKerberosCredentials: ${ugi.hasKerberosCredentials}")
        if (ugi.hasKerberosCredentials) {
          ugi
        } else {
          logger.warn("No Kerberos credentials found in current UGI; authentication may fail")
          ugi
        }
      }
    }

    builder.getOrCreate()
  }

  /** Print usage information to stderr. */
  private def printUsage(): Unit = {
    Console.err.println(
      s"""|
         |HiveConnector — Spark Connector for Apache Hive
         |
         |Usage:
         |  spark-submit --class com.irgp.connectors.hive.HiveConnector \
         |    hive-connector-1.0.0.jar \
         |    <sqlQuery> <hiveJdbcUrl> [options]
         |
         |Arguments:
         |  sqlQuery        SQL query to execute
         |  hiveJdbcUrl     HiveServer2 JDBC URL (e.g., jdbc:hive2://host:10000/default)
         |
         |Options:
         |  --principal <principal>   Kerberos principal (e.g., user@REALM.COM)
         |  --output-path <path>      Write results to CSV at this path
         |""".stripMargin)
  }
}
