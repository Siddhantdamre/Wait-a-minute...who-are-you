from transformers import AutoModelForQuestionAnswering, AutoTokenizer, Trainer, TrainingArguments
from datasets import load_dataset

# Load dataset
dataset = load_dataset("path_to_your_squad_format_dataset")

# Load model and tokenizer
model_name = "bert-large-uncased"
model = AutoModelForQuestionAnswering.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Tokenize dataset
def preprocess_function(examples):
    return tokenizer(
        examples["question"], examples["context"], truncation=True, padding="max_length", max_length=384
    )
tokenized_datasets = dataset.map(preprocess_function, batched=True)

# Define training arguments
training_args = TrainingArguments(
    output_dir="./results",
    evaluation_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
)

# Train the model
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets["train"],
    eval_dataset=tokenized_datasets["validation"],
)
trainer.train()

# Save the fine-tuned model
model.save_pretrained("./fine_tuned_model")
tokenizer.save_pretrained("./fine_tuned_model")

def handle_ambiguity(input_text, question):
    answers = qa_pipeline(question=question, context=input_text, topk=3)  # Top 3 answers
    if len(answers) > 1:
        print("The input is ambiguous. Here are possible answers:")
        for i, answer in enumerate(answers):
            print(f"{i+1}: {answer['answer']} (Confidence: {answer['score']:.2f})")
        user_choice = int(input("Select the most appropriate answer (1/2/3): "))
        return answers[user_choice - 1]['answer']
    return answers[0]['answer']

from transformers import pipeline

reasoning_pipeline = pipeline("text2text-generation", model="gpt-3.5-turbo")

def generate_reasoning_chain(question, context):
    prompt = (
        f"Context: {context}\n"
        f"Question: {question}\n"
        f"Provide a detailed reasoning chain before answering the question:"
    )
    reasoning = reasoning_pipeline(prompt, max_length=512, num_return_sequences=1)
    return reasoning[0]['generated_text']

# Example usage
context = "John Doe visited New York City on January 15, 2023."
question = "Who visited New York City?"
reasoning_chain = generate_reasoning_chain(question, context)
print(reasoning_chain)

