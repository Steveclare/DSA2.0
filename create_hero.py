from PIL import Image, ImageDraw, ImageFont
import numpy as np
from random import choice, randint
import os

def generate_hero_image():
    # Create a new image with a gradient background
    width = 800
    height = 400
    image = Image.new('RGBA', (width, height))
    draw = ImageDraw.Draw(image)
    
    # Random color scheme selection
    color_schemes = [
        # Blue-Purple gradient
        ((44, 62, 80), (64, 82, 100)),
        # Dark to Light Blue
        ((20, 30, 60), (40, 60, 120)),
        # Sunset colors
        ((45, 52, 54), (85, 52, 54)),
        # Deep Ocean
        ((0, 52, 89), (0, 126, 167)),
        # Forest
        ((11, 72, 107), (35, 113, 164)),
        # Night Sky
        ((25, 25, 112), (65, 105, 225))
    ]
    
    base_color, target_color = choice(color_schemes)
    
    # Create a smooth gradient background
    for y in range(height):
        r = int(base_color[0] + (y / height) * (target_color[0] - base_color[0]))
        g = int(base_color[1] + (y / height) * (target_color[1] - base_color[1]))
        b = int(base_color[2] + (y / height) * (target_color[2] - base_color[2]))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    
    # Random shape generation
    shape_types = ['rectangle', 'circle']
    num_shapes = randint(15, 30)
    
    for _ in range(num_shapes):
        shape = choice(shape_types)
        x = randint(-50, width+50)
        y = randint(-50, height+50)
        size = randint(20, 150)
        opacity = randint(30, 80)
        
        # Random shape color with slight variation from background
        color_variation = randint(-20, 20)
        shape_color = (
            min(255, max(0, target_color[0] + color_variation)),
            min(255, max(0, target_color[1] + color_variation)),
            min(255, max(0, target_color[2] + color_variation)),
            opacity
        )
        
        if shape == 'rectangle':
            angle = randint(0, 45)
            draw.rectangle(
                [x, y, x + size, y + size],
                fill=shape_color,
                outline=None
            )
        else:  # circle
            draw.ellipse(
                [x, y, x + size, y + size],
                fill=shape_color,
                outline=None
            )
    
    # Add some small dots for texture
    for _ in range(100):
        x = randint(0, width)
        y = randint(0, height)
        size = randint(1, 3)
        opacity = randint(20, 40)
        draw.ellipse(
            [x, y, x + size, y + size],
            fill=(255, 255, 255, opacity),
            outline=None
        )
    
    return image

# Generate and save the image
hero_image = generate_hero_image()
# Convert to RGB before saving as JPG
hero_image = hero_image.convert('RGB')
hero_image.save('assets/dsa-hero.jpg', quality=95) 