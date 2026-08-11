BEGIN;

CREATE TABLE IF NOT EXISTS executions_quotidiennes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cle_execution TEXT NOT NULL UNIQUE,
    declencheur TEXT NOT NULL CHECK (declencheur IN ('n8n', 'manuel', 'test')),
    statut TEXT NOT NULL CHECK (
        statut IN ('en_cours', 'analyse', 'terminee', 'partielle', 'echec')
    ),
    parametres JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(parametres) = 'object'),
    collecte_id BIGINT REFERENCES collectes_haicop(id) ON DELETE SET NULL,
    nb_candidats INTEGER NOT NULL DEFAULT 0 CHECK (nb_candidats >= 0),
    nb_analyses INTEGER NOT NULL DEFAULT 0 CHECK (nb_analyses >= 0),
    digest_chemin TEXT,
    digest_sha256 TEXT CHECK (
        digest_sha256 IS NULL OR digest_sha256 ~ '^[0-9a-f]{64}$'
    ),
    erreur TEXT,
    demarree_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    terminee_le TIMESTAMPTZ,
    mise_a_jour_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (
        (statut IN ('en_cours', 'analyse') AND terminee_le IS NULL)
        OR
        (statut IN ('terminee', 'partielle', 'echec') AND terminee_le IS NOT NULL)
    )
);

CREATE TABLE IF NOT EXISTS candidats_execution (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    execution_id BIGINT NOT NULL
        REFERENCES executions_quotidiennes(id) ON DELETE CASCADE,
    tender_id TEXT NOT NULL REFERENCES appels_offres(tender_id) ON DELETE CASCADE,
    contexte_sha256 TEXT NOT NULL CHECK (contexte_sha256 ~ '^[0-9a-f]{64}$'),
    score_pertinence SMALLINT NOT NULL,
    raisons JSONB NOT NULL DEFAULT '[]'::jsonb
        CHECK (jsonb_typeof(raisons) = 'array'),
    statut TEXT NOT NULL CHECK (
        statut IN ('a_analyser', 'analyse', 'termine', 'ignore', 'echec')
    ),
    analyse_id BIGINT REFERENCES analyses_ao(id) ON DELETE SET NULL,
    erreur TEXT,
    cree_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    mise_a_jour_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (execution_id, tender_id)
);

CREATE TABLE IF NOT EXISTS diffusions_digest (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    execution_id BIGINT NOT NULL
        REFERENCES executions_quotidiennes(id) ON DELETE CASCADE,
    canal TEXT NOT NULL CHECK (canal IN ('email', 'telegram', 'mailpit')),
    destinataire_hash TEXT NOT NULL CHECK (destinataire_hash ~ '^[0-9a-f]{64}$'),
    digest_sha256 TEXT NOT NULL CHECK (digest_sha256 ~ '^[0-9a-f]{64}$'),
    statut TEXT NOT NULL CHECK (statut IN ('en_cours', 'envoyee', 'echec', 'ignoree')),
    tentatives INTEGER NOT NULL DEFAULT 1 CHECK (tentatives >= 1),
    identifiant_externe TEXT,
    erreur TEXT,
    envoyee_le TIMESTAMPTZ,
    mise_a_jour_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (execution_id, canal, destinataire_hash)
);

CREATE INDEX IF NOT EXISTS idx_executions_quotidiennes_date
    ON executions_quotidiennes (demarree_le DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_candidats_execution_statut
    ON candidats_execution (execution_id, statut, score_pertinence DESC);
CREATE INDEX IF NOT EXISTS idx_diffusions_digest_execution
    ON diffusions_digest (execution_id, canal, statut);

CREATE OR REPLACE FUNCTION maj_horodatage_automation()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.mise_a_jour_le = clock_timestamp();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_executions_quotidiennes_maj
    ON executions_quotidiennes;
CREATE TRIGGER trg_executions_quotidiennes_maj
BEFORE UPDATE ON executions_quotidiennes
FOR EACH ROW EXECUTE FUNCTION maj_horodatage_automation();

DROP TRIGGER IF EXISTS trg_candidats_execution_maj
    ON candidats_execution;
CREATE TRIGGER trg_candidats_execution_maj
BEFORE UPDATE ON candidats_execution
FOR EACH ROW EXECUTE FUNCTION maj_horodatage_automation();

DROP TRIGGER IF EXISTS trg_diffusions_digest_maj
    ON diffusions_digest;
CREATE TRIGGER trg_diffusions_digest_maj
BEFORE UPDATE ON diffusions_digest
FOR EACH ROW EXECUTE FUNCTION maj_horodatage_automation();

COMMENT ON TABLE executions_quotidiennes IS
    'Journal idempotent des orchestrations quotidiennes HAICOP.';
COMMENT ON TABLE candidats_execution IS
    'AO retenus pour une execution et leur contexte exact a analyser.';
COMMENT ON TABLE diffusions_digest IS
    'Preuve idempotente des notifications de digest par canal.';

COMMIT;
