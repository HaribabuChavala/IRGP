package com.irgp.connectors.oracle

import org.apache.spark.sql.{DataFrame, SparkSession}
import org.slf4j.LoggerFactory

/**
  * OracleConnector — Spark-based JDBC connector for Oracle databases.
  *
  * Usage:
  *   spark-submit --class com.irgp.connectors.oracle.OracleConnector \
  *     oracle-connector-1.0.0.jar \
  *     "SELECT * FROM sales WHERE region = 'US'" \
  *     "jdbc:oracle:thin:@//host:1521/service" \
  *     myuser mypassword \
  *     --partition-column sale_id --num-partitions 8
  */
object OracleConnector {

  private val logger = LoggerFactory.getLogger(OracleConnector.getClass)

  case class Config(
      sqlQuery: String,
      jdbcUrl: String,
      user: String,
      password: String,
      partitionColumn: Option[String] = None,
      numPartitions: Int = 4,
      output_path: Option[String] = None
  )

  def main(args: Array[String]): Unit = {
    logger.info("OracleConnector starting...")

    try {
      val config = parseArgs(args)
      logger.info(s"Configuration parsed: query='${config.sqlQuery.take(80)}...', partitions=${config.numPartitions}")

      val spark = createSparkSession()
      logger.info("SparkSession created successfully")

      val jdbcOptions = buildJdbcOptions(config)
      logger.info(s"JDBC options built for URL: ${config.jdbcUrl}")

      val jdbcDF: DataFrame = spark.read
        .format("jdbc")
        .options(jdbcOptions)
        .load()

      logger.info(s"JDBC DataFrame loaded with ${jdbcDF.rdd.getNumPartitions} partitions")

      // Execute the actual SQL query on the loaded DataFrame
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

      logger.info("OracleConnector completed successfully")

    } catch {
      case e: IllegalArgumentException =>
        logger.error(s"Invalid arguments: ${e.getMessage}")
        printUsage()
        System.exit(1)
      case e: org.apache.spark.sql.AnalysisException =>
        logger.error(s"SQL analysis error: ${e.getMessage}")
        System.exit(2)
      case e: java.sql.SQLException =>
        logger.error(s"JDBC/Oracle connection error: ${e.getMessage}")
        System.exit(3)
      case e: Exception =>
        logger.error(s"Unexpected error: ${e.getMessage}", e)
        System.exit(4)
    }
  }

  /**
    * Parse command-line arguments into a Config object.
    * Positional: sqlQuery jdbcUrl user password
    * Named (optional): --partition-column <col> --num-partitions <n> --output-path <path>
    */
  private def parseArgs(args: Array[String]): Config = {
    if (args.length < 4) {
      throw new IllegalArgumentException("At least 4 arguments required: sqlQuery jdbcUrl user password")
    }

    val positionalArgs = args.take(4).map(_.trim)
    val namedArgs = args.drop(4).grouped(2).filter(_.length == 2).map {
      case Array(key, value) => key.stripPrefix("--") -> value
    }.toMap

    Config(
      sqlQuery = positionalArgs(0),
      jdbcUrl = positionalArgs(1),
      user = positionalArgs(2),
      password = positionalArgs(3),
      partitionColumn = namedArgs.get("partition-column"),
      numPartitions = namedArgs.get("num-partitions").map(_.toInt).getOrElse(4),
      output_path = namedArgs.get("output-path")
    )
  }

  /** Create a SparkSession with Oracle JDBC driver registered. */
  private def createSparkSession(): SparkSession = {
    SparkSession.builder()
      .appName("IRGP-Oracle-Connector")
      .config("spark.jars", "")
      .getOrCreate()
  }

  /**
    * Build JDBC read options. If a partition column is provided, the data
    * is read in parallel using Spark's built-in JDBC partitioning.
    */
  private def buildJdbcOptions(config: Config): Map[String, String] = {
    val base = Map(
      "url" -> config.jdbcUrl,
      "user" -> config.user,
      "password" -> config.password,
      "driver" -> "oracle.jdbc.OracleDriver",
      "fetchsize" -> "10000"
    )

    config.partitionColumn match {
      case Some(col) =>
        // Use infer and lower/upper bounds for partitioning
        base ++ Map(
          "partitionColumn" -> col,
          "numPartitions" -> config.numPartitions.toString,
          "lowerBound" -> "0",
          "upperBound" -> Int.MaxValue.toString
        )
      case None =>
        // Without a partition column, Spark reads with a single partition.
        // We still set numPartitions via the dbtable approach by wrapping in a subquery.
        base
    }
  }

  /** Print usage information to stderr. */
  private def printUsage(): Unit = {
    Console.err.println(
      s"""|
         |OracleConnector — Spark JDBC Connector for Oracle
         |
         |Usage:
         |  spark-submit --class com.irgp.connectors.oracle.OracleConnector \
         |    oracle-connector-1.0.0.jar \
         |    <sqlQuery> <jdbcUrl> <user> <password> [options]
         |
         |Arguments:
         |  sqlQuery        SQL query to execute
         |  jdbcUrl         Oracle JDBC URL (e.g., jdbc:oracle:thin:@//host:1521/service)
         |  user            Oracle username
         |  password        Oracle password
         |
         |Options:
         |  --partition-column <col>   Column for parallel JDBC read partitioning
         |  --num-partitions <n>       Number of partitions (default: 4)
         |  --output-path <path>       Write results to CSV at this path
         |""".stripMargin)
  }
}
