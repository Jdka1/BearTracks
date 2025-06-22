import requests
import time
import json
import os

url = 'https://berkeleytime.com/api/graphql'

headers = {
    'accept': '*/*',
    'accept-language': 'en-US,en;q=0.9',
    'content-type': 'application/json',
    'origin': 'https://berkeleytime.com',
    'referer': 'https://berkeleytime.com/scheduler/new',
    'sec-ch-ua': '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
    'cookie': '_ga=GA1.2.1259891995.1750541637; _gid=GA1.2.1908279898.1750541637; csrftoken=VOwoOk3uSyeiltDgVXkrxsmimEZ21L9tLpD0O9mRPHfFYnhE17EWLtZNuj28Gcky; _gat=1; _ga_YD3VKZFFC9=GS2.2.s1750544581$o2$g1$t1750545446$j60$l0$h0; csrftoken=VOwoOk3uSyeiltDgVXkrxsmimEZ21L9tLpD0O9mRPHfFYnhE17EWLtZNuj28Gcky'
}

graphql_query = """
query GetCoursesForFilter(
  $playlists: String!,
  $year: String!,
  $semester: String!,
  $first: Int!,
  $after: String
) {
  allCourses(inPlaylists: $playlists, first: $first, after: $after) {
    pageInfo {
      endCursor
      hasNextPage
    }
    edges {
      node {
        ...SchedulerCourse
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment SchedulerCourse on CourseType {
  id
  title
  units
  waitlisted
  openSeats
  enrolled
  enrolledMax
  courseNumber
  department
  description
  abbreviation
  sectionSet(isPrimary: true, year: $year, semester: $semester) {
    edges {
      node {
        ...Lecture
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}

fragment Lecture on SectionType {
  ...Section
  associatedSections {
    edges {
      node {
        ...Section
        __typename
      }
      __typename
    }
    __typename
  }
  __typename
}

fragment Section on SectionType {
  id
  ccn
  kind
  instructor
  startTime
  endTime
  enrolled
  enrolledMax
  locationName
  waitlisted
  waitlistedMax
  days
  wordDays
  disabled
  sectionNumber
  isPrimary
  __typename
}
"""


output_file = "berkeley_courses_2025_fall.json"
buffer = []
cursor = None
course_count = 0
chunk_size = 500

# Remove old file if it exists
if os.path.exists(output_file):
    os.remove(output_file)

# Start the JSON array
with open(output_file, "w", encoding="utf-8") as f:
    f.write("[\n")

def flush_buffer(buffer, first=False, last=False):
    mode = "a"
    with open(output_file, mode, encoding="utf-8") as f:
        for i, course in enumerate(buffer):
            json.dump(course, f, ensure_ascii=False, indent=2)
            # Comma at the end unless it's the very last course
            if not last or i < len(buffer) - 1:
                f.write(",\n")
            else:
                f.write("\n")

while True:
    variables = {
        "playlists": "UGxheWxpc3RUeXBlOjMyNTcz",
        "year": "2025",
        "semester": "fall",
        "first": 50,
        "after": cursor
    }

    response = requests.post(url, json={"query": graphql_query, "variables": variables}, headers=headers)

    if response.status_code != 200:
        print(f"❌ Request failed with status code {response.status_code}")
        print(response.text)
        break

    data = response.json()
    edges = data["data"]["allCourses"]["edges"]
    page_info = data["data"]["allCourses"]["pageInfo"]

    for edge in edges:
        buffer.append(edge["node"])
        course_count += 1

        # Flush every 500
        if len(buffer) >= chunk_size:
            flush_buffer(buffer)
            buffer = []

    print(f"✅ Fetched {course_count} courses so far...")

    if not page_info["hasNextPage"]:
        break

    cursor = page_info["endCursor"]
    time.sleep(0.5)

# Final flush
if buffer:
    flush_buffer(buffer, last=True)

# Close the JSON array
with open(output_file, "a", encoding="utf-8") as f:
    f.write("]\n")

print(f"\n✅ Export complete: {course_count} courses written to {output_file}")
