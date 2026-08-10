BEGIN;

-- Preserve the exact semantic snapshot read by OpenClaw and make one analysis
-- row authoritative for a stable tender context. The context hash already
-- includes the profile, rubric and evaluation date.
ALTER TABLE analyses_ao
    ADD COLUMN IF NOT EXISTS contexte_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS bareme_version TEXT NOT NULL DEFAULT 'v0-model-indicatif',
    ADD COLUMN IF NOT EXISTS date_evaluation DATE NOT NULL DEFAULT CURRENT_DATE;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'analyses_ao'::regclass
          AND conname = 'analyses_ao_contexte_snapshot_object_check'
    ) THEN
        ALTER TABLE analyses_ao
            ADD CONSTRAINT analyses_ao_contexte_snapshot_object_check
            CHECK (jsonb_typeof(contexte_snapshot) = 'object');
    END IF;
END;
$$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_analyses_ao_contexte
    ON analyses_ao (tender_id, contexte_sha256);

CREATE INDEX IF NOT EXISTS idx_analyses_ao_date_evaluation
    ON analyses_ao (date_evaluation DESC, decision, score_total DESC);

CREATE OR REPLACE VIEW v_dernieres_analyses_ao AS
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
    a.generee_le,
    a.fiche_sha256,
    a.profil_sha256,
    a.bareme_version,
    a.date_evaluation,
    a.sources
FROM analyses_ao AS a
JOIN appels_offres AS ao ON ao.tender_id = a.tender_id
ORDER BY a.tender_id, a.generee_le DESC, a.id DESC;

COMMENT ON COLUMN analyses_ao.contexte_snapshot IS
    'Snapshot JSON exact lu pour produire la fiche; ne contient aucun secret.';
COMMENT ON COLUMN analyses_ao.bareme_version IS
    'Version du bareme de score utilise par la skill analyse-ao.';
COMMENT ON COLUMN analyses_ao.date_evaluation IS
    'Date de reference pour les delais J-X/J+X et l identite de l analyse.';

COMMIT;
