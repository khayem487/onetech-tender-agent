BEGIN;

DO $$
DECLARE
    interaction_count INTEGER;
    saved_status TEXT;
BEGIN
    INSERT INTO telegram_poll_state (consommateur, prochain_update_id)
    VALUES ('sql-smoke-telegram', 101)
    ON CONFLICT (consommateur) DO UPDATE SET prochain_update_id = EXCLUDED.prochain_update_id;

    INSERT INTO telegram_interactions (
        update_id,
        chat_hash,
        message_id,
        expediteur_hash,
        message_sha256,
        type_interaction,
        statut
    ) VALUES (
        987654321,
        repeat('a', 64),
        41,
        repeat('b', 64),
        repeat('c', 64),
        'mention',
        'recue'
    ) ON CONFLICT DO NOTHING;

    -- A replay of the same Telegram update must not create another response job.
    INSERT INTO telegram_interactions (
        update_id,
        chat_hash,
        message_id,
        expediteur_hash,
        message_sha256,
        type_interaction,
        statut
    ) VALUES (
        987654321,
        repeat('a', 64),
        41,
        repeat('b', 64),
        repeat('c', 64),
        'mention',
        'recue'
    ) ON CONFLICT DO NOTHING;

    SELECT count(*) INTO interaction_count
    FROM telegram_interactions
    WHERE update_id = 987654321;
    IF interaction_count <> 1 THEN
        RAISE EXCEPTION 'Telegram update deduplication failed: % rows', interaction_count;
    END IF;

    UPDATE telegram_interactions
    SET statut = 'repondue', message_reponse_id = 99
    WHERE update_id = 987654321;

    SELECT statut INTO saved_status
    FROM telegram_interactions
    WHERE update_id = 987654321;
    IF saved_status <> 'repondue' THEN
        RAISE EXCEPTION 'Telegram response state was not saved';
    END IF;
END;
$$;

ROLLBACK;
