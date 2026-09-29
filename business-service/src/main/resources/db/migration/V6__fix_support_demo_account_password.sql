-- Keeps the seeded local smoke account aligned with the documented support-pass.
UPDATE account_user
SET password_hash = '$2b$12$WyoQ8lcef5ySUy0.unheue0V/wLkuaGlyisAczQtk87CQ/YcUC8Oa',
    updated_at = CURRENT_TIMESTAMP
WHERE username = 'support';
