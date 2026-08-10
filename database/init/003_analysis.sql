BEGIN;

-- Generated reasoning is deliberately isolated from official HAICOP facts.
-- A repeated save of the same fiche against the same source snapshot is
-- idempotent, while a changed source snapshot creates a new auditable version.
CREATE TABLE IF NOT EXISTS analyses_ao (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tender_id TEXT NOT NULL REFERENCES appels_offres(tender_id) ON DELETE CASCADE,
    statut TEXT NOT NULL CHECK (statut IN ('complete', 'partielle')),
    score_adequation SMALLINT NOT NULL CHECK (score_adequation BETWEEN 0 AND 25),
    score_delai SMALLINT NOT NULL CHECK (score_delai BETWEEN 0 AND 25),
    score_administratif SMALLINT NOT NULL CHECK (score_administratif BETWEEN 0 AND 25),
    score_risque SMALLINT NOT NULL CHECK (score_risque BETWEEN 0 AND 25),
    score_total SMALLINT GENERATED ALWAYS AS (
        score_adequation + score_delai + score_administratif + score_risque
    ) STORED,
    decision TEXT NOT NULL CHECK (decision IN ('GO', 'A_DISCUTER', 'NO_GO')),
    moteur TEXT NOT NULL DEFAULT 'openclaw',
    modele TEXT,
    fiche_chemin TEXT NOT NULL,
    fiche_markdown TEXT NOT NULL,
    fiche_sha256 TEXT NOT NULL CHECK (fiche_sha256 ~ '^[0-9a-f]{64}$'),
    contexte_sha256 TEXT NOT NULL CHECK (contexte_sha256 ~ '^[0-9a-f]{64}$'),
    profil_sha256 TEXT CHECK (profil_sha256 ~ '^[0-9a-f]{64}$'),
    sources JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(sources) = 'object'),
    generee_le TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (tender_id, contexte_sha256, fiche_sha256),
    CHECK (
        (score_adequation + score_delai + score_administratif + score_risque >= 70
            AND decision = 'GO')
        OR
        (score_adequation + score_delai + score_administratif + score_risque
            BETWEEN 45 AND 69 AND decision = 'A_DISCUTER')
        OR
        (score_adequation + score_delai + score_administratif + score_risque < 45
            AND decision = 'NO_GO')
    )
);

CREATE INDEX IF NOT EXISTS idx_analyses_ao_tender_date
    ON analyses_ao (tender_id, generee_le DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_analyses_ao_decision_score
    ON analyses_ao (decision, score_total DESC);

DO $$
BEGIN
    IF to_regclass('public.v_dernieres_analyses_ao') IS NULL THEN
        EXECUTE $view$
            CREATE VIEW v_dernieres_analyses_ao AS
            SELECT DISTINCT ON (a.tender_id)
                a.id,
                a.tender_id,
                ao.organisme,
                ao.titre,
                ao.date_publication,
                ao.date_limite,
                ao.url_detail,
                a.statut,
                a.score_adequation,
                a.score_delai,
                a.score_administratif,
                a.score_risque,
                a.score_total,
                a.decision,
                a.moteur,
                a.modele,
                a.fiche_chemin,
                a.contexte_sha256,
                a.generee_le
            FROM analyses_ao AS a
            JOIN appels_offres AS ao ON ao.tender_id = a.tender_id
            ORDER BY a.tender_id, a.generee_le DESC, a.id DESC
        $view$;
    END IF;
END;
$$;

COMMENT ON TABLE analyses_ao IS
    'Fiches et scores generes, separes des faits officiels HAICOP.';
COMMENT ON VIEW v_dernieres_analyses_ao IS
    'Derniere analyse enregistree pour chaque appel offres.';

COMMIT;
