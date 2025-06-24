# disable certificate verification globally
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import os
import sys
import ast
import datetime
import itertools
import random
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import pandas as pd
import regex as re
from flask import Flask, request, jsonify
from flask_cors import CORS
from anthropic import Anthropic
from supabase import create_client, Client

sys.path.insert(1, "./")
import config

# environment config and initialize clients
MODEL_NAME_CHATBOT = "claude-3-haiku-20240307"
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
anthropic_client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

# color printing
RED    = "\033[31m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"

BOLD  = "\033[1m"

RESET  = "\033[0m"

app = Flask(__name__)
CORS(app)  # enable CORS for all routes


"""
    helper that expands day abbreviations to full names
"""
DAY_MAP = {"M": "Monday", "Tu": "Tuesday", "W": "Wednesday", "Th": "Thursday", "F": "Friday"}
def expand_days(days_str):
    return [DAY_MAP.get(ch) for ch in days_str if DAY_MAP.get(ch)]


"""
    get all courses from Supabase db
"""
def get_courses_from_supabase():
    MAX_PER_PAGE = 1000
    all_courses = []
    start = 0

    while True:
        # fetch rows [start … start+999]
        resp = (
            supabase
            .table("Courses")
            .select("*")
            .range(start, start + MAX_PER_PAGE - 1)
            .execute()
        )
        batch = resp.data
        if not batch:
            break

        all_courses.extend(batch)
        # if we got fewer than MAX_PER_PAGE rows, we’re done
        if len(batch) < MAX_PER_PAGE:
            break

        start += MAX_PER_PAGE

    print(f"Fetched {len(all_courses)} total courses")

    return all_courses


"""
    filter courses df to match a list of names (ie, a list of major requirements)
"""
def filter_by_names(df: pd.DataFrame, course_names: list[str]) -> pd.DataFrame:
    filtered_chunks = []

    for course_name in course_names:
        # extract department (letters + spaces before the number)
        dept_match = re.findall(r"(?i)((?:[A-Z]+\s*)+)\d", course_name)
        # extract number (digits + optional trailing letters)
        num_match  = re.findall(r"(?<=\s)(\d+[A-Z]*)", course_name)

        if not dept_match or not num_match:
            # warn and skip malformed names
            # print(f"Warning: '{course_name}' is not in expected format, skipping.")
            continue

        dept   = dept_match[0].strip().upper()
        number = num_match[0].strip().upper()
        # print(f"Filtering for: '{dept}', '{number}'")

        chunk = df[
            (df["abbreviation"].str.upper() == dept) &
            (df["courseNumber"].str.upper() == number)
        ]
        filtered_chunks.append(chunk)

    if not filtered_chunks:
        # no valid names => empty DataFrame with same columns
        return df.iloc[0:0].copy()

    # concatenate, drop duplicate rows, reset index
    result = pd.concat(filtered_chunks, ignore_index=True)
    result = result.drop_duplicates().reset_index(drop=True)
    return result


"""
    create embeddings for courses in a df and store in a Chroma collection
"""
def create_embeddings(
    df: pd.DataFrame,
    id_col: str,
    text_col: str,
    # TODO: add department and class name
    embeddings_dir: str,
    collection_name: str = "courses"
):
    """
    Create or replace a Chroma collection of course embeddings.

    Args:
        df: DataFrame containing at least id_col and text_col
        id_col: name of the column to use as unique identifier
        text_col: name of the column containing text to embed
        department_col: name of the column containing the department
        embeddings_dir: directory for PersistentClient
        collection_name: name of the Chroma collection
    """
    # Initialize embedding function and Chroma client
    embedding_fn = SentenceTransformerEmbeddingFunction()
    client = chromadb.PersistentClient(path=embeddings_dir)

    # Remove existing collection if present
    existing = [col.name for col in client.list_collections()]
    if collection_name in existing:
        client.delete_collection(collection_name)
        # print(f"Deleted existing collection '{collection_name}'.")

    # Create new collection
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_fn
    )

    # Prepare data
    raw_ids = df[id_col].astype(str).tolist()
    # Ensure uniqueness by appending a counter to duplicates
    ids = []
    seen = {}
    for raw_id in raw_ids:
        if raw_id in seen:
            seen[raw_id] += 1
            unique_id = f"{raw_id}_{seen[raw_id]}"
        else:
            seen[raw_id] = 0
            unique_id = raw_id
        ids.append(unique_id)

    texts = df[text_col].astype(str).tolist()
    # Keep original id_col value in metadata
    metadatas = [{id_col: raw_id} for raw_id in raw_ids]

    # Add to Chroma
    collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas
    )
    # print(f"Added {len(ids)} embeddings to collection '{collection_name}'.")


def query_embeddings(
    query_text: str,
    embeddings_dir: str,
    collection_name: str = "courses",
    top_k: int = 5
) -> dict:
    """
    Query the embeddings collection for the most relevant courses.

    Returns a dict with keys 'ids', 'distances'.
    """
    embedding_fn = SentenceTransformerEmbeddingFunction()
    client = chromadb.PersistentClient(path=embeddings_dir)
    collection = client.get_collection(name=collection_name)

    results = collection.query(
        query_texts=[query_text],
        n_results=top_k
    )
    return results


"""

"""
def flatten_sectionSet(df):
    sections_data = []
    for index, row in df.iterrows():
        course_id = row['id']
        section_set = row['sectionSet']

        section_dict = ast.literal_eval(section_set)

        # Check if section_set is a dictionary and has the 'edges' key
        if isinstance(section_dict, dict) and 'edges' in section_set:
            edges = section_dict['edges']
            if isinstance(edges, list):
                for edge in edges:
                    if isinstance(edge, dict) and 'node' in edge:
                        node = edge['node']
                        if isinstance(node, dict):
                            sections_data.append({
                                'course_id': course_id,
                                'wordDays': node.get('wordDays'),
                                'startTime': node.get('startTime'),
                                'endTime': node.get('endTime')
                            })

    return pd.DataFrame(sections_data)


"""
    
"""
def parse_days(word_days):
    if isinstance(word_days, str):
        day_mapping = {
            "M": "Monday", "Tu": "Tuesday", "W": "Wednesday", "Th": "Thursday", "F": "Friday"
        }
        # Split the string by spaces and map each word day
        return [day_mapping[day] for day in day_mapping if day in word_days]
    return []


"""

"""
def parse_time_str(time_str):
    """Parses 'HH:MM' time string into a datetime.time object."""
    if not time_str:
        return None
    # return datetime.datetime.strptime(time_str.split("T")[1], "%H:%M:%S").time()
    return datetime.datetime.strptime(time_str, '%H:%M').time()

def is_time_disallowed(start_time_str, end_time_str, days, disallowed_slots):
    """
    Returns True if [start_time, end_time] on any of the given days overlaps
    a disallowed slot, else False.
    """
    course_start = parse_time_str(start_time_str)
    course_end   = parse_time_str(end_time_str)
    # if course_start is None and course_end is None:
    #     return True  # treat invalid times as disallowed

    for day in days:
        for slot in disallowed_slots.get(day, []):
            dis_start = parse_time_str(slot[0])
            dis_end   = parse_time_str(slot[1])
            if dis_start is None or dis_end is None:
                continue
            # if course_start < dis_end and course_end > dis_start:
            #     return True
            if course_start > dis_start and course_start < dis_end:
                return True
            if course_end > dis_start and course_end < dis_end:
                return True
    return False


"""

"""
def parse_time_str(time_str):
    """Parses 'HH:MM' time string into a datetime.time object."""
    if not time_str:
        return None
    return datetime.datetime.strptime(time_str, '%H:%M').time()

def are_times_overlapping(start_time1_str, end_time1_str, days1, start_time2_str, end_time2_str, days2):
    """
    Checks if two class times overlap.
    Assumes start_time_str and end_time_str are in 'HH:MM' format.
    """
    # Convert time strings to datetime.time objects
    start1 = parse_time_str(start_time1_str)
    end1 = parse_time_str(end_time1_str)
    start2 = parse_time_str(start_time2_str)
    end2 = parse_time_str(end_time2_str)

    # Handle cases with invalid time strings (though filtering should prevent this)
    if start1 is None or end1 is None or start2 is None or end2 is None:
        return False

    # Check for overlapping days first
    common_days = set(days1).intersection(set(days2))
    if not common_days:
        return False # No overlapping days, so no time overlap

    # Check for time overlap on common days
    # Two time intervals [start1, end1] and [start2, end2] overlap if:
    # start1 < end2 AND start2 < end1
    return start1 < end2 and start2 < end1

def find_non_overlapping_combinations(df_times_allowed, num_classes=4):
    """
    Finds combinations of num_classes from df_times_allowed that do not overlap in time.
    Returns a list of lists, where each inner list contains the course_ids of a valid combination.
    """
    # Group sections by course_id
    course_sections = df_times_allowed.groupby('course_id').apply(lambda x: x.to_dict('records'), include_groups=False).to_dict()

    valid_combinations = []

    # Iterate through all combinations of num_classes from the unique course IDs
    all_course_ids = list(course_sections.keys())
    for combo_ids in itertools.combinations(all_course_ids, num_classes):
        # For each combination of courses, we need to check if there exists a selection
        # of one section per course such that no two selected sections overlap.
        
        # Get all possible section combinations for the chosen courses
        sections_for_combo = [course_sections[cid] for cid in combo_ids]
        
        # Iterate through all possible combinations of sections (one from each course)
        # using itertools.product
        for selected_sections in itertools.product(*sections_for_combo):
            # Check if this combination of sections has any time overlaps
            overlap = False
            for i in range(len(selected_sections)):
                for j in range(i + 1, len(selected_sections)):
                    section1 = selected_sections[i]
                    section2 = selected_sections[j]
                    if are_times_overlapping(section1['startTime'], section1['endTime'], section1['days'],
                                             section2['startTime'], section2['endTime'], section2['days']):
                        overlap = True
                        break
                if overlap:
                    break

            # If no overlap found for this selection of sections, this course combination is valid
            if not overlap:
                valid_combinations.append(list(combo_ids))
                # No need to check other section combinations for this set of courses
                break 
                
    return valid_combinations


"""

"""
"""
    parse timing constraints from user input to a dict (see system message for format)
"""
def parse_user_input(text):
    system_message_time = (
        """You are a parser that converts natural‐language scheduling constraints into a Python
        dictionary mapping each day of the week (Monday, Tuesday, …, Sunday) to a list of
        disallowed time ranges. Time ranges must be tuples of two strings in HH:MM 24-hour format.
        Days with no constraints should map to an empty list."""

        """Important:
            - Treat any “on any day” or “every day” rule as applying to all seven days.
            - Also apply any day-specific rules in addition to the global ones.
            - Do not merge or override constraints—if more than one applies to a given day, output them all as separate tuples.
            - Always output exactly one Python dict literal, e.g.:

            {
            "Monday":    [("00:00","09:00")],
            "Tuesday":   [("00:00","09:00")],
            "Wednesday": [("00:00","09:00"),("15:00","23:59")],
            … 
            }"""
        
        """Important: Only output the dict literal - no surrounding text or explanation."""

    )

    system_message_interests = (
        """You are an expert parser.
Given a user's input describing their academic or course interests, extract and return only the areas of interest as a Python list of strings.
Each string should be a concise topic, field, or subject area mentioned by the user.
Do not include any explanation or extra text—output only the Python list literal.

Examples:

Input: "I'm interested in machine learning, data science, and maybe some neuroscience." Output: ["machine learning", "data science", "neuroscience"]

Input: "I'd like to take classes in philosophy or cognitive science." Output: ["philosophy", "cognitive science"]

Input: "Anything related to robotics, AI, or computer vision." Output: ["robotics", "AI", "computer vision"]

Important:

If no interests are found, return an empty list: [].
Do not include any explanation or formatting—just the list."""

    )

    time_resp = anthropic_client.messages.create(
        model=MODEL_NAME_CHATBOT,
        system=system_message_time,
        max_tokens=512,
        messages=[{"role": "user", "content": text}],
    )

    interest_resp = anthropic_client.messages.create(
        model=MODEL_NAME_CHATBOT,
        system=system_message_interests,
        max_tokens=512,
        messages=[{"role": "user", "content": text}],
    )

    reply = time_resp.content[0].text.strip()
    interest_reply = interest_resp.content[0].text.strip()

    # print(f"\nClaude reply for time constraints: {reply}\n")

    return interest_reply, ast.literal_eval(reply)


@app.route('/api/schedule', methods=['POST'])
def generate_schedule():
    """
    (1) Parse request JSON
    (2) Create df from supabase
    (3) Filter courses that fulfil requirements
    (4) Filter courses that match interests
    (5) Filter courses that satisty time constraints
    (6) Create a 4-class schedule
    """

    
    # 1. PARSE REQUEST JSON

    print(RED + BOLD + "\n\n1. Parsing request JSON" + RESET)

    data = request.get_json()
    major = data.get('major', '')
    not_completed = data.get('not_completed', [])
    user_input = data.get('user_input', 'no morning classes')
    num_courses = data.get('num_courses', 4)

    # split user input to find interests --> to query embeddings on interests
    query, time_constraints = parse_user_input(user_input)
    print("User input: '" + user_input + "'")
    print("Parsed query: " + query + "\nParsed time constraints:")
    print(time_constraints)

    
    # 2. CREATE DF FROM SUPABASE

    print(RED + BOLD + "\n\n2. Creating DataFrame from Supabase" + RESET)

    df = pd.DataFrame(get_courses_from_supabase())

    
    # 3. FILTER COURSES THAT FULFILL REQUIREMENTS

    print(RED + BOLD + "\n\n3. Filtering courses based on requirements" + RESET)

    df_filtered_names = filter_by_names(df, not_completed)
    print(f"Filtered {len(df_filtered_names)} courses based on names: {not_completed}")

    
    # 4. FILTER COURSES THAT MATCH INTERESTS

    print(RED + BOLD + "\n\n4. Filtering courses based on interests" + RESET)

    # build embeddings
    create_embeddings(df, "id", "description", "./embeddings")

    # query embeddings based on user input
    results = query_embeddings(
        query,
        "./embeddings",
        top_k = 5
    )
    ids = results['ids'][0]
    distances = results['distances'][0]
    
    # save top 5 relevant courses to df_interesting_courses with a new column "embeddingScore"
    top_ids = set(str(i) for i in ids)
    df_interesting_courses = df[df["id"].astype(str).isin(top_ids)].copy()
    id_to_distance = {str(i): dist for i, dist in zip(ids, distances)}
    df_interesting_courses["embeddingScore"] = df_interesting_courses["id"].astype(str).map(id_to_distance)

    print(f"Found {len(df_interesting_courses)} courses matching interests: {query}")
    print("\nTop relevant courses:")
    # print(results)
    for rank, (course_id, dist) in enumerate(zip(ids, distances), start=1):
        # Lookup the course title in df using the course_id
        course_row = df[df["id"].astype(str) == str(course_id)]
        course_title = course_row["title"].iloc[0] if not course_row.empty else "Unknown Title"
        print(f"{rank}. {course_title} (score: {dist:.4f})")


    # 5. FILTER COURSES THAT SATISFY TIME CONSTRAINTS

    print(RED + BOLD + "\n\n5. Filtering courses based on time constraints" + RESET)

    df_filtered_names_times = flatten_sectionSet(df_filtered_names)
    df_filtered_names_times['days'] = df_filtered_names_times['wordDays'].apply(parse_days) # convert 'wordDays' to 'days'

    # drop the original 'wordDays' column
    df_filtered_names_times = df_filtered_names_times.drop(columns=['wordDays'])
    df_filtered_names_times.dropna(inplace=True)
    df_filtered_names_times["startTime"] = df_filtered_names_times["startTime"].apply(lambda x: x.split("T")[1][:-3])
    df_filtered_names_times["endTime"] = df_filtered_names_times["endTime"].apply(lambda x: x.split("T")[1][:-3])

    # do the same for interesting courses
    df_interesting_courses_times = flatten_sectionSet(df_interesting_courses)
    df_interesting_courses_times['days'] = df_interesting_courses_times['wordDays'].apply(parse_days)
    df_interesting_courses_times = df_interesting_courses_times.drop(columns=['wordDays'])
    df_interesting_courses_times.dropna(inplace=True)
    df_interesting_courses_times["startTime"] = df_interesting_courses_times["startTime"].apply(lambda x: x.split("T")[1][:-3])
    df_interesting_courses_times["endTime"] = df_interesting_courses_times["endTime"].apply(lambda x: x.split("T")[1][:-3])

    # parsed_disallowed_slots = {}
    # for line in time_constraints.strip().splitlines():
    #     day, timestr = line.split(':', 1)
    #     try:
    #         parsed_disallowed_slots[day.strip()] = ast.literal_eval(timestr.strip())
    #     except (SyntaxError, ValueError):
    #         print(f"Warning: couldn't parse slots for {day!r}")

    # --- 2) Filter df_times to only those *not* conflicting with disallowed slots --- #
    # df_times must have columns: ['course_id', 'startTime', 'endTime', 'days']
    mask_allowed = ~df_filtered_names_times.apply(
        lambda r: is_time_disallowed(r['startTime'],
                                    r['endTime'],
                                    r['days'],
                                    time_constraints),
        axis=1
    )
    df_filtered_names_times_allowed = df_filtered_names_times[mask_allowed].copy()

    mask_allowed = ~df_interesting_courses_times.apply(
        lambda r: is_time_disallowed(r['startTime'],
                                    r['endTime'],
                                    r['days'],
                                    time_constraints),
        axis=1
    )
    df_interesting_courses_times_allowed = df_interesting_courses_times[mask_allowed].copy()

    # --- 3) Extract the allowed course IDs and filter df_courses --- #
    allowed_ids = df_filtered_names_times_allowed['course_id'].unique().tolist()
    df_filtered_names_times_allowed_original = df[df['id'].isin(allowed_ids)].copy()

    allowed_ids = df_interesting_courses_times_allowed['course_id'].unique().tolist()
    df_interesting_courses_times_allowed_original = df[df['id'].isin(allowed_ids)].copy()

    print(f"Filtered {len(df_filtered_names_times_allowed_original)} required courses based on time constraints:")
    print(df_filtered_names_times_allowed_original[['id', 'abbreviation', 'courseNumber', 'title']])

    print(f"\nFiltered {len(df_interesting_courses_times_allowed_original)} interesting courses based on time constraints:")
    print(df_interesting_courses_times_allowed_original[['id', 'abbreviation', 'courseNumber', 'title']])
    print()


    # 5. FIND NON-OVERLAPPING COMBINATIONS

    # Assuming df_times_allowed is already created and contains the columns:
    # 'course_id', 'startTime', 'endTime', 'days'

    # Concatenate the filtered DataFrames for required and interesting courses
    df_all_filtered_courses = pd.concat(
        [df_filtered_names_times_allowed, df_interesting_courses_times_allowed],
        ignore_index=True
    ).drop_duplicates(subset=['course_id']).reset_index(drop=True)

    # print(f"Total unique courses after combining required and interesting: {len(df_all_filtered_courses)}")
    # print(df_all_filtered_courses[['id', 'abbreviation', 'courseNumber', 'title']])

    # # Find all possible non-overlapping combinations of 4 classes
    # non_overlapping_combos = find_non_overlapping_combinations(df_all_filtered_courses, num_courses)

    # # Prepare detailed course info for each combination
    # detailed_combos = []
    # for combo in non_overlapping_combos[:10]:
    #     combo_details = []
    #     for course_id in combo:
    #         # Find the first matching section for this course_id
    #         section_row = df_all_filtered_courses[df_all_filtered_courses['course_id'] == course_id].iloc[0]
    #         # Find the course-level info
    #         course_row = df[df['id'] == course_id].iloc[0]
    #         combo_details.append({
    #             "name": f"{course_row.get('abbreviation', '')} {course_row.get('courseNumber', '')}",
    #             "department": course_row.get("abbreviation", ""),
    #             "units": course_row.get("units", ""),
    #             "days": " ".join(section_row.get("days", [])),
    #             "startTime": section_row.get("startTime", ""),
    #             "endTime": section_row.get("endTime", ""),
    #             "location": section_row.get("location", ""),
    #             "instructor": section_row.get("instructor", "")
    #         })
    #     detailed_combos.append(combo_details)

    # return jsonify({
    #     "combinations": detailed_combos
    # })

    # return f"Found {len(non_overlapping_combos)} non-overlapping combinations of {num_courses} classes:"
    # Print the first few combinations
    # for i, combo in enumerate(non_overlapping_combos[:10]): # Print first 10 for brevity
    #     print(f"Combination {i+1}: {combo}")

    # Find all possible non-overlapping combinations of 4 classes
    non_overlapping_combos = find_non_overlapping_combinations(df_all_filtered_courses, num_courses)

    # If there are more than 100, sample 100 random combinations
    sample_size = min(50, len(non_overlapping_combos))
    sampled_combos = random.sample(non_overlapping_combos, sample_size) if len(non_overlapping_combos) > sample_size else non_overlapping_combos

    # Prepare detailed course info for each sampled combination
    sampled_detailed_combos = []
    for combo in sampled_combos:
        combo_details = []
        for course_id in combo:
            section_row = df_all_filtered_courses[df_all_filtered_courses['course_id'] == course_id].iloc[0]
            course_row = df[df['id'] == course_id].iloc[0]
            combo_details.append({
                "name": f"{course_row.get('abbreviation', '')} {course_row.get('courseNumber', '')}",
                "title": course_row.get("title", ""),
                "department": course_row.get("abbreviation", ""),
                "units": course_row.get("units", ""),
                "description": course_row.get("description", ""),
                "days": " ".join(section_row.get("days", [])),
                "startTime": section_row.get("startTime", ""),
                "endTime": section_row.get("endTime", ""),
                "location": section_row.get("location", ""),
                "instructor": section_row.get("instructor", "")
            })
        sampled_detailed_combos.append(combo_details)

    # Compose a prompt for Anthropic to select the best 10 schedules
    anthropic_prompt = (
    "You are an expert academic advisor. Given the following 50 possible 4-class schedules, "
    "choose the 4 best schedules that provide a balance between technical classes, major requirements, "
    "and the user's stated interests. Each schedule is a list of course dicts with keys: "
    "name, title, department, units, description, days, startTime, endTime, location, instructor.\n\n"
    "IMPORTANT: ALWAYS INCLUDE AT LEAST ONE NON-TECHNICAL CLASS THAT IS RELATED TO HUMANITIES/SOCIAL SCIENCES.\n"
    "Return ONLY a valid Python list of the 4 best schedules (each schedule is a list of course dicts), "
    "MAKE SURE TO ENCLOSE all list and dict fields in double quotes (\" ... \"). "
    "DO NOT include any explanation, markdown, or extra text—just the Python list literal.\n\n"
    "EXAMPLE OUTPUT:\n"
    "[\n"
    "  [\n"
    """    {"name": "CS61A", "title": "Structure and Interpretation of Computer Programs", "department": "CS", "units": 4, "description": "...", "days": "Monday Wednesday Friday", "startTime": "10:00", "endTime": "11:00", "location": "201 Soda", "instructor": "John Smith"},\n"""
    """    {"name": "HIST7B", "title": "The United States from Civil War to Present", "department": "HIST", "units": 4, "description": "...", "days": "Tuesday Thursday", "startTime": "13:00", "endTime": "14:30", "location": "155 Dwinelle", "instructor": "Jane Doe"},\n"""
    "    ...\n"
    "  ],\n"
    "  ...\n"
    "]\n"
    "IMPORTANT: Only output the Python list literal containing ONLY FOUR SCHEDULES as shown above—no explanation, no markdown, no extra text."
)

    text = (f"User's interests: {query}\n\n"
        "Schedules:\n"
        f"{sampled_detailed_combos}\n\n")

    # Call Anthropic API to select the best 10 schedules
    advisor_resp = anthropic_client.messages.create(
        model=MODEL_NAME_CHATBOT,
        system=anthropic_prompt,
        max_tokens=4096,
        messages=[{"role": "user", "content": text}],
    )
    advisor_reply = advisor_resp.content[0].text.strip()

    # print("\n\n")
    # print(advisor_reply)
    # print("\n\n")

    # Safely evaluate the returned list of schedules
    try:
        best_schedules = ast.literal_eval(advisor_reply)
    except Exception as e:
        # print("Anthropic API returned invalid Python. Returning random sample instead.")
        best_schedules = sampled_detailed_combos[:4]

    return jsonify({
        "combinations": best_schedules
    })


if __name__ == "__main__":
    # listen on 0.0.0.0:5000, reload on change
    app.run(host="0.0.0.0", port=5000, debug=True)