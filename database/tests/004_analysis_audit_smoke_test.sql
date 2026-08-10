BEGIN;

INSERT INTO collectes_haicop (source, statut, terminee_le)
VALUES ('test-analysis-audit', 'terminee', clock_timestamp())
RETURNING id \gset test_collection_

INSERT INTO appels_offres (
    tender_id, organisme, titre, date_limite, url_detail, donnees_brutes, collecte_id
) VALUES (
    'Tender-TEST-ANALYSIS-AUDIT',
    'Organisme de test',
    'AO de test audit analyse',
    clock_timestamp() + interval '30 days',
    'https://www.marchespublics.gov.tn/fr/appels-doffres/Tender-TEST-ANALYSIS-AUDIT',
    '{"test": true}'::jsonb,
    :test_collection_id
);

INSERT INTO analyses_ao (
    tender_id, statut,
    score_adequation, score_delai, score_administratif, score_risque,
    decision, fiche_chemin, fiche_markdown, fiche_sha256, contexte_sha256,
    profil_sha256, sources, contexte_snapshot, bareme_version, date_evaluation
) VALUES (
    'Tender-TEST-ANALYSIS-AUDIT', 'complete',
    20, 20, 15, 15,
    'GO', 'fiches/test.md', '# première fiche', repeat('a', 64), repeat('b', 64),
    repeat('c', 64), '{"test": true}'::jsonb, '{"version": 1}'::jsonb,
    'test-v1', DATE '2026-08-10'
)
ON CONFLICT (tender_id, contexte_sha256) DO UPDATE SET
    fiche_markdown = EXCLUDED.fiche_markdown,
    fiche_sha256 = EXCLUDED.fiche_sha256;

INSERT INTO analyses_ao (
    tender_id, statut,
    score_adequation, score_delai, score_administratif, score_risque,
    decision, fiche_chemin, fiche_markdown, fiche_sha256, contexte_sha256,
    profil_sha256, sources, contexte_snapshot, bareme_version, date_evaluation
) VALUES (
    'Tender-TEST-ANALYSIS-AUDIT', 'complete',
    20, 20, 15, 15,
    'GO', 'fiches/test.md', '# fiche corrigée', repeat('d', 64), repeat('b', 64),
    repeat('c', 64), '{"test": true}'::jsonb, '{"version": 1}'::jsonb,
    'test-v1', DATE '2026-08-10'
)
ON CONFLICT (tender_id, contexte_sha256) DO UPDATE SET
    fiche_markdown = EXCLUDED.fiche_markdown,
    fiche_sha256 = EXCLUDED.fiche_sha256;

DO $$
BEGIN
    IF (
        SELECT count(*) FROM analyses_ao
        WHERE tender_id = 'Tender-TEST-ANALYSIS-AUDIT'
    ) <> 1 THEN
        RAISE EXCEPTION 'Une analyse du même contexte a été dupliquée';
    END IF;
    IF (
        SELECT fiche_sha256 FROM analyses_ao
        WHERE tender_id = 'Tender-TEST-ANALYSIS-AUDIT'
    ) <> repeat('d', 64) THEN
        RAISE EXCEPTION 'La fiche corrigée n a pas remplacé la première';
    END IF;
END;
$$;

ROLLBACK;
