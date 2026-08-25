-- ChainLoom
-- Foundation setup
-- Version: 1.1
-- Purpose: Establish the project database and logical layers.

CREATE DATABASE IF NOT EXISTS CHAINLOOM
COMMENT = 'ChainLoom hackathon - governed supply chain intelligence';

CREATE SCHEMA IF NOT EXISTS CHAINLOOM.RAW
COMMENT = 'Raw synthetic source-like supply chain data';

CREATE SCHEMA IF NOT EXISTS CHAINLOOM.CURATED
COMMENT = 'Curated business-ready supply chain data';

CREATE SCHEMA IF NOT EXISTS CHAINLOOM.SEMANTIC
COMMENT = 'Governed semantic layer for ChainLoom';

CREATE SCHEMA IF NOT EXISTS CHAINLOOM.ANALYTICS
COMMENT = 'Analytical outputs and investigation support';

CREATE SCHEMA IF NOT EXISTS CHAINLOOM.APP
COMMENT = 'Application-facing objects';

SHOW SCHEMAS IN DATABASE CHAINLOOM;