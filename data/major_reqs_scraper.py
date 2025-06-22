import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import unquote, urlparse, parse_qs

def parse_major_required_courses(url):
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    valid_sections = [
        "Lower Division Requirements",
        "Upper Division Requirements",
        "Prerequisites",
        "Upper Division Requirements (Nine Courses)",
        "Lower Division Prerequisites",
        "Principles and techniques of data science"
    ]
    stop_after = "Upper Division Requirements"

    course_list = []
    all_tags = soup.find_all(["h2", "h3", "h4", "table"])
    current_req = None

    for tag in all_tags:
        if tag.name in ["h2", "h3", "h4"]:
            heading = tag.get_text(strip=True)
            if heading in valid_sections:
                current_req = heading
            elif current_req == stop_after:
                break  # Stop after Upper Division Requirements
        elif tag.name == "table" and current_req:
            for row in tag.find_all("tr")[1:]:  # skip header
                cells = row.find_all("td")
                if cells:
                    link = cells[0].find("a")
                    if link and "href" in link.attrs:
                        href = link["href"]
                        parsed_url = urlparse(href)
                        query = parse_qs(parsed_url.query)
                        course_code = unquote(query.get("P", [""])[0]).strip()
                        if course_code:
                            course_list.append(course_code)

    return course_list

if __name__ == "__main__":
    url = "https://guide.berkeley.edu/undergraduate/degree-programs/computer-science/#majorrequirementstext"
    parsed = parse_major_required_courses(url)
    with open("major_requirements.json", "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2)
    print(json.dumps(parsed, indent=2))
