BEGIN;

INSERT INTO collectes_haicop (source, statut, terminee_le)
VALUES ('test-analysis', 'terminee', clock_timestamp())
RETURNING id \gset test_collection_

INSERT INTO appels_offres (
    tender_id,
    organisme,
    titre,
    date_limite,
    url_detail,
    donnees_brutes,
    collecte_id
) VALUES (
    'Tender-TEST-ANALYSIS',
    'Organisme de test',
    'AO de test analyse',
    clock_timestamp() + interval '30 days',
    'https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-TEST-ANALYSIS',
    '{"test": true}'::jsonb,
    :test_collection_id
);

INSERT INTO analyses_ao (
    tender_id,
    statut,
    score_adequation,
    score_delai,
    score_administratif,
    score_risque,
    decision,
    fiche_chemin,
    fiche_markdown,
    fiche_sha256,
    contexte_sha256,
    sources
) VALUES (
    'Tender-TEST-ANALYSIS',
    'complete',
    20,
    20,
    15,
    15,
    'GO',
    'fiches/test.md',
    '# fiche test',
    repeat('a', 64),
    repeat('b', 64),
    '{"test": true}'::jsonb
)
ON CONFLICT (tender_id, contexte_sha256, fiche_sha256) DO NOTHING;

INSERT INTO analyses_ao (
    tender_id,
    statut,
    score_adequation,
    score_delai,
    score_administratif,
    score_risque,
    decision,
    fiche_chemin,
    fiche_markdown,
    fiche_sha256,
    contexte_sha256,
    sources
) VALUES (
    'Tender-TEST-ANALYSIS',
    'complete',
    20,
    20,
    15,
    15,
    'GO',
    'fiches/test.md',
    '# fiche test',
    repeat('a', 64),
    repeat('b', 64),
    '{"test": true}'::jsonb
)
ON CONFLICT (tender_id, contexte_sha256, fiche_sha256) DO NOTHING;

DO $$
BEGIN
    IF (
        SELECT count(*) FROM analyses_ao
        WHERE tender_id = 'Tender-TEST-ANALYSIS'
    ) <> 1 THEN
        RAISE EXCEPTION 'La sauvegarde analyse idempotente a echoue';
    END IF;

    IF (
        SELECT score_total FROM analyses_ao
        WHERE tender_id = 'Tender-TEST-ANALYSIS'
    ) <> 70 THEN
        RAISE EXCEPTION 'Le score total genere est incorrect';
    END IF;
END;
$$;

ROLLBACK;
