"""
Management command: seed_food_database
Creates ~65 common Indian food items in the FoodItem table.
Safe to re-run: uses get_or_create on name.
"""

from django.core.management.base import BaseCommand
from strength_app.models import FoodItem

FOOD_DATA = [
    # (name, name_hindi, category, cal/100g, protein, carbs, fat, fiber, serving_g, serving_desc, is_mess_common)

    # ── Grains & Rice ──────────────────────────────────────────────────────────
    ('White Rice (cooked)',     'Chawal',       'grain', 130, 2.7, 28.2, 0.3, 0.4,  200, '1 medium bowl',        True),
    ('Brown Rice (cooked)',     'Brown Chawal', 'grain', 123, 2.6, 25.6, 0.9, 1.8,  200, '1 medium bowl',        False),
    ('Roti (wheat)',            'Roti',         'grain', 297, 9.0, 56.0, 4.0, 3.5,   40, '1 medium roti',        True),
    ('Paratha (plain)',         'Paratha',      'grain', 326, 7.0, 43.0,14.0, 2.5,   80, '1 medium paratha',     True),
    ('Idli',                    'Idli',         'grain', 58,  2.0, 11.0, 0.4, 0.5,  120, '2 medium idlis',       False),
    ('Dosa (plain)',            'Dosa',         'grain', 133, 3.4, 23.0, 3.0, 0.6,  100, '1 medium dosa',        False),
    ('Upma',                    'Upma',         'grain', 155, 3.5, 22.0, 6.0, 1.2,  150, '1 medium bowl',        False),
    ('Poha',                    'Poha',         'grain', 130, 3.0, 26.0, 1.5, 1.0,  150, '1 medium plate',       True),
    ('Bread (white slice)',     'Bread',        'grain', 265, 9.0, 49.0, 3.2, 2.7,   60, '2 slices',             False),
    ('Oats (cooked)',           'Oats',         'grain', 71,  2.5, 12.0, 1.5, 1.7,  200, '1 medium bowl',        False),
    ('Semolina / Rava',         'Sooji',        'grain', 360, 10.6,74.5, 1.0, 3.9,   50, '50g dry',              False),
    ('Bajra Roti',              'Bajra Roti',   'grain', 290, 8.0, 54.0, 5.0, 2.8,   45, '1 medium roti',        False),
    ('Jowar Roti',              'Jowar Roti',   'grain', 329, 10.4,67.6, 3.4, 2.6,   45, '1 medium roti',        False),

    # ── Dal & Legumes ─────────────────────────────────────────────────────────
    ('Dal (toor/arhar, cooked)','Toor Dal',     'dal',   116, 7.2, 19.0, 0.4, 2.5,  200, '1 medium bowl',        True),
    ('Dal (moong, cooked)',     'Moong Dal',    'dal',   105, 7.5, 18.5, 0.3, 1.9,  200, '1 medium bowl',        True),
    ('Chana Dal (cooked)',      'Chana Dal',    'dal',   164, 8.9, 26.5, 2.5, 3.5,  200, '1 medium bowl',        False),
    ('Rajma (cooked)',          'Rajma',        'dal',   127, 8.7, 22.0, 0.5, 6.4,  200, '1 medium bowl',        False),
    ('Chole / Chickpeas',       'Chole',        'dal',   164, 8.9, 27.4, 2.6, 7.6,  200, '1 medium bowl',        False),
    ('Sprouts (mixed)',         'Sprouts',      'dal',   62,  4.0,  9.5, 0.4, 1.8,  100, '1 small bowl',         False),
    ('Paneer',                  'Paneer',       'dairy', 265,18.3,  1.2,20.8, 0.0,   80, '4 medium cubes',       False),
    ('Soya Chunks (cooked)',    'Soya Badi',    'dal',   112,17.5,  7.0, 0.5, 1.5,  100, '1 small bowl',         False),

    # ── Vegetables ────────────────────────────────────────────────────────────
    ('Spinach (cooked)',        'Palak',        'vegetable', 23, 2.9, 3.6, 0.4, 2.2, 100, '1 small serving',     True),
    ('Aloo (potato, boiled)',   'Aloo',         'vegetable', 87, 1.9,20.0, 0.1, 1.8, 150, '1 medium potato',     True),
    ('Bhindi (okra)',           'Bhindi',       'vegetable', 33, 1.9, 7.0, 0.2, 3.2, 100, '1 small serving',     False),
    ('Gobhi (cauliflower)',     'Gobhi',        'vegetable', 25, 1.9, 5.0, 0.3, 2.5, 100, '1 small serving',     True),
    ('Brinjal / Baingan',       'Baingan',      'vegetable', 25, 1.0, 5.9, 0.2, 3.0, 100, '1 small serving',     False),
    ('Lauki / Bottle Gourd',    'Lauki',        'vegetable', 15, 0.6, 3.4, 0.1, 0.5, 100, '1 small serving',     False),
    ('Methi (fenugreek leaves)','Methi',        'vegetable', 49, 4.4, 6.0, 0.9, 2.7, 100, '1 small serving',     False),
    ('Tomato',                  'Tamatar',      'vegetable', 18, 0.9, 3.9, 0.2, 1.2,  80, '1 medium tomato',     True),
    ('Onion',                   'Pyaaz',        'vegetable', 40, 1.1, 9.3, 0.1, 1.7,  80, '1 medium onion',      True),
    ('Carrot',                  'Gajar',        'vegetable', 41, 0.9, 9.6, 0.2, 2.8,  80, '1 medium carrot',     True),
    ('Cucumber',                'Kheera',       'vegetable', 15, 0.6, 3.6, 0.1, 0.5, 100, '1 small bowl',        False),
    ('Mixed Sabzi (dry curry)', 'Sabzi',        'vegetable', 95, 2.5,10.0, 5.0, 2.0, 150, '1 medium serving',    True),

    # ── Fruits ────────────────────────────────────────────────────────────────
    ('Banana',                  'Kela',         'fruit', 89,  1.1, 22.8, 0.3, 2.6, 120, '1 medium banana',      False),
    ('Apple',                   'Seb',          'fruit', 52,  0.3, 13.8, 0.2, 2.4, 150, '1 medium apple',       False),
    ('Mango',                   'Aam',          'fruit', 60,  0.8, 15.0, 0.4, 1.6, 150, '1 medium slice',       False),
    ('Papaya',                  'Papita',       'fruit', 43,  0.5, 10.8, 0.3, 1.7, 200, '1 medium bowl',        False),
    ('Guava',                   'Amrood',       'fruit', 68,  2.6, 14.3, 1.0, 5.4, 100, '1 medium guava',       False),
    ('Orange',                  'Santra',       'fruit', 47,  0.9, 11.8, 0.1, 2.4, 150, '1 medium orange',      False),
    ('Watermelon',              'Tarbooz',      'fruit', 30,  0.6,  7.5, 0.2, 0.4, 300, '2 medium slices',      False),

    # ── Dairy ─────────────────────────────────────────────────────────────────
    ('Milk (full fat)',         'Doodh',        'dairy', 61,  3.2,  4.8, 3.3, 0.0, 250, '1 glass',              True),
    ('Curd / Dahi',             'Dahi',         'dairy', 61,  3.4,  4.7, 3.3, 0.0, 200, '1 medium bowl',        True),
    ('Buttermilk / Chaas',      'Chaas',        'dairy', 15,  1.2,  1.8, 0.2, 0.0, 250, '1 glass',              False),
    ('Ghee',                    'Ghee',         'oil_fat',900, 0.0,  0.0,100.0,0.0,  10, '1 teaspoon',           True),
    ('Egg (whole, boiled)',     'Anda',         'non_veg',155, 13.0, 1.1,11.0, 0.0,  55, '1 large egg',          False),
    ('Paneer (low fat)',        'Low Fat Paneer','dairy',180, 18.0, 3.0, 9.0, 0.0,  80, '4 medium cubes',       False),

    # ── Non-Vegetarian ────────────────────────────────────────────────────────
    ('Chicken Breast (cooked)', 'Murg',         'non_veg',165,31.0,  0.0, 3.6, 0.0, 120, '1 medium piece',      False),
    ('Chicken Curry',           'Chicken Curry','non_veg',150,14.0,  4.0, 9.0, 0.5, 150, '1 medium bowl',        True),
    ('Egg Bhurji',              'Egg Bhurji',   'non_veg',175,12.0,  3.5,12.5, 0.3, 120, '2-egg serving',        False),
    ('Fish Curry',              'Fish Curry',   'non_veg',130,16.0,  3.0, 6.0, 0.0, 150, '1 medium bowl',        False),
    ('Tuna (canned, water)',    'Tuna',         'non_veg',116,26.0,  0.0, 1.0, 0.0, 100, '100g',                 False),

    # ── Snacks & Street Food ──────────────────────────────────────────────────
    ('Samosa',                  'Samosa',       'snack', 308, 5.0, 34.0,17.0, 2.0,  90, '1 medium samosa',      True),
    ('Vada Pav',                'Vada Pav',     'snack', 290, 6.0, 42.0,11.0, 2.5, 150, '1 vada pav',           False),
    ('Dhokla',                  'Dhokla',       'snack', 160, 5.0, 28.0, 3.5, 1.2, 100, '2 medium pieces',      False),
    ('Chivda / Poha Chivda',    'Chivda',       'snack', 380, 7.5, 54.0,15.0, 3.5,  50, '1 small handful',      False),
    ('Biscuit (Marie)',         'Biscuit',      'snack', 450, 7.5, 74.0,13.5, 1.5,  30, '4 biscuits',           False),
    ('Peanuts (roasted)',       'Moongfali',    'snack', 567,25.8, 16.1,49.2, 8.5,  30, '1 small handful',      False),
    ('Chana (roasted, bhuna)',  'Bhuna Chana',  'snack', 364,22.0, 53.0, 5.0,17.0,  30, '1 small handful',      False),

    # ── Beverages ─────────────────────────────────────────────────────────────
    ('Chai (with milk+sugar)',  'Chai',         'beverage',38,1.5,  6.5, 1.0, 0.0, 150, '1 small cup',          True),
    ('Coffee (with milk)',      'Coffee',       'beverage',30,1.2,  4.5, 0.8, 0.0, 200, '1 medium cup',         False),
    ('Coconut Water',           'Naariyal Pani','beverage',19,0.7,  3.7, 0.2, 1.1, 250, '1 medium coconut',     False),
    ('Lassi (sweet)',           'Lassi',        'beverage',100,3.5,17.0, 2.5, 0.0, 250, '1 glass',              False),
    ('Protein Shake (whey+milk)','Protein Shake','beverage',155,24.0,10.0, 2.0, 0.5, 300, '1 scoop + 250ml milk', False),

    # ── Mess Common ───────────────────────────────────────────────────────────
    ('Dal Rice (combination)',  'Dal Chawal',   'mess',  150, 5.5, 28.0, 1.5, 1.5, 350, '1 full plate',         True),
    ('Curd Rice',               'Dahi Chawal',  'mess',  110, 3.5, 22.0, 1.0, 0.4, 300, '1 medium plate',       True),
    ('Khichdi',                 'Khichdi',      'mess',  130, 5.0, 24.0, 2.5, 2.0, 250, '1 medium bowl',        True),
]


class Command(BaseCommand):
    help = 'Seed the FoodItem table with ~65 Indian food items'

    def handle(self, *args, **kwargs):
        created = 0
        updated = 0
        for row in FOOD_DATA:
            (name, name_hindi, category,
             cal, protein, carbs, fat, fiber,
             serving_g, serving_desc, is_mess) = row

            obj, was_created = FoodItem.objects.get_or_create(
                name=name,
                defaults={
                    'name_hindi': name_hindi,
                    'category': category,
                    'calories_per_100g': cal,
                    'protein_per_100g': protein,
                    'carbs_per_100g': carbs,
                    'fat_per_100g': fat,
                    'fiber_per_100g': fiber,
                    'serving_size_g': serving_g,
                    'serving_description': serving_desc,
                    'is_mess_common': is_mess,
                    'is_active': True,
                }
            )
            if was_created:
                created += 1
            else:
                # Update nutritional values in case data changed
                obj.calories_per_100g = cal
                obj.protein_per_100g  = protein
                obj.carbs_per_100g    = carbs
                obj.fat_per_100g      = fat
                obj.fiber_per_100g    = fiber
                obj.is_mess_common    = is_mess
                obj.save()
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Food database seeded: {created} created, {updated} updated ({created + updated} total)'
        ))
