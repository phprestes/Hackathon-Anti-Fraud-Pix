CREATE TABLE analysis_status(
    id                              SERIAL PRIMARY KEY,
    enumerator                      VARCHAR(50) NOT NULL UNIQUE,
    severity                        SMALLINT NOT NULL UNIQUE,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

INSERT INTO analysis_status (enumerator, severity) VALUES
('approved', 0),
('two_factor_required', 1),
('rejected', 2);

CREATE TABLE pix_transaction(
    id                              SERIAL PRIMARY KEY,
    pix_id                          VARCHAR(100) NOT NULL UNIQUE,
    amount                          BIGINT NOT NULL CHECK (amount > 0),
    transaction_date                TIMESTAMPTZ NOT NULL,
    source_branch                   VARCHAR(10) NOT NULL,
    source_account_number           VARCHAR(20) NOT NULL,
    source_opening_date             TIMESTAMPTZ NOT NULL,
    source_document_number          VARCHAR(18) NOT NULL,
    destination_participant         CHAR(8) NOT NULL,
    destination_branch              VARCHAR(10) NOT NULL,
    destination_account_number      VARCHAR(20) NOT NULL,
    destination_opening_date        TIMESTAMPTZ NOT NULL,
    destination_document_number     VARCHAR(18) NOT NULL,
    device_id                       VARCHAR(100) NOT NULL,
    channel                         VARCHAR(30) NOT NULL,
    ip                              INET NOT NULL,
    latitude                        NUMERIC(9,6),
    longitude                       NUMERIC(9,6),
    payload                         JSONB NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE INDEX pix_transaction_source_date_idx      ON pix_transaction (source_document_number, transaction_date);
CREATE INDEX pix_transaction_device_date_idx      ON pix_transaction (device_id, transaction_date);
CREATE INDEX pix_transaction_destination_date_idx ON pix_transaction (destination_document_number, transaction_date);
CREATE INDEX pix_transaction_pair_idx             ON pix_transaction (source_document_number, destination_document_number);

CREATE TABLE pix_analysis(
    id                              SERIAL PRIMARY KEY,
    analysis_key                    CHAR(36) NOT NULL UNIQUE,
    pix_transaction_id              INTEGER NOT NULL UNIQUE REFERENCES pix_transaction(id),
    status_id                       INTEGER NOT NULL REFERENCES analysis_status(id),
    metadata                        JSONB NOT NULL,
    rule_set_version                VARCHAR(20) NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);

CREATE TABLE pix_analysis_reason(
    id                              SERIAL PRIMARY KEY,
    pix_analysis_id                 INTEGER NOT NULL REFERENCES pix_analysis(id),
    rule_code                       VARCHAR(60) NOT NULL,
    decision_status_id              INTEGER NOT NULL REFERENCES analysis_status(id),
    reason                          TEXT NOT NULL,
    created_at                      TIMESTAMP NOT NULL DEFAULT(NOW())
);
