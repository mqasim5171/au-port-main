import pandas as pd

df = pd.read_csv("/Users/macbookair/Documents/au-port/frontend/public/feedback/cleaned_student_feedback.csv")

# Rename columns
df = df.rename(columns={
    "CourseName": "course",
    "Comments": "comment",
    "Sentiment": "sentiment"
})

# Map sentiment to lowercase
df["sentiment"] = df["sentiment"].str.lower()

# Add a dummy batch column (e.g., all 2023 for now)
df["batch"] = 2023

df.to_csv("/Users/macbookair/Documents/au-port/backend/cleaned_student_feedback.csv", index=False)
print("Saved fixed CSV ✅")
