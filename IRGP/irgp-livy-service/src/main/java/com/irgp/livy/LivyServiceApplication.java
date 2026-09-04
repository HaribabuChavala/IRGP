package com.irgp.livy;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Livy Service — Spring Boot microservice that proxies requests to Apache Livy.
 * <p>
 * Provides a REST API for managing Spark sessions and executing SQL
 * statements through Apache Livy's REST interface.
 */
@SpringBootApplication
public class LivyServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(LivyServiceApplication.class, args);
    }
}
