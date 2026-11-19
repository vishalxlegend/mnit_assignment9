-- Convert the original sample vehicles to toy models.
-- Original-price guards make this safe to rerun without dividing prices again.
BEGIN TRANSACTION;
UPDATE products SET name = 'City Hatchback Toy', description = 'A miniature hatchback toy for a city-themed vehicle collection.', price_paise = 65000 WHERE id = 1 AND price_paise = 65000000;
UPDATE products SET name = 'Comfort Sedan Toy', description = 'A sedan toy model for pretend city journeys and display.', price_paise = 98000 WHERE id = 2 AND price_paise = 98000000;
UPDATE products SET name = 'Adventure SUV Toy', description = 'An SUV toy model for imaginary family adventures.', price_paise = 145000 WHERE id = 3 AND price_paise = 145000000;
UPDATE products SET name = 'Electric City Toy', description = 'A toy model inspired by a compact electric city car.', price_paise = 105000 WHERE id = 4 AND price_paise = 105000000;
UPDATE products SET name = 'Family MPV Toy', description = 'A miniature MPV for pretend family road trips.', price_paise = 125000 WHERE id = 5 AND price_paise = 125000000;
UPDATE products SET name = 'Sport Hatchback Toy', description = 'A sporty hatchback toy for an imaginary racing collection.', price_paise = 92000 WHERE id = 6 AND price_paise = 92000000;
UPDATE products SET name = 'Executive Sedan Toy', description = 'An executive sedan toy model for a miniature car collection.', price_paise = 185000 WHERE id = 7 AND price_paise = 185000000;
UPDATE products SET name = 'Compact SUV Toy', description = 'A compact SUV toy for pretend city adventures.', price_paise = 110000 WHERE id = 8 AND price_paise = 110000000;
UPDATE products SET name = 'Touring Wagon Toy', description = 'A miniature touring wagon for imaginary road trips.', price_paise = 138000 WHERE id = 9 AND price_paise = 138000000;
UPDATE products SET name = 'Hybrid Sedan Toy', description = 'A toy sedan model inspired by hybrid car styling.', price_paise = 210000 WHERE id = 10 AND price_paise = 210000000;
UPDATE products SET name = 'Urban Crossover Toy', description = 'An urban crossover toy for a miniature city collection.', price_paise = 118000 WHERE id = 11 AND price_paise = 118000000;
UPDATE products SET name = 'Electric SUV Toy', description = 'A toy SUV model inspired by electric vehicle styling.', price_paise = 245000 WHERE id = 12 AND price_paise = 245000000;
UPDATE products SET name = 'Budget Hatchback Toy', description = 'A simple hatchback toy for starting a car collection.', price_paise = 48000 WHERE id = 13 AND price_paise = 48000000;
UPDATE products SET name = 'Premium SUV Toy', description = 'A premium-style SUV toy model for play and display.', price_paise = 320000 WHERE id = 14 AND price_paise = 320000000;
UPDATE products SET name = 'Offroad Explorer Toy', description = 'An offroad-inspired toy vehicle for imaginary expeditions.', price_paise = 280000 WHERE id = 15 AND price_paise = 280000000;
UPDATE products SET name = 'City CNG Toy', description = 'A miniature toy model inspired by a city CNG hatchback.', price_paise = 78000 WHERE id = 16 AND price_paise = 78000000;
UPDATE products SET name = 'Luxury Sedan Toy', description = 'A luxury-style sedan toy for a miniature vehicle display.', price_paise = 450000 WHERE id = 17 AND price_paise = 450000000;
UPDATE products SET name = 'Utility Pickup Toy', description = 'A pickup truck toy model for pretend worksite adventures.', price_paise = 225000 WHERE id = 18 AND price_paise = 225000000;
UPDATE products SET name = 'Cargo Van Toy', description = 'A miniature cargo van for imaginary delivery rounds.', price_paise = 125000 WHERE id = 19 AND price_paise = 125000000;
UPDATE products SET name = 'Sports Coupe Toy', description = 'A sports coupe toy model for a sporty car collection.', price_paise = 350000 WHERE id = 20 AND price_paise = 350000000;
COMMIT;
