from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()

previous_id = None

print("Gemini Chatbot")
print("Type 'exit' to stop.\n")

while True:
    user_input = input("You: ")

    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    if previous_id is None:
        interaction = client.interactions.create(
            model="gemini-3.5-flash",
            input=user_input
        )
    else:
        interaction = client.interactions.create(
            model="gemini-3.5-flash",
            input=user_input,
            previous_interaction_id=previous_id
        )

    print("Gemini:", interaction.output_text)
    print()

    previous_id = interaction.id