from perception.vision import BlipVision

vision = BlipVision()

caption = vision.describe("data/sample_image.jpg")
print("\n===== IMAGE CAPTION =====\n")
print(caption)

