from backend.image_gen import generate_quote_image
import traceback

try:
    print("Testing generate_quote_image directly...")
    bio = generate_quote_image("Test Quote", "Test Author", "philosophical")
    print(f"Success! Bio size: {len(bio.getvalue())}")
except Exception as e:
    print("Failed!")
    traceback.print_exc()
