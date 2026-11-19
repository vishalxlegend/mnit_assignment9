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
    (1, 'City Hatchback Toy', 'A miniature hatchback toy for a city-themed vehicle collection.', 65000, '/products/images/1.jpg', 5),
    (2, 'Comfort Sedan Toy', 'A sedan toy model for pretend city journeys and display.', 98000, '/products/images/2.jpg', 3),
    (3, 'Adventure SUV Toy', 'An SUV toy model for imaginary family adventures.', 145000, '/products/images/3.jpg', 2),
    (4, 'Electric City Toy', 'A toy model inspired by a compact electric city car.', 105000, '/products/images/4.jpg', 6),
    (5, 'Family MPV Toy', 'A miniature MPV for pretend family road trips.', 125000, '/products/images/5.jpg', 4),
    (6, 'Sport Hatchback Toy', 'A sporty hatchback toy for an imaginary racing collection.', 92000, '/products/images/6.jpg', 3),
    (7, 'Executive Sedan Toy', 'An executive sedan toy model for a miniature car collection.', 185000, '/products/images/7.jpg', 2),
    (8, 'Compact SUV Toy', 'A compact SUV toy for pretend city adventures.', 110000, '/products/images/8.jpg', 7),
    (9, 'Touring Wagon Toy', 'A miniature touring wagon for imaginary road trips.', 138000, '/products/images/9.jpg', 3),
    (10, 'Hybrid Sedan Toy', 'A toy sedan model inspired by hybrid car styling.', 210000, '/products/images/10.jpg', 4),
    (11, 'Urban Crossover Toy', 'An urban crossover toy for a miniature city collection.', 118000, '/products/images/11.jpg', 5),
    (12, 'Electric SUV Toy', 'A toy SUV model inspired by electric vehicle styling.', 245000, '/products/images/12.jpg', 2),
    (13, 'Budget Hatchback Toy', 'A simple hatchback toy for starting a car collection.', 48000, '/products/images/13.jpg', 10),
    (14, 'Premium SUV Toy', 'A premium-style SUV toy model for play and display.', 320000, '/products/images/14.jpg', 1),
    (15, 'Offroad Explorer Toy', 'An offroad-inspired toy vehicle for imaginary expeditions.', 280000, '/products/images/15.jpg', 3),
    (16, 'City CNG Toy', 'A miniature toy model inspired by a city CNG hatchback.', 78000, '/products/images/16.jpg', 8),
    (17, 'Luxury Sedan Toy', 'A luxury-style sedan toy for a miniature vehicle display.', 450000, '/products/images/17.jpg', 1),
    (18, 'Utility Pickup Toy', 'A pickup truck toy model for pretend worksite adventures.', 225000, '/products/images/18.jpg', 4),
    (19, 'Cargo Van Toy', 'A miniature cargo van for imaginary delivery rounds.', 125000, '/products/images/19.jpg', 6),
    (20, 'Sports Coupe Toy', 'A sports coupe toy model for a sporty car collection.', 350000, '/products/images/20.jpg', 0);

