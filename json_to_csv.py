import pandas as pd


df = pd.read_json('berkeley_courses_2025_fall.json')
df.to_csv('courses.csv', index=False)
