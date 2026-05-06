import pandas as pd
from textblob import TextBlob
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from tqdm import tqdm

tqdm.pandas()  # enable progress_apply

# ------------------------
# 1. Load Data
# ------------------------
print("📂 Loading data...")
df = pd.read_csv("../public/feedback/student-qec-reviews.csv")

# Clean comments
df['Comments'] = df['Comments'].astype(str).str.strip()
df.dropna(subset=['Comments'], inplace=True)

print(f"✅ Loaded {len(df)} comments for processing.\n")

# ------------------------
# 2. Sentiment Analysis
# ------------------------
print("📝 Analyzing sentiment...")
def get_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.1:
        return "Positive"
    elif polarity < -0.1:
        return "Negative"
    else:
        return "Neutral"

df['Sentiment'] = df['Comments'].progress_apply(get_sentiment)
print("✅ Sentiment analysis complete.\n")

# ------------------------
# 3. Emotion Detection
# ------------------------
print("😊 Detecting emotions...")
emotion_classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    return_all_scores=False
)

df['Emotion'] = df['Comments'].progress_apply(
    lambda x: emotion_classifier(x[:512])[0]['label']
)
print("✅ Emotion detection complete.\n")

# ------------------------
# 4. Topic Modeling with BERTopic
# ------------------------
print("🔎 Extracting topics with BERTopic...")
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
topic_model = BERTopic(embedding_model=embedding_model, verbose=True)

topics, probs = topic_model.fit_transform(df['Comments'].tolist())
df['Topic'] = topics

# Save topic info separately
topic_info = topic_model.get_topic_info()
topic_info.to_csv("../public/feedback/topic_summary.csv", index=False)

print("✅ Topic modeling complete.\n")

# ------------------------
# 5. Save Final Cleaned Data
# ------------------------
output_file = "../public/feedback/cleaned_student_feedback.csv"
df.to_csv(output_file, index=False)

print(f"🎉 All tasks complete!")
print(f"📊 Cleaned data saved as {output_file}")
print("📊 Topic summary saved as topic_summary.csv")
