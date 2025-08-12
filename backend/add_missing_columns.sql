-- Add missing columns to users table
ALTER TABLE users 
ADD COLUMN IF NOT EXISTS name VARCHAR(255),
ADD COLUMN IF NOT EXISTS signup_method VARCHAR(50) DEFAULT 'email_only',
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- Update existing users to have a default signup_method
UPDATE users 
SET signup_method = CASE 
    WHEN password IS NOT NULL THEN 'password'
    ELSE 'email_only'
END
WHERE signup_method IS NULL;

-- Update existing users to have an updated_at timestamp
UPDATE users 
SET updated_at = created_at
WHERE updated_at IS NULL;
