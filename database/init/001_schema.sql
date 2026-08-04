BEGIN;

-- One row per collector execution. This makes collection runs observable and
-- gives later digests a reliable audit trail.
CREATE TABLE IF NOT EXISTS collectes_haicop (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'haicop',
    statut TEXT NOT NULL DEFAULT 'en_cours'
        CHECK (statut IN ('en_cours', 'terminee', 'echec')),
    demarree_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    terminee_le TIMESTAMPTZ,
    nb_recus INTEGER NOT NULL DEFAULT 0 CHECK (nb_recus >= 0),
    nb_inseres INTEGER NOT NULL DEFAULT 0 CHECK (nb_inseres >= 0),
    nb_mis_a_jour INTEGER NOT NULL DEFAULT 0 CHECK (nb_mis_a_jour >= 0),
    erreur TEXT,
    parametres JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(parametres) = 'object'),
    CHECK (terminee_le IS NULL OR terminee_le >= demarree_le)
);

-- Official tender facts collected from HAICOP. AI-generated analysis is kept
-- out of this table so source data and model output cannot be confused.
CREATE TABLE IF NOT EXISTS appels_offres (
    tender_id TEXT PRIMARY KEY,
    source TEXT NOT NULL DEFAULT 'haicop',
    plan_id TEXT,
    organisme TEXT,
    titre TEXT,
    date_publication TIMESTAMPTZ,
    date_limite TIMESTAMPTZ,
    reserve_pme BOOLEAN,
    url_detail TEXT NOT NULL,
    champs_details JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(champs_details) = 'object'),
    donnees_brutes JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(donnees_brutes) = 'object'),
    collecte_id BIGINT REFERENCES collectes_haicop(id) ON DELETE SET NULL,
    premiere_collecte_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    derniere_collecte_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    mise_a_jour_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    CHECK (tender_id = btrim(tender_id) AND tender_id <> ''),
    CHECK (url_detail = btrim(url_detail) AND url_detail <> ''),
    CHECK (derniere_collecte_le >= premiere_collecte_le)
);

-- Public documents discovered on a tender detail page. The unique pair
-- (tender_id, url) prevents the same document from being stored twice.
CREATE TABLE IF NOT EXISTS documents_ao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES appels_offres(tender_id) ON DELETE CASCADE,
    libelle TEXT,
    type_document TEXT,
    url TEXT NOT NULL,
    chemin_local TEXT,
    texte_extrait TEXT,
    empreinte_sha256 TEXT,
    metadonnees_brutes JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(metadonnees_brutes) = 'object'),
    premiere_collecte_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    derniere_collecte_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    mise_a_jour_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (tender_id, url),
    CHECK (url = btrim(url) AND url <> ''),
    CHECK (
        empreinte_sha256 IS NULL
        OR empreinte_sha256 ~ '^[0-9a-fA-F]{64}$'
    ),
    CHECK (derniere_collecte_le >= premiere_collecte_le)
);

CREATE OR REPLACE FUNCTION definir_mise_a_jour_le()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.mise_a_jour_le = clock_timestamp();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_appels_offres_mise_a_jour ON appels_offres;
CREATE TRIGGER trg_appels_offres_mise_a_jour
BEFORE UPDATE ON appels_offres
FOR EACH ROW
EXECUTE FUNCTION definir_mise_a_jour_le();

DROP TRIGGER IF EXISTS trg_documents_ao_mise_a_jour ON documents_ao;
CREATE TRIGGER trg_documents_ao_mise_a_jour
BEFORE UPDATE ON documents_ao
FOR EACH ROW
EXECUTE FUNCTION definir_mise_a_jour_le();

CREATE INDEX IF NOT EXISTS idx_appels_offres_date_publication
    ON appels_offres (date_publication DESC);

CREATE INDEX IF NOT EXISTS idx_appels_offres_date_limite
    ON appels_offres (date_limite);

CREATE INDEX IF NOT EXISTS idx_appels_offres_organisme
    ON appels_offres (organisme);

CREATE INDEX IF NOT EXISTS idx_appels_offres_donnees_brutes_gin
    ON appels_offres USING GIN (donnees_brutes);

CREATE INDEX IF NOT EXISTS idx_documents_ao_tender_id
    ON documents_ao (tender_id);

CREATE INDEX IF NOT EXISTS idx_collectes_haicop_demarree_le
    ON collectes_haicop (demarree_le DESC);

CREATE OR REPLACE VIEW v_appels_offres_ouverts AS
SELECT
    tender_id,
    organisme,
    titre,
    date_publication,
    date_limite,
    reserve_pme,
    url_detail,
    CASE
        WHEN date_limite IS NULL THEN 'echeance_inconnue'
        ELSE 'ouvert'
    END AS statut_echeance,
    CASE
        WHEN date_limite IS NULL THEN NULL
        ELSE date_limite - clock_timestamp()
    END AS temps_restant
FROM appels_offres
WHERE date_limite IS NULL OR date_limite >= clock_timestamp();

COMMENT ON TABLE collectes_haicop IS
    'Journal de chaque execution du collecteur HAICOP.';
COMMENT ON TABLE appels_offres IS
    'Donnees officielles des appels offres collectes depuis HAICOP.';
COMMENT ON TABLE documents_ao IS
    'Documents publics rattaches aux appels offres.';
COMMENT ON COLUMN appels_offres.donnees_brutes IS
    'Payload HAICOP original conserve pour audit et evolution du schema.';
COMMENT ON VIEW v_appels_offres_ouverts IS
    'Appels offres non expires ou dont echeance est inconnue.';

COMMIT;
