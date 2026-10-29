-- This file creates the database and sample data on the first run.
-- Prices are integer paise: 100 paise = 1 rupee.
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    price_paise INTEGER NOT NULL CHECK (price_paise >= 0),
    image_url TEXT NOT NULL,
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0)
);

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES
    (1, 'City Hatchback',
     'A compact petrol hatchback with a manual transmission, five seats, and an easy-to-park design for daily city trips.',
     65000000, '/products/images/1.jpg', 5),
    (2, 'Comfort Sedan',
     'A spacious five-seat sedan with an automatic transmission, generous boot space, and a comfortable cabin for longer journeys.',
     98000000, '/products/images/2.jpg', 3),
    (3, 'Adventure SUV',
     'A versatile five-seat SUV with an automatic transmission, higher ground clearance, and room for family luggage.',
     145000000, '/products/images/3.jpg', 2);


INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (1, 'City Hatchback', 'Compact petrol hatchback with manual transmission and five seats.', 65000000, '/products/images/1.jpg', 5)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (2, 'Comfort Sedan', 'Spacious automatic sedan with five seats and a large boot.', 98000000, '/products/images/2.jpg', 3)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (3, 'Adventure SUV', 'Family SUV with automatic transmission and high ground clearance.', 145000000, '/products/images/3.jpg', 2)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (4, 'Electric City', 'Compact electric car for quiet and efficient city travel.', 105000000, '/products/images/4.jpg', 6)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (5, 'Family MPV', 'Seven-seat petrol MPV with flexible luggage space.', 125000000, '/products/images/5.jpg', 4)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (6, 'Sport Hatchback', 'Petrol hatchback with a turbo engine and manual transmission.', 92000000, '/products/images/6.jpg', 3)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (7, 'Executive Sedan', 'Premium automatic sedan with a spacious rear cabin.', 185000000, '/products/images/7.jpg', 2)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (8, 'Compact SUV', 'Five-seat petrol SUV with a compact body for city driving.', 110000000, '/products/images/8.jpg', 7)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (9, 'Touring Wagon', 'Comfortable family wagon with generous luggage capacity.', 138000000, '/products/images/9.jpg', 3)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (10, 'Hybrid Sedan', 'Petrol-electric hybrid sedan with automatic transmission.', 210000000, '/products/images/10.jpg', 4)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (11, 'Urban Crossover', 'Compact crossover with five seats and a raised driving position.', 118000000, '/products/images/11.jpg', 5)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (12, 'Electric SUV', 'Battery-powered family SUV with an automatic drivetrain.', 245000000, '/products/images/12.jpg', 2)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (13, 'Budget Hatchback', 'Affordable petrol hatchback with manual transmission.', 48000000, '/products/images/13.jpg', 10)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (14, 'Premium SUV', 'Seven-seat automatic SUV with a premium interior.', 320000000, '/products/images/14.jpg', 1)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (15, 'Offroad Explorer', 'Four-wheel-drive SUV designed for rough terrain.', 280000000, '/products/images/15.jpg', 3)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (16, 'City CNG', 'Petrol and CNG hatchback with a manual transmission.', 78000000, '/products/images/16.jpg', 8)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (17, 'Luxury Sedan', 'Premium sedan with automatic transmission and a refined cabin.', 450000000, '/products/images/17.jpg', 1)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (18, 'Utility Pickup', 'Double-cab pickup with an open load bed for work and travel.', 225000000, '/products/images/18.jpg', 4)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (19, 'Cargo Van', 'Practical commercial van with an enclosed cargo area.', 125000000, '/products/images/19.jpg', 6)
ON CONFLICT(id) DO NOTHING;

INSERT INTO products (id, name, description, price_paise, image_url, stock)
VALUES (20, 'Sports Coupe', 'Two-door petrol coupe with an automatic transmission.', 350000000, '/products/images/20.jpg', 0)
ON CONFLICT(id) DO NOTHING;
