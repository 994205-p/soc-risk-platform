INSERT INTO roles (role_name) VALUES
 ('management'), ('soc_analyst'), ('security_engineer')
ON CONFLICT (role_name) DO NOTHING;

-- Demo users. Password for all demo accounts is "demo1234".
-- password_hash values are bcrypt hashes generated at seed-time by backend/app/utils/seed_users.py
-- (kept out of this static SQL file so hashing logic lives in one place; see README "Demo users").
