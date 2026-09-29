INSERT INTO account_user (
    id, username, password_hash, role_code, enabled
) VALUES
    (
        '30ef62a1-b5ef-4a75-9ce5-5666e1f3c501',
        'student',
        '$2b$12$T2Q3H8CnylVTR82eYeeb3uW5NjgSeb0YHROSc6NLGegOL4lghn4xu',
        'STUDENT',
        TRUE
    ),
    (
        '6a4a13be-8d8a-4c87-8f33-d32755d26711',
        'support',
        '$2b$12$jbjSPCyfx7.QDAe9fjtpp.DCo1k2CQ0fNEkUOGkixB8OBWNkWdwtm',
        'SUPPORT_AGENT',
        TRUE
    ),
    (
        'e0bb3d4f-5a60-4e0f-89e4-7d9f7928a8f3',
        'admin',
        '$2b$12$FRLnkOXTbxAxKzd9Gcc4vejihobngCuMpH9wN/BiHPVS7N3CgVSvK',
        'ADMIN',
        TRUE
    );
