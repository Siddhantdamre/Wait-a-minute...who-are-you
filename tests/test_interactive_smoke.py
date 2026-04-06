from core.agent import StoryAgent

agent = StoryAgent()

intent = {"theme": "courage", "region": "Maharashtra"}
context_docs = [{"content": "A village once faced a great danger."}]

# Step 1: Start interactive story
arc, interaction = agent.narrate_interactive(intent, context_docs)

print("\nQUESTION:")
print(interaction.question)
for i, opt in enumerate(interaction.options, 1):
    print(f"{i}. {opt}")

# Step 2: Simulate user choice
user_choice = interaction.options[0]
print("\nUSER CHOICE:", user_choice)

story = agent.continue_after_choice(arc, user_choice)
print("\nFINAL STORY:")
print(story)
