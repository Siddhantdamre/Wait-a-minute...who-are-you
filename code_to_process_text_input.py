from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline, Seq2SeqTrainer, Seq2SeqTrainingArguments
from datasets import load_dataset, Dataset
import pandas as pd
import json

# ----------------------------
# Step 1: Prepare the ARC Dataset
# ----------------------------
print("Loading ARC dataset...")
dataset = load_dataset("ai2_arc", "challenge")

train_data = [
    {
        "input": f"Context: Choices: {', '.join(sample['choices'])}\nQuestion: {sample['question']}",
        "output": sample["answer"]
    }
    for sample in dataset['train']
]

with open("arc_finetuning.json", "w") as f:
    json.dump(train_data, f)
print("Dataset prepared and saved as arc_finetuning.json")

# ----------------------------
# Step 2: Fine-Tune the Model
# ----------------------------
print("Loading model and tokenizer...")
model_name = "t5-large"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

print("Preprocessing training data...")
train_df = pd.DataFrame(train_data)

def preprocess(data):
    return tokenizer(
        data["input"],
        text_pair=data["output"],
        truncation=True,
        padding="max_length",
        max_length=512
    )

train_dataset = Dataset.from_pandas(train_df)
train_dataset = train_dataset.map(preprocess, batched=True)

print("Setting up training arguments...")
training_args = Seq2SeqTrainingArguments(
    output_dir="./finetuned_model",
    evaluation_strategy="epoch",
    learning_rate=5e-5,
    per_device_train_batch_size=4,
    num_train_epochs=3,
    save_strategy="epoch",
    logging_dir="./logs",
    logging_steps=10
)

print("Initializing trainer...")
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset
)

print("Starting fine-tuning...")
trainer.train()
print("Fine-tuning complete! Model saved in ./finetuned_model")

# ----------------------------
# Step 3: Enhanced Reasoning with Ambiguity Handling
# ----------------------------
print("Loading fine-tuned model...")
reasoning_pipeline = pipeline("text2text-generation", model="./finetuned_model")

def generate_cot_with_ambiguity_examples(context, question):
    examples = """
    Example 1:
    Context: Choices: [Steel, Aluminum, Copper, Gold]
    Question: Which material is best for making electric wires?
    Step 1: Wire materials need to be conductive and affordable.
    Step 2: Copper is more affordable than gold and highly conductive.
    Step 3: The best material for electric wires is Copper.
    Answer: Copper

    Example 2:
    Context: Choices: [Shark, Whale, Dolphin, Turtle]
    Question: Which is a mammal?
    Step 1: Mammals give birth to live young and nurse them.
    Step 2: Whales and dolphins are mammals, but sharks and turtles are not.
    Step 3: Dolphin is a mammal.
    Answer: Dolphin
    """
    prompt = f"{examples}\nContext: {context}\nQuestion: {question}\nAnswer step-by-step:"
    response = reasoning_pipeline(prompt, max_length=1024)
    return response[0]['generated_text']

# ----------------------------
# Step 4: Evaluate and Collect Feedback
# ----------------------------
print("Evaluating the model...")
incorrect_samples = []

def evaluate_model(dataset):
    correct = 0
    total = len(dataset['test'])

    print("Starting evaluation...")
    for sample in dataset['test'][:50]:  # Evaluate on a small subset for speed
        context = f"Choices: {', '.join(sample['choices'])}"
        question = sample['question']
        true_answer = sample['answer']

        response = generate_cot_with_ambiguity_examples(context, question)

        if true_answer in response:
            correct += 1
        else:
            incorrect_samples.append({
                "context": context,
                "question": question,
                "model_answer": response,
                "true_answer": true_answer
            })

    accuracy = (correct / total) * 100
    print(f"Model Accuracy: {accuracy:.2f}%")
    return accuracy

accuracy = evaluate_model(dataset)

# ----------------------------
# Step 5: Fine-Tune with Feedback Data
# ----------------------------
print("Processing incorrect samples for feedback...")
feedback_data = [
    {
        "input": f"Context: {sample['context']}\nQuestion: {sample['question']}",
        "output": sample['true_answer']
    }
    for sample in incorrect_samples
]

with open("feedback_data.json", "w") as f:
    json.dump(feedback_data, f)

print("Feedback data saved. Re-run fine-tuning with feedback_data.json to improve further.")
