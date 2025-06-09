from PIL import Image, ImageDraw

# Create a new image with a white background
size = (64, 64)
image = Image.new('RGB', size, 'white')
draw = ImageDraw.Draw(image)

# Draw a blue rectangle
draw.rectangle([(10, 10), (54, 54)], fill='blue')

# Draw "DS" text in white
draw.text((20, 25), "DS", fill='white')

# Save the icon
image.save('icon.png') 