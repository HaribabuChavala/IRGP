CREATE USER keycloak WITH PASSWORD 'keycloak-dev-password';
CREATE DATABASE keycloak OWNER keycloak;
GRANT ALL PRIVILEGES ON DATABASE keycloak TO keycloak;
