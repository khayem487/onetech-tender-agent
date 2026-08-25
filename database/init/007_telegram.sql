BEGIN;

-- Telegram is an external, at-least-once source.  Keep a privacy-minimised
-- audit trail so polling retries cannot make the bot answer the same group
-- message twice.  Message bodies are deliberately *not* persisted.
CREATE TABLE IF NOT EXISTS telegram_poll_state (
    consommateur TEXT PRIMARY KEY,
    prochain_update_id BIGINT NOT NULL DEFAULT 0 CHECK (prochain_update_id >= 0),
    mise_a_jour_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp()
);

CREATE TABLE IF NOT EXISTS telegram_interactions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    update_id BIGINT NOT NULL UNIQUE CHECK (update_id >= 0),
    chat_hash TEXT NOT NULL CHECK (chat_hash ~ '^[0-9a-f]{64}$'),
    message_id BIGINT NOT NULL CHECK (message_id > 0),
    expediteur_hash TEXT,
    message_sha256 TEXT NOT NULL CHECK (message_sha256 ~ '^[0-9a-f]{64}$'),
    type_interaction TEXT NOT NULL CHECK (type_interaction IN ('mention', 'reply', 'command')),
    statut TEXT NOT NULL CHECK (
        statut IN ('recue', 'traitement', 'repondue', 'ignoree', 'echec')
    ),
    tentatives INTEGER NOT NULL DEFAULT 0 CHECK (tentatives >= 0),
    message_reponse_id BIGINT,
    erreur TEXT,
    recue_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    traitee_le TIMESTAMPTZ,
    mise_a_jour_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (chat_hash, message_id)
);

CREATE INDEX IF NOT EXISTS idx_telegram_interactions_statut
    ON telegram_interactions (statut, recue_le DESC);

DROP TRIGGER IF EXISTS trg_telegram_poll_state_maj ON telegram_poll_state;
CREATE TRIGGER trg_telegram_poll_state_maj
BEFORE UPDATE ON telegram_poll_state
FOR EACH ROW EXECUTE FUNCTION maj_horodatage_automation();

DROP TRIGGER IF EXISTS trg_telegram_interactions_maj ON telegram_interactions;
CREATE TRIGGER trg_telegram_interactions_maj
BEFORE UPDATE ON telegram_interactions
FOR EACH ROW EXECUTE FUNCTION maj_horodatage_automation();

COMMENT ON TABLE telegram_poll_state IS
    'Offset durable du polling Telegram par consommateur.';
COMMENT ON TABLE telegram_interactions IS
    'Journal sans contenu des messages Telegram admissibles ou ignorés.';

COMMIT;
