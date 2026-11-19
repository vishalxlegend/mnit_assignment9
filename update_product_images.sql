-- Run against an existing products.db to match the numbered JPEG assets.
UPDATE products
SET image_url = '/products/images/' || id || '.jpg';
