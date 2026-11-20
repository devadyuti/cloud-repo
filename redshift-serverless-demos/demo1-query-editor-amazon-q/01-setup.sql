-- =============================================================================
-- Demo 1 setup: Amazon Q generative SQL on a loyalty / loyalty dataset
-- Target: Amazon Redshift Serverless (run in Query Editor v2)
-- Safe to run in database `dev`. Creates schema `anycompany_demo`.
-- Re-runnable: drops and recreates the schema each time.
-- =============================================================================

DROP SCHEMA IF EXISTS anycompany_demo CASCADE;
CREATE SCHEMA anycompany_demo;

-- -----------------------------------------------------------------------------
-- Numbers helper (recursive CTE -> real table).
-- generate_series() is leader-node only and unreliable for INSERT on Serverless,
-- so we materialise a numbers table and drive all data generation from it.
-- -----------------------------------------------------------------------------
CREATE TABLE anycompany_demo._numbers AS
WITH RECURSIVE nums(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM nums WHERE n < 5000
)
SELECT n FROM nums;

-- -----------------------------------------------------------------------------
-- Dimension: members  (500 rows)
-- -----------------------------------------------------------------------------
CREATE TABLE anycompany_demo.members (
    member_id   INTEGER      NOT NULL,
    first_name  VARCHAR(50),
    last_name   VARCHAR(50),
    email       VARCHAR(120),
    city        VARCHAR(50),
    region      VARCHAR(50),
    tier        VARCHAR(20),
    join_date   DATE,
    PRIMARY KEY (member_id)
);

INSERT INTO anycompany_demo.members
SELECT
    n AS member_id,
    CASE n % 10
        WHEN 0 THEN 'Olivia' WHEN 1 THEN 'Jack'   WHEN 2 THEN 'Amelia'
        WHEN 3 THEN 'Harry'  WHEN 4 THEN 'Isla'    WHEN 5 THEN 'George'
        WHEN 6 THEN 'Ava'    WHEN 7 THEN 'Noah'    WHEN 8 THEN 'Mia'
        ELSE 'Leo' END AS first_name,
    CASE n % 8
        WHEN 0 THEN 'Smith'  WHEN 1 THEN 'Jones'  WHEN 2 THEN 'Taylor'
        WHEN 3 THEN 'Brown'  WHEN 4 THEN 'Wilson' WHEN 5 THEN 'Evans'
        WHEN 6 THEN 'Patel'  ELSE 'Walker' END AS last_name,
    'member' || n || '@example.com' AS email,
    CASE n % 8
        WHEN 0 THEN 'London'     WHEN 1 THEN 'Manchester' WHEN 2 THEN 'Birmingham'
        WHEN 3 THEN 'Leeds'      WHEN 4 THEN 'Glasgow'    WHEN 5 THEN 'Bristol'
        WHEN 6 THEN 'Liverpool'  ELSE 'Edinburgh' END AS city,
    CASE n % 8
        WHEN 0 THEN 'England'  WHEN 1 THEN 'England'  WHEN 2 THEN 'England'
        WHEN 3 THEN 'England'  WHEN 4 THEN 'Scotland' WHEN 5 THEN 'England'
        WHEN 6 THEN 'England'  ELSE 'Scotland' END AS region,
    CASE
        WHEN n % 100 = 0 THEN 'Platinum'
        WHEN n % 10  = 0 THEN 'Gold'
        WHEN n % 3   = 0 THEN 'Silver'
        ELSE 'Bronze' END AS tier,
    DATEADD(day, -(n % 1000), CURRENT_DATE) AS join_date
FROM anycompany_demo._numbers
WHERE n <= 500;

-- -----------------------------------------------------------------------------
-- Dimension: merchants  (12 rows)
-- -----------------------------------------------------------------------------
CREATE TABLE anycompany_demo.merchants (
    merchant_id    INTEGER      NOT NULL,
    merchant_name  VARCHAR(80),
    category       VARCHAR(40),
    city           VARCHAR(50),
    PRIMARY KEY (merchant_id)
);

INSERT INTO anycompany_demo.merchants VALUES
    (1,  'FreshMart Grocery',   'Grocery',      'London'),
    (2,  'Corner Coffee',       'Coffee',       'Manchester'),
    (3,  'PetrolPlus Fuel',     'Fuel',         'Birmingham'),
    (4,  'The Garden Bistro',   'Dining',       'London'),
    (5,  'UrbanStyle Retail',   'Retail',       'Leeds'),
    (6,  'SkyHigh Travel',      'Travel',       'Glasgow'),
    (7,  'QuickBite Takeaway',  'Dining',       'Bristol'),
    (8,  'GreenLeaf Pharmacy',  'Health',       'Liverpool'),
    (9,  'TechHub Electronics', 'Retail',       'Edinburgh'),
    (10, 'DailyGrind Coffee',   'Coffee',       'London'),
    (11, 'MegaFuel Station',    'Fuel',         'Leeds'),
    (12, 'HomeNest Furnishing', 'Home',         'Manchester');

-- -----------------------------------------------------------------------------
-- Dimension: offers  (one active offer per merchant)
-- -----------------------------------------------------------------------------
CREATE TABLE anycompany_demo.offers (
    offer_id      INTEGER      NOT NULL,
    merchant_id   INTEGER      NOT NULL,
    offer_name    VARCHAR(100),
    cashback_pct  DECIMAL(4,2),
    start_date    DATE,
    end_date      DATE,
    is_active     BOOLEAN,
    PRIMARY KEY (offer_id)
);

INSERT INTO anycompany_demo.offers
SELECT
    merchant_id AS offer_id,
    merchant_id,
    merchant_name || ' cashback' AS offer_name,
    CASE category
        WHEN 'Grocery' THEN 1.50 WHEN 'Coffee' THEN 5.00 WHEN 'Fuel'   THEN 2.00
        WHEN 'Dining'  THEN 4.00 WHEN 'Retail' THEN 3.00 WHEN 'Travel' THEN 6.00
        WHEN 'Health'  THEN 2.50 ELSE 3.50 END AS cashback_pct,
    DATEADD(day, -180, CURRENT_DATE) AS start_date,
    DATEADD(day,  180, CURRENT_DATE) AS end_date,
    TRUE AS is_active
FROM anycompany_demo.merchants;

-- -----------------------------------------------------------------------------
-- Fact: transactions  (5,000 rows over the last ~365 days)
-- -----------------------------------------------------------------------------
CREATE TABLE anycompany_demo.transactions (
    transaction_id   INTEGER        NOT NULL,
    member_id        INTEGER        NOT NULL,
    merchant_id      INTEGER        NOT NULL,
    txn_ts           TIMESTAMP,
    amount           DECIMAL(10,2),
    cashback_earned  DECIMAL(10,2),
    channel          VARCHAR(20),
    PRIMARY KEY (transaction_id)
);

INSERT INTO anycompany_demo.transactions
SELECT
    n AS transaction_id,
    (FLOOR(RANDOM() * 500) + 1)::INT           AS member_id,
    (FLOOR(RANDOM() * 12) + 1)::INT            AS merchant_id,
    DATEADD(second, -(FLOOR(RANDOM() * 31536000))::INT, GETDATE()) AS txn_ts,
    ROUND((RANDOM() * 199 + 1)::NUMERIC, 2)    AS amount,
    0.00                                       AS cashback_earned,  -- filled below
    CASE WHEN RANDOM() < 0.6 THEN 'card_present' ELSE 'online' END AS channel
FROM anycompany_demo._numbers
WHERE n <= 5000;

-- Set cashback based on the merchant's active offer rate (realistic join-able value)
UPDATE anycompany_demo.transactions t
SET cashback_earned = ROUND(t.amount * o.cashback_pct / 100.0, 2)
FROM anycompany_demo.offers o
WHERE o.merchant_id = t.merchant_id;

-- -----------------------------------------------------------------------------
-- Fact: redemptions  (800 rows over the last ~365 days)
-- -----------------------------------------------------------------------------
CREATE TABLE anycompany_demo.redemptions (
    redemption_id    INTEGER      NOT NULL,
    member_id        INTEGER      NOT NULL,
    redeemed_ts      TIMESTAMP,
    points_redeemed  INTEGER,
    anycompany_type      VARCHAR(40),
    PRIMARY KEY (redemption_id)
);

INSERT INTO anycompany_demo.redemptions
SELECT
    n AS redemption_id,
    (FLOOR(RANDOM() * 500) + 1)::INT AS member_id,
    DATEADD(second, -(FLOOR(RANDOM() * 31536000))::INT, GETDATE()) AS redeemed_ts,
    ((FLOOR(RANDOM() * 20) + 1) * 100)::INT AS points_redeemed,
    CASE n % 4
        WHEN 0 THEN 'Gift Card'
        WHEN 1 THEN 'Statement Credit'
        WHEN 2 THEN 'Travel Miles'
        ELSE 'Merchandise' END AS anycompany_type
FROM anycompany_demo._numbers
WHERE n <= 800;

-- -----------------------------------------------------------------------------
-- Housekeeping
-- -----------------------------------------------------------------------------
DROP TABLE anycompany_demo._numbers;

ANALYZE anycompany_demo.members;
ANALYZE anycompany_demo.merchants;
ANALYZE anycompany_demo.offers;
ANALYZE anycompany_demo.transactions;
ANALYZE anycompany_demo.redemptions;

-- Done. Run 02-verify.sql to confirm.
